# Setup Guide

Follow this guide from top to bottom. It is written for non-technical users who
want to use GitHub Actions as the main way to run the job-hunt automation.

## What This Tool Does

This private repository can search for jobs, score them against your profile,
tailor a LaTeX resume, write cover letters from your story bank, and save the
outputs in `jobs/`.

Before running any workflow, finish the project instructions, story bank, base
resume, API config, job search config, scoring config, and cover letter profile.
The automation works best when the source material is already clean.

Important: when using Claude Code, Codex, Copilot, or any other AI helper in VS
Code, use it only to edit your personal files: resume, story bank, project
instructions, and config files. Do not ask it to change `scripts/`, `tests/`,
`.github/workflows/`, `Dockerfile`, or other code files in your local repo. If
you find a real code problem, ask a technical person to create a pull request
against the shared template repo instead.

## 1. Install The Required Apps

Install:

1. **Git** from `https://git-scm.com/downloads`
2. **Visual Studio Code** from `https://code.visualstudio.com/`
3. **Python** from `https://www.python.org/downloads/`
4. **Docker Desktop** from `https://www.docker.com/products/docker-desktop/`

After installing Docker Desktop, open it once and wait until it says the Docker
engine is running.

## 2. Create Your Own Private Repository

The job-hunter template is private and should stay private.

1. Open the shared template repository on GitHub.
2. Click **Use this template**.
3. Choose **Create a new repository**.
4. Set visibility to **Private**.
5. Create the repository.

Your new private repository is your personal job-hunt workspace.

## 3. Clone Your Repository In VS Code

1. Open VS Code.
2. Click **Source Control** in the left sidebar.
3. Click **Clone Repository**.
4. Paste your repository URL from GitHub.
5. Choose a folder on your computer.
6. Click **Open** when VS Code asks.

Alternative terminal command:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
code .
```

## 4. Set Up Git On Your Computer

Open **Terminal -> New Terminal** in VS Code and run:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global --list
```

GitHub does not accept account passwords for Git pushes. If VS Code or Git asks
you to sign in, use the browser sign-in flow. If a terminal asks for a password,
use a GitHub personal access token instead of your GitHub password.

## 5. Install VS Code Extensions And An AI Helper

Install these VS Code extensions:

- **Python** by Microsoft
- **Pylance** by Microsoft
- **YAML** by Red Hat
- **LaTeX Workshop** by James Yu
- **Docker** by Microsoft
- **GitHub Pull Requests and Issues** by GitHub

Also install one AI coding helper that can see the files in your local repo.
This is strongly recommended because it lets the AI preserve the exact format of
your story bank, resume, and config files.

Choose one:

- **GitHub Copilot:** install the GitHub Copilot extension in VS Code and sign in
  with GitHub.
- **Claude Code:** install the Claude Code VS Code extension, or install the CLI
  from Anthropic's official Claude Code docs, then sign in.
- **Codex:** install Node.js if needed, then run:

```bash
npm install -g @openai/codex
```

Then open the repo folder in VS Code and start the tool from VS Code or the
terminal. When the tool asks for permission to read or edit files, allow access
only to this repository.

Use the AI helper for personal setup only. It should not edit automation code,
tests, workflows, Docker files, or scripts.

If you do not want to install an AI coding helper, the browser-chatbot prompts
in the project-instructions, story-bank, and resume sections still work. They
require more copying and pasting.

## 6. Install Python Requirements Directly

No virtual environment is required for this guide.

`requirements.txt` includes the SDKs for the supported cloud LLM providers:
Anthropic, OpenAI, and Google Gemini. Keep the SDK for any provider you configure
in `config/api_config.yml`. If a provider SDK is missing, the pipeline fails with
an install hint such as `python -m pip install openai`.

In the VS Code terminal, run these from the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

On Windows, if `python` is not recognized, try:

```bash
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m playwright install chromium
```

## 7. Optional: Set Up Local LaTeX Preview

Most users can rely on GitHub Actions to create PDFs. Do this only if you want
to preview or rework resume PDFs on your laptop.

Check Docker:

```bash
docker --version
docker run --rm texlive/texlive:latest pdflatex --version
```

Create `.vscode/settings.json` and paste:

```json
{
  "latex-workshop.latex.outDir": "%DIR%",
  "latex-workshop.latex.tools": [
    {
      "name": "pdflatex-docker",
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-v",
        "%DIR%:/work",
        "-w",
        "/work",
        "texlive/texlive:latest",
        "pdflatex",
        "-interaction=nonstopmode",
        "-synctex=1",
        "%DOCFILE%.tex"
      ]
    }
  ],
  "latex-workshop.latex.recipes": [
    {
      "name": "Build with Docker pdflatex",
      "tools": ["pdflatex-docker"]
    }
  ],
  "latex-workshop.latex.recipe.default": "Build with Docker pdflatex"
}
```

