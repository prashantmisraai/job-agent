"""Streamlit interface for the AI job hunt assistant."""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path

import streamlit as st

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from job_hunt_assistant.orchestrator import load_resume, run_pipeline
from job_hunt_assistant.scrapers_api import fetch_scrapperjobs
from job_hunt_assistant.utils.apply_assistant import (
    classify_apply_site,
    extract_candidate_fields,
    suggested_auto_apply_sites,
)
from job_hunt_assistant.utils.auth import logout_button, require_login
from job_hunt_assistant.utils.resume_parser import extract_resume_text_from_upload
from job_hunt_assistant.utils.scoring import score_jobs
from job_hunt_assistant.utils.tracking import log_application


st.set_page_config(page_title="AI Job Hunt Assistant", page_icon=":briefcase:", layout="wide")

current_user = require_login()

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem; padding-bottom: 3rem;}
    [data-testid="stMetricValue"] {font-size: 1.35rem;}
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {padding-top: .4rem;}
    .app-kicker {color: #52796f; font-weight: 700; letter-spacing: .04em; text-transform: uppercase;}
    .app-title {font-size: 2.2rem; line-height: 1.08; font-weight: 800; margin: .1rem 0 .4rem;}
    .app-subtitle {color: #4b5563; font-size: 1.03rem; max-width: 820px;}
    .soft-note {background: #f7faf9; border: 1px solid #dbe7e2; border-radius: 8px; padding: .75rem .9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

display_name = escape(current_user.display_name or current_user.username)
st.markdown('<div class="app-kicker">Private beta</div>', unsafe_allow_html=True)
st.markdown('<div class="app-title">AI Job Hunt Assistant</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="app-subtitle">Welcome, {display_name}. Find roles, score fit, generate tailored resumes and cover letters, then track every approved application from one focused workspace.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    logout_button()
    st.divider()
    st.header("Search")
    keyword = st.text_input("Job keyword", value="business analyst")
    location = st.text_input("Location", value="Remote")
    min_confidence = st.slider("Minimum confidence score", min_value=0, max_value=100, value=35)

    st.header("Sources")
    linkedin_limit = st.number_input("LinkedIn jobs", min_value=0, max_value=25, value=5, step=1)
    naukri_limit = st.number_input("Naukri jobs", min_value=0, max_value=25, value=5, step=1)
    hirist_limit = st.number_input("Hirist jobs", min_value=0, max_value=25, value=5, step=1)
    company_names = st.text_area(
        "Company names",
        placeholder="Google, Microsoft, Infosys, TCS",
        help="Comma or newline separated. The app creates career-page search links for each company.",
        height=90,
    )
    jobs_per_company = st.number_input("Career searches per company", min_value=1, max_value=3, value=2, step=1)

    with st.expander("Paste a specific job", expanded=False):
        manual_job_title = st.text_input("Job title from career page", placeholder="Senior AI Engineer")
        manual_company = st.text_input("Company from career page", placeholder="Google")
        manual_job_url = st.text_input("Specific job apply URL", placeholder="https://.../jobs/...")
        manual_job_description = st.text_area(
            "Specific job description",
            placeholder="Paste the real JD from the company career page here.",
            height=120,
        )

    st.header("Candidate")
    uploaded_resume = st.file_uploader("Upload resume", type=["txt", "docx", "pdf"])
    default_resume = load_resume()
    resume_from_file = ""
    if uploaded_resume is not None:
        try:
            resume_from_file = extract_resume_text_from_upload(uploaded_resume)
            st.success("Resume extracted.")
        except Exception as exc:
            st.error(str(exc))

    resume_text = st.text_area("Resume text", value=resume_from_file or default_resume, height=260)
    user_bio = st.text_area(
        "Bio",
        value="I'm a data professional passionate about public service and practical automation.",
        height=120,
    )
    st.header("Apply Assistant")
    st.caption("Assisted sites: " + ", ".join(suggested_auto_apply_sites()))

if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "application_packages" not in st.session_state:
    st.session_state.application_packages = []

metric_columns = st.columns(4)
metric_columns[0].metric("Jobs in shortlist", len(st.session_state.jobs))
metric_columns[1].metric("Packages created", len(st.session_state.application_packages))
metric_columns[2].metric("Minimum score", f"{min_confidence}%")
metric_columns[3].metric("Portal limits", int(linkedin_limit + naukri_limit + hirist_limit))

st.markdown(
    '<div class="soft-note">Start with one focused keyword and a real resume. Keep source limits modest, then paste a specific company JD when you want the strongest resume and cover letter output.</div>',
    unsafe_allow_html=True,
)

if st.button("Fetch and Score Jobs", type="primary"):
    companies = [
        company.strip()
        for raw in company_names.replace("\n", ",").split(",")
        if (company := raw.strip())
    ]
    total_limit = int(linkedin_limit + naukri_limit + hirist_limit + len(companies) * jobs_per_company)

    with st.spinner("Fetching and scoring job postings..."):
        jobs = fetch_scrapperjobs(
            keyword=keyword,
            location=location,
            limit=max(total_limit, 1),
            linkedin_limit=int(linkedin_limit),
            naukri_limit=int(naukri_limit),
            hirist_limit=int(hirist_limit),
            companies=companies,
            jobs_per_company=int(jobs_per_company),
        )
        if manual_job_title and manual_company and (manual_job_description or manual_job_url):
            jobs.append(
                {
                    "title": manual_job_title.strip(),
                    "agency": manual_company.strip(),
                    "summary": manual_job_description.strip()
                    or f"Specific company career-page posting for {manual_job_title.strip()} at {manual_company.strip()}.",
                    "source": "Company Careers",
                    "url": manual_job_url.strip(),
                    "result_type": "job",
                }
            )
        scored_jobs = score_jobs(jobs, resume_text, keyword)
        st.session_state.jobs = [
            job
            for job in scored_jobs
            if job.get("result_type") == "career_search"
            or int(job.get("confidence_score", 0)) >= min_confidence
        ]

    st.success(f"Found {len(st.session_state.jobs)} relevant jobs.")

selected_jobs = []
if st.session_state.jobs:
    st.subheader("Ranked Jobs")

    for index, job in enumerate(st.session_state.jobs):
        title = job.get("title", "Untitled Role")
        agency = job.get("agency", "Unknown Company")
        source = job.get("source", "Unknown")
        ats_score = job.get("ats_score", 0)
        confidence = job.get("confidence_score", 0)
        url = job.get("url", "")
        job_id = job.get("job_id", "")

        with st.container(border=True):
            is_career_search = job.get("result_type") == "career_search"
            columns = st.columns([0.06, 0.46, 0.14, 0.14, 0.20])
            if is_career_search:
                columns[0].caption("Open")
            else:
                selected = columns[0].checkbox("Select", key=f"job_select_{index}", label_visibility="collapsed")
            columns[1].markdown(f"**{title}**  \n{agency} | {source}")
            if is_career_search:
                columns[2].caption("Career page")
                columns[3].caption("Choose job first")
            else:
                columns[2].metric("ATS", f"{ats_score}%")
                columns[3].metric("Confidence", f"{confidence}%")
            if url:
                columns[4].link_button("Open Careers" if is_career_search else "Apply", url)
            else:
                columns[4].caption("No direct link")

            if job_id:
                st.caption(f"Job ID: {job_id}")
            if is_career_search:
                st.info("This is a career-page discovery result, not a job description. Open it and choose a specific posting before running AI analysis.")
            else:
                matched = ", ".join(job.get("matched_keywords", [])[:10]) or "No strong keyword overlap yet"
                missing = ", ".join(job.get("missing_keywords", [])[:8]) or "No major missing keywords found"
                st.caption(f"Matched: {matched}")
                st.caption(f"Missing / improve: {missing}")
            st.write(job.get("summary", ""))

            if not is_career_search and selected:
                selected_jobs.append(job)

    if st.button("Apply to Selected Jobs"):
        if not selected_jobs:
            st.warning("Select at least one job first.")
        else:
            for job in selected_jobs:
                title = job.get("title", "Selected Role")
                agency = job.get("agency", "Selected Company")
                st.divider()
                st.subheader(f"{title} at {agency}")
                if job.get("url"):
                    st.link_button("Open Apply Link", str(job["url"]))

                with st.spinner(f"Running agents for {title}..."):
                    try:
                        result = run_pipeline(job, resume_text, user_bio, log_immediately=False)
                    except Exception as exc:
                        st.error(str(exc))
                        st.stop()
                st.session_state.application_packages.append({"job": job, "result": result})

                st.markdown("### JD Analysis")
                st.markdown(result["jd_analysis"] or "_No JD analysis returned._")

                st.markdown("### Resume and Cover Letter")
                st.markdown(result["resume_output"] or "_No resume output returned._")

                st.markdown("### Tailored Resume DOCX")
                score_columns = st.columns(2)
                score_columns[0].metric("Projected ATS", f"{result.get('projected_ats_score', 0)}%")
                score_columns[1].metric("Projected Confidence", f"{result.get('projected_confidence_score', 0)}%")
                st.caption(f"Created: {result['optimized_resume_path']}")

                st.markdown("### Outreach Messages")
                if result.get("job_id"):
                    st.caption(f"Job ID used in outreach: {result['job_id']}")
                st.markdown(result["outreach_message"] or "_No outreach message returned._")

                st.caption("Not logged yet. Use Apply Assistant below after you review and submit.")
                st.caption(f"Cover letter saved to: {result['cover_letter_path']}")

if st.session_state.application_packages:
    st.divider()
    st.subheader("Apply Assistant")
    st.markdown(
        "Open the real apply URL, attach the tailored resume, fill common fields, answer custom questions, "
        "and log only after you submit or approve the application."
    )

    candidate_fields = extract_candidate_fields(resume_text)
    for index, package in enumerate(st.session_state.application_packages):
        job = package["job"]
        result = package["result"]
        title = str(result.get("job_title", job.get("title", "Selected Role")))
        agency = str(result.get("agency", job.get("agency", "Selected Company")))
        apply_url = str(job.get("url", ""))
        site_info = classify_apply_site(apply_url)

        with st.container(border=True):
            st.markdown(f"**{title}**  \n{agency}")
            st.info(f"{site_info['label']}: {site_info['note']}")
            if apply_url:
                st.link_button("Open Real Apply URL", apply_url)
            st.caption(f"Attach tailored resume: {result['optimized_resume_path']}")
            st.caption(f"Use cover letter: {result['cover_letter_path']}")

            with st.expander("Common fields", expanded=True):
                col_left, col_right = st.columns(2)
                full_name = col_left.text_input("Full name", candidate_fields["full_name"], key=f"name_{index}")
                email = col_right.text_input("Email", candidate_fields["email"], key=f"email_{index}")
                phone = col_left.text_input("Phone", candidate_fields["phone"], key=f"phone_{index}")
                location_value = col_right.text_input("Location", candidate_fields["location"], key=f"location_{index}")
                linkedin_value = st.text_input("LinkedIn", candidate_fields["linkedin"], key=f"linkedin_{index}")
                github_value = st.text_input("GitHub / Portfolio", candidate_fields["github"], key=f"github_{index}")

            custom_answers = st.text_area(
                "Custom questions / answers",
                placeholder="Paste screening questions here and write final answers before submitting.",
                height=120,
                key=f"custom_{index}",
            )

            st.markdown("**Final review**")
            opened = st.checkbox("I opened the real apply URL", key=f"opened_{index}")
            attached = st.checkbox("I attached the tailored .docx resume", key=f"attached_{index}")
            fields_checked = st.checkbox("I verified common fields and custom questions", key=f"fields_{index}")
            final_review = st.checkbox("Ready to submit? Yes, I reviewed everything", key=f"review_{index}")
            submitted = st.checkbox("I submitted the application on the external site", key=f"submitted_{index}")

            can_log = opened and attached and fields_checked and final_review and submitted
            if st.button("Log Approved Application", key=f"log_{index}", disabled=not can_log):
                notes = (
                    f"Fields reviewed: name={full_name}, email={email}, phone={phone}, "
                    f"location={location_value}, linkedin={linkedin_value}, github={github_value}. "
                    f"Custom answers: {custom_answers}"
                )
                log_path = log_application(
                    job_title=title,
                    agency=agency,
                    resume_summary=str(result.get("resume_summary", "")),
                    source=str(result.get("source", job.get("source", ""))),
                    status="SUBMITTED",
                    apply_url=apply_url,
                    resume_path=str(result.get("optimized_resume_path", "")),
                    job_id=str(result.get("job_id", "")),
                    notes=notes,
                )
                st.success(f"Application logged: {log_path}")
