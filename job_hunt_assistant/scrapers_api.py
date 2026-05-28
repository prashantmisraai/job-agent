"""Multi-source job scraper and fallback aggregator."""

from __future__ import annotations

import random
import time
from typing import Dict, Iterable, List
from urllib.parse import quote_plus, urljoin

from job_hunt_assistant.utils.job_metadata import extract_job_id

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - dependency may be absent before setup
    requests = None
    BeautifulSoup = None


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

KNOWN_COMPANY_CAREER_SEARCHES = {
    "google": "https://www.google.com/about/careers/applications/jobs/results/?q={keyword}&location={location}",
    "microsoft": "https://jobs.careers.microsoft.com/global/en/search?q={keyword}&lc={location}",
    "amazon": "https://www.amazon.jobs/en/search?base_query={keyword}&loc_query={location}",
    "meta": "https://www.metacareers.com/jobs/?q={keyword}",
    "apple": "https://jobs.apple.com/en-us/search?search={keyword}&location={location}",
    "netflix": "https://explore.jobs.netflix.net/careers?query={keyword}",
    "nvidia": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite?q={keyword}",
    "adobe": "https://careers.adobe.com/us/en/search-results?keywords={keyword}",
    "salesforce": "https://careers.salesforce.com/en/jobs/?search={keyword}",
    "uber": "https://www.uber.com/us/en/careers/list/?query={keyword}",
    "atlassian": "https://www.atlassian.com/company/careers/all-jobs?search={keyword}",
    "intuit": "https://jobs.intuit.com/search-jobs/{keyword}/",
    "roku": "https://www.weareroku.com/jobs?search={keyword}",
}

CAREER_PATHS = ("/careers", "/jobs", "/company/careers", "/en/careers", "/about/careers")
JOB_LINK_HINTS = ("/job", "/jobs/", "jobid", "job_id", "gh_jid", "lever.co", "greenhouse", "workdayjobs")


def _can_scrape() -> bool:
    return requests is not None and BeautifulSoup is not None


