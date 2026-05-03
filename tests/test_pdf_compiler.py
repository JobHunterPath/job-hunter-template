"""Tests for pipeline/pdf_compiler.py — subprocess and shutil.which are mocked."""

from unittest.mock import MagicMock, patch

from pipeline import pdf_compiler


def _fake_run_creates_pdf(pdf_path):
    """Returns a side_effect that writes a fake PDF file on subprocess.run calls."""
    def _run(cmd, **kwargs):
        if 'pdflatex' in ' '.join(str(c) for c in cmd):
            pdf_path.write_bytes(b'%PDF-fake')
        result = MagicMock()
        result.stdout = ''
        return result
    return _run


def test_compile_tex_returns_pdf_path_when_pdflatex_succeeds(tmp_path):
    tex = tmp_path / 'resume.tex'
    tex.write_text(r'\documentclass{article}\begin{document}x\end{document}')
    expected_pdf = tmp_path / 'resume.pdf'

    with patch('pipeline.pdf_compiler.shutil.which', return_value='/usr/bin/pdflatex'), \
         patch('pipeline.pdf_compiler.subprocess.run', side_effect=_fake_run_creates_pdf(expected_pdf)):
        result = pdf_compiler.compile_tex(str(tex), str(tmp_path))

    assert result == str(expected_pdf)


def test_compile_tex_returns_none_when_no_pdf_produced(tmp_path):
    tex = tmp_path / 'resume.tex'
    tex.write_text('bad latex')
    mock_result = MagicMock()
    mock_result.stdout = 'LaTeX error'

    with patch('pipeline.pdf_compiler.shutil.which', return_value='/usr/bin/pdflatex'), \
         patch('pipeline.pdf_compiler.subprocess.run', return_value=mock_result):
        result = pdf_compiler.compile_tex(str(tex), str(tmp_path))

    assert result is None


def test_compile_tex_uses_docker_when_no_pdflatex(tmp_path):
    tex = tmp_path / 'resume.tex'
    tex.write_text('content')
    expected_pdf = tmp_path / 'resume.pdf'
    docker_calls = []

    def _run(cmd, **kwargs):
        docker_calls.append(cmd)
        if 'pdflatex' in ' '.join(str(c) for c in cmd):
            expected_pdf.write_bytes(b'%PDF-fake')
        result = MagicMock()
        result.stdout = ''
        return result

    with patch('pipeline.pdf_compiler.shutil.which', return_value=None), \
         patch('pipeline.pdf_compiler.subprocess.run', side_effect=_run):
        result = pdf_compiler.compile_tex(str(tex), str(tmp_path))

    assert any('docker' in str(c) for c in docker_calls[0])
    assert result == str(expected_pdf)
