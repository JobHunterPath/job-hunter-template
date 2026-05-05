"""
Global job board scrapers: Arbeitnow and JSearch (RapidAPI).

These search across the whole market rather than targeting specific career pages,
so they complement the per-company ATS fetchers in sources/ats.py.

- Arbeitnow: free, no auth, Germany-focused REST API.
- JSearch:   RapidAPI aggregator (LinkedIn, Indeed, Glassdoor, etc.);
             free tier = 200 req/month; requires RAPIDAPI_KEY.
"""

import logging
from datetime import datetime, timezone
import requests

from core.config import get_timeout
from core.utils import strip_html, location_matches, title_matches

_TIMEOUT = get_timeout("job_boards")

logger = logging.getLogger(__name__)

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"


def _parse_arbeitnow_date(value) -> str:
    """Return YYYY-MM-DD from a Unix timestamp int or ISO string, or '' on failure."""
    if not value:
        return ""
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d")
        return str(value)[:10]
    except Exception:
        return ""


def fetch_arbeitnow_jobs(
    title_filters: list[str],
    location_filter: str,
    max_pages: int = 3,
) -> list[dict]:
    """
    Fetch jobs from Arbeitnow. Free, no auth required.
    Paginates up to max_pages; stops early when a page returns no data.
    """
    jobs = []

    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(ARBEITNOW_URL, params={"page": page}, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("data", [])
        except Exception as e:
            logger.warning(f"[arbeitnow] page {page}: {e}")
            break

        if not data:
            break

        for job in data:
            title = job.get("title", "")
            location = job.get("location", "")

            if not title_matches(title, title_filters):
                continue
            if not location_matches(location, location_filter):
                continue

            description = strip_html(job.get("description", ""))
            jobs.append({
                "title": title,
                "company": job.get("company_name", ""),
                "url": job.get("url", ""),
                "posted": _parse_arbeitnow_date(job.get("created_at")),
                "snippet": f"{location} — {description[:1000]}" if location else description[:1000],
                "source": "Arbeitnow",
            })

    logger.info(f"[arbeitnow] {len(jobs)} matching jobs")
    return jobs


def fetch_jsearch_jobs(
    title_filters: list[str],
    location_filter: str,
    rapidapi_key: str,
    num_pages: int = 1,
) -> list[dict]:
    """
    Fetch jobs via JSearch on RapidAPI. Aggregates LinkedIn, Indeed, Glassdoor.
    Issues one request per title (to stay within the free tier of 200 req/month).
    Returns [] immediately if no API key is provided.
    """
    if not rapidapi_key:
        logger.warning("[jsearch] No RAPIDAPI_KEY configured — skipping")
        return []

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    titles = title_filters or ["Product Owner", "Product Manager"]
    jobs = []

    for title in titles:
        query = f"{title} in {location_filter}" if location_filter else title

        for page in range(1, num_pages + 1):
            try:
                resp = requests.get(
                    JSEARCH_URL,
                    headers=headers,
                    params={
                        "query": query,
                        "page": str(page),
                        "num_pages": "1",
                        "country": "de",
                        "language": "en",
                    },
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
            except Exception as e:
                logger.warning(f"[jsearch] query={query!r} page={page}: {e}")
                break

            for job in data:
                city = job.get("job_city") or ""
                country = job.get("job_country") or ""
                location_str = f"{city}, {country}".strip(", ")
                description = (job.get("job_description") or "")[:1000]

                jobs.append({
                    "title": job.get("job_title", ""),
                    "company": job.get("employer_name", ""),
                    "url": job.get("job_apply_link", ""),
                    "posted": (job.get("job_posted_at_datetime_utc") or "")[:10],
                    "snippet": f"{location_str} — {description}" if location_str else description,
                    "source": "JSearch",
                })

    logger.info(f"[jsearch] {len(jobs)} jobs returned")
    return jobs