To build locally, open `resume_double_column.tex` or
`resume_single_column.tex`, then run **LaTeX Workshop: Build LaTeX project**.

## 8. Choose Your Resume Layout

This template includes:

- `resume_double_column.tex`: polished double-column AltaCV layout.
- `resume_single_column.tex`: simpler single-column ATS-friendly layout.

Open `config/api_config.yml` and choose the file the automation should use:

```yaml
profile:
  resume_tex: "resume_double_column.tex"
```

For the single-column version:

```yaml
profile:
  resume_tex: "resume_single_column.tex"
```

## 9. Fill In Project Instructions

Open `project_instructions.md` before building the story bank. This file tells
the AI helper who you are, what roles you are targeting, what rules to follow,
and how story IDs should be handled.

Replace the placeholder profile under **About Me** with your own factual
information:

- Current role
- Years of experience
- Target roles
- Target industries
- Target locations
- Industries or companies to avoid
- Strongest proof points
- Honest gaps

Also review the house rules and story ID guidance. Keep the rules strict:
project instructions should tell the AI not to invent metrics, titles,
companies, dates, skills, or outcomes.

### AI Helper Prompt

Use this prompt if you want Claude Code, Codex, Copilot, or another repo-aware
tool to help update only `project_instructions.md`:

```text
Help me personalize project_instructions.md before I build my story bank.

Files to edit:
- project_instructions.md

Do not edit:
- story_bank.md
- resume .tex files
- config files
- scripts/
- tests/
- .github/workflows/
- Dockerfile
- requirements.txt
- any automation code

Task:
- Replace the placeholder "About Me" section with my factual profile.
- Keep the existing role, house rules, story ID guidance, and prompt structure.
- Adjust examples only if needed to match my target roles and story ID scheme.

Hard rules:
- Do not invent metrics, employers, titles, skills, dates, or outcomes.
- Keep instructions strict and factual.
- Preserve markdown headings and prompt formats.
- If you think code or scripts need a fix, stop and tell me to raise a template
  repo pull request instead.

My profile notes:
[PASTE YOUR BACKGROUND, TARGET ROLES, TARGET LOCATIONS, PROOF POINTS, AND GAPS HERE]
```

## 10. Build Your Story Bank

Open `story_bank.md`. The format matters because cover letters and project
tailoring use this file as source material.

Use the personalized `project_instructions.md` from the previous step while
building or refining the story bank.

The story bank has:

- **Draft - Raw Notes:** rough notes about work, education, projects,
  volunteering, or side projects.
- **Final - refined STAR stories:** polished, factual stories in Situation,
  Task, Action, Result format.
- **Allocation Log:** a table that prevents duplicate story IDs.

Story IDs must stay stable. Do not reuse or renumber old IDs.

Examples:

- `ACME-PM-01`: company or role story
- `TECH-01`: technical project
- `UNI-01`: university project
- `SIDE-01`: side project
- `VOL-01`: volunteer project

### Manual Flow

1. Add rough notes under **Draft - Raw Notes**.
2. Give each story a unique ID.
3. Convert the strongest notes into STAR format under
   **Final - refined STAR stories**.
4. Add each ID to the **Allocation Log**.
5. Keep weak or unverified material in Draft until you can verify it.

### Best Option: Use An AI Helper In VS Code

Paste this prompt into Claude Code, Codex, Copilot, or another repo-aware tool:

```text
Help me build story_bank.md without changing its standard format.

Files to read or edit:
- story_bank.md
- project_instructions.md, which should already be personalized

Do not edit:
- scripts/
- tests/
- .github/workflows/
- Dockerfile
- requirements.txt
- any automation code

Task:
- Add my raw notes under "Draft - Raw Notes".
- Create final STAR stories under "Final - refined STAR stories" only when the
  notes are strong enough.
- Update the Allocation Log.

Hard rules:
- Preserve all existing headings and table formats in story_bank.md.
- Keep story IDs stable. Do not reuse or renumber IDs.
- Do not invent metrics, employers, titles, skills, dates, or outcomes.
- If a metric is not verified, use a concrete scope anchor instead.
- If a story is weak, keep it in Draft and explain what is missing.
- Keep each final story in this format:
  Situation, Task, Action bullets, Result bullets, Tags.
- If you think code or scripts need a fix, stop and tell me to raise a template
  repo pull request instead.

My raw notes:
[PASTE YOUR ACHIEVEMENTS, TASKS, PROJECTS, VOLUNTEERING, EDUCATION, AND RESULTS HERE]
```

