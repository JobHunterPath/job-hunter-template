"""
Weekly job: discovers new Berlin tech companies via an LLM + Brave,
validates their career pages exist, and appends them to companies.yml.
Deduplicates against existing entries automatically.
"""

import os
import re
import json
import requests
import yaml

from core.config import BRAVE_API_KEY, load_api_config
from core.llm_client import get_llm_client

# scripts/discovery/ → scripts/ → repo root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMPANIES_FILE = os.path.join(ROOT, "config", "companies.yml")
SEARCH_CONFIG_FILE = os.path.join(ROOT, "config", "search_config.yml")

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": BRAVE_API_KEY,
}

# ATS URL patterns and the canonical career_url format to store in companies.yml.
# Order matters: more specific patterns first.
ATS_PATTERNS = [
    (r"boards\.greenhouse\.io/([^/?#\s]+)",       "boards.greenhouse.io/{slug}"),
    (r"job-boards\.greenhouse\.io/([^/?#\s]+)",   "job-boards.greenhouse.io/{slug}"),
    (r"jobs\.lever\.co/([^/?#\s]+)",              "jobs.lever.co/{slug}"),
    (r"apply\.workable\.com/([^/?#\s]+)",         "apply.workable.com/{slug}"),
    (r"jobs\.ashbyhq\.com/([^/?#\s]+)",           "jobs.ashbyhq.com/{slug}"),
    (r"jobs\.smartrecruiters\.com/([^/?#\s]+)",   "jobs.smartrecruiters.com/{slug}"),
    # Subdomain-based ATS: slug is the company subdomain
    (r"([^./]+)\.careers\.hibob\.com",            "{slug}.careers.hibob.com"),
    (r"([^./]+)\.jobs\.personio\.de",             "{slug}.jobs.personio.de"),
    (r"([^./]+)\.recruitee\.com",                 "{slug}.recruitee.com"),
    # jobs.personio.com uses path-based slugs
    (r"jobs\.personio\.com/([^/?#\s]+)",          "jobs.personio.com/{slug}"),
]

CAREER_PATH_PATTERNS = ["/careers", "/jobs", "/work-with-us", "/join-us"]

# One prompt per sector — run independently so every vertical gets proper coverage.
SECTOR_PROMPTS = [
    {
        "sector": "automotive & mobility",
        "prompt": (
            "List 10 companies based in Berlin (or with a significant Berlin office) "
            "in automotive tech, connected vehicles, EV charging, fleet management, "
            "ride-hailing software, or urban mobility platforms. Requirements:\n"
            "- English as primary working language\n"
            "- Known to hire Product Owners or Product Managers\n"
            "- NOT defence, military, weapons, banking, or gambling companies\n"
            "- NOT already in this list: {existing}\n\n"
            "Return ONLY a valid JSON array of company name strings. "
            "No explanation, no markdown, no code fences.\n"
            'Example: ["Volkswagen Digital Solutions", "Volocopter", "Lilium", "Sono Motors"]'
        ),
    },
    {
        "sector": "commercial aviation & travel tech",
        "prompt": (
            "List 10 companies based in Berlin (or with a significant Berlin office) "
            "in commercial airline software, airport systems, aviation operations tech, "
            "travel booking platforms, or tourism tech. Requirements:\n"
            "- English as primary working language\n"
            "- Known to hire Product Owners or Product Managers\n"
            "- Civil/commercial aviation ONLY — NO defence, military, or weapons companies\n"
            "- NOT already in this list: {existing}\n\n"
            "Return ONLY a valid JSON array of company name strings. "
            "No explanation, no markdown, no code fences.\n"
            'Example: ["Lufthansa Systems", "Hahn Air", "Amadeus", "TUI Group"]'
        ),
    },
    {
        "sector": "industrial & enterprise tech",
        "prompt": (
            "List 10 companies based in Berlin (or with a significant Berlin office) "
            "in industrial automation, manufacturing software, Industry 4.0, IIoT platforms, "
            "enterprise SaaS, B2B analytics, or supply-chain tech. "
            "Large corporates with Berlin offices (e.g. Siemens, Bosch) are welcome. Requirements:\n"
            "- English as primary working language\n"
            "- Known to hire Product Owners or Product Managers\n"
            "- NOT defence, military, weapons, banking, or gambling companies\n"
            "- NOT already in this list: {existing}\n\n"
            "Return ONLY a valid JSON array of company name strings. "
            "No explanation, no markdown, no code fences.\n"
            'Example: ["Siemens", "Bosch", "Celonis", "Software AG", "Enpal"]'
        ),
    },
    {
        "sector": "Berlin tech startups & scale-ups",
        "prompt": (
            "List 10 Berlin-based tech startups or scale-ups (ideally Series A–D, founded after 2010) "
            "in any sector EXCEPT banking/crypto-lending, gambling, defence, military, or weapons. "
            "Sectors of particular interest: fintech (non-bank), health tech, climate tech, "
            "logistics, marketplace, developer tools, SaaS. Requirements:\n"
            "- English as primary working language\n"
            "- Known to hire Product Owners or Product Managers\n"
            "- NOT already in this list: {existing}\n\n"
            "Return ONLY a valid JSON array of company name strings. "
            "No explanation, no markdown, no code fences.\n"
            'Example: ["Forto", "Moss", "Taxfix", "Pitch", "Hygraph"]'
        ),
    },
]


