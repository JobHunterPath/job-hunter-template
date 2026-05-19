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
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from urllib.parse import urlparse

import requests  # kept as a stable test/mock patch point for provider HTTP calls
import yaml

from core.config import RAPIDAPI_KEY
from core.utils import title_matches
from sources.ats import fetch_ats_jobs
from sources.ai_web_search import fetch_ai_web_search_jobs
from sources.job_boards import fetch_arbeitnow_jobs, fetch_jsearch_jobs
from sources.search_providers import (
    BraveProvider,
    canonicalize_url,
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
                "search_lang": region_config.get("search_lang", ""),
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
    job_titles = config.get("global_search", {}).get("job_titles", [])
    excluded_title_terms = config.get("exclusion_rules", {}).get("excluded_title_terms", [])
    exclusions = " ".join(f'-"{term}"' for term in excluded_title_terms)

    if not job_titles:
        logger.warning("[scraper] global_search.job_titles is empty; no search queries built")
        return queries

    for company in companies:
        url = company["career_url"]
        name = company["name"]
        location = company.get("location", "")

        for title in job_titles:
            query = f'"{title}" site:{url}'
            if location:
                query += f' "{location}"'
            if exclusions:
                query += f" {exclusions}"
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


def is_excluded_url(url: str, config: dict) -> bool:
    """Return True when caller-configured URL patterns identify non-posting pages."""
    patterns = config.get("exclusion_rules", {}).get("excluded_url_patterns", [])
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns)


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


def _make_filter(config: dict, seen_urls: set[str], results: list[dict], title_filters: list[str], lock: Optional[threading.Lock] = None):
    excluded_title_terms = config.get("exclusion_rules", {}).get("excluded_title_terms", [])
    _lock = lock or threading.Lock()

    def add_job(job: dict, allow_excluded_urls: bool = False) -> bool:
        url = job.get("url", "")
        canonical_url = canonicalize_url(url)
        if not url:
            return False
        # All filtering before the lock (no shared state needed)
        if not allow_excluded_urls and is_excluded_url(url, config):
            logger.debug("[skip] Excluded URL pattern: %s", url[:80])
            return False
        if title_filters and not title_matches(job.get("title", ""), title_filters, excluded_title_terms):
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
        # Atomic dedup + append
        with _lock:
            if canonical_url in seen_urls:
                return False
            seen_urls.add(canonical_url)
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

    global_cfg = config.get("global_search", {})
    title_filters = global_cfg.get("job_titles", [])
    excluded_title_terms = config.get("exclusion_rules", {}).get("excluded_title_terms", [])
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
    lock = threading.Lock()
    add_job = _make_filter(config, seen_urls, results, title_filters, lock)

    try:
        for job in fetch_ai_web_search_jobs(title_filters, enabled_regions):
            add_job(job, allow_excluded_urls=True)
    except Exception as e:
        logger.warning("[scraper] AI web search failed: %s", e)

    if not companies:
        logger.warning("[scraper] No companies to scrape. Check search_config.yml")

    scraping_cfg = config.get("scraping", {})
    max_workers = int(scraping_cfg.get("max_workers", 10))

    def _process_company(company: dict) -> None:
        company_region_config = company.get("_region_config") or {
            "location": company.get("location", ""),
            "country": company.get("country", ""),
            "search_lang": company.get("search_lang", ""),
        }
        ats_jobs = fetch_ats_jobs(company, company.get("location", ""), title_filters, excluded_title_terms)
        if ats_jobs is not None:
            for job in ats_jobs:
                add_job(job)
            return

        direct_found = 0
        try:
            for job in fetch_static_career_jobs(company, title_filters, excluded_title_terms):
                direct_found += int(add_job(job))
        except Exception as e:
            logger.debug("[scraper] HTTP career scrape failed for %s: %s", company["name"], e)

        if direct_found == 0:
            try:
                for job in fetch_playwright_career_jobs(company, title_filters, excluded_title_terms):
                    direct_found += int(add_job(job))
            except Exception as e:
                logger.debug("[scraper] Playwright career scrape failed for %s: %s", company["name"], e)

        if direct_found:
            return

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

                if not url:
                    continue
                if is_excluded_url(url, config):
                    logger.debug("[skip] Excluded URL pattern: %s", url[:80])
                    filtered_count += 1
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

    total_scrape_timeout = int(scraping_cfg.get("total_timeout_seconds", 1800))
    total_companies = len(companies)
    company_counter = 0
    company_counter_lock = threading.Lock()

    def _process_company_tracked(company: dict) -> None:
        nonlocal company_counter
        with company_counter_lock:
            company_counter += 1
            idx = company_counter
        logger.info("[scraper] [%d/%d] %s", idx, total_companies, company["name"])
        _process_company(company)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_company_tracked, company): company for company in companies}
        try:
            for future in as_completed(futures, timeout=total_scrape_timeout):
                company = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.warning("[scraper] Error processing %s: %s", company.get("name", "?"), e)
        except TimeoutError:
            logger.warning("[scraper] Company scraping hit %ss total timeout, proceeding with partial results", total_scrape_timeout)

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
            for job in fetch_arbeitnow_jobs(
                title_filters,
                board_location,
                max_pages,
                excluded_title_terms,
            ):
                add_job(job)

        if boards_cfg.get("jsearch", {}).get("enabled", False):
            num_pages = boards_cfg["jsearch"].get("num_pages", 1)
            logger.info(
                "[scraper] JSearch: region=%r, location=%r, titles=%s",
                region_name,
                board_location,
                title_filters,
            )
            for job in fetch_jsearch_jobs(
                title_filters,
                board_location,
                RAPIDAPI_KEY,
                num_pages,
                excluded_title_terms,
                region_config.get("country", ""),
                region_config.get("search_lang", ""),
            ):
                add_job(job)

    logger.info("[scraper] Complete: %s jobs found", len(results))
    return results


if __name__ == "__main__":
    jobs = scrape()
    print(json.dumps(jobs, indent=2))