Review every final story. If you cannot defend it in an interview, move it back
to Draft or rewrite it.

### Browser Chatbot Option

1. Copy the full current `story_bank.md`.
2. Copy the relevant parts of `project_instructions.md`.
3. Paste both into a browser chatbot with your notes and this prompt:

```text
I need help updating my story bank for a job-hunt automation repo.

Return an updated story_bank.md that preserves the exact standard format.

Hard rules:
- Keep these headings: Story ID Scheme, Draft - Raw Notes, Final - refined STAR stories, Allocation Log.
- Preserve the Allocation Log markdown table format.
- Keep story IDs stable. Do not reuse or renumber IDs.
- Do not invent metrics, employers, titles, skills, dates, or outcomes.
- If no metric is verified, use a concrete scope anchor such as team size,
  stakeholder count, launch timeline, release cadence, user group, or workflow scope.
- Final stories must use: Situation, Task, Action bullets, Result bullets, Tags.
- Put uncertain or weak material in Draft, not Final.
- Do not suggest changes to scripts, tests, workflows, Docker files, or code.
- Return only the full updated story_bank.md, no explanation.

Current story_bank.md:
[PASTE CURRENT STORY_BANK.MD HERE]

Project instructions:
[PASTE RELEVANT PROJECT_INSTRUCTIONS.MD CONTENT HERE]

My raw notes:
[PASTE YOUR NOTES HERE]
```

## 11. Prepare Your Base Resume Before Any Workflow

Open the resume file you selected and replace placeholders such as
`Candidate Name`, `candidate@example.com`, `Target City`, `Example Company`, and
example bullet points.

Use only real information you can defend in an interview. Do not invent metrics,
titles, companies, skills, or dates.

### Best Option: Use An AI Helper In VS Code

Open your AI helper in this repo and paste:

```text
I need you to update my base LaTeX resume without changing the LaTeX structure.

Files to use:
- The resume .tex file I selected in section 8.
- story_bank.md if useful.

My resume/profile notes are below.

Do not edit:
- scripts/
- tests/
- .github/workflows/
- Dockerfile
- requirements.txt
- any automation code

Rules:
- Preserve the existing LaTeX commands, sections, escaping, and layout.
- Replace placeholder content with my real content.
- Do not invent metrics, employers, dates, titles, skills, or outcomes.
- If a detail is missing, leave a clear TODO comment instead of making it up.
- Keep the resume to the existing page target.
- Do not rewrite config files.
- If you think code or scripts need a fix, stop and tell me to raise a template
  repo pull request instead.

My notes:
[PASTE YOUR EXISTING RESUME TEXT OR PROFILE NOTES HERE]
```

Review the changed `.tex` file before committing it.

### Browser Chatbot Option

Use this when you do not have Claude Code, Codex, Copilot, or a similar local
repo-aware tool.

1. Open your selected resume `.tex` file.
2. Copy the full file into a browser chatbot.
3. Paste your current resume text or notes.
4. Use this prompt:

```text
I will paste a LaTeX resume template and my current resume/profile notes.

Task:
Return a complete updated LaTeX resume that preserves the template's LaTeX
structure and replaces placeholders with my real content.

Hard rules:
- Do not change LaTeX commands unless absolutely necessary.
- Do not invent metrics, employers, dates, titles, skills, or outcomes.
- Escape LaTeX special characters when needed, such as &, %, $, #, and _.
- Keep the same sections unless my notes clearly support a better section.
- If information is missing, write TODO in plain text inside the relevant field.
- Do not suggest changes to scripts, tests, workflows, Docker files, or code.
- Return only the full updated LaTeX file, no explanation.

LaTeX template:
[PASTE THE FULL .TEX FILE HERE]

My resume/profile notes:
[PASTE YOUR CURRENT RESUME OR NOTES HERE]
```

Then replace the content of the selected `.tex` file with the returned LaTeX and
build or run a workflow later to verify it.

## 12. Update Your Cover Letter Profile

Open `config/cover_letter_config.yml`.

Replace `candidate_background` with a short factual summary of your background.
Also update:

```yaml
closing:
  format: "Best regards,\nCandidate Name"
```

Use your real name.

## 13. Configure The LLM Provider

