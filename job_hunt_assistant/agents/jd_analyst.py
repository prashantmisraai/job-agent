"""CrewAI agent that extracts structured insights from a job description."""

from __future__ import annotations

from pathlib import Path

from crewai import Agent, Task

from job_hunt_assistant.utils.config import BASE_DIR, GROQ_API_KEY
from job_hunt_assistant.utils.llm import get_crewai_llm


llm = get_crewai_llm(temperature=0.15)


def get_jd_analyst_agent() -> Agent:
    return Agent(
        role="Job Description Analyst",
        goal="Extract practical job-search intelligence from job descriptions.",
        backstory=(
            "You are a precise recruiting analyst who reads job posts and identifies "
            "the responsibilities, skills, qualifications, and signals a candidate "
            "should target in their application."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_jd_analysis_task(agent: Agent, job_description: str) -> Task:
    output_path = Path(BASE_DIR) / "data" / "report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    return Task(
        description=(
            "Analyze the following job description and extract the details a candidate "
            "needs to tailor an application.\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            "Return structured markdown with these sections:\n"
            "## Role Snapshot\n"
            "## Key Responsibilities\n"
            "## Required Skills\n"
            "## Preferred Qualifications\n"
            "## Resume Keywords\n"
            "## Application Strategy\n"
        ),
        expected_output=(
            "A structured markdown report with concise bullets under each requested heading."
        ),
        agent=agent,
        output_file=str(output_path),
    )

