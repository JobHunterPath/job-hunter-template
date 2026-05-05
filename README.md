# Job Hunt Automation Template

This repository automates job discovery across multiple locations, fit scoring, resume tailoring, cover
letter generation, and PDF output for a configurable job search. The scraper
uses direct ATS APIs first, then HTTP/BeautifulSoup, Playwright, an ephemeral
SearXNG container in GitHub Actions, and optional search APIs such as Brave,
Tavily, and Exa.

## Start Here

For initial setup, read [SETUP.md](SETUP.md) first. It walks through the
process step by step, including how to choose a resume layout, fill in your
story bank, configure job search, and run the automation from GitHub.

For future updates, run **Actions -> Update From Template** in your own repo.
It opens a pull request with the latest maintained template files while keeping
your resume, story bank, generated jobs, and config files untouched by default.
After merging that pull request, run `git pull origin main` locally. Detailed
step-by-step update instructions are in [SETUP.md](SETUP.md#21-getting-future-template-updates).

## Quick Start

1. Choose and customize a LaTeX resume:
   - `resume_double_column.tex` for the AltaCV double-column layout.
   - `resume_single_column.tex` for an ATS-friendly single-column layout.
2. Replace `story_bank.md` with raw notes and verified STAR stories from your experience.
3. Customize `project_instructions.md` with your own profile, ID scheme, and chatbot prompts.
4. Update every file in `config/`, especially:
   - `api_config.yml`
   - `search_config.yml`
   - `scoring_config.yml`
   - `cover_letter_config.yml`
   - `tailoring_config.yml`
5. In `config/api_config.yml`, set `profile.resume_tex`, `profile.story_bank`, and `profile.project_instructions`.
6. Store API keys in environment variables, GitHub Actions secrets, or keyring.
7. Run tests, then run the pipeline locally or through GitHub Actions.

## Search Fallbacks

Search APIs are optional except for the LLM provider you choose. After direct
ATS, HTTP/BeautifulSoup, and Playwright scraping, the default search-provider
fallback order is configured in `config/api_config.yml`:

```yaml
http:
  search_providers:
    order:
      - searxng
      - brave
      - tavily
      - exa
```

GitHub Actions starts SearXNG temporarily for each hunt, discovery, and
tailor-links job. If SearXNG or any API provider fails, the pipeline continues
with the next available option.

## Local Run

```bash
python -m pip install -r requirements.txt
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

The template includes an empty `jobs/` folder so GitHub Actions can write and
commit generated outputs on the first run.

The tracker in `config/applied_jobs.yml` prevents duplicate processing.

## Applied Jobs

<!-- JOBS_TABLE_START -->
| Date | Job | Score | Files |
|---|---|---|---|
<!-- JOBS_TABLE_END -->