Open `config/api_config.yml`.

Supported providers:

- `anthropic`
- `openai`
- `google`
- `ollama`

When changing providers, update four things together:

1. `llm.default_provider` and every `llm.providers.*` role you want to move.
2. Every matching `llm.models.*` value, using model names from that same provider.
3. The matching entry under `secrets:`. Set the provider you use to
   `required: true`; set providers you are not using to `required: false`.
4. `requirements.txt`. It includes the supported cloud LLM SDKs by default. If
   you later remove unused SDKs, add back the SDK for the provider you choose.

To switch everything to OpenAI, for example:

```yaml
llm:
  default_provider: openai
  providers:
    validation: openai
    scoring: openai
    tailoring: openai
    cover_letter: openai
    discovery: openai
    linkedin: openai
    ai_web_search: openai
    jd_extraction: openai
  models:
    validation: "REPLACE_WITH_OPENAI_MODEL"
    scoring: "REPLACE_WITH_OPENAI_MODEL"
    tailoring: "REPLACE_WITH_OPENAI_MODEL"
    cover_letter: "REPLACE_WITH_OPENAI_MODEL"
    discovery: "REPLACE_WITH_OPENAI_MODEL"
    linkedin: "REPLACE_WITH_OPENAI_MODEL"
    ai_web_search: "REPLACE_WITH_OPENAI_MODEL"
    jd_extraction: "REPLACE_WITH_OPENAI_MODEL"
secrets:
  anthropic:
    env_var: "ANTHROPIC_API_KEY"
    required: false
  openai:
    env_var: "OPENAI_API_KEY"
    required: true
  google:
    env_var: "GOOGLE_API_KEY"
    required: false
```

Important: if you change the LLM provider, you must also change every model name
under `llm.models`. Anthropic model names do not work with OpenAI, OpenAI model
names do not work with Google, and so on.

Provider dependency checklist:

| Provider in `api_config.yml` | Required Python package in `requirements.txt` | Secret to add | `secrets.<provider>.required` |
|---|---|---|---|
| `anthropic` | `anthropic` | `ANTHROPIC_API_KEY` | `true` |
| `openai` | `openai` | `OPENAI_API_KEY` | `true` |
| `google` | `google-genai` | `GOOGLE_API_KEY` | `true` |
| `ollama` | `openai` | none for local Ollama | no secret required |

If you mix providers by role, mark every provider you actually use as
`required: true` and add every matching GitHub secret.

How to find valid model names:

- Anthropic Claude: open `https://docs.anthropic.com/en/docs/about-claude/models/all-models`
  and copy the **Anthropic API** model name.
- OpenAI: open `https://platform.openai.com/docs/models`, or list models with
  the API after setting `OPENAI_API_KEY`:

```bash
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

- Google Gemini: open `https://ai.google.dev/gemini-api/docs/models`, or use
  the Gemini API model-list docs at
  `https://ai.google.dev/api/rest/generativelanguage/models/list`.
- Ollama: open `https://ollama.com/search`, choose a model, pull it locally,
  then use the pulled model name:

```bash
ollama pull llama3.2
ollama list
```

Use cheaper/faster models for `validation`, `scoring`, `jd_extraction`, and
`ai_web_search`.
Use stronger models for `tailoring`, `cover_letter`, `discovery`, and
`linkedin`.

`llm.max_workers` controls how many validation and scoring LLM calls run in
parallel. The default is `5`. For Google free tier, start with `max_workers: 2`
and set `llm.rate_limits.google.requests_per_minute` below the RPM shown in AI
Studio. The LLM client retries 429 rate-limit errors and transient 5xx failures
automatically with exponential backoff, but retries cannot overcome exhausted
quota.

`http.jd_enrichment` controls best-effort fetching of full job descriptions for
sparse search snippets. LinkedIn job pages often return HTTP 429 to direct
fetches, so `linkedin\.com/jobs/` is skipped by default and the pipeline keeps
the search snippet.

Use the matching secret name:

- Anthropic: `ANTHROPIC_API_KEY`
- OpenAI: `OPENAI_API_KEY`
- Google Gemini: `GOOGLE_API_KEY`

The workflow files expose all three cloud LLM secret names to Python. Empty
unused secrets are fine, but the secret for the configured provider must exist
before running Actions.

### Create An Anthropic Claude API Key

Use this if `config/api_config.yml` uses `anthropic`.

1. Open `https://console.anthropic.com/`.
2. Create an account or sign in.
3. Add billing if Anthropic asks for it.
4. Open the API keys section.
5. Create a new API key.
6. Copy it immediately. You may not be able to see it again.
7. Store it in GitHub Secrets as:

