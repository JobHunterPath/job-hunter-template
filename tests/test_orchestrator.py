"""Tests for pipeline/orchestrator.py orchestration safeguards."""

from unittest.mock import patch

from pipeline import orchestrator


def _match(idx: int) -> dict:
    return {
        "score": idx,
        "matched_keywords": [],
        "gaps": [],
        "job": {
            "title": f"Product Manager {idx}",
            "company": "TestCo",
            "url": f"https://example.com/jobs/{idx}",
            "snippet": "Product role.",
        },
    }


def test_process_jobs_caps_tailoring_to_15_highest_scores():
    jobs = [_match(idx)["job"] for idx in range(20)]
    matches = [_match(idx) for idx in range(20)]
    processed_titles = []

    def fake_process(match):
        processed_titles.append(match["job"]["title"])
        return True

    with patch("pipeline.orchestrator.filter_matches", return_value=matches), \
         patch("pipeline.orchestrator._process_match", side_effect=fake_process):
        processed = orchestrator._process_jobs(
            jobs,
            skip_validate=True,
            skip_score=False,
            max_years=4,
            api_cfg={},
        )

    assert len(processed) == orchestrator.MAX_TAILORING_PER_RUN
    assert processed_titles == [f"Product Manager {idx}" for idx in range(19, 4, -1)]


def test_jobs_from_links_skips_irrelevant_extracted_title():
    irrelevant = {
        "title": "Product Engineer",
        "company": "TestCo",
        "url": "https://example.com/jobs/engineer",
        "snippet": "Engineering role.",
    }

    with patch("pipeline.orchestrator._load_search_rules", return_value=(["Product Manager"], ["engineer"])), \
         patch("pipeline.orchestrator.fetch_jd", return_value=irrelevant), \
         patch("pipeline.orchestrator._register_company") as register:
        jobs = orchestrator._jobs_from_links("https://example.com/jobs/engineer", False, set())

    assert jobs == []
    register.assert_not_called()
