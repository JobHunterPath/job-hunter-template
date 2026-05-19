"""
Job hunt pipeline orchestrator.

Two modes, one entry point:

  hunt (default)   Scrape jobs from configured companies and boards.
                   Runs daily via GitHub Actions.

  tailor-links     Tailor resume for a specific list of URLs.
                   Pass --links "URL1, URL2" or set TAILOR_LINKS env var.
                   Discovered companies are registered to search_config.yml regions.

Usage:
  python scripts/pipeline/orchestrator.py
  python scripts/pipeline/orchestrator.py --region berlin
  python scripts/pipeline/orchestrator.py --mode tailor-links --links "https://url1, https://url2"
  python scripts/pipeline/orchestrator.py --mode tailor-links --skip-score --force
"""

import argparse
import json
import os
import re
import sys
import yaml
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List

from core.config import setup_logging, load_api_config, profile_path
from core.utils import title_matches, url_is_alive
from sources.scraper import scrape
from pipeline.validator import validate
from pipeline.scorer import filter_matches
from pipeline.tailorer import tailor
from pipeline.cover_writer import write_cover
from pipeline.pdf_compiler import compile_tex
from tracking.tracker import filter_new_jobs, load_processed, mark_processed
from sources.jd_fetcher import fetch_jd

logger = setup_logging(log_level=os.environ.get("LOG_LEVEL", "INFO"))

TODAY = datetime.today().strftime("%Y-%m-%d")
MAX_TAILORING_PER_RUN = 15

# scripts/pipeline/ → scripts/ → repo root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOBS_DIR = profile_path("output_dir", "jobs")
JOBS_DIR.mkdir(exist_ok=True)


# ── Utilities ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s+", "-", text.strip())[:50]


TABLE_START = "<!-- JOBS_TABLE_START -->"
TABLE_END = "<!-- JOBS_TABLE_END -->"
TABLE_HEADER = "| Date | Job | Score | Files |\n|---|---|---|---|"


def _parse_urls(raw: str) -> list[str]:
    """Split a comma- or newline-separated string of URLs into a clean list."""
    return [
        token.strip()
        for token in raw.replace(",", "\n").splitlines()
        if token.strip() and not token.strip().startswith("#")
    ]


