"""Tests for pipeline/tailorer.py — all LLM calls are mocked."""

from unittest.mock import MagicMock, patch

from pipeline import tailorer

MATCH = {
    'job': {
        'title': 'Product Manager',
        'company': 'TestCo',
        'snippet': 'PM role requiring agile, roadmapping.',
    },
    'matched_keywords': ['agile', 'roadmapping'],
    'gaps': ['automotive'],
    'score': 85,
}

SAMPLE_LATEX = r"""\documentclass{altacv}
\begin{document}
\section{Experience}
\cvevent{Product Owner}{ExampleCo}{2021--Present}{Target City}
\begin{itemize}
\item Led platform product strategy
\end{itemize}
\end{document}"""


def _mock_client(text: str) -> MagicMock:
    mock = MagicMock()
    mock.complete.return_value = text
    return mock


def test_tailor_returns_llm_output():
    with patch('pipeline.tailorer.get_llm_client', return_value=_mock_client(SAMPLE_LATEX)):
        result = tailorer.tailor(MATCH)
    assert result == SAMPLE_LATEX


def test_tailor_output_starts_with_backslash():
    with patch('pipeline.tailorer.get_llm_client', return_value=_mock_client(SAMPLE_LATEX)):
        result = tailorer.tailor(MATCH)
    assert result.startswith('\\')


def test_tailor_falls_back_to_base_tex_on_api_error():
    mock = MagicMock()
    mock.complete.side_effect = Exception('API down')
    with patch('pipeline.tailorer.get_llm_client', return_value=mock):
        result = tailorer.tailor(MATCH)
    assert result == tailorer.BASE_TEX


def test_tailor_returns_non_latex_response_unchanged():
    with patch('pipeline.tailorer.get_llm_client', return_value=_mock_client('plain text response')):
        result = tailorer.tailor(MATCH)
    assert result == 'plain text response'


def test_tailor_passes_keywords_and_gaps_in_prompt():
    captured = {}

    def capture_complete(**kwargs):
        captured['user'] = kwargs.get('user', '')
        return SAMPLE_LATEX

    mock = MagicMock()
    mock.complete.side_effect = capture_complete

    with patch('pipeline.tailorer.get_llm_client', return_value=mock):
        tailorer.tailor(MATCH)

    assert 'agile' in captured['user']
    assert 'automotive' in captured['user']