```text
ANTHROPIC_API_KEY
```

### Create An OpenAI API Key

Use this if `config/api_config.yml` uses `openai`.

1. Open `https://platform.openai.com/`.
2. Create an account or sign in.
3. Create or select a project if prompted.
4. Open the API keys section.
5. Create a new API key.
6. Copy it immediately.
7. Store it in GitHub Secrets as:

```text
OPENAI_API_KEY
```

### Create A Google Gemini API Key

Use this if `config/api_config.yml` uses `google`.

1. Open `https://aistudio.google.com/`.
2. Sign in with your Google account.
3. Open API keys.
4. Create a new API key.
5. Copy it immediately.
6. Store it in GitHub Secrets as:

```text
GOOGLE_API_KEY
```

Ollama can work locally, but GitHub-hosted Actions cannot use Ollama running on
your laptop. Use Anthropic, OpenAI, or Google for scheduled GitHub Actions.

Optional search-provider secrets:

- `BRAVE_API_KEY`
- `TAVILY_API_KEY`
- `EXA_API_KEY`
- `RAPIDAPI_KEY`

The pipeline can still use direct ATS scraping, HTTP scraping, Playwright, and
temporary SearXNG in GitHub Actions when optional search keys are missing.

### Optional: Enable AI Web Search

AI web search uses the configured `llm.providers.ai_web_search` provider to find
job postings by title and region. It does not search by company name. Leave it
disabled if you want the lowest-cost default setup.

Recommended models:

- Anthropic: `claude-haiku-4-5-20251001` (switch to `claude-sonnet-4-6` if you see frequent 529 errors at peak hours)
- Google validation/JD extraction: `gemini-2.5-flash-lite`
- Google scoring: `gemini-2.5-flash` until Flash Lite score quality is compared on real matches
- OpenAI: `gpt-4o-mini`

Keep `min_confidence` enabled in `http.search_providers.ai_web_search`. The AI
web-search prompt includes compact exclusion rules from `config/search_config.yml`
so low-confidence or irrelevant search results are dropped before
validation/scoring spends LLM tokens.

To enable it, set:

```yaml
http:
  search_providers:
    ai_web_search:
      enabled: true
      max_prompts_per_run: 80
      max_prompts_per_region: 8
      max_results_per_prompt: 8
      max_results_per_region: 30
      max_total_results_per_run: 120
      min_confidence: 0.5
```

The default sources (`greenhouse`, `lever`, `ashby`, `generic_web`) target
well-indexed ATS boards and exclude aggregators. Every result still goes through
dedupe, URL verification, JD fetching, validation, and scoring before any
tailoring or cover-letter generation.

### Optional: Enable JobSpy (Indeed + Google Jobs)

`python-jobspy` is installed via `requirements.txt`. Enable it in
`config/search_config.yml`:

```yaml
jobspy:
  enabled: true
  hours_old: 72          # only return jobs posted within this window
  results_per_query: 20  # per title × region × source
  country_indeed_by_region:
    berlin: germany      # add a row for every region that has an Indeed country code
    vancouver: canada
```

Regions with a matching `country_indeed_by_region` entry use both Indeed and
Google Jobs. Regions without an entry fall back to Google Jobs only. No API key
is required. JobSpy results go through the same dedupe, URL verification,
validation, and scoring gates as every other source.

### Create A Brave Search API Key, Optional

Brave helps with broader web search when direct company scraping is not enough.

1. Open `https://brave.com/search/api/`.
2. Create an account or sign in.
3. Choose a plan.
4. Create or copy your API key.
5. Store it in GitHub Secrets as:

```text
BRAVE_API_KEY
```

### Create A Tavily API Key, Optional

1. Open `https://tavily.com/`.
2. Create an account or sign in.
3. Copy your API key from the dashboard.
4. Store it in GitHub Secrets as:

```text
TAVILY_API_KEY
```

### Create An Exa API Key, Optional

1. Open `https://exa.ai/`.
2. Create an account or sign in.
3. Copy your API key from the dashboard.
4. Store it in GitHub Secrets as:

```text
EXA_API_KEY
```

### Create A RapidAPI / JSearch Key, Optional

JSearch can add job-board results, but the pipeline can run without it.

1. Open `https://rapidapi.com/`.
2. Create an account or sign in.
3. Search for the JSearch API.
4. Subscribe to JSearch if you want to use it.
5. Open your RapidAPI app or project.
6. Copy the RapidAPI key.
7. Store it in GitHub Secrets as:

