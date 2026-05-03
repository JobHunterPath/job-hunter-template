"""
Hybrid job scraper: direct ATS APIs where possible, Brave Search as fallback.

For each company:
  1. Detect if career_url belongs to a known ATS (Greenhouse, Lever, SmartRecruiters, Workable).
  2. If yes → query the ATS API directly (real-time, structured, precise location).
  3. If no  → fall back to Brave Search with location term in the query.
"""

import os
import logging
from typing import Optional
from urllib.parse import urlparse
import requests
import yaml

from core.config import BRAVE_API_KEY, RAPIDAPI_KEY
from sources.ats import fetch_ats_jobs
from sources.job_boards import fetch_arbeitnow_jobs, fetch_jsearch_jobs

# scripts/sources/ → scripts/ → repo root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"

logger = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": BRAVE_API_KEY,
}

_LISTING_ONLY_PATHS = {"/jobs", "/careers", "/positions", "/openings", "/vacancies", "/work-with-us", "/join-us"}


def load_search_config() -> dict:
    config_file = os.path.join(ROOT, "config", "search_config.yml")
    with open(config_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.info(f"[scraper] Loaded search configuration from {config_file}")
    return config


def load_companies(region: Optional[str] = None) -> list[dict]:
    """
    Load companies from search_config.yml by region.
    Attaches the region's location to each company so queries can be geo-targeted.
    Skips companies listed under excluded_companies.
    """
    config = load_search_config()
    excluded = {name.lower() for name in config.get("excluded_companies", [])}
    companies = []

    regions_to_load = [region] if region else config.get("regions", {}).keys()

    for reg in regions_to_load:
        if reg not in config.get("regions", {}):
            logger.warning(f"[scraper] Region '{reg}' not found in search_config.yml")
            continue

        region_config = config["regions"][reg]
        if not region_config.get("enabled", True):
            logger.info(f"[scraper] Region '{reg}' is disabled. Skipping.")
            continue

        location = region_config.get("location", "")
        region_companies = region_config.get("companies", [])
        loaded = 0
        for company in region_companies:
            if company["name"].lower() in excluded:
                logger.info(f"[scraper] Skipping excluded company: {company['name']}")
                continue
            companies.append({**company, "location": location})
            loaded += 1

        logger.info(f"[scraper] Loaded {loaded} companies from region '{reg}' (location={location!r})")

    logger.info(f"[scraper] Total: {len(companies)} companies")
    return companies


def build_queries(companies: list[dict], config: dict) -> list[tuple[str, str, str]]:
    """
    Build Brave Search queries. Appends the region location to every query.
    Returns list of (query, company_name, location) tuples.
    """
    queries = []
    job_titles = config.get("global_search", {}).get("job_titles", ["Product Owner", "Product Manager"])

    for company in companies:
        url = company["career_url"]
        name = company["name"]
        location = company.get("location", "")

        for title in job_titles:
            query = f'"{title}" site:{url}'
            if location:
                query += f' "{location}"'
            queries.append((query, name, location or "global"))

    logger.info(f"[scraper] Built {len(queries)} Brave queries for {len(companies)} companies")
    return queries


def is_valid_job_url(url: str) -> bool:
    """Return False for root/listing pages that are not individual job postings."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    if not path:
        return False
    if path in _LISTING_ONLY_PATHS:
        return False

    segments = [s for s in path.split("/") if s]
    if len(segments) < 2:
        return False

    return True


def is_stale_posting(title: str, snippet: str, config: dict) -> bool:
    """Return True if the snippet signals the posting is closed or expired."""
    combined = (title + " " + snippet).lower()
    stale_indicators = config.get("exclusion_rules", {}).get("stale_indicators", [])
    return any(indicator in combined for indicator in stale_indicators)


def is_too_senior(title: str, snippet: str, config: dict) -> bool:
    combined = (title + " " + snippet).lower()
    senior_flags = config.get("exclusion_rules", {}).get("senior_flags", [])
    return any(flag in combined for flag in senior_flags)


def is_excluded(snippet: str, config: dict) -> bool:
    excluded_industries = config.get("exclusion_rules", {}).get("excluded_industries", [])
    return any(kw in snippet.lower() for kw in excluded_industries)


def is_german(title: str, snippet: str, config: dict) -> bool:
    combined = (title + " " + snippet).lower()
    german_indicators = config.get("exclusion_rules", {}).get("german_indicators", [])
    return any(word in combined for word in german_indicators)


def brave_search(query: str, region_config: dict, count: Optional[int] = None) -> list[dict]:
    if count is None:
        count = 10

    params = {
        "q": query,
        "count": count,
        "search_lang": region_config.get("search_lang", "en"),
        "country": region_config.get("country", "DE"),
        "text_decorations": False,
        "spellcheck": False,
    }

    try:
        resp = requests.get(BRAVE_URL, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("web", {}).get("results", [])
        logger.debug(f"[scraper] Brave returned {len(results)} results for: {query[:60]}")
        return results
    except requests.HTTPError as e:
        logger.error(f"[scraper] HTTP error during Brave Search: {e}")
        raise
    except Exception as e:
        logger.error(f"[scraper] Unexpected error in Brave Search: {e}")
        raise


def scrape(region: Optional[str] = None) -> list[dict]:
    """
    Scrape jobs for all configured companies.
    Uses direct ATS APIs where available; falls back to Brave Search for others.
    """
    config = load_search_config()
    companies = load_companies(region)

    if not companies:
        logger.warning("[scraper] No companies to scrape. Check search_config.yml")
        return []

    global_cfg = config.get("global_search", {})
    title_filters = global_cfg.get("job_titles", ["Product Owner", "Product Manager"])

    region_config = next(
        (rc for rc in config.get("regions", {}).values() if rc.get("enabled", True)),
        {"country": "DE", "search_lang": "en"},
    )

    results = []
    seen_urls = set()

    for company in companies:
        location = company.get("location", "")

        # ── Direct ATS API (preferred) ───────────────────────────────────────
        ats_jobs = fetch_ats_jobs(company, location, title_filters)

        if ats_jobs is not None:
            for job in ats_jobs:
                if not job.get("url") or job["url"] in seen_urls:
                    continue
                if is_german(job["title"], job["snippet"], config):
                    logger.debug(f"[skip] German posting: {job['title'][:60]}")
                    continue
                if is_too_senior(job["title"], job["snippet"], config):
                    logger.debug(f"[skip] Too senior: {job['title'][:60]}")
                    continue
                if is_excluded(job["snippet"], config):
                    logger.debug(f"[skip] Excluded industry: {job['title'][:60]}")
                    continue
                seen_urls.add(job["url"])
                results.append(job)
                logger.info(f"[found] {job['title'][:50]} @ {company['name']} [{job['source']}]")
            continue

        # ── Brave Search fallback (non-ATS career pages) ────────────────────
        for query, company_name, _ in build_queries([company], config):
            logger.info(f"[scraper] Brave: {query[:80]}...")

            try:
                raw = brave_search(query, region_config, count=10)
            except Exception as e:
                logger.warning(f"[scraper] Brave error for {company_name}: {e}")
                continue

            filtered_count = 0
            for item in raw:
                url = item.get("url", "")
                title = item.get("title", "")
                snippet = item.get("description", "")

                if not url or url in seen_urls:
                    continue
                if not is_valid_job_url(url):
                    logger.debug(f"[skip] Not a job posting URL: {url[:80]}")
                    filtered_count += 1
                    continue
                if is_stale_posting(title, snippet, config):
                    logger.debug(f"[skip] Stale/closed posting: {title[:60]}")
                    filtered_count += 1
                    continue
                if is_german(title, snippet, config):
                    logger.debug(f"[skip] German posting: {title[:60]}")
                    filtered_count += 1
                    continue
                if is_too_senior(title, snippet, config):
                    logger.debug(f"[skip] Too senior: {title[:60]}")
                    filtered_count += 1
                    continue
                if is_excluded(snippet, config):
                    logger.debug(f"[skip] Excluded industry: {title[:60]}")
                    filtered_count += 1
                    continue
                seen_urls.add(url)
                results.append({
                    "title": title,
                    "company": company_name,
                    "url": url,
                    "posted": "",
                    "snippet": snippet,
                    "source": "Brave/ATS",
                    "query": query,
                })
                logger.info(f"[found] {title[:50]} @ {company_name} [Brave]")

            if filtered_count > 0:
                logger.debug(f"[scraper] Filtered {filtered_count} ineligible results from {company_name}")

    # ── Global job boards (Arbeitnow + JSearch) ─────────────────────────────
    board_location = region_config.get("location", "")
    boards_cfg = config.get("job_boards", {})

    def _add_global_jobs(global_jobs: list[dict]) -> None:
        for job in global_jobs:
            if not job.get("url") or job["url"] in seen_urls:
                continue
            if is_german(job["title"], job["snippet"], config):
                logger.debug(f"[skip] German posting: {job['title'][:60]}")
                continue
            if is_too_senior(job["title"], job["snippet"], config):
                logger.debug(f"[skip] Too senior: {job['title'][:60]}")
                continue
            if is_excluded(job["snippet"], config):
                logger.debug(f"[skip] Excluded industry: {job['title'][:60]}")
                continue
            seen_urls.add(job["url"])
            results.append(job)
            logger.info(f"[found] {job['title'][:50]} @ {job.get('company', '?')} [{job['source']}]")

    if boards_cfg.get("arbeitnow", {}).get("enabled", False):
        max_pages = boards_cfg["arbeitnow"].get("max_pages", 3)
        logger.info(f"[scraper] Arbeitnow: location={board_location!r}, max_pages={max_pages}")
        _add_global_jobs(fetch_arbeitnow_jobs(title_filters, board_location, max_pages))

    if boards_cfg.get("jsearch", {}).get("enabled", False):
        num_pages = boards_cfg["jsearch"].get("num_pages", 1)
        logger.info(f"[scraper] JSearch: location={board_location!r}, titles={title_filters}")
        _add_global_jobs(fetch_jsearch_jobs(title_filters, board_location, RAPIDAPI_KEY, num_pages))

    logger.info(f"[scraper] Complete: {len(results)} jobs found")
    return results


if __name__ == "__main__":
    import json
    jobs = scrape()
    print(json.dumps(jobs, indent=2))