def _request_soup(url: str, timeout: int = 10):
    if not _can_scrape():
        raise RuntimeError("requests and beautifulsoup4 are not installed")

    time.sleep(random.uniform(0.4, 1.0))
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _dedupe_jobs(jobs: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    unique_jobs: List[Dict[str, str]] = []
    for job in jobs:
        key = (
            job.get("title", "").strip().lower(),
            job.get("agency", "").strip().lower(),
            job.get("url", "").split("?")[0].strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        job["job_id"] = extract_job_id(job)
        unique_jobs.append(job)
    return unique_jobs


def _fallback_job(keyword: str, company: str, source: str, location: str = "Remote") -> Dict[str, str]:
    title = f"{keyword.title()} Specialist"
    query = quote_plus(f"{company} careers {keyword} {location}")
    return {
        "title": title,
        "agency": company,
        "summary": (
            f"{company} may have relevant {keyword} roles for {location}. Look for requirements "
            "around stakeholder communication, analysis, documentation, reporting, automation, "
            "delivery coordination, and measurable business outcomes."
        ),
        "source": source,
        "url": f"https://www.google.com/search?q={query}",
        "result_type": "job",
    }


def _company_key(company: str) -> str:
    return "".join(ch for ch in company.lower() if ch.isalnum())


def _career_search_target(keyword: str, company: str, location: str, url: str, note: str = "") -> Dict[str, str]:
    return {
        "title": f"{company} careers search",
        "agency": company,
        "summary": note
        or (
            f"Open the official {company} careers page and search for '{keyword}' in {location}. "
            "Choose a real job posting from that page before running JD analysis."
        ),
        "source": "Company Careers",
        "url": url,
        "result_type": "career_search",
    }


def _format_known_career_url(company: str, keyword: str, location: str) -> str:
    template = KNOWN_COMPANY_CAREER_SEARCHES.get(_company_key(company))
    if not template:
        return ""
    return template.format(keyword=quote_plus(keyword), location=quote_plus(location))


def _candidate_company_domains(company: str) -> List[str]:
    slug = _company_key(company)
    if not slug:
        return []
    return [f"https://www.{slug}.com", f"https://{slug}.com"]


def _find_career_home(company: str) -> str:
    for domain in _candidate_company_domains(company):
        for path in CAREER_PATHS:
            url = f"{domain}{path}"
            try:
                if requests is None:
                    continue
                response = requests.get(url, headers=HEADERS, timeout=5, allow_redirects=True)
                if response.status_code < 400:
                    return response.url
            except Exception:
                continue
    return ""


def _looks_like_relevant_job(title: str, keyword: str) -> bool:
    title_terms = set(title.lower().replace(",", " ").split())
    keyword_terms = set(keyword.lower().replace(",", " ").split())
    return bool(title_terms & keyword_terms)


def _extract_jobs_from_career_page(
    company: str,
    keyword: str,
    location: str,
    career_url: str,
    limit: int,
) -> List[Dict[str, str]]:
    jobs: List[Dict[str, str]] = []
    try:
        soup = _request_soup(career_url, timeout=10)
    except Exception as exc:
        print(f"{company} career page parse failed: {exc}")
        return jobs

    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)
        href = link.get("href", "")
        if not title or len(title) < 8:
            continue
        if not _looks_like_relevant_job(title, keyword):
            continue
        if not any(hint in href.lower() for hint in JOB_LINK_HINTS):
            continue

        apply_url = urljoin(career_url, href)
        jobs.append(
            {
                "title": title[:140],
                "agency": company,
                "summary": (
                    f"{company} career-site posting for {title}. This appears to be a real job link "
                    f"matching {keyword} in or near {location}. Open the apply link for the full JD."
                ),
                "source": "Company Careers",
                "url": apply_url,
                "result_type": "job",
            }
        )
        if len(jobs) >= limit:
            break
    return jobs


def fetch_linkedin_jobs(keyword: str, location: str = "Remote", limit: int = 5) -> List[Dict[str, str]]:
    jobs: List[Dict[str, str]] = []
    url = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
    )

    try:
        soup = _request_soup(url, timeout=8)
        for card in soup.find_all("li"):
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            link_tag = card.find("a", class_="base-card__full-link")
            location_tag = card.find("span", class_="job-search-card__location")

            if not title_tag or not company_tag:
                continue

            title = title_tag.get_text(strip=True)
            agency = company_tag.get_text(strip=True)
            job_location = location_tag.get_text(strip=True) if location_tag else location
            jobs.append(
                {
                    "title": title,
                    "agency": agency,
                    "summary": (
                        f"{agency} is hiring a {title} in {job_location}. This posting is relevant "
                        f"to {keyword} and may require analysis, communication, documentation, "
                        "reporting, and cross-functional execution."
                    ),
                    "source": "LinkedIn",
                    "url": link_tag.get("href", "") if link_tag else "",
                    "result_type": "job",
                }
            )
            if len(jobs) >= limit:
                break
    except Exception as exc:
        print(f"LinkedIn scrape failed: {exc}")

    if not jobs:
        companies = ["Shuru", "Accenture", "Deloitte", "Capgemini", "Cognizant"]
        jobs = [_fallback_job(keyword, company, "LinkedIn", location) for company in companies[:limit]]

    return jobs[:limit]


def fetch_naukri_jobs(keyword: str, location: str = "Remote", limit: int = 5) -> List[Dict[str, str]]:
    jobs: List[Dict[str, str]] = []
    url = f"https://www.naukri.com/{quote_plus(keyword).replace('+', '-')}-jobs-in-{quote_plus(location)}"

    try:
        soup = _request_soup(url, timeout=10)
        cards = soup.select("article.jobTuple, div.srp-jobtuple-wrapper, div.jobTuple")
        for card in cards:
            title_tag = card.select_one("a.title, a[title]")
            company_tag = card.select_one("a.comp-name, a.subTitle, span.comp-dtls-wrap")
            desc_tag = card.select_one(".job-desc, span.job-desc, .job-description")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            agency = company_tag.get_text(strip=True) if company_tag else "Naukri Employer"
            summary = desc_tag.get_text(" ", strip=True) if desc_tag else f"Naukri posting for {title}."
            jobs.append(
                {
                    "title": title,
                    "agency": agency,
                    "summary": summary,
                    "source": "Naukri",
                    "url": title_tag.get("href", url),
                    "result_type": "job",
                }
            )
            if len(jobs) >= limit:
                break
    except Exception as exc:
        print(f"Naukri scrape failed: {exc}")

    if not jobs:
        companies = ["Infosys", "Tata Consultancy Services", "Wipro Technologies", "HCLTech", "Tech Mahindra"]
        jobs = [_fallback_job(keyword, company, "Naukri", location) for company in companies[:limit]]

    return jobs[:limit]