```text
RAPIDAPI_KEY
```

## 14. Configure Job Search Regions And Companies

Open `config/search_config.yml`.

For each region, update:

- `enabled`
- `country`
- `search_lang`
- `location`
- `description`
- `companies`

Update `global_search.job_titles` with the roles you want. Update
`exclusion_rules.excluded_title_terms` with roles you do not want, such as
`engineer`, `intern`, or `working student`.

### Prompt To Find 50 Initial Companies

Use this prompt in an AI helper or browser chatbot before waiting for discovery.
If you use an AI helper in VS Code, ask it to edit only `config/search_config.yml`
and not any code files.

```text
Find 50 companies for my initial job-search region.

Target region:
[CITY / COUNTRY / REMOTE REGION]

Target roles:
[ROLE TITLES, FOR EXAMPLE PRODUCT MANAGER, PRODUCT OWNER]

Preferences:
[INDUSTRIES, COMPANY SIZE, LANGUAGE REQUIREMENTS, REMOTE/HYBRID/ONSITE]

Avoid:
[COMPANIES OR INDUSTRIES TO EXCLUDE]

Return YAML only in this exact format:

companies:
  - name: Company Name
    career_url: company-career-domain-or-ats-url

Rules:
- Use company career pages or ATS board URLs, not job-detail URLs.
- Prefer Greenhouse, Lever, SmartRecruiters, Ashby, Personio, Workday, or company careers pages.
- Do not include duplicate companies.
- Do not include companies from my avoid list.
- If unsure about a career URL, include the main careers page domain.
- Do not change scripts, tests, workflows, Docker files, or automation code.
```

Paste the returned company list under the right region in `config/search_config.yml`.

Example:

```yaml
regions:
  primary:
    enabled: true
    country: "DE"
    search_lang: "en"
    location: "Berlin"
    description: "Berlin product roles"
    companies:
      - name: Example Company
        career_url: boards.greenhouse.io/example
```

## 15. Set Scoring And Tailoring Rules

Open `config/scoring_config.yml`.

Important fields:

```yaml
scoring:
  min_fit_score: 70
  max_years_experience_required: 5
```

Use a lower `min_fit_score` for more jobs, or a higher score for stricter
filtering.

Open `config/tailoring_config.yml` only if you need to change what the AI can
modify. The default forbidden rules protect against invented experience.

## 16. Add API Keys In GitHub

Do not paste API keys into files.

### Create `GH_PAT`

`GH_PAT` is required for GitHub Actions to save generated files back into your
private repository.

1. Open GitHub.
2. Click your profile picture.
3. Go to **Settings -> Developer settings -> Personal access tokens**.
4. Choose **Fine-grained tokens**.
5. Click **Generate new token**.
6. Name it `job-hunt-actions`.
7. Set **Repository access** to only this private repo.
8. Set **Contents** to **Read and write**.
9. Generate the token and copy it immediately.

If fine-grained tokens are blocked, use a classic token with the `repo` scope.

### Add Repository Secrets

In your repository, open:

```text
Settings -> Secrets and variables -> Actions -> Secrets
```

Add:

- `GH_PAT`
- one LLM key: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GOOGLE_API_KEY`
- optional search keys: `BRAVE_API_KEY`, `TAVILY_API_KEY`, `EXA_API_KEY`, `RAPIDAPI_KEY`
- `TEMPLATE_REPO_PAT` for future template updates

After adding a different LLM secret, re-check `config/api_config.yml`:

- If using Anthropic only, `secrets.anthropic.required` should be `true`, while
  `secrets.openai.required` and `secrets.google.required` should be `false`.
- If using OpenAI only, `secrets.openai.required` should be `true`, while
  `secrets.anthropic.required` and `secrets.google.required` should be `false`.
- If using Google only, `secrets.google.required` should be `true`, while
  `secrets.anthropic.required` and `secrets.openai.required` should be `false`.
- If intentionally mixing providers, every provider used in `llm.providers`
  needs `required: true` and a matching GitHub secret.

The upstream job-hunter template is private, so `TEMPLATE_REPO_PAT` is needed if
you want **Update From Template** to fetch future updates.

Create `TEMPLATE_REPO_PAT` from an account that can access the template repo:

1. Create a fine-grained token.
2. Select only `Job-Network-Projects/job-hunter-template`.
3. Set **Contents** to **Read-only**.
4. Add it to this repo as a secret named `TEMPLATE_REPO_PAT`.

If your organization uses SAML/SSO, authorize the token for the organization.

## 17. Optional: Test Locally

Run tests:

```bash
python -m pytest -q
```

If local tests are too much, you can continue with GitHub Actions after secrets
are configured.

## 18. Optional: Run Local Commands

Run one direct job link locally:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py --mode tailor-links --links "https://example.com/job"
```

