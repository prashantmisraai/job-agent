"""Human-in-the-loop apply assistant helpers."""

from __future__ import annotations

import re
from typing import Dict, List
from urllib.parse import urlparse


AUTO_APPLY_FRIENDLY = {
    "greenhouse.io": "Best candidate for assisted auto-fill. Usually simple forms and resume upload.",
    "lever.co": "Best candidate for assisted auto-fill. Usually simple forms and resume upload.",
    "ashbyhq.com": "Good candidate for assisted auto-fill. Forms are structured and predictable.",
    "smartrecruiters.com": "Good candidate for assisted auto-fill, but review custom questions carefully.",
    "workable.com": "Good candidate for assisted auto-fill, with final review recommended.",
}

ASSISTED_ONLY = {
    "linkedin.com": "Use guided mode only. LinkedIn may block automation and can restrict accounts.",
    "naukri.com": "Use guided mode only. Naukri often has OTP/CAPTCHA/profile prompts.",
    "workdayjobs.com": "Use guided mode. Workday forms vary heavily by company and often require accounts.",
    "myworkdayjobs.com": "Use guided mode. Workday forms vary heavily by company and often require accounts.",
    "indeed.com": "Use guided mode. Indeed can add screening questions and anti-automation checks.",
}


def classify_apply_site(url: str) -> Dict[str, str]:
    host = urlparse(url).netloc.lower().replace("www.", "")
    for domain, note in AUTO_APPLY_FRIENDLY.items():
        if domain in host:
            return {"level": "auto_fill_friendly", "label": "Auto-fill friendly", "note": note}
    for domain, note in ASSISTED_ONLY.items():
        if domain in host:
            return {"level": "assisted_only", "label": "Guided apply only", "note": note}
    return {
        "level": "manual_review",
        "label": "Manual review",
        "note": "Unknown ATS. Use guided mode and verify every field before submitting.",
    }


def extract_candidate_fields(resume_text: str) -> Dict[str, str]:
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", resume_text)
    phone = re.search(r"(\+?\d[\d\s().-]{8,}\d)", resume_text)
    linkedin = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?", resume_text)
    github = re.search(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+/?", resume_text)

    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    name = lines[0] if lines else ""
    location = ""
    for line in lines[:8]:
        if any(city in line.lower() for city in ("bengaluru", "bangalore", "pune", "hyderabad", "delhi", "mumbai", "remote")):
            location = line.split("|")[-1].strip()
            break

    return {
        "full_name": name,
        "email": email.group(0) if email else "",
        "phone": phone.group(0).strip() if phone else "",
        "linkedin": linkedin.group(0) if linkedin else "",
        "github": github.group(0) if github else "",
        "location": location,
    }


def suggested_auto_apply_sites() -> List[str]:
    return [
        "Greenhouse",
        "Lever",
        "Ashby",
        "SmartRecruiters",
        "Workable",
    ]

