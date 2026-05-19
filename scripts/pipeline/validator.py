"""
Pre-filters scraped jobs before AI scoring/tailoring.

Two checks (in order):
  1. URL reachability — HEAD-check each posting URL; drop definitive 4xx/5xx.
  2. LLM freshness check — ask a cheap model whether the snippet signals a
     closed/filled posting or an explicitly excessive experience requirement.

Running this before scorer saves the more expensive scoring and tailoring
calls on dead or obviously unsuitable postings.
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from core.config import load_api_config
from core.llm_client import get_llm_client
from core.utils import url_is_alive

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a job-posting validator. "
    "Return ONLY valid JSON with no markdown fences and no explanation."
)

_PROMPT = """\
Read this job posting snippet and answer two questions.

1. Is this an active, open posting?
   Mark is_active=false ONLY if the text explicitly says the role is filled,
   closed, expired, archived, or no longer accepting applications.
   When in doubt, default to true.

2. Does this posting explicitly require MORE than {max_years} years of experience?
   Mark over_experience=true ONLY if the description clearly states a minimum
   exceeding {max_years} years (e.g. "10+ years required", "minimum 8 years").
   When in doubt, default to false.

Snippet:
{snippet}

Return JSON: {{"is_active": bool, "over_experience": bool, "reason": "one-line reason if rejected, else null"}}"""


def validate(
    jobs: list[dict],
    max_years: int,
    api_cfg: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (valid_jobs, rejected_jobs).

    Rejected jobs have a ``_rejection_reason`` key added for logging.
    Jobs where LLM validation fails are passed through (fail-open) to avoid
    false negatives from transient API errors.
    """
    if api_cfg is None:
        api_cfg = load_api_config()

    llm = api_cfg.get("llm", {})
    model = llm.get("models", {}).get("validation", "claude-haiku-4-5-20251001")
    max_tokens = llm.get("max_tokens", {}).get("validation", 200)

    url_cfg = api_cfg.get("http", {}).get("url_verification", {})
    check_urls = url_cfg.get("enabled", True)
    url_timeout = url_cfg.get("timeout_seconds", 5)

    max_workers = int(api_cfg.get("llm", {}).get("max_workers", 5))

    counter = 0
    counter_lock = threading.Lock()
    # Results collected in (original_index, kind, job) tuples for stable ordering
    results: list[tuple[int, str, dict]] = []
    results_lock = threading.Lock()

    def _validate_job(args: tuple[int, dict]) -> None:
        nonlocal counter
        idx_orig, job = args
        url = job.get("url", "")
        label = f"{job.get('title', '?')[:40]} @ {job.get('company', '?')}"
        with counter_lock:
            counter += 1
            display_idx = counter
        prefix = f"[validate] [{display_idx}/{len(jobs)}] {label}"
        logger.info(prefix)

        # 1 -- URL reachability
        if check_urls and url and not url_is_alive(url, url_timeout):
            logger.info(f"{prefix}: dead URL: {url[:80]}")
            with results_lock:
                results.append((idx_orig, "rejected", {**job, "_rejection_reason": "dead_url"}))
            return

        # 2 -- LLM freshness + experience check
        snippet = (job.get("snippet") or "")[:2000]
        if not snippet:
            with results_lock:
                results.append((idx_orig, "valid", job))
            return

        try:
            prompt = _PROMPT.format(max_years=max_years, snippet=snippet)
            raw = get_llm_client("validation").complete(
                system=_SYSTEM,
                user=prompt,
                model=model,
                max_tokens=max_tokens,
            )
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                ).strip()
            result = json.loads(raw)

            if not result.get("is_active", True):
                reason = result.get("reason", "inactive")
                logger.info(f"{prefix}: inactive: {reason}")
                with results_lock:
                    results.append((idx_orig, "rejected", {**job, "_rejection_reason": reason}))
                return

            if result.get("over_experience", False):
                reason = result.get("reason", "over_experience")
                logger.info(f"{prefix}: over experience limit: {reason}")
                with results_lock:
                    results.append((idx_orig, "rejected", {**job, "_rejection_reason": reason}))
                return

            logger.info(f"{prefix}: valid")
            with results_lock:
                results.append((idx_orig, "valid", job))

        except Exception as e:
            logger.warning(f"{prefix}: validation error ({e}) -- passing through")
            with results_lock:
                results.append((idx_orig, "valid", job))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_validate_job, enumerate(jobs)))

    results.sort(key=lambda t: t[0])
    valid = [job for _, kind, job in results if kind == "valid"]
    rejected = [job for _, kind, job in results if kind == "rejected"]

    logger.info(f"[validate] {len(valid)} valid, {len(rejected)} rejected of {len(jobs)}")
    return valid, rejected
