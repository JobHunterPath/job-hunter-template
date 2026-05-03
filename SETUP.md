# Setup Guide

Use this guide after creating your private repository from the template.

## 1. Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS/Linux, activate with:

```bash
source .venv/bin/activate
```

If you need JavaScript-rendered job pages:

```bash
playwright install chromium
```

## 2. Add Your Profile Files

Edit:

- `resume_double_column.tex` for the AltaCV double-column layout
- `resume_single_column.tex` for the ATS-friendly single-column layout
- `resume.tex`, optional default entrypoint that currently loads the double-column version
- `story_bank.md`
- `config/cover_letter_config.yml`

Keep all resume metrics and story outcomes factual.

Select the resume variant used by the pipeline in `config/api_config.yml`:

```yaml
profile:
  resume_tex: "resume_double_column.tex"   # or "resume_single_column.tex"
```

## 3. Configure Search

Edit `config/search_config.yml`:

- Set your region, country, language, and location.
- Add target companies and their career URLs.
- Update `global_search.job_titles`.
- Add companies or industries you want to exclude.

## 4. Configure LLM Provider

Edit `config/api_config.yml`.

Supported providers:

- `anthropic`
- `openai`
- `google`
- `ollama`

Store real API keys as environment variables, GitHub Actions secrets, or local
keyring entries. Do not commit secrets.

## 5. Run Locally

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py
```

For direct job URLs:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py --mode tailor-links --links "https://example.com/job"
```

## 6. GitHub Actions

Add repository secrets matching `config/api_config.yml`, for example:

- `ANTHROPIC_API_KEY`
- `BRAVE_API_KEY`
- `RAPIDAPI_KEY`, optional
- `GH_PAT`, if you want workflows to commit generated outputs back to the repo

Then run the workflows manually once before relying on schedules.
