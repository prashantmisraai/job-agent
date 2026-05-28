"""Resume-to-job keyword and ATS-style scoring helpers."""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, Iterable, List


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "you",
    "your",
}


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{1,}", text.lower())
    return [token.strip(".-") for token in tokens if token not in STOPWORDS and len(token) > 2]


def top_keywords(text: str, limit: int = 30) -> List[str]:
    counts = Counter(tokenize(text))
    return [word for word, _ in counts.most_common(limit)]


def _phrase_hits(phrases: Iterable[str], text: str) -> List[str]:
    normalized = text.lower()
    return [phrase for phrase in phrases if phrase and phrase.lower() in normalized]


def score_job(job: Dict[str, str], resume_text: str, search_keyword: str = "") -> Dict[str, object]:
    """Return ATS-style relevance metrics for a job.

    This is intentionally transparent: score is based on keyword overlap,
    title relevance, source/link quality, and search phrase alignment.
    """

    if job.get("result_type") == "career_search":
        enriched = dict(job)
        enriched.update(
            {
                "ats_score": 0,
                "confidence_score": 0,
                "matched_keywords": [],
                "missing_keywords": [],
            }
        )
        return enriched

    job_text = " ".join(
        [
            job.get("title", ""),
            job.get("agency", ""),
            job.get("summary", ""),
            job.get("source", ""),
        ]
    )
    resume_terms = set(top_keywords(resume_text, limit=80))
    job_terms = set(top_keywords(job_text, limit=45))
    matched_terms = sorted(resume_terms & job_terms)
    missing_terms = sorted(job_terms - resume_terms)[:12]

    overlap_score = min(55, int((len(matched_terms) / max(len(job_terms), 1)) * 80))
    keyword_terms = tokenize(search_keyword)
    title_hits = _phrase_hits(keyword_terms, job.get("title", ""))
    body_hits = _phrase_hits(keyword_terms, job_text)
    title_score = 18 if title_hits else 8 if body_hits else 0
    apply_link_score = 12 if job.get("url") else 2
    source_score = 10 if job.get("source") not in {"Fallback Portal", "Company Career Search"} else 5
    summary_score = 5 if len(job.get("summary", "")) > 120 else 0

    score = min(100, overlap_score + title_score + apply_link_score + source_score + summary_score)
    confidence = min(100, int(score * 0.75 + apply_link_score * 1.2 + source_score))

    enriched = dict(job)
    enriched.update(
        {
            "ats_score": score,
            "confidence_score": confidence,
            "matched_keywords": matched_terms[:15],
            "missing_keywords": missing_terms,
        }
    )
    return enriched


def score_jobs(jobs: List[Dict[str, str]], resume_text: str, search_keyword: str = "") -> List[Dict[str, object]]:
    scored = [score_job(job, resume_text, search_keyword) for job in jobs]
    return sorted(scored, key=lambda item: item.get("confidence_score", 0), reverse=True)
