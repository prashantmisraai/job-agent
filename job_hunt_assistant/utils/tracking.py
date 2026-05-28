"""Output and application tracking helpers."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import COVER_LETTERS_DIR, DATA_DIR


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")
    return "_".join(part for part in cleaned.split("_") if part)[:80] or "cover_letter"


def save_cover_letter_file(cover_letter_text: str, job_title: str = "job", agency: str = "company") -> Path:
    COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{_safe_slug(job_title)}_{_safe_slug(agency)}.txt"
    output_path = COVER_LETTERS_DIR / filename
    output_path.write_text(cover_letter_text.strip() + "\n", encoding="utf-8")
    return output_path


def log_application(
    job_title: str,
    agency: str,
    resume_summary: str,
    source: Optional[str] = None,
    status: str = "GENERATED",
    apply_url: str = "",
    resume_path: str = "",
    job_id: str = "",
    notes: str = "",
) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DATA_DIR / "applications_log.csv"
    is_new = not log_path.exists()

    with log_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "timestamp",
                "job_title",
                "agency",
                "source",
                "status",
                "job_id",
                "apply_url",
                "resume_path",
                "resume_summary",
                "notes",
            ],
        )
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "job_title": job_title,
                "agency": agency,
                "source": source or "",
                "status": status,
                "job_id": job_id,
                "apply_url": apply_url,
                "resume_path": resume_path,
                "resume_summary": " ".join(resume_summary.split()),
                "notes": " ".join(notes.split()),
            }
        )

    return log_path