def load_companies() -> tuple[list[dict], set[str]]:
    with open(COMPANIES_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    companies = data.get("companies", [])
    excluded = {e.lower() for e in data.get("excluded", [])}

    # Also pull in names/URLs from search_config.yml so we don't
    # re-discover companies that are already being scraped, and
    # also honour that file's excluded_companies list.
    if os.path.exists(SEARCH_CONFIG_FILE):
        with open(SEARCH_CONFIG_FILE, encoding="utf-8") as f:
            sc = yaml.safe_load(f) or {}
        for region in sc.get("regions", {}).values():
            for c in region.get("companies", []):
                if not any(x["name"].lower() == c["name"].lower() for x in companies):
                    companies.append({"name": c["name"], "career_url": c["career_url"]})
        for name in sc.get("excluded_companies", []):
            excluded.add(name.lower())

    return companies, excluded


def save_companies(companies: list[dict], excluded: set[str]):
    header = (
        "# Source of truth for all tracked Berlin companies.\n"
        "# Auto-discovery appends here weekly.\n"
        "# You can also add/remove manually anytime.\n"
        "# Format: name + career_url (domain or ATS path)\n\n"
    )
    with open(COMPANIES_FILE, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(
            {
                "companies": companies,
                "excluded": sorted(list(excluded)),
            },
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )


def get_existing_names(companies: list[dict]) -> set[str]:
    return {c["name"].lower() for c in companies}


def get_existing_urls(companies: list[dict]) -> set[str]:
    return {c["career_url"].lower() for c in companies}


def discover_company_names(existing: list[dict]) -> list[str]:
    """Run one LLM query per sector and combine the results."""
    existing_names = ", ".join(c["name"] for c in existing[:60])
    seen: set[str] = set()
    all_names: list[str] = []

    for spec in SECTOR_PROMPTS:
        prompt = spec["prompt"].format(existing=existing_names)
        print(f"[discover] Querying sector: {spec['sector']}...")
        try:
            _llm = load_api_config().get("llm", {})
            _model = _llm.get("models", {}).get("discovery", "claude-sonnet-4-6")
            _max_tokens = _llm.get("max_tokens", {}).get("discovery", 400)
            raw = get_llm_client("discovery").complete(
                user=prompt,
                model=_model,
                max_tokens=_max_tokens,
            )
            names = json.loads(raw)
            added = 0
            for name in names:
                if isinstance(name, str) and name.lower() not in seen:
                    seen.add(name.lower())
                    all_names.append(name)
                    added += 1
            print(f"  → {added} new suggestions")
        except Exception as e:
            print(f"  [discover] Sector '{spec['sector']}' failed: {e}")

    return all_names


def brave_search(query: str, count: int = 5) -> list[dict]:
    params = {
        "q": query,
        "count": count,
        "search_lang": "en",
        "country": "DE",
        "text_decorations": False,
    }
    resp = requests.get(
        BRAVE_URL, headers=BRAVE_HEADERS, params=params, timeout=15
    )
    resp.raise_for_status()
    return resp.json().get("web", {}).get("results", [])


def find_career_url(company_name: str, existing_urls: set[str]) -> dict | None:
    """
    Search Brave for the company's career page.

    Two passes:
      1. ATS-targeted query across all supported platforms.
      2. Broad career/jobs query for companies on custom domains.

    Returns a dict with name + career_url if found, None otherwise.
    """
    ats_sites = (
        "site:boards.greenhouse.io OR site:job-boards.greenhouse.io "
        "OR site:jobs.lever.co OR site:jobs.smartrecruiters.com "
        "OR site:apply.workable.com OR site:jobs.ashbyhq.com "
        "OR site:careers.hibob.com OR site:recruitee.com "
        "OR site:jobs.personio.de OR site:jobs.personio.com"
    )
    ats_query = f'"{company_name}" Berlin {ats_sites}'
    broad_query = f'"{company_name}" Berlin "Product Manager" OR "Product Owner" careers jobs'

    for query in (ats_query, broad_query):
        try:
            results = brave_search(query, count=7)
        except Exception as e:
            print(f"  [brave] Error searching for {company_name}: {e}")
            continue

        for result in results:
            url = result.get("url", "")

            for pattern, template in ATS_PATTERNS:
                match = re.search(pattern, url)
                if match:
                    slug = match.group(1).rstrip("/")
                    career_url = template.format(slug=slug)
                    if career_url.lower() not in existing_urls:
                        print(f"  [found] {company_name} -> {career_url} (ATS)")
                        return {"name": company_name, "career_url": career_url}

            for path in CAREER_PATH_PATTERNS:
                if path in url.lower():
                    domain_match = re.match(r"https?://([^/]+)", url)
                    if domain_match:
                        domain = domain_match.group(1)
                        career_url = f"{domain}{path}"
                        if career_url.lower() not in existing_urls:
                            print(f"  [found] {company_name} -> {career_url} (direct)")
                            return {"name": company_name, "career_url": career_url}

    print(f"  [miss] No career page found for {company_name}")
    return None


def run():
    print("\n" + "="*50)
    print("Weekly Company Discovery")
    print("="*50 + "\n")

    existing, excluded = load_companies()
    existing_names = get_existing_names(existing)
    existing_urls = get_existing_urls(existing)
    print(f"[discover] Currently tracking {len(existing)} companies")
    print(f"[discover] Excluding {len(excluded)} companies: {sorted(excluded)}")

    sectors = ", ".join(s["sector"] for s in SECTOR_PROMPTS)
    print(f"[discover] Querying LLM across {len(SECTOR_PROMPTS)} sectors: {sectors}")
    suggested = discover_company_names(existing)
    print(f"[discover] LLM suggested {len(suggested)} companies total: {suggested}\n")

    new_names = [
        name for name in suggested
        if name.lower() not in existing_names
        and name.lower() not in excluded
    ]

    skipped_excluded = [name for name in suggested if name.lower() in excluded]
    if skipped_excluded:
        print(f"[discover] Excluded by exclusion list: {skipped_excluded}")

    print(f"[discover] {len(new_names)} not yet tracked: {new_names}\n")

    new_entries = []
    for name in new_names:
        print(f"[discover] Looking up: {name}")
        entry = find_career_url(name, existing_urls)
        if entry:
            new_entries.append(entry)
            existing_urls.add(entry["career_url"].lower())

    if not new_entries:
        print("\n[discover] No new companies to add.")
        return

    updated = existing + new_entries
    save_companies(updated, excluded)

    print(f"\n[discover] Added {len(new_entries)} new companies:")
    for entry in new_entries:
        print(f"  + {entry['name']} -> {entry['career_url']}")
    print(f"\n[discover] companies.yml now tracks {len(updated)} companies")


if __name__ == "__main__":
    run()