def _load_search_rules() -> tuple[list[str], list[str]]:
    """Return configured accepted job titles and excluded title terms."""
    search_cfg_path = Path(ROOT) / "config" / "search_config.yml"
    try:
        data = yaml.safe_load(search_cfg_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return [], []

    title_filters = data.get("global_search", {}).get("job_titles", [])
    excluded_title_terms = data.get("exclusion_rules", {}).get("excluded_title_terms", [])
    return title_filters, excluded_title_terms


def _parse_existing_rows(table_body: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in table_body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        url_match = re.search(r"\]\((https?://[^)]+)\)", line)
        if url_match:
            rows[url_match.group(1)] = line
    return rows


def update_readme(matches: List[dict]) -> None:
    logger.info(f"[readme] Updating with {len(matches)} job(s)")
    readme_path = Path(ROOT) / "README.md"
    try:
        content = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        start_idx = content.find(TABLE_START)
        end_idx = content.find(TABLE_END)
        if start_idx == -1 or end_idx == -1:
            logger.warning("[readme] Markers not found — skipping update")
            return
        table_block = content[start_idx + len(TABLE_START):end_idx]
        existing_rows = _parse_existing_rows(table_block)
        for m in sorted(matches, key=lambda x: x["score"], reverse=True):
            job = m["job"]
            if job["url"] in existing_rows:
                continue
            slug = f"{TODAY}_{slugify(job['company'])}_{slugify(job['title'])}"
            existing_rows[job["url"]] = (
                f"| {TODAY} | [{job['title']} @ {job['company']}]({job['url']})"
                f" | {m['score']} | [Files](jobs/{slug}/) |"
            )
        all_rows = sorted(existing_rows.values(), reverse=True)
        new_table = f"\n{TABLE_HEADER}\n" + "\n".join(all_rows) + "\n"
        updated = (
            content[:start_idx]
            + TABLE_START + new_table + TABLE_END
            + content[end_idx + len(TABLE_END):]
        )
        readme_path.write_text(updated, encoding="utf-8")
        logger.info(f"[readme] Table now has {len(all_rows)} row(s)")
    except Exception as e:
        logger.error(f"[readme] Update failed: {e}")
        raise


# ── Job sources ────────────────────────────────────────────────────────────────

def _jobs_from_hunt(region: str | None = None) -> tuple[list[dict], set, set]:
    """Scrape configured companies/boards, then deduplicate against processed jobs."""
    jobs = scrape(region=region)
    if not jobs:
        return [], set(), set()
    new_jobs, existing_urls, existing_titles = filter_new_jobs(jobs)
    return new_jobs, existing_urls, existing_titles


def _jobs_from_links(raw: str, force: bool, existing_urls: set) -> list[dict]:
    """
    Fetch job descriptions from a list of direct URLs.

    Skips URLs already in applied_jobs.yml unless --force is set.
    Registers each new company to search_config.yml regions for future hunt runs.
    """
    jobs = []
    title_filters, excluded_title_terms = _load_search_rules()
    for url in _parse_urls(raw):
        if not force and url in existing_urls:
            logger.info(f"  [skip] Already processed (use --force to re-tailor): {url}")
            continue
        job = fetch_jd(url)
        if job:
            if not title_matches(job.get("title", ""), title_filters, excluded_title_terms):
                logger.info(
                    "  [skip] Irrelevant title after JD extraction: %s @ %s",
                    job.get("title", "?"),
                    job.get("company", "?"),
                )
                continue
            _register_company(job)
            jobs.append(job)
            logger.info(f"  fetched: {job['title']} @ {job['company']}")
        else:
            logger.warning(f"  could not fetch JD: {url}")
    return jobs


# ── Company registration ───────────────────────────────────────────────────────

_CAREER_URL_PATTERNS = [
    (r"(?:boards|job-boards)\.greenhouse\.io/([^/?#]+)", "boards.greenhouse.io/{0}"),
    (r"jobs\.lever\.co/([^/?#]+)",            "jobs.lever.co/{0}"),
    (r"jobs\.smartrecruiters\.com/([^/?#]+)", "jobs.smartrecruiters.com/{0}"),
    (r"jobs\.ashbyhq\.com/([^/?#]+)",         "jobs.ashbyhq.com/{0}"),
    (r"([^/.]+)\.careers\.hibob\.com",        "{0}.careers.hibob.com"),
    (r"([^/.]+)\.jobs\.personio\.de",         "{0}.jobs.personio.de"),
    (r"([^/.]+)\.breezy\.hr",                 "{0}.breezy.hr"),
    (r"([^/.]+)\.workable\.com",              "{0}.workable.com"),
    (r"([^/.]+)\.recruitee\.com",             "{0}.recruitee.com"),
]


def _extract_career_url(job_url: str) -> str | None:
    """Derive the ATS base/career URL from a specific job posting URL."""
    for pattern, template in _CAREER_URL_PATTERNS:
        m = re.search(pattern, job_url, re.IGNORECASE)
        if m:
            return template.format(m.group(1))
    return None


def _register_company(job: dict) -> None:
    """
    Add the job's company to search_config.yml regions so the daily hunt scraper picks it up.
    """
    career_url = _extract_career_url(job.get("url", ""))
    if not career_url:
        logger.debug(f"[register] Cannot derive career URL for {job.get('company')} — skipping")
        return

    company_name = job["company"]

    # ── search_config.yml (daily hunt scraper) ─────────────────────────────────
    search_cfg_path = Path(ROOT) / "config" / "search_config.yml"
    try:
        sc_data = yaml.safe_load(search_cfg_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        logger.warning("[register] search_config.yml not found — skipping scraper registration")
        return

    regions = sc_data.get("regions", {})
    added_to = []
    for region_name, region_config in regions.items():
        if not region_config.get("enabled", True):
            continue
        companies = region_config.get("companies", [])
        existing_names = {c.get("name", "").lower() for c in companies}
        if company_name.lower() not in existing_names:
            companies.append({"name": company_name, "career_url": career_url})
            region_config["companies"] = companies
            added_to.append(region_name)

    if added_to:
        search_cfg_path.write_text(
            yaml.dump(sc_data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        logger.info(f"[register] Added {company_name} ({career_url}) → search_config.yml regions: {', '.join(added_to)}")
    else:
        logger.debug(f"[register] {company_name} already in all enabled regions")


# ── Snippet enrichment ────────────────────────────────────────────────────────

def _enrich_snippets(jobs: list[dict]) -> list[dict]:
    """
    Fetch full JD content for jobs with sparse or missing snippets.

    ATS APIs (Greenhouse, Lever, Ashby, etc.) return rich descriptions directly.
    Brave Search results carry only a short meta snippet, and HiBob jobs return
    an empty snippet (Playwright listing scraper gets titles only). Enriching
    before validation and scoring significantly improves quality for both cases.
    """
    sparse = [
        j for j in jobs
        if not j.get("snippet")
        or len(j.get("snippet", "")) < 300
        or j.get("source", "").startswith("Brave")
    ]
    if not sparse:
        return jobs

    logger.info(f"[pipeline] Enriching {len(sparse)} job(s) with sparse snippets...")
    enriched: dict[str, dict] = {}

    def _fetch_one(job: dict) -> None:
        logger.info(f"  enriching: {job['title'][:50]} @ {job['company']}")
        full = fetch_jd(job["url"], use_llm=False)
        if full and full.get("snippet"):
            enriched[job["url"]] = {**job, "snippet": full["snippet"]}
            logger.info(f"    -> {len(full['snippet'])} chars")
        else:
            logger.warning(f"    -> enrichment failed, keeping original snippet")

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(_fetch_one, sparse))

    return [enriched.get(j["url"], j) for j in jobs]


def _drop_dead_urls_before_enrichment(jobs: list[dict], api_cfg: dict) -> list[dict]:
    """Avoid fetching full JDs for postings that already fail URL verification."""
    url_cfg = api_cfg.get("http", {}).get("url_verification", {})
    if not url_cfg.get("enabled", True):
        return jobs

    timeout = int(url_cfg.get("timeout_seconds", 5))
    alive: list[dict] = []
    rejected = 0
    for job in jobs:
        url = job.get("url", "")
        if url and not url_is_alive(url, timeout):
            rejected += 1
            logger.info(
                "[pipeline] Skipping dead URL before enrichment: %s @ %s",
                job.get("title", "?")[:50],
                job.get("company", "?"),
            )
            continue
        alive.append(job)

    if rejected:
        logger.info("[pipeline] Dropped %s dead URL(s) before enrichment", rejected)
    return alive


# ── Match processing ───────────────────────────────────────────────────────────

def _process_match(match: dict) -> bool:
    """
    Tailor, compile PDF, and write cover letter for a single matched job.
    Returns True on full success, False if a critical step fails.
    PDF compilation is non-critical — failure there does not abort the job.
    """
    job = match["job"]
    slug = f"{TODAY}_{slugify(job['company'])}_{slugify(job['title'])}"
    job_dir = JOBS_DIR / slug
    job_dir.mkdir(exist_ok=True)

    meta = {
        "date": TODAY,
        "title": job["title"],
        "company": job["company"],
        "url": job["url"],
        "posted": job.get("posted", ""),
        "score": match["score"],
        "matched_keywords": match.get("matched_keywords", []),
        "gaps": match.get("gaps", []),
        "source": job.get("source", "scraped"),
    }
    (job_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (job_dir / "jd.md").write_text(
        f"# {job['title']} @ {job['company']}\n\n"
        f"**URL:** {job['url']}\n\n"
        f"**Posted:** {job.get('posted', 'Unknown')}\n\n"
        f"{job['snippet']}",
        encoding="utf-8",
    )

    logger.info("  Tailoring resume...")
    try:
        tex_path = job_dir / "resume_tailored.tex"
        tex_path.write_text(tailor(match), encoding="utf-8")
        logger.info("  resume tailored")
    except Exception as e:
        logger.error(f"  tailoring failed: {e}")
        return False

    logger.info("  Compiling PDF...")
    try:
        pdf = compile_tex(str(tex_path), str(job_dir))
        logger.info(f"  PDF {'generated' if pdf else '(LaTeX saved, no PDF)'}")
    except Exception as e:
        logger.warning(f"  PDF compilation failed: {e} — continuing")

    logger.info("  Writing cover letter...")
    try:
        write_cover(match, str(job_dir))
        logger.info("  cover letter written")
    except Exception as e:
        logger.error(f"  cover letter failed: {e}")
        return False

    logger.info(f"  complete → jobs/{slug}/")
    return True


def _process_jobs(
    jobs: list[dict],
    *,
    skip_validate: bool,
    skip_score: bool,
    max_years: int,
    api_cfg: dict,
) -> list[dict]:
    """
    Shared downstream pipeline: validate → score → tailor → cover → PDF.
    Returns the list of successfully processed match dicts.
    """
    if not skip_validate:
        logger.info(f"[pipeline] Validating {len(jobs)} job(s)...")
        jobs, rejected = validate(jobs, max_years=max_years, api_cfg=api_cfg)
        for j in rejected:
            logger.info(f"  Rejected: {j.get('title')} @ {j.get('company')}: {j.get('_rejection_reason')}")
        if not jobs:
            logger.warning("[pipeline] All jobs rejected during validation.")
            return []
        logger.info(f"[pipeline] {len(jobs)} job(s) passed validation")
    else:
        logger.info("[pipeline] Validation skipped (--skip-validate)")

    if skip_score:
        logger.info("[pipeline] Scoring skipped (--skip-score) — processing all")
        matches = [{"job": j, "score": 0, "matched_keywords": [], "gaps": []} for j in jobs]
    else:
        logger.info(f"[pipeline] Scoring {len(jobs)} job(s)...")
        matches = filter_matches(jobs)
        if not matches:
            logger.warning("[pipeline] No jobs passed the scoring threshold.")
            return []
        logger.info(f"[pipeline] {len(matches)} job(s) passed scoring")

    if len(matches) > MAX_TAILORING_PER_RUN:
        matches = sorted(matches, key=lambda m: m.get("score", 0), reverse=True)
        logger.info(
            "[pipeline] Hard limit: tailoring top %s of %s matched job(s)",
            MAX_TAILORING_PER_RUN,
            len(matches),
        )
        matches = matches[:MAX_TAILORING_PER_RUN]

    logger.info(f"[pipeline] Processing {len(matches)} matched job(s)...")
    processed = []
    for idx, match in enumerate(matches, 1):
        job = match["job"]
        logger.info(
            f"[pipeline] [{idx}/{len(matches)}] "
            f"{job['title']} @ {job['company']} (score={match['score']})"
        )
        try:
            if _process_match(match):
                processed.append(match)
        except Exception as e:
            logger.error(f"  Unexpected error: {e}", exc_info=True)

    return processed


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Job hunt pipeline — hunt or tailor specific links.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/pipeline/orchestrator.py
  python scripts/pipeline/orchestrator.py --region berlin
  python scripts/pipeline/orchestrator.py --mode tailor-links --links "https://url1, https://url2"
  python scripts/pipeline/orchestrator.py --mode tailor-links --skip-score --force
        """,
    )
    p.add_argument(
        "--mode",
        choices=["hunt", "tailor-links"],
        default="hunt",
        help="hunt: scrape configured companies (default). tailor-links: process specific URLs.",
    )
    p.add_argument(
        "--links",
        metavar="URLS",
        help="Comma-separated job URLs for tailor-links mode. "
             "Falls back to TAILOR_LINKS env var if omitted.",
    )
    p.add_argument(
        "--region",
        help="Optional search_config.yml region key for hunt mode, e.g. berlin. "
             "Omit to scrape all enabled regions.",
    )
    p.add_argument("--skip-score",    action="store_true", help="Bypass scoring threshold")
    p.add_argument("--skip-validate", action="store_true", help="Bypass validation checks")
    p.add_argument("--force",         action="store_true", help="Re-process already-tracked jobs")
    return p


def run(args: argparse.Namespace) -> int:
    logger.info(f"\n{'='*60}")
    region_label = args.region if args.mode == "hunt" and args.region else "all"
    logger.info(f"Pipeline | mode={args.mode} | region={region_label} | {TODAY}")
    logger.info(f"{'='*60}")

    api_cfg = load_api_config()
    scoring_cfg = yaml.safe_load(
        open(os.path.join(ROOT, "config", "scoring_config.yml"), encoding="utf-8")
    )
    max_years = scoring_cfg.get("scoring", {}).get("max_years_experience_required", 4)

    # ── Source jobs ────────────────────────────────────────────────────────────
    if args.mode == "hunt":
        logger.info("[pipeline] Step 1: Scraping and deduplicating jobs...")
        jobs, existing_urls, existing_titles = _jobs_from_hunt(args.region)
        if not jobs:
            logger.warning("[pipeline] No new jobs found. Exiting.")
            return 0

        jobs = _drop_dead_urls_before_enrichment(jobs, api_cfg)
        if not jobs:
            logger.warning("[pipeline] All scraped jobs failed URL verification before enrichment.")
            return 0

        logger.info("[pipeline] Step 1b: Enriching sparse job descriptions...")
        jobs = _enrich_snippets(jobs)

    else:  # tailor-links
        raw_links = args.links or os.environ.get("TAILOR_LINKS", "")
        if not raw_links:
            logger.error(
                "[pipeline] No URLs provided. "
                "Use --links 'URL1, URL2' or set the TAILOR_LINKS environment variable."
            )
            return 1
        existing_urls, existing_titles = load_processed()
        logger.info("[pipeline] Step 1: Fetching job descriptions from links...")
        jobs = _jobs_from_links(raw_links, args.force, existing_urls)
        if not jobs:
            logger.warning("[pipeline] No jobs fetched. Exiting.")
            return 2

    logger.info(f"[pipeline] {len(jobs)} job(s) ready for processing")

    # ── Shared downstream pipeline ─────────────────────────────────────────────
    processed = _process_jobs(
        jobs,
        skip_validate=args.skip_validate,
        skip_score=args.skip_score,
        max_years=max_years,
        api_cfg=api_cfg,
    )

    # ── Finalise ───────────────────────────────────────────────────────────────
    if processed:
        logger.info("[pipeline] Updating README and tracker...")
        update_readme(processed)
        mark_processed([m["job"] for m in processed], existing_urls, existing_titles)

    logger.info(f"\n{'='*60}")
    logger.info(f"[pipeline] Done. {len(processed)} job(s) processed.")
    logger.info(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(run(_build_parser().parse_args()))
