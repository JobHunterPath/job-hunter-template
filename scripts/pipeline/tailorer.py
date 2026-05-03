"""
Produces a tailored .tex resume per matched job.
Mirrors JD keywords in summary and bullets without fabricating metrics.
Tailoring strategy is configurable via tailoring_config.yml.
"""

import logging

from core.config import load_api_config, profile_path
from core.llm_client import get_llm_client

logger = logging.getLogger(__name__)

# scripts/pipeline/ → scripts/ → repo root
with open(profile_path("resume_tex", "resume.tex"), encoding="utf-8") as f:
    BASE_TEX = f.read()


SYSTEM = """You are editing a LaTeX resume.
Return ONLY the complete modified LaTeX file.
No markdown fences, no explanation, no commentary."""

PROMPT = """Tailor this LaTeX resume for the job description below.

STRICT RULES:
1. Do NOT invent metrics, titles, or skills not in the original.
2. Only modify: (a) the Summary section text, (b) bullet ordering within each role, (c) synonyms to mirror JD keywords naturally.
3. Summary must stay 4 lines or fewer. No em dashes.
4. Mirror these JD keywords where naturally possible: {keywords}
5. Keep all LaTeX commands and formatting intact.
6. Return the complete .tex file.

BASE RESUME:
{tex}

JOB DESCRIPTION:
{jd}

GAPS (do not fabricate these, simply do not emphasize them):
{gaps}"""


def tailor(match_result: dict) -> str:
    """
    Tailor the base resume for a specific job.

    Args:
        match_result: Scored match dict with job, matched_keywords, gaps.

    Returns:
        Modified LaTeX resume text (falls back to BASE_TEX on error).
    """
    job = match_result["job"]
    keywords = ", ".join(match_result.get("matched_keywords", []))
    gaps = ", ".join(match_result.get("gaps", []))

    api_cfg = load_api_config()
    llm = api_cfg.get("llm", {})
    model = llm.get("models", {}).get("tailoring", "claude-sonnet-4-6")
    max_tokens = llm.get("max_tokens", {}).get("tailoring", 4000)

    prompt = PROMPT.format(
        keywords=keywords,
        tex=BASE_TEX,
        jd=job["snippet"],
        gaps=gaps,
    )

    try:
        tailored_text = get_llm_client("tailoring").complete(
            system=SYSTEM,
            user=prompt,
            model=model,
            max_tokens=max_tokens,
        )
        logger.info(f"[tailor] Tailored for {job.get('title', '?')} @ {job.get('company', '?')}")

        if not tailored_text.startswith("\\"):
            logger.warning("[tailor] Response does not appear to be LaTeX.")

        return tailored_text
    except Exception as e:
        logger.error(f"[tailor] Error: {e} — returning base resume")
        return BASE_TEX
