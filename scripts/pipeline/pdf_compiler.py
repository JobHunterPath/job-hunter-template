"""
Compiles a tailored .tex resume into a PDF.

Uses native pdflatex when available (GitHub Actions), falls back to a
Docker texlive container for local Windows runs.
"""

import os
import shutil
import subprocess

from core.config import profile_path

# scripts/pipeline/ → scripts/ → repo root
def compile_tex(tex_path: str, output_dir: str) -> str | None:
    """
    Compile a .tex file to PDF.

    Args:
        tex_path:   Absolute path to the .tex file.
        output_dir: Directory where the PDF will be written.

    Returns:
        Path to the generated PDF, or None if compilation failed.
    """
    # Copy image and class file dependencies into output dir so pdflatex finds them
    for src in (
        profile_path("profile_image", "profile-placeholder.png"),
        profile_path("latex_class", "altacv.cls"),
    ):
        if src.exists():
            shutil.copy(src, output_dir)

    abs_output_dir = os.path.abspath(output_dir)
    abs_tex_path = os.path.abspath(tex_path)

    if shutil.which("pdflatex"):
        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", abs_output_dir,
            abs_tex_path,
        ]
        timeout = 120
    else:
        # Local Windows: run via Docker texlive image
        print("  [compile] Pulling texlive Docker image (first run may take several minutes)...")
        subprocess.run(
            ["docker", "pull", "texlive/texlive:latest"],
            timeout=600,
        )

        container_tex = f"/workspace/{os.path.basename(abs_tex_path)}"
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{abs_output_dir}:/workspace",
            "texlive/texlive:latest",
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", "/workspace",
            container_tex,
        ]
        timeout = 300

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    expected_pdf = os.path.join(
        abs_output_dir,
        os.path.basename(tex_path).replace(".tex", ".pdf"),
    )

    if os.path.exists(expected_pdf):
        return expected_pdf

    print(f"  [compile] FAILED — check log in {abs_output_dir}")
    print(result.stdout[-1000:])
    return None
