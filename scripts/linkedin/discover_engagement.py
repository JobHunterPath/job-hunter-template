"""Discover LinkedIn people/posts and draft non-transactional networking text."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from core.config import setup_logging
from linkedin.common import (
    append_section,
    complete_linkedin,
    configured_path,
    extract_json,
    format_yaml_list,
    load_linkedin_config,
    today_slug,
)
from sources.search_providers import search_web

logger = setup_logging(log_level=os.environ.get("LOG_LEVEL", "INFO"))

SYSTEM = """You curate LinkedIn networking and engagement candidates.
Return JSON only. Do not include markdown fences."""

PROMPT = """Review these public search results and create human-reviewed
LinkedIn engagement and networking suggestions.

The user will act manually. Never instruct automatic posting, commenting,
following, connecting, or messaging.

POSITIONING:
{positioning}

TARGET PEOPLE:
{target_people}

TOPICS:
{topics}

MESSAGE RULES:
- no job ask
- no referral ask
- no generic flattery
- no "pick your brain"
- max {max_message_words} words per message
- ask for discussion only when it feels natural

FORBIDDEN PHRASES:
{forbidden_phrases}

SEARCH RESULTS:
{results}

Return a JSON object with keys "people" and "posts".
Each person: name, role_or_context, url, why_relevant, relationship_type,
suggested_action, message_variants.
Each post: author_or_source, topic, url, why_relevant, suggested_comment."""


def _collect_results(config: dict) -> list[dict]:
    discovery = config.get("engagement_discovery", {})
    region = discovery.get("region", {})
    topics = discovery.get("topics", [])
    domains = discovery.get("linkedin_domains", {})
    results_per_query = int(discovery.get("results_per_query", 5))

    collected: list[dict] = []
    seen = set()
    for topic in topics:
        queries = [
            f'site:{domains.get("people", "linkedin.com/in")} "{topic}"',
            f'site:{domains.get("posts", "linkedin.com/posts")} "{topic}"',
        ]
        for query in queries:
            for item in search_web(query, region, count=results_per_query):
                url = item.get("url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                collected.append({"query": query, **item})
    return collected


def _render_people(items: list[dict]) -> str:
    if not items:
        return "_No people suggestions returned._"
    sections = []
    for item in items:
        messages = item.get("message_variants") or []
        if isinstance(messages, list):
            messages_text = "\n".join(f"  - {msg}" for msg in messages)
        else:
            messages_text = f"  - {messages}"
        sections.append(
            f"""### {item.get('name', 'Unknown person')}

- Role/context: {item.get('role_or_context', '')}
- Link: {item.get('url', '')}
- Why relevant: {item.get('why_relevant', '')}
- Relationship type: {item.get('relationship_type', '')}
- Suggested action: {item.get('suggested_action', 'review manually')}
- Ask readiness: cold
- Message variants:
{messages_text}
"""
        )
    return "\n\n".join(sections)


def _render_posts(items: list[dict]) -> str:
    if not items:
        return "_No post suggestions returned._"
    sections = []
    for item in items:
        sections.append(
            f"""### {item.get('topic', 'Post to review')}

- Author/source: {item.get('author_or_source', '')}
- Link: {item.get('url', '')}
- Why relevant: {item.get('why_relevant', '')}
- Suggested comment: {item.get('suggested_comment', '')}
- Action: review manually
"""
        )
    return "\n\n".join(sections)


def discover(config_path: Path | None = None) -> dict:
    config = load_linkedin_config(config_path)
    raw_results = _collect_results(config)
    if not raw_results:
        logger.warning("[linkedin] No LinkedIn search results found.")
        return {"people": [], "posts": []}

    discovery = config.get("engagement_discovery", {})
    networking = config.get("networking", {})
    prompt = PROMPT.format(
        positioning=config.get("positioning", ""),
        target_people=format_yaml_list(networking.get("target_people", [])),
        topics=format_yaml_list(discovery.get("topics", [])),
        max_message_words=int(networking.get("max_message_words", 70)),
        forbidden_phrases=format_yaml_list(config.get("forbidden_phrases", [])),
        results=format_yaml_list([
            f"{item.get('title', '')} | {item.get('url', '')} | {item.get('description', '')}"
            for item in raw_results[:40]
        ]),
    )
    payload = extract_json(complete_linkedin(SYSTEM, prompt))
    if not isinstance(payload, dict):
        raise ValueError("Discovery response must be a JSON object")

    people = list(payload.get("people", []))[: int(networking.get("suggestions_per_run", 8))]
    posts = list(payload.get("posts", []))[: int(discovery.get("posts_per_run", 8))]

    append_section(
        configured_path(config, "networking"),
        f"## {today_slug()}\n\n{_render_people(people)}",
    )
    append_section(
        configured_path(config, "engagement"),
        f"## {today_slug()}\n\n{_render_posts(posts)}",
    )
    logger.info("[linkedin] Added %s people and %s post suggestions.", len(people), len(posts))
    return {"people": people, "posts": posts}


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover LinkedIn engagement and networking suggestions.")
    parser.add_argument("--config", type=Path, help="Path to linkedin/config.yml")
    args = parser.parse_args()
    discover(args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
