"""Tests for pipeline/scorer.py — all LLM calls are mocked."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pipeline import scorer

CONFIG = {
    'scoring': {
        'min_fit_score': 80,
        'max_years_experience_required': 4,
        'strategic_overrides': [
            {'company': 'Infineon', 'reason': 'strategic', 'min_score_override': 75},
        ],
    },
}

JOB = {
    'title': 'Product Manager',
    'company': 'TestCo',
    'url': 'https://testco.com/job',
    'snippet': 'PM role with agile, roadmapping, stakeholder management.',
}


def _mock_client(text: str) -> MagicMock:
    """Return a mock LLMClient whose complete() returns text."""
    mock = MagicMock()
    mock.complete.return_value = text
    return mock


# ── check_strategic_override ────────────────────────────────────────────────

def test_strategic_override_matches():
    result = scorer.check_strategic_override({'company': 'Infineon Technologies'}, CONFIG)
    assert result == 75


def test_strategic_override_no_match():
    result = scorer.check_strategic_override({'company': 'Unknown Corp'}, CONFIG)
    assert result is None


# ── score() ─────────────────────────────────────────────────────────────────

def test_score_valid_response():
    payload = json.dumps({
        'score': 85,
        'matched_keywords': ['agile', 'roadmap'],
        'gaps': ['automotive'],
        'years_exp_required': 3,
    })
    with patch('pipeline.scorer.get_llm_client', return_value=_mock_client(payload)):
        result = scorer.score(JOB, CONFIG)

    assert result['score'] == 85
    assert result['matched_keywords'] == ['agile', 'roadmap']
    assert result['gaps'] == ['automotive']
    assert result['job'] is JOB


def test_score_json_parse_error():
    with patch('pipeline.scorer.get_llm_client', return_value=_mock_client('not json')):
        result = scorer.score(JOB, CONFIG)

    assert result['score'] == 0
    assert 'parse error' in result['gaps']
    assert result['job'] is JOB


def test_score_api_error():
    mock = MagicMock()
    mock.complete.side_effect = Exception('API down')
    with patch('pipeline.scorer.get_llm_client', return_value=mock):
        result = scorer.score(JOB, CONFIG)

    assert result['score'] == 0
    assert 'api error' in result['gaps']


# ── filter_matches() ─────────────────────────────────────────────────────────

def _score_result(score_val, years=3, company='TestCo'):
    job = {**JOB, 'company': company}
    return {'score': score_val, 'matched_keywords': [], 'gaps': [], 'years_exp_required': years, 'job': job}


def test_filter_passes_above_threshold():
    with patch.object(scorer, 'score', return_value=_score_result(85)):
        matches = scorer.filter_matches([JOB], config=CONFIG)
    assert len(matches) == 1


def test_filter_rejects_below_threshold():
    with patch.object(scorer, 'score', return_value=_score_result(60)):
        matches = scorer.filter_matches([JOB], config=CONFIG)
    assert len(matches) == 0


def test_filter_rejects_too_many_years():
    with patch.object(scorer, 'score', return_value=_score_result(90, years=10)):
        matches = scorer.filter_matches([JOB], config=CONFIG)
    assert len(matches) == 0


def test_filter_strategic_override_lowers_threshold():
    # 78 is below 80 but above Infineon's override of 75
    with patch.object(scorer, 'score', return_value=_score_result(78, company='Infineon')):
        matches = scorer.filter_matches([{**JOB, 'company': 'Infineon'}], config=CONFIG)
    assert len(matches) == 1


def test_filter_strategic_override_still_fails_if_too_low():
    # 70 is below even Infineon's 75 override
    with patch.object(scorer, 'score', return_value=_score_result(70, company='Infineon')):
        matches = scorer.filter_matches([{**JOB, 'company': 'Infineon'}], config=CONFIG)
    assert len(matches) == 0


def test_filter_null_years_not_rejected():
    result = _score_result(90)
    result['years_exp_required'] = None
    with patch.object(scorer, 'score', return_value=result):
        matches = scorer.filter_matches([JOB], config=CONFIG)
    assert len(matches) == 1
