"""Search and career-page provider strategies.

The scraper and discovery jobs need the same fallback chain: cheap direct
fetching first, API search providers last.  Each provider implements the same
small interface so callers can use a Chain of Responsibility style router
without knowing provider-specific response shapes.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from html import unescape
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from core.config import (
    BRAVE_API_KEY,
    EXA_API_KEY,
    TAVILY_API_KEY,
    get_timeout,
    load_api_config,
)
from core.utils import title_matches

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
TAVILY_URL = "https://api.tavily.com/search"
EXA_URL = "https://api.exa.ai/search"

JOB_HINTS = (
    "job", "jobs", "career", "careers", "position", "positions", "opening",
    "openings", "vacancy", "vacancies",
)


@dataclass
class SearchResult:
    url: str
    title: str
    description: str
    source: str


class SearchProvider:
    """Strategy interface for web-search providers."""

    name = "provider"

    def enabled(self) -> bool:
        return True

    def search(self, query: str, region_config: dict, count: int = 10) -> list[SearchResult]:
        raise NotImplementedError


def _timeout(section: str) -> int:
    return get_timeout(section)


def _search_cfg() -> dict:
    return load_api_config().get("http", {}).get("search_providers", {}) or {}


def _with_scheme(url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def _text(value: object) -> str:
    return unescape(str(value or "")).strip()


def _looks_like_job_url(url: str) -> bool:
    lower = url.lower()
    return any(hint in lower for hint in JOB_HINTS)


def _location_match(text: str, location: str) -> bool:
    if not location:
        return True
    lower = text.lower()
    location = location.lower()
    if location in lower:
        return True
    if "remote" in location and "remote" in lower:
        return True
    return False


def normalize_web_results(raw: list[dict], source: str) -> list[SearchResult]:
    results = []
    for item in raw:
        url = item.get("url") or item.get("link")
        if not url:
            continue
        results.append(
            SearchResult(
                url=url,
                title=_text(item.get("title") or item.get("name")),
                description=_text(
                    item.get("description")
                    or item.get("snippet")
                    or item.get("content")
                    or item.get("text")
                ),
                source=source,
            )
        )
    return results


class SearxngProvider(SearchProvider):
    name = "searxng"

    def __init__(self) -> None:
        self.base_url = (
            os.environ.get("SEARXNG_BASE_URL")
            or _search_cfg().get("searxng_base_url")
            or ""
        ).rstrip("/")

    def enabled(self) -> bool:
        return bool(self.base_url)

    def search(self, query: str, region_config: dict, count: int = 10) -> list[SearchResult]:
        params = {
            "q": query,
            "format": "json",
            "safesearch": 0,
        }
        if region_config.get("search_lang"):
            params["language"] = region_config["search_lang"]
        resp = requests.get(
            f"{self.base_url}/search",
            params=params,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=_timeout("brave_search"),
        )
        resp.raise_for_status()
        raw = resp.json().get("results", [])[:count]
        return normalize_web_results(raw, "SearXNG")


class BraveProvider(SearchProvider):
    name = "brave"

    def enabled(self) -> bool:
        return bool(BRAVE_API_KEY)

    def search(self, query: str, region_config: dict, count: int = 10) -> list[SearchResult]:
        params = {
            "q": query,
            "count": count,
            "text_decorations": False,
            "spellcheck": False,
        }
        if region_config.get("search_lang"):
            params["search_lang"] = region_config["search_lang"]
        if region_config.get("country"):
            params["country"] = region_config["country"]
        resp = requests.get(
            BRAVE_URL,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            params=params,
            timeout=_timeout("brave_search"),
        )
        resp.raise_for_status()
        return normalize_web_results(resp.json().get("web", {}).get("results", []), "Brave")


class TavilyProvider(SearchProvider):
    name = "tavily"

    def enabled(self) -> bool:
        return bool(TAVILY_API_KEY)

    def search(self, query: str, region_config: dict, count: int = 10) -> list[SearchResult]:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": count,
            "include_answer": False,
            "include_raw_content": False,
        }
        resp = requests.post(TAVILY_URL, json=payload, timeout=_timeout("brave_search"))
        resp.raise_for_status()
        return normalize_web_results(resp.json().get("results", []), "Tavily")


class ExaProvider(SearchProvider):
    name = "exa"

    def enabled(self) -> bool:
        return bool(EXA_API_KEY)

    def search(self, query: str, region_config: dict, count: int = 10) -> list[SearchResult]:
        payload = {
            "query": query,
            "numResults": count,
            "type": "keyword",
            "contents": {"text": {"maxCharacters": 500}},
        }
        resp = requests.post(
            EXA_URL,
            json=payload,
            headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
            timeout=_timeout("brave_search"),
        )
        resp.raise_for_status()
        raw = []
        for item in resp.json().get("results", []):
            raw.append({
                "url": item.get("url"),
                "title": item.get("title"),
                "description": item.get("text") or item.get("highlights"),
            })
        return normalize_web_results(raw, "Exa")


class SearchRouter:
    """Tries enabled search providers in configured order."""

    def __init__(self, providers: Optional[list[SearchProvider]] = None) -> None:
        available = {
            "searxng": SearxngProvider(),
            "brave": BraveProvider(),
            "tavily": TavilyProvider(),
            "exa": ExaProvider(),
        }
        order = _search_cfg().get("order") or list(available)
        ordered = [available[name] for name in order if name in available]
        self.providers = providers if providers is not None else ordered

    def search(self, query: str, region_config: dict, count: int = 10) -> list[SearchResult]:
        all_results: list[SearchResult] = []
        for provider in self.providers:
            if not provider.enabled():
                logger.debug("[search] %s disabled or missing credentials", provider.name)
                continue
            try:
                logger.info("[search] %s: %s", provider.name, query[:80])
                results = provider.search(query, region_config, count=count)
                if results:
                    all_results.extend(results)
                    break
            except Exception as exc:
                logger.warning("[search] %s failed: %s", provider.name, exc)
        return all_results[:count]


def search_web(query: str, region_config: dict, count: int = 10) -> list[dict]:
    """Compatibility helper returning Brave-like dictionaries."""
    return [
        {
            "url": result.url,
            "title": result.title,
            "description": result.description,
            "source": result.source,
        }
        for result in SearchRouter().search(query, region_config, count=count)
    ]


def extract_jobs_from_html(
    html: str,
    base_url: str,
    company_name: str,
    title_filters: list[str],
    location: str,
    source: str,
    excluded_title_terms: list[str] | None = None,
) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[dict] = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href"))
        url = urljoin(base_url, href)
        text = " ".join(anchor.get_text(" ", strip=True).split())
        context = " ".join(
            anchor.parent.get_text(" ", strip=True).split()
            if anchor.parent else text
        )
        haystack = f"{text} {href} {context}"

        title_text = text or next((t for t in title_filters if t.lower() in haystack.lower()), "")

        if not _looks_like_job_url(url) and not title_matches(title_text or haystack, title_filters, excluded_title_terms):
            continue
        if not title_matches(title_text or haystack, title_filters, excluded_title_terms):
            continue
        if not _location_match(haystack, location):
            continue
        if url in seen:
            continue

        seen.add(url)
        jobs.append({
            "title": text or next((t for t in title_filters if t.lower() in haystack.lower()), "Job"),
            "company": company_name,
            "url": url,
            "posted": "",
            "snippet": context or text,
            "source": source,
        })

    return jobs


def fetch_static_career_jobs(
    company: dict,
    title_filters: list[str],
    excluded_title_terms: list[str] | None = None,
) -> list[dict]:
    url = _with_scheme(company["career_url"])
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=_timeout("ats_scraper"),
        allow_redirects=True,
    )
    resp.raise_for_status()
    if not isinstance(resp.text, str):
        return []
    return extract_jobs_from_html(
        resp.text,
        resp.url or url,
        company["name"],
        title_filters,
        company.get("location", ""),
        "HTTP career page",
        excluded_title_terms,
    )


def fetch_playwright_career_jobs(
    company: dict,
    title_filters: list[str],
    excluded_title_terms: list[str] | None = None,
) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.debug("[search] playwright not installed; skipping career render")
        return []

    url = _with_scheme(company["career_url"])
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, wait_until="networkidle", timeout=20_000)
            html = page.content()
            return extract_jobs_from_html(
                html,
                page.url or url,
                company["name"],
                title_filters,
                company.get("location", ""),
                "Playwright career page",
                excluded_title_terms,
            )
        finally:
            browser.close()


def discover_company_homepage(company_name: str, region_config: dict) -> Optional[str]:
    location = region_config.get("location", "")
    query = f'"{company_name}" "{location}" official website careers'
    results = SearchRouter().search(query, region_config, count=5)
    for result in results:
        parsed = urlparse(result.url)
        if parsed.netloc and "linkedin." not in parsed.netloc and "glassdoor." not in parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return None


def search_career_urls(company_name: str, region_config: dict, count: int = 7) -> list[dict]:
    location = region_config.get("location", "")
    job_titles = region_config.get("job_titles", [])
    title_query = " OR ".join(f'"{title}"' for title in job_titles)
    ats_sites = (
        "site:boards.greenhouse.io OR site:job-boards.greenhouse.io "
        "OR site:jobs.lever.co OR site:jobs.smartrecruiters.com "
        "OR site:apply.workable.com OR site:jobs.ashbyhq.com "
        "OR site:careers.hibob.com OR site:recruitee.com "
        "OR site:jobs.personio.de OR site:jobs.personio.com"
    )
    queries = [f'"{company_name}" {location} {ats_sites}']
    if title_query:
        queries.append(f'"{company_name}" {location} {title_query} careers jobs')
    out: list[dict] = []
    seen = set()
    for query in queries:
        for item in search_web(query, region_config, count=count):
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            out.append(item)
    return out
