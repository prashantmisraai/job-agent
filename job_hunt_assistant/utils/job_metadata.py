"""Helpers for extracting job metadata from scraped postings."""

from __future__ import annotations

import re
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse


JOB_ID_KEYS = ("job_id", "jobId", "id", "currentJobId", "jk", "gh_jid", "lever-origin")


def extract_job_id(job_data: Dict[str, Any]) -> str:
    for key in JOB_ID_KEYS:
        value = job_data.get(key)
        if value:
            return str(value)

    url = str(job_data.get("url", ""))
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in JOB_ID_KEYS:
        if query.get(key):
            return query[key][0]

    patterns = [
        r"currentJobId=(\d+)",
        r"/jobs/view/(\d+)",
        r"/job/(\d+)",
        r"/j/([A-Za-z0-9_-]+)",
        r"gh_jid=(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    text = " ".join(str(job_data.get(key, "")) for key in ("title", "summary", "description"))
    match = re.search(r"\b(?:job\s*id|requisition|req(?:uisition)?\s*id)[:#\s-]*([A-Za-z0-9_-]+)", text, re.I)
    return match.group(1) if match else ""

