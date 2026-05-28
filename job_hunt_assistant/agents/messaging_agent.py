"""CrewAI agent for personalized recruiter outreach messages."""

from __future__ import annotations

from crewai import Agent, Task

try:
    from groq import Groq  # noqa: F401
except ImportError:  # pragma: no cover - optional direct SDK dependency
    Groq = None

from job_hunt_assistant.utils.config import groq_key
from job_hunt_assistant.utils.llm import get_crewai_llm


llm = get_crewai_llm(temperature=0.3)


def get_messaging_agent() -> Agent:
    return Agent(
        role="Recruiter Outreach Writer",
        goal="Write short, personalized outreach notes for hiring managers and recruiters.",
        backstory=(
            "You help job seekers express interest clearly and professionally in a "
            "way that feels human, specific, and easy for a recruiter to respond to."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_messaging_task(
    agent: Agent,
    job_summary: str,
    agency_name: str,
    user_bio: str,
    job_title: str = "",
    job_id: str = "",
) -> Task:
    job_id_line = f"JOB ID: {job_id}\n" if job_id else "JOB ID: Not available\n"
    return Task(
        description=(
            "Write two brief outreach messages for LinkedIn or email.\n\n"
            f"AGENCY OR COMPANY: {agency_name}\n"
            f"JOB TITLE: {job_title or 'Not provided'}\n"
            f"{job_id_line}"
            f"JOB SUMMARY:\n{job_summary}\n\n"
            f"CANDIDATE BIO:\n{user_bio}\n\n"
            "Create exactly two marked sections:\n"
            "<<HIRING_MANAGER_MESSAGE>>\n"
            "A direct message to the hiring manager expressing interest, mentioning the job ID if available, "
            "and connecting the candidate's background to the role.\n\n"
            "<<EMPLOYEE_REFERRAL_MESSAGE>>\n"
            "A message to a current employee asking politely whether they would be open to referring "
            "the candidate or pointing them to the right recruiter. Mention the job ID if available."
        ),
        expected_output=(
            "Two professional outreach messages, each under 150 words, with the requested markers."
        ),
        agent=agent,
    )
