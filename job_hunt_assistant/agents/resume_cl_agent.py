"""CrewAI agent for tailored resume summaries and cover letters."""

from __future__ import annotations

from pathlib import Path

from crewai import Agent, Task

try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: F401
except ImportError:  # pragma: no cover - optional provider dependency
    ChatGoogleGenerativeAI = None

from job_hunt_assistant.utils.config import BASE_DIR, groq_API_KEY
from job_hunt_assistant.utils.llm import get_crewai_llm


llm = get_crewai_llm(temperature=0.35)


def get_resume_cl_agent() -> Agent:
    return Agent(
        role="Resume and Cover Letter Specialist",
        goal="Create targeted application materials that align a candidate with a specific role.",
        backstory=(
            "You are an expert career writer who turns job requirements and candidate "
            "experience into concise, credible, role-specific resume summaries and cover letters."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_resume_cl_task(agent: Agent, job_summary: str, resume_text: str) -> Task:
    output_path = Path(BASE_DIR) / "data" / "resume_agent_output.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    return Task(
        description=(
            "Use the job summary and candidate resume below to create tailored application content.\n\n"
            f"JOB SUMMARY:\n{job_summary}\n\n"
            f"CANDIDATE RESUME:\n{resume_text}\n\n"
            "Create a genuinely tailored application package. Rewrite the resume as a complete, polished resume "
            "using the candidate's existing resume as the factual base. Do not label it as targeted, tailored, "
            "optimized, original, or ATS keyword alignment. Do not append keyword-stuffing sections.\n\n"
            "Resume tailoring rules:\n"
            "- Keep the candidate's identity, employers, dates, education, and certifications factual.\n"
            "- Rewrite the professional summary for this exact role and company.\n"
            "- Reorder and refine skills so the most relevant technologies appear first.\n"
            "- Rewrite experience bullets to foreground relevant achievements, architecture, scale, metrics, "
            "ML/software/platform work, content/search/recommendation relevance, and production impact.\n"
            "- Use metrics already present in the resume when possible. If a bullet clearly needs a metric but "
            "the base resume does not provide one, make the bullet stronger without inventing a number.\n"
            "- Add job-relevant technologies only when they are already present or strongly supported by adjacent "
            "experience in the original resume. Never invent employment history, degrees, publications, or fake metrics.\n"
            "- Remove target-role lists and generic statements that are not useful for the selected job.\n\n"
            "Output exactly three labeled sections using these markers:\n"
            "<<TAILORED_RESUME>>\n"
            "Write the full resume here. Start with the candidate name and contact line. Include normal resume "
            "sections such as Professional Summary, Core Technical Skills, Professional Experience, Technical "
            "Projects, Technical Writing, Education, and Certifications where appropriate.\n\n"
            "<<RESUME_SUMMARY>>\n"
            "Write the rewritten professional summary only.\n\n"
            "<<COVER_LETTER>>\n"
            "Write a professional, personalized cover letter suitable for this job. "
            "Keep it concise, specific, and grounded in the resume."
        ),
        expected_output=(
            "A full tailored resume, a resume summary, and a cover letter with markers "
            "<<TAILORED_RESUME>>, <<RESUME_SUMMARY>>, and <<COVER_LETTER>>."
        ),
        agent=agent,
        output_file=str(output_path),
    )
