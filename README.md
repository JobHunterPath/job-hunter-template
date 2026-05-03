# Job Hunt Automation Template

This repository automates job discovery, fit scoring, resume tailoring, cover
letter generation, and PDF output for a configurable job search.

## Start Here

For initial setup, read [SETUP.md](SETUP.md) first. It walks through the
process step by step, including how to choose a resume layout, fill in your
story bank, configure job search, and run the automation from GitHub.

## Quick Start

1. Choose and customize a LaTeX resume:
   - `resume_double_column.tex` for the AltaCV double-column layout.
   - `resume_single_column.tex` for an ATS-friendly single-column layout.
   - `resume.tex` is a small default entrypoint that loads the double-column version.
2. Replace `story_bank.md` with verified STAR stories from your experience.
3. Update every file in `config/`, especially:
   - `api_config.yml`
   - `search_config.yml`
   - `scoring_config.yml`
   - `cover_letter_config.yml`
   - `tailoring_config.yml`
4. In `config/api_config.yml`, set `profile.resume_tex` to the resume file you want the pipeline to tailor.
5. Store API keys in environment variables, GitHub Actions secrets, or keyring.
6. Run tests, then run the pipeline locally or through GitHub Actions.

## Local Run

```bash
pip install -r requirements.txt
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py
```

For direct job URLs:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py --mode tailor-links --links "https://example.com/job"
```

## Outputs

Generated application files are written to:

```text
jobs/YYYY-MM-DD_company_role/
```

The tracker in `config/applied_jobs.yml` prevents duplicate processing.

## Applied Jobs

<!-- JOBS_TABLE_START -->
| Date | Job | Score | Files |
|---|---|---|---|
<!-- JOBS_TABLE_END -->