Run the daily hunt locally:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py
```

Optional LinkedIn support:

```bash
PYTHONPATH=scripts python scripts/linkedin/generate_ideas.py
PYTHONPATH=scripts python scripts/linkedin/draft_posts.py
PYTHONPATH=scripts python scripts/linkedin/discover_engagement.py
```

LinkedIn support never posts, comments, follows, connects, messages, or likes.
Review every output manually.

## 19. Preflight Checklist Before Committing

Do not commit or run workflows until these are done:

- `project_instructions.md` has your factual profile, target roles, and rules.
- `story_bank.md` has real final STAR stories, not only examples.
- `config/api_config.yml` points to the resume file you actually edited.
- The active resume `.tex` has your real base resume content.
- `config/cover_letter_config.yml` has your real background and name.
- `config/search_config.yml` has your target regions, titles, exclusions, and companies.
- `config/scoring_config.yml` has a score threshold you are comfortable with.
- GitHub Secrets include `GH_PAT` and the LLM API key for your configured provider.

## 20. Commit And Push Your Setup

GitHub Actions only sees files that have been pushed to GitHub. If you edited
files only on your laptop and did not push them, the workflows will run with old
files.

In the VS Code terminal, run:

```bash
git status
git add .
git commit -m "complete initial job hunt setup"
git push origin main
```

If Git says `nothing to commit`, that is okay. Continue to the next step.

If Git asks who you are, run the Git setup commands again with your own name and
email:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

If `git push` fails because GitHub asks for a password, sign in through VS Code
or use a GitHub personal access token.

## 21. Set Up Faster GitHub Actions With The Runner Image

Your repository should build and publish its own GHCR runner image. The image
contains Python dependencies, Playwright Chromium, and LaTeX already installed,
so workflow runs are faster after the first build.

Build your repo's image:

1. Open **Actions -> Build Runner Image**.
2. Click **Run workflow**.
3. Wait for it to finish.

Your repo publishes this repo-scoped image:

```text
ghcr.io/<your-github-owner>/<your-repository>/job-hunt-runner:latest
```

Every person who creates a repo from the template publishes their own package
under their own repo. This avoids permission conflicts with another package
named `job-hunt-runner` under the same GitHub account.

If publishing fails, open **Settings -> Actions -> General**, set workflow
permissions to **Read and write permissions**, save, and re-run the image build.

If publishing fails with `403 Forbidden` while pushing to `ghcr.io`, check these
in order:

1. Confirm **Settings -> Actions -> General -> Workflow permissions** is set to
   **Read and write permissions**.
2. Pull the latest template update so the image name is repo-scoped as shown
   above, then rerun **Build Runner Image**.
3. If a package already exists under **GitHub profile -> Packages** or
   **Repository -> Packages**, open the package settings and give this repository
   **Write** access under **Manage Actions access**.
4. If the old package is not needed, delete the old `job-hunt-runner` package
   and rerun the workflow.

Do this before the first real workflow run. If the image is missing, workflows
can still use a slower fallback, but the recommended GitHub Actions setup is to
use the runner image.

## 22. Run The Automation In GitHub

Open the **Actions** tab in your GitHub repository. If GitHub shows a button to
enable workflows for this repository, click it.

For specific job links:

1. Open your repository on GitHub.
2. Click **Actions**.
3. Select **Tailor Links**.
4. Click **Run workflow**.
5. Paste one or more job URLs.
6. Click **Run workflow**.

For search:

1. Open **Actions -> Job Hunt Pipeline**.
2. Click **Run workflow**.
3. Set `job` to `hunt`.
4. Set `region` to `all` or enter one region key such as `primary`.
5. Click **Run workflow**.

Scheduled hunts run the primary enabled region every weekday. Secondary enabled
regions run Monday, Wednesday, and Friday. Empty slots exit before the expensive
pipeline steps. Run the workflow manually once before relying on the schedule.

## 23. Review The Output

Each processed job creates:

```text
jobs/YYYY-MM-DD_company_role/
```

Inside you may see:

- `jd.md`
- `resume_tailored.tex`
- `resume_tailored.pdf`
- `cover_letter.md`
- `cover_letter.pdf`
- `meta.json`

Always review the tailored resume and cover letter before applying.

Each hunt run tailors at most 15 matched jobs. If more than 15 jobs pass the
score threshold, the pipeline processes the 15 highest-scoring matches first.

## 24. Getting Future Template Updates

Use **Actions -> Update From Template** when you want the latest maintained
code, workflows, dependencies, and docs.

1. Open your repository on GitHub.
2. Go to **Actions -> Update From Template**.
3. Click **Run workflow**.
4. Keep `upstream_repo` as `Job-Network-Projects/job-hunter-template`.
5. Keep `upstream_branch` as `main`.
6. Leave `update_config` off unless you intentionally want template config files.
7. Leave `update_linkedin` off unless you intentionally want the starter LinkedIn workspace.
8. Wait for the workflow to open a pull request.
9. Review and merge the pull request.
10. Pull the merged changes locally:

```bash
git checkout main
git pull origin main
```

### If The Update Pull Request Has Conflicts

Conflicts mean GitHub cannot safely combine your files with the template update
without a decision from you. This usually happens when both your repo and the
template changed the same maintained file.

Recommended option for non-technical users:

1. Do not click random conflict buttons.
2. Ask a technical person to review the pull request.
3. Tell them your personal files should be protected:
   - resume `.tex` files
   - `story_bank.md`
   - `project_instructions.md`
   - files in `jobs/`
   - your personal config files, unless you intentionally enabled `update_config`
4. After they resolve the conflicts and merge the PR, run:

```bash
git checkout main
git pull origin main
```

If you want to resolve conflicts yourself in GitHub:

1. Open the update pull request.
2. Click **Resolve conflicts** if GitHub shows the button.
3. For each conflicted file, choose the template version for maintained files
   such as `scripts/`, `tests/`, workflows, `README.md`, and `SETUP.md`.
4. Keep your version for personal files such as resumes, story bank, project
   instructions, generated jobs, and configs.
5. Remove all conflict marker lines. They are the lines that start with
   `<<<<<<<`, `=======`, or `>>>>>>>`.

6. Click **Mark as resolved**.
7. Merge the pull request only after the files look correct.

If the workflow cannot read the private template repo, confirm this repo has a
`TEMPLATE_REPO_PAT` secret with read access to
`Job-Network-Projects/job-hunter-template`.

The update workflow preserves resumes, story bank, project instructions,
generated jobs, config files, and LinkedIn workspace files by default.

The pull request uses semantic versioning from the template repo:

- `PATCH`: fixes, cleanup, or documentation updates.
- `MINOR`: backward-compatible new features.
- `MAJOR`: breaking setup, workflow, or config changes.

For a `MAJOR` update, read the changelog and review setup/config changes before
merging.

## Common Problems

**No jobs found**

Check `config/search_config.yml`. Make sure the region is enabled, job titles
match your target roles, company career URLs are valid, and exclusions are not
too broad.

**Workflow says a secret is missing**

Check **Settings -> Secrets and variables -> Actions**. Secret names must match
`config/api_config.yml` exactly.

**Actions tab says workflows are disabled**

Click the button to enable workflows for this repository, then refresh the
Actions page.

**Build Runner Image fails with `403 Forbidden`**

This is a GitHub Container Registry permission issue. First set
**Settings -> Actions -> General -> Workflow permissions** to **Read and write
permissions**. If it still fails, open the existing package settings and give
this repository **Write** access under **Manage Actions access**, or delete the
old `job-hunt-runner` package and rerun the workflow.

**The LLM provider fails**

Check `config/api_config.yml`. The provider name, role providers, model names,
and required secret must match. If you changed providers, make sure every role
uses the new provider or intentionally mixes providers. Also replace every
`llm.models.*` value with a valid model name from that provider. Check
`secrets.<provider>.required`: the provider you use should be `true`, and unused
providers should be `false`. If the error mentions `python -m pip install ...`,
confirm `requirements.txt` includes that provider's Python package.

**PDF was not generated**

The `.tex` file is still saved. Open the workflow logs and search for the LaTeX
error. Common causes are unescaped `&`, `%`, `$`, `_`, or a missing brace.

**Story bank format got messy**

Restore the standard headings from this guide, then ask an AI helper to preserve
the exact `story_bank.md` format while moving content back under Draft, Final,
and Allocation Log.

**Cover letter sounds generic**

Add stronger, more specific final STAR stories and improve
`candidate_background` in `config/cover_letter_config.yml`.

**Git push fails**

Sign in to GitHub through VS Code, or use a GitHub personal access token when
the terminal asks for a password.