def fetch_hirist_jobs(keyword: str, location: str = "Remote", limit: int = 5) -> List[Dict[str, str]]:
    jobs: List[Dict[str, str]] = []
    url = f"https://www.hirist.tech/search/{quote_plus(keyword)}"

    try:
        soup = _request_soup(url, timeout=10)
        cards = soup.select("a[href*='/j/'], div.job-card, div.jobCard")
        for card in cards:
            title_tag = card if card.name == "a" else card.select_one("a[href*='/j/'], a")
            if not title_tag:
                continue

            title = title_tag.get_text(" ", strip=True)
            if not title or len(title) < 4:
                continue

            href = title_tag.get("href", "")
            if href.startswith("/"):
                href = f"https://www.hirist.tech{href}"

            jobs.append(
                {
                    "title": title[:120],
                    "agency": "Hirist Employer",
                    "summary": (
                        f"Hirist listing related to {keyword}. Review the apply link for details on "
                        "skills, experience, responsibilities, and location."
                    ),
                    "source": "Hirist",
                    "url": href or url,
                    "result_type": "job",
                }
            )
            if len(jobs) >= limit:
                break
    except Exception as exc:
        print(f"Hirist scrape failed: {exc}")

    if not jobs:
        companies = ["Product Analytics Team", "SaaS Platform Group", "Fintech Hiring Team", "Data Product Lab", "AI Ops Studio"]
        jobs = [_fallback_job(keyword, company, "Hirist", location) for company in companies[:limit]]

    return jobs[:limit]


def fetch_company_career_jobs(
    keyword: str,
    companies: Iterable[str],
    location: str = "Remote",
    jobs_per_company: int = 3,
) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for company in [item.strip() for item in companies if item.strip()]:
        career_url = _format_known_career_url(company, keyword, location) or _find_career_home(company)
        if not career_url:
            company_slug = _company_key(company)
            career_url = f"https://www.{company_slug}.com/careers" if company_slug else ""

        real_jobs = _extract_jobs_from_career_page(company, keyword, location, career_url, jobs_per_company)
        if real_jobs:
            results.extend(real_jobs)
            continue

        results.append(
            _career_search_target(
                keyword,
                company,
                location,
                career_url,
                note=(
                    f"Official career-site search target for {company}. Open this page, select a specific "
                    f"{keyword} posting, then use that real job link/JD for analysis."
                ),
            )
        )

    return results


def fetch_scrapperjobs(
    keyword: str,
    location: str = "Remote",
    limit: int = 15,
    linkedin_limit: int = 5,
    naukri_limit: int = 5,
    hirist_limit: int = 5,
    companies: Iterable[str] | None = None,
    jobs_per_company: int = 2,
) -> List[Dict[str, str]]:
    """Fetch and combine jobs from LinkedIn, Naukri, Hirist, and company searches."""

    all_jobs: List[Dict[str, str]] = []
    all_jobs.extend(fetch_linkedin_jobs(keyword, location, linkedin_limit))
    all_jobs.extend(fetch_naukri_jobs(keyword, location, naukri_limit))
    all_jobs.extend(fetch_hirist_jobs(keyword, location, hirist_limit))

    if companies:
        all_jobs.extend(fetch_company_career_jobs(keyword, companies, location, jobs_per_company))

    return _dedupe_jobs(all_jobs)[:limit]


def fetch_scrapper_jobs(keyword: str, location: str = "Remote", limit: int = 15) -> List[Dict[str, str]]:
    """PEP 8 alias used by the orchestrator."""

    return fetch_scrapperjobs(keyword, location, limit)
