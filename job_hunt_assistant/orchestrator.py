"""CrewAI orchestration for the job hunt assistant."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from job_hunt_assistant.scrapers_api import fetch_scrapper_jobs
from job_hunt_assistant.utils.config import BASE_DIR
from job_hunt_assistant.utils.job_metadata import extract_job_id
from job_hunt_assistant.utils.resume_optimizer import build_optimized_resume_text, save_optimized_resume_docx
from job_hunt_assistant.utils.tracking import log_application, save_cover_letter_file


def load_resume(path: Optional[Path] = None) -> str:
    resume_path = path or (Path(BASE_DIR) / "data" / "sample_resume.txt")
    if not resume_path.exists():
        return ""
    return resume_path.read_text(encoding="utf-8")


def extract_between_markers(text: str, start_marker: str, end_marker: Optional[str] = None) -> str:
    if not text:
        return ""

    start_index = text.find(start_marker)
    if start_index == -1:
        return ""

    start_index += len(start_marker)
    end_index = text.find(end_marker, start_index) if end_marker else len(text)
    if end_index == -1:
        end_index = len(text)

    return text[start_index:end_index].strip()


def _task_output_text(task: Any) -> str:
    output = getattr(task, "output", None)
    if output is None:
        return ""
    raw = getattr(output, "raw", None)
    if raw:
        return str(raw)
    return str(output)


def run_pipeline(
    job_data: Dict[str, Any],
    resume_text: str,
    user_bio: str,
    log_immediately: bool = True,
) -> Dict[str, Any]:
    """Run all agents for one selected job posting.

    Args:
        job_data: A job dictionary with title, agency, summary, source, and optional url.
        resume_text: Candidate resume text from the UI or local sample file.
        user_bio: Candidate bio for outreach personalization.
    """

    if job_data.get("result_type") == "career_search":
        raise ValueError(
            "This is a company career-page search target, not a specific job posting. "
            "Open the careers link, choose a real job, then run the assistant on that posting."
        )

    job_title = job_data.get("title", "Selected Role")
    agency_name = job_data.get("agency", "Selected Company")
    job_summary = job_data.get("summary", "")
    job_id = extract_job_id(job_data)

    try:
        from crewai import Crew, Process

        from job_hunt_assistant.agents.jd_analyst import (
            create_jd_analysis_task,
            get_jd_analyst_agent,
        )
        from job_hunt_assistant.agents.messaging_agent import (
            create_messaging_task,
            get_messaging_agent,
        )
        from job_hunt_assistant.agents.resume_cl_agent import (
            create_resume_cl_task,
            get_resume_cl_agent,
        )
    except ImportError as exc:
        raise RuntimeError(
            "CrewAI dependencies are not installed. Install them with "
            "`pip install -r job_hunt_assistant/requirements.txt` before running the pipeline."
        ) from exc

    jd_agent = get_jd_analyst_agent()
    resume_agent = get_resume_cl_agent()
    messaging_agent = get_messaging_agent()

    jd_task = create_jd_analysis_task(jd_agent, job_summary)
    resume_task = create_resume_cl_task(resume_agent, job_summary, resume_text)
    messaging_task = create_messaging_task(
        messaging_agent,
        job_summary,
        agency_name,
        user_bio,
        job_title=job_title,
        job_id=job_id,
    )

    crew = Crew(
        agents=[jd_agent, resume_agent, messaging_agent],
        tasks=[jd_task, resume_task, messaging_task],
        process=Process.sequential,
        verbose=True,
    )

    final_result = crew.kickoff()
    resume_output = _task_output_text(resume_task)
    tailored_resume_text = extract_between_markers(
        resume_output,
        "<<TAILORED_RESUME>>",
        "<<RESUME_SUMMARY>>",
    )
    resume_summary = extract_between_markers(resume_output, "<<RESUME_SUMMARY>>", "<<COVER_LETTER>>")
    cover_letter = extract_between_markers(resume_output, "<<COVER_LETTER>>")
    optimized_resume = build_optimized_resume_text(
        resume_text=resume_text,
        job_data=job_data,
        resume_summary=resume_summary,
        target_score=90,
        tailored_resume_text=tailored_resume_text,
    )
    optimized_resume_path = save_optimized_resume_docx(
        optimized_resume_text=str(optimized_resume["optimized_resume_text"]),
        job_title=job_title,
        agency=agency_name,
    )

    log_path = ""
    if log_immediately:
        log_path = str(
            log_application(
                job_title=job_title,
                agency=agency_name,
                resume_summary=resume_summary,
                source=job_data.get("source"),
                status="GENERATED",
                apply_url=str(job_data.get("url", "")),
                resume_path=str(optimized_resume_path),
                job_id=job_id,
            )
        )
    cover_letter_path = save_cover_letter_file(
        cover_letter_text=cover_letter,
        job_title=job_title,
        agency=agency_name,
    )

    return {
        "job_title": job_title,
        "agency": agency_name,
        "source": job_data.get("source", ""),
        "job_id": job_id,
        "jd_analysis": _task_output_text(jd_task),
        "resume_output": resume_output,
        "outreach_message": _task_output_text(messaging_task),
        "final_result": str(final_result),
        "resume_summary": resume_summary,
        "cover_letter": cover_letter,
        "optimized_resume_text": optimized_resume["optimized_resume_text"],
        "optimized_resume_path": str(optimized_resume_path),
        "projected_ats_score": optimized_resume["projected_ats_score"],
        "projected_confidence_score": optimized_resume["projected_confidence_score"],
        "log_path": log_path,
        "cover_letter_path": str(cover_letter_path),
    }


if __name__ == "__main__":
    sample_job = fetch_scrapper_jobs("business analyst", limit=1)[0]
    sample_resume = load_resume()
    sample_bio = "I'm a data professional passionate about public service and practical automation."
    result = run_pipeline(sample_job, sample_resume, sample_bio)
    print(result["final_result"])
