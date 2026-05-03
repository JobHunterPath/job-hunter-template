"""
Shared utility functions used across pipeline stages.
"""

import re
import requests


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace to plain text."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def location_matches(location_str: str, target: str) -> bool:
    """Return True if target appears (case-insensitive) in location_str, or if target is empty."""
    if not target:
        return True
    return target.lower() in location_str.lower()


def title_matches(title: str, title_filters: list[str]) -> bool:
    """Return True if any filter appears (case-insensitive) in title, or if filters is empty."""
    if not title_filters:
        return True
    return any(f.lower() in title.lower() for f in title_filters)


def url_is_alive(url: str, timeout: int = 5) -> bool:
    """
    HEAD-check a URL. Returns False only on definitive 4xx/5xx responses.
    Returns True on network errors (a transient error does not mean the job is dead).
    """
    try:
        resp = requests.head(
            url, timeout=timeout, allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code == 405:
            resp = requests.get(
                url, timeout=timeout, allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
        return resp.status_code < 400
    except Exception:
        return True  # network error != dead posting
