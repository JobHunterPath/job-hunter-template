"""Hybrid job scraper.

The fallback order is intentionally conservative:
  1. Direct ATS APIs where available.
  2. Static career-page scraping with requests + BeautifulSoup.
  3. Playwright rendering for JavaScript-heavy career pages.
  4. Search providers: SearXNG, Brave, Tavily, Exa.
"""

import json
import logging
import os
from typing import Optional
from urllib.parse import urlparse

import requests  # kept as a stable test/mock patch point for provider HTTP calls
import yaml

from core.config import RAPIDAPI_KEY
from core.utils import title_matches
from sources.ats import fetch_ats_jobs
from sources.job_boards import fetch_arbeitnow_jobs, fetch_jsearch_jobs
from sources.search_providers import (
    BraveProvider,
    fetch_playwright_career_jobs,
    fetch_static_career_jobs,
    search_web,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger(__name__)

_LISTING_ONLY_PATHS = {
    "/jobs", "/careers", "/positions", "/openings", "/vacancies",
    "/work-with-us", "/join-us",
}


def load_search_config() -> dict:
    config_file = os.path.join(ROOT, "config", "search_config.yml")
    with open(config_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.info("[scraper] Loaded search configuration from %s", config_file)
    return config


def load_companies(region: Optional[str] = None) -> list[dict]:
    """Load enabled companies from search_config.yml, optionally scoped by region."""
    config = load_search_config()
    excluded = {name.lower() for name in config.get("excluded_companies", [])}
    companies = []

    regions_to_load = [region] if region else config.get("regions", {}).keys()

    for reg in regions_to_load:
        if reg not in config.get("regions", {}):
            logger.warning("[scraper] Region %r not found in search_config.yml", reg)
            continue

        region_config = config["regions"][reg]
        if not region_config.get("enabled", True):
            logger.info("[scraper] Region %r is disabled. Skipping.", reg)
            continue

        location = region_config.get("location", "")
        loaded = 0
        for company in region_config.get("companies", []):
            if company["name"].lower() in excluded:
                logger.info("[scraper] Skipping excluded company: %s", company["name"])
                continue
            companies.append({
                **company,
                "region": reg,
                "location": location,
                "country": region_config.get("country", ""),
                "search_lang": region_config.get("search_lang", "en"),
                "_region_config": region_config,
            })
            loaded += 1

        logger.info(
            "[scraper] Loaded %s companies from region %r (location=%r)",
            loaded,
            reg,
            location,
        )

    logger.info("[scraper] Total: %s companies", len(companies))
    return companies


def build_queries(companies: list[dict], config: dict) -> list[tuple[str, str, str]]:
    """Build search queries. Returns (query, company_name, location)."""
    queries = []
    job_titles = config.get("global_search", {}).get(
        "job_titles", ["Product Owner", "Product Manager"]
    )

    for company in companies:
        url = company["career_url"]
        name = company["name"]
        location = company.get("location", "")

        for title in job_titles:
            query = f'"{title}" site:{url}'
            if location:
                query += f' "{location}"'
            queries.append((query, name, location or "global"))

    logger.info("[scraper] Built %s search queries for %s companies", len(queries), len(companies))
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
    return len(segments) >= 2


def is_stale_posting(title: str, snippet: str, config: dict) -> bool:
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
    """Compatibility wrapper for tests/tools that call Brave directly."""
    count = count or 10
    try:
        results = BraveProvider().search(query, region_config, count=count)
    except Exception as e:
        logger.error("[scraper] Error during Brave Search: %s", e)
        raise
    return [
        {
            "url": result.url,
            "title": result.title,
            "description": result.description,
            "source": result.source,
        }
        for result in results
    ]


def _make_filter(config: dict, seen_urls: set[str], results: list[dict], title_filters: list[str]):
    def add_job(job: dict) -> bool:
        if not job.get("url") or job["url"] in seen_urls:
            return False
        if title_filters and not title_matches(job.get("title", ""), title_filters):
            logger.debug("[skip] Title not in filters: %s", job.get("title", "")[:60])
            return False
        if is_german(job.get("title", ""), job.get("snippet", ""), config):
            logger.debug("[skip] German posting: %s", job.get("title", "")[:60])
            return False
        if is_too_senior(job.get("title", ""), job.get("snippet", ""), config):
            logger.debug("[skip] Too senior: %s", job.get("title", "")[:60])
            return False
        if is_excluded(job.get("snippet", ""), config):
            logger.debug("[skip] Excluded industry: %s", job.get("title", "")[:60])
            return False

        seen_urls.add(job["url"])
        results.append(job)
        logger.info(
            "[found] %s @ %s [%s]",
            job.get("title", "")[:50],
            job.get("company", "?"),
            job.get("source", "?"),
        )
        return True

    return add_job


def scrape(region: Optional[str] = None) -> list[dict]:
    """Scrape jobs for configured companies and global boards."""
    config = load_search_config()
    companies = load_companies(region)

    if not companies:
        logger.warning("[scraper] No companies to scrape. Check search_config.yml")
        return []

    global_cfg = config.get("global_search", {})
    title_filters = global_cfg.get("job_titles", ["Product Owner", "Product Manager"])
    if region:
        region_cfg = config.get("regions", {}).get(region)
        enabled_regions = {
            region: region_cfg
        } if region_cfg and region_cfg.get("enabled", True) else {}
    else:
        enabled_regions = {
            name: rc for name, rc in config.get("regions", {}).items()
            if rc.get("enabled", True)
        }

    results: list[dict] = []
    seen_urls: set[str] = set()
    add_job = _make_filter(config, seen_urls, results, title_filters)

    for company in companies:
        company_region_config = company.get("_region_config") or {
            "location": company.get("location", ""),
            "country": company.get("country", ""),
            "search_lang": company.get("search_lang", "en"),
        }
        ats_jobs = fetch_ats_jobs(company, company.get("location", ""), title_filters)
        if ats_jobs is not None:
            for job in ats_jobs:
                add_job(job)
            continue

        direct_found = 0
        try:
            for job in fetch_static_career_jobs(company, title_filters):
                direct_found += int(add_job(job))
        except Exception as e:
            logger.debug("[scraper] HTTP career scrape failed for %s: %s", company["name"], e)

        if direct_found == 0:
            try:
                for job in fetch_playwright_career_jobs(company, title_filters):
                    direct_found += int(add_job(job))
            except Exception as e:
                logger.debug("[scraper] Playwright career scrape failed for %s: %s", company["name"], e)

        if direct_found:
            continue

        for query, company_name, _ in build_queries([company], config):
            try:
                raw = search_web(query, company_region_config, count=10)
            except Exception as e:
                logger.warning("[scraper] Search error for %s: %s", company_name, e)
                continue

            filtered_count = 0
            for item in raw:
                url = item.get("url", "")
                title = item.get("title", "")
                snippet = item.get("description", "")

                if not url or url in seen_urls:
                    continue
                if not is_valid_job_url(url):
                    logger.debug("[skip] Not a job posting URL: %s", url[:80])
                    filtered_count += 1
                    continue
                if is_stale_posting(title, snippet, config):
                    logger.debug("[skip] Stale/closed posting: %s", title[:60])
                    filtered_count += 1
                    continue

                add_job({
                    "title": title,
                    "company": company_name,
                    "url": url,
                    "posted": "",
                    "snippet": snippet,
                    "source": item.get("source", "Search fallback"),
                    "query": query,
                })

            if filtered_count > 0:
                logger.debug("[scraper] Filtered %s ineligible results from %s", filtered_count, company_name)

    boards_cfg = config.get("job_boards", {})

    for region_name, region_config in enabled_regions.items():
        board_location = region_config.get("location", "")
        if boards_cfg.get("arbeitnow", {}).get("enabled", False):
            max_pages = boards_cfg["arbeitnow"].get("max_pages", 3)
            logger.info(
                "[scraper] Arbeitnow: region=%r, location=%r, max_pages=%s",
                region_name,
                board_location,
                max_pages,
            )
            for job in fetch_arbeitnow_jobs(title_filters, board_location, max_pages):
                add_job(job)

        if boards_cfg.get("jsearch", {}).get("enabled", False):
            num_pages = boards_cfg["jsearch"].get("num_pages", 1)
            logger.info(
                "[scraper] JSearch: region=%r, location=%r, titles=%s",
                region_name,
                board_location,
                title_filters,
            )
            for job in fetch_jsearch_jobs(title_filters, board_location, RAPIDAPI_KEY, num_pages):
                add_job(job)

    logger.info("[scraper] Complete: %s jobs found", len(results))
    return results


if __name__ == "__main__":
    jobs = scrape()
    print(json.dumps(jobs, indent=2))
