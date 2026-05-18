# Job Hunt Automation Template

This repository automates job discovery across multiple locations, fit scoring, resume tailoring, cover
letter generation, and PDF output for a configurable job search. The scraper
uses direct ATS APIs first, then HTTP/BeautifulSoup, Playwright, an ephemeral
SearXNG container in GitHub Actions, and optional search APIs such as Brave,
Tavily, and Exa.

It also includes a lightweight LinkedIn content and networking system. The
LinkedIn workflow generates public-safe post ideas from your private story bank,
creates weekly draft posts for review, and suggests people/posts for manual
engagement. It never posts, comments, follows, connects, messages, or likes
automatically.

## Start Here

For initial setup, read [SETUP.md](SETUP.md) first. It walks through the
process step by step, including how to fill in project instructions, build your
story bank, choose a resume layout, configure job search, and run the automation
from GitHub.

When using AI helpers in VS Code, use them only for personal setup files such as
the story bank, resume, project instructions, and configs. Do not ask them to
change scripts, tests, workflows, Docker files, or automation code in your local
repo. Code fixes should come through a reviewed pull request to the shared
template repo.

For future updates, run **Actions -> Update From Template** in your own repo.
It opens a pull request with the latest maintained template files while keeping
your resume, story bank, generated jobs, and config files untouched by default.
The pull request shows whether the template update is a patch, minor, or major
version change.
After merging that pull request, run `git pull origin main` locally. Detailed
step-by-step update instructions are in [SETUP.md](SETUP.md#24-getting-future-template-updates).

The GitHub workflows use your repo's own GHCR runner image with Python,
Playwright, and LaTeX already installed. The image is rebuilt automatically when
`Dockerfile` or `requirements.txt` changes, which avoids spending 10-20 minutes
installing LaTeX on every job run. New repos build this repo-scoped image:
`ghcr.io/<owner>/<repo>/job-hunt-runner:latest`.

## Quick Start

1. Customize `project_instructions.md` with your own profile, ID scheme, and chatbot prompts.
2. Replace `story_bank.md` with raw notes and verified STAR stories from your experience.
3. Choose and customize a LaTeX resume:
   - `resume_double_column.tex` for the AltaCV double-column layout.
   - `resume_single_column.tex` for an ATS-friendly single-column layout.
4. Update every file in `config/`, especially:
   - `api_config.yml`
   - `search_config.yml`
   - `scoring_config.yml`
   - `cover_letter_config.yml`
   - `tailoring_config.yml` (controls what the AI can change, including project
     content selection when an uncommented Projects section exists in your resume)
5. In `config/api_config.yml`, set `profile.resume_tex`, `profile.story_bank`, and `profile.project_instructions`.
6. If you change LLM provider, replace the `llm.models` values, add the matching secret, and set the matching `secrets.<provider>.required` flag.
7. Create and store API keys using the step-by-step instructions in `SETUP.md`.
8. Run the preflight checklist, commit, and push before starting GitHub Actions.
9. Configure `linkedin/config.yml` if you want LinkedIn ideas, drafts, and networking suggestions.

Scheduled GitHub hunts run enabled regions one hour apart, starting at
06:00 Europe/Berlin time on weekdays. The first enabled region in
`config/search_config.yml` runs first, the second enabled region runs one hour
later, and so on. Extra cron slots exit before the pipeline starts, so a repo
with one enabled region only runs the first slot. Manual **Job Hunt Pipeline**
runs include a `region` field where you can enter `all` or a specific region
key from `config/search_config.yml`.

**Project section tailoring:** When your resume contains an uncommented
Projects section, the tailorer selects and adjusts project content from your
story bank to match each job description. It will never uncomment a
commented-out section or add a new one. Configure the allowed story ID prefixes,
project count, bullet count, and page limit in
`config/tailoring_config.yml` under `tailoring.rules.projects`.

## Search Fallbacks

Search APIs are optional except for the LLM provider you choose. After direct
ATS, HTTP/BeautifulSoup, and Playwright scraping, the default search-provider
fallback order is configured in `config/api_config.yml`:

For LLM providers, `config/api_config.yml`, GitHub Secrets, and
`requirements.txt` must agree:

| Provider | Python package | Secret |
|---|---|---|
| `anthropic` | `anthropic` | `ANTHROPIC_API_KEY` |
| `openai` | `openai` | `OPENAI_API_KEY` |
| `google` | `google-generativeai` | `GOOGLE_API_KEY` |
| `ollama` | `openai` | none for local Ollama |

Set `secrets.<provider>.required: true` only for providers you actually use.

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

LinkedIn review files are written to:

```text
linkedin/ideas.md
linkedin/drafts/
linkedin/engagement.md
linkedin/networking.md
```

Review everything manually before using it on LinkedIn.

Each hunt run tailors at most 15 matched jobs. If more jobs pass scoring, the
pipeline processes the 15 highest-scoring matches first.

Job-title search policy is driven by `config/search_config.yml`:

- `global_search.job_titles` controls the roles searched across ATS pages,
  career pages, discovery, JSearch, and search-provider fallbacks.
- `exclusion_rules.excluded_title_terms` blocks irrelevant title terms before
  expensive validation, scoring, tailoring, and PDF work.

Keep those two lists aligned: add the role families you want to
`global_search.job_titles`, and add adjacent roles you do not want to
`excluded_title_terms`.

## Applied Jobs

<!-- JOBS_TABLE_START -->
| Date | Job | Score | Files |
|---|---|---|---|
<!-- JOBS_TABLE_END -->
