# Setup Guide

Follow this guide from top to bottom. It assumes you are new to GitHub, Git,
VS Code, Docker, and LaTeX.

## What This Tool Does

This repository can search for jobs, score them against your profile, tailor a
LaTeX resume, write cover letters from your story bank, and save the outputs in
`jobs/`. The template includes this folder empty at first.

Before running the automation, you will set up your computer, create your own
private copy of the template, edit the resume and config files, test locally,
then run GitHub Actions.

## 1. Install The Required Apps

Install these first:

1. **Git** from `https://git-scm.com/downloads`
2. **Visual Studio Code** from `https://code.visualstudio.com/`
3. **Python** from `https://www.python.org/downloads/`
4. **Docker Desktop** from `https://www.docker.com/products/docker-desktop/`

After installing Docker Desktop, open it once and wait until it says the Docker
engine is running.

## 2. Set Up Git On Your Computer

Git needs your name and email so your commits are labeled correctly.

Open VS Code, then open a terminal:

```text
Terminal -> New Terminal
```

Run these commands with your own name and email:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Check that it worked:

```bash
git config --global --list
```

GitHub does not accept account passwords for Git pushes. The easiest option is
to sign in through VS Code when prompted. If GitHub asks for a password in the
terminal, use a GitHub personal access token instead of your GitHub password.

## 3. Create Your Own Private Repository

1. Open the shared template repository on GitHub.
2. Click **Use this template**.
3. Choose **Create a new repository**.
4. Set visibility to **Private**.
5. Create the repository.

Your new private repository is now your personal job-hunt workspace.

## 4. Clone Your Repository In VS Code

The easiest way:

1. Open VS Code.
2. Click **Source Control** in the left sidebar.
3. Click **Clone Repository**.
4. Paste your repository URL from GitHub.
5. Choose a folder on your computer.
6. Click **Open** when VS Code asks if you want to open the cloned repository.

Alternative terminal command:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
code .
```

## 5. Install Recommended VS Code Extensions

In VS Code, open **Extensions** and install:

- **Python** by Microsoft
- **Pylance** by Microsoft
- **YAML** by Red Hat
- **LaTeX Workshop** by James Yu
- **Docker** by Microsoft
- **GitHub Pull Requests and Issues** by GitHub

These make it easier to edit Python, YAML configs, LaTeX resumes, Docker setup,
and GitHub pull requests.

## 6. Create The Python Environment

In the VS Code terminal, run:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
playwright install chromium
```

On macOS/Linux, activate with:

```bash
source .venv/bin/activate
```

If VS Code asks which Python interpreter to use, choose the one inside `.venv`.

## 7. Set Up Docker For LaTeX

Check Docker:

```bash
docker --version
```

Test the LaTeX Docker image:

```bash
docker run --rm texlive/texlive:latest pdflatex --version
```

The first run can take a while because Docker downloads the TeX Live image.

## 8. Add VS Code LaTeX Build Settings

Create a folder named `.vscode` in the repository root if it does not exist.
Inside it, create `settings.json`.

Paste this:

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

To build a resume PDF:

1. Open `resume_double_column.tex` or `resume_single_column.tex`.
2. Open the Command Palette with `Ctrl+Shift+P`.
3. Run **LaTeX Workshop: Build LaTeX project**.

If Docker is not running, start Docker Desktop and try again.

## 9. Choose Your Resume Layout

This template includes two resume layouts:

- `resume_double_column.tex`: polished double-column AltaCV layout.
- `resume_single_column.tex`: simpler single-column ATS-friendly layout.

The automation uses the file selected in `config/api_config.yml`.

Open `config/api_config.yml` and find:

```yaml
profile:
  resume_tex: "resume_double_column.tex"
```

Change it to this if you prefer the single-column resume:

```yaml
profile:
  resume_tex: "resume_single_column.tex"
```

## 10. Personalize Your Resume

Open the resume file you selected and replace placeholders such as:

- `Candidate Name`
- `candidate@example.com`
- `Target City`
- `Example Company`
- example bullet points

Use only real information you can defend in an interview. Do not invent
metrics, titles, skills, companies, or dates.

## 11. Fill In Your Story Bank

Open `story_bank.md`.

The story bank has two layers:

1. **Draft - Raw Notes:** messy notes about your work, projects, volunteering,
   education, or side projects.
2. **Final - refined STAR stories:** polished stories that a chatbot has helped
   convert into Situation, Task, Action, Result format.

Start by adding raw notes. Do not try to make them perfect.

### Story IDs

Each story has a stable ID that you create. IDs help you categorize your
experiences and retrieve them later when tailoring to a job.

Examples:

- `ACME-PM-01`: one company, one Product Manager role
- `SHOP-PO-01`: one company, one Product Owner role
- `TECH-01`: technical project
- `VOL-01`: volunteer project
- `UNI-01`: university project
- `SIDE-01`: side project

Rules:

- Do not reuse IDs.
- Do not renumber old IDs.
- Add new IDs to the allocation log at the bottom of `story_bank.md`.

### Raw Notes To Final STAR Stories

Use `project_instructions.md` with an LLM chatbot to convert raw notes into
final STAR stories.

Simple workflow:

1. Add raw notes under `Draft - Raw Notes` in `story_bank.md`.
2. Open `project_instructions.md`.
3. Copy **Prompt 1 - Initial Story Refinement** into your chatbot.
4. Paste the relevant raw notes below the prompt.
5. Review the chatbot output carefully.
6. Move only accurate, defensible stories into `Final - refined STAR stories`.
7. Update the allocation log.

The automation uses the final refined stories for cover letters, so keep that
section factual and clean.

If you do not have a verified number, use a concrete scope instead, such as
team size, user group, launch timeline, or process improvement.

The story bank and project instruction file paths are configurable in
`config/api_config.yml`:

```yaml
profile:
  story_bank: "story_bank.md"
  project_instructions: "project_instructions.md"
```

## 12. Update Your Cover Letter Profile

Open `config/cover_letter_config.yml`.

Find:

```yaml
candidate_background:
```

Replace the example text with a short factual summary of your background.

Also update the closing:

```yaml
closing:
  format: "Best regards,\nCandidate Name"
```

Replace `Candidate Name` with your name.

## 13. Configure Job Search

Open `config/search_config.yml`.

The search config uses regions to define locations. Each region represents a city or area with its own set of companies.

### Basic Configuration

For a single location, update the `berlin` region:

- `location`: your target city or region (e.g., "Berlin", "Munich").
- `country`: your target country code, such as `DE`, `GB`, or `US`.
- `job_titles`: the roles you want (e.g., "Product Manager", "Product Owner").
- `exclusion_rules.excluded_title_terms`: title terms you never want processed,
  such as "engineer", "working student", "intern", or terms outside your target
  role family.
- `companies`: companies you want the automation to check.
- `excluded_companies`: companies you never want to process.

Example company entry:

```yaml
- name: Example Company
  career_url: boards.greenhouse.io/example
```

Common career URL formats:

- `boards.greenhouse.io/companyname`
- `jobs.lever.co/companyname`
- `jobs.smartrecruiters.com/companyname`
- `careers.companyname.com`

### Adding Multiple Locations

To search in multiple cities or regions:

1. Copy the entire `berlin` region block.
2. Paste it below and change the region name (e.g., `munich`, `hamburg`, `london`).
3. Set `enabled: true` to activate the new region.
4. Update `location`, `country`, `search_lang`, and `description` for the new area.
5. Replace the `companies` list with companies specific to that location.
6. Companies from all enabled regions will be scraped daily.

Example for adding Munich:

```yaml
regions:
  berlin:
    # ... existing berlin config ...

  munich:
    enabled: true
    country: "DE"
    search_lang: "en"
    location: "Munich"
    description: "Munich tech companies"
    companies:
      - name: Example Munich Company
        career_url: boards.greenhouse.io/examplemunich
      # Add more Munich companies...
```

You can have as many regions as needed. Disable regions by setting `enabled: false`.

## 14. Set Your Scoring Rules

Open `config/scoring_config.yml`.

Important fields:

```yaml
min_fit_score: 70
max_years_experience_required: 5
```

Use a lower `min_fit_score` if you want more jobs to pass. Use a higher score
if you want stricter filtering.

## 15. Get API Keys Or Set Up A Local LLM

The automation needs two kinds of services:

- an LLM provider for validation, scoring, tailoring, and cover letters
- optional search providers for broad discovery when direct scraping is not enough

You can use a cloud LLM provider, or you can run a local LLM with Ollama.

### Option A: Anthropic Claude

Use this if you want strong resume and cover-letter quality with minimal setup.

1. Go to `https://console.anthropic.com/`.
2. Create or sign in to your account.
3. Add billing if required.
4. Open API keys in the console.
5. Create a new key.
6. Copy it once and store it safely.

Use this secret name:

```text
ANTHROPIC_API_KEY
```

In `config/api_config.yml`, keep:

```yaml
llm:
  default_provider: anthropic
```

### Option B: OpenAI

Use this if you prefer OpenAI models.

1. Go to `https://platform.openai.com/`.
2. Create or sign in to your account.
3. Create a project if prompted.
4. Open API keys.
5. Create a new API key.
6. Copy it once and store it safely.

Use this secret name:

```text
OPENAI_API_KEY
```

In `config/api_config.yml`, set:

```yaml
llm:
  default_provider: openai
  providers:
    validation: openai
    scoring: openai
    tailoring: openai
    cover_letter: openai
    discovery: openai
```

Install the OpenAI Python package:

```bash
python -m pip install openai
```

### Option C: Google Gemini

Use this if you prefer Google Gemini.

1. Go to `https://aistudio.google.com/`.
2. Sign in with your Google account.
3. Open API keys.
4. Create a new API key.
5. Copy it once and store it safely.

Use this secret name:

```text
GOOGLE_API_KEY
```

In `config/api_config.yml`, set:

```yaml
llm:
  default_provider: google
  providers:
    validation: google
    scoring: google
    tailoring: google
    cover_letter: google
    discovery: google
```

Install the Google package:

```bash
python -m pip install google-generativeai
```

### Option D: Local LLM With Ollama

Use this if you want to run models on your own computer. This avoids LLM API
costs, but quality and speed depend on your machine and model.

1. Install Ollama from `https://ollama.com/`.
2. Open a terminal.
3. Pull a model:

```bash
ollama pull llama3.2
```

4. Test it:

```bash
ollama run llama3.2
```

5. Type a short message. If the model responds, Ollama works.
6. Exit with `Ctrl+D` or close the terminal.

The automation talks to Ollama at:

```text
http://localhost:11434
```

In `config/api_config.yml`, set:

```yaml
llm:
  default_provider: ollama
  providers:
    validation: ollama
    scoring: ollama
    tailoring: ollama
    cover_letter: ollama
    discovery: ollama
  models:
    validation: "llama3.2"
    scoring: "llama3.2"
    tailoring: "llama3.2"
    cover_letter: "llama3.2"
    discovery: "llama3.2"

secrets:
  anthropic:
    required: false
```

Install the OpenAI Python package because Ollama uses an OpenAI-compatible API
inside this project:

```bash
python -m pip install openai
```

Keep Ollama running whenever you run the automation locally.

Important: GitHub-hosted Actions cannot use Ollama running on your laptop. If
you want scheduled GitHub Actions, use a cloud provider such as Anthropic,
OpenAI, or Google, or set up your own self-hosted runner.

### Search Providers For Discovery And Scraping

The pipeline does not depend on one search API. It tries direct ATS APIs,
HTTP/BeautifulSoup scraping, Playwright rendering, a temporary SearXNG container
inside GitHub Actions, and then whichever external APIs you configure.

SearXNG needs no key. The workflows start it from this repo using
`.github/searxng/settings.yml` and expose it at:

```text
http://127.0.0.1:8080
```

If SearXNG cannot start or an upstream search engine throttles it, the pipeline
continues with the other providers.

### Brave Search API, Optional

Brave Search can be used to discover jobs from web search.

1. Go to `https://brave.com/search/api/`.
2. Create an account.
3. Choose a plan.
4. Create or copy your API key.

Use this secret name:

```text
BRAVE_API_KEY
```

### Tavily, Optional

1. Go to `https://tavily.com/`.
2. Create a free account.
3. Copy your API key from the dashboard.

Use this secret name:

```text
TAVILY_API_KEY
```

### Exa, Optional

1. Go to `https://exa.ai/`.
2. Create a free account.
3. Copy your API key from the dashboard.

Use this secret name:

```text
EXA_API_KEY
```

### RapidAPI / JSearch, Optional

JSearch is optional. It can add more job-board results, but the pipeline can run
without it.

1. Go to `https://rapidapi.com/`.
2. Create an account.
3. Subscribe to the JSearch API if you want to use it.
4. Open your RapidAPI app or project.
5. Copy the API key.

Use this secret name:

```text
RAPIDAPI_KEY
```

## 16. Store API Keys Locally

For local testing, store keys in your terminal session or in your system
keyring.

### Quick Local Option: Environment Variables

PowerShell on Windows:

```powershell
$env:ANTHROPIC_API_KEY="paste-your-key-here"
$env:BRAVE_API_KEY="paste-your-key-here"
$env:TAVILY_API_KEY="paste-your-key-here"
$env:EXA_API_KEY="paste-your-key-here"
```

macOS/Linux:

```bash
export ANTHROPIC_API_KEY="paste-your-key-here"
export BRAVE_API_KEY="paste-your-key-here"
export TAVILY_API_KEY="paste-your-key-here"
export EXA_API_KEY="paste-your-key-here"
```

Use `OPENAI_API_KEY` or `GOOGLE_API_KEY` instead of `ANTHROPIC_API_KEY` if you
chose OpenAI or Google.

These values last only for the current terminal session.

### Better Local Option: Keyring

With your `.venv` active, run Python:

```bash
python
```

Then paste the lines you need:

```python
import keyring
keyring.set_password("job-hunt", "ANTHROPIC_API_KEY", "paste-your-key-here")
keyring.set_password("job-hunt", "BRAVE_API_KEY", "paste-your-key-here")
keyring.set_password("job-hunt", "TAVILY_API_KEY", "paste-your-key-here")
keyring.set_password("job-hunt", "EXA_API_KEY", "paste-your-key-here")
keyring.set_password("job-hunt", "RAPIDAPI_KEY", "paste-your-key-here")
```

Use `OPENAI_API_KEY` or `GOOGLE_API_KEY` instead of `ANTHROPIC_API_KEY` if you
chose OpenAI or Google.

Exit Python:

```python
exit()
```

Never commit API keys into files.

## 17. Test Locally First

Run tests:

```bash
python -m pytest -q
```

Run one direct job link:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py --mode tailor-links --links "https://example.com/job"
```

You need API keys, or Ollama running locally, before real job processing can
work. If local testing is too much, use GitHub Actions after adding secrets in
the next step.

## 18. Add API Keys In GitHub

Do not paste API keys into files.

`GH_PAT` is required if you want GitHub Actions to run this automation and save
generated files back into your repository. Without it, the workflow may run but
will fail when it tries to push `jobs/`, `README.md`, or updated config files.

### Create `GH_PAT`

1. Open GitHub.
2. Click your profile picture in the top-right corner.
3. Go to **Settings**.
4. Go to **Developer settings**.
5. Go to **Personal access tokens**.
6. Choose **Fine-grained tokens**.
7. Click **Generate new token**.
8. Use a clear name, for example:

```text
job-hunt-actions
```

9. Set an expiration date you are comfortable maintaining.
10. For **Resource owner**, select your GitHub user or organization.
11. For **Repository access**, choose **Only select repositories**.
12. Select the private repo you created from this template.
13. Under **Repository permissions**, set:

```text
Contents: Read and write
```

14. Click **Generate token**.
15. Copy the token immediately. GitHub will not show it again.

If your organization blocks fine-grained tokens, create a classic token instead
and give it the `repo` scope.

For this template's workflows, `GH_PAT` only needs to check out your repo and
push normal generated files back to the same repo. That is why
`Contents: Read and write` is enough.

`GH_PAT` does not need workflow permission unless you later change the workflows
so they push edits to files under `.github/workflows/` or call the GitHub API to
start other workflow runs.

In your GitHub repository:

1. Go to **Settings**.
2. Go to **Secrets and variables**.
3. Click **Actions**.
4. Click **New repository secret**.

Add the secrets you use:

- `ANTHROPIC_API_KEY`: required if using Anthropic.
- `OPENAI_API_KEY`: required if using OpenAI.
- `GOOGLE_API_KEY`: required if using Google Gemini.
- `BRAVE_API_KEY`: optional search fallback.
- `TAVILY_API_KEY`: optional search fallback.
- `EXA_API_KEY`: optional search fallback.
- `RAPIDAPI_KEY`: optional, only if using JSearch.
- `GH_PAT`: required for GitHub Actions to commit generated files back to your repository.

If you use Ollama locally, you do not need an LLM API key for local runs. For
GitHub-hosted Actions, use a cloud LLM provider instead.

The secret names must match `config/api_config.yml`.

## 19. Run The Automation In GitHub

1. Open your repository on GitHub.
2. Click **Actions**.
3. Select **Tailor Links** if you want to process specific job links.
4. Click **Run workflow**.
5. Paste one job URL into `url_1`.
6. Click **Run workflow**.

When the run finishes, check the `jobs/` folder in your repository.

The folder starts empty except for `.gitkeep`; each successful run adds one
subfolder per processed job.

For scheduled daily search, use the **Job Hunt Pipeline** workflow. Scheduled
hunt runs are staggered by enabled region:

- 06:00 UTC runs the first enabled region in `config/search_config.yml`.
- 07:00 UTC runs the second enabled region.
- Later hourly slots continue through 17:00 UTC.
- Empty slots exit quickly if you have fewer enabled regions.

To run a hunt manually:

1. Open **Actions -> Job Hunt Pipeline**.
2. Click **Run workflow**.
3. Set `job` to `hunt`.
4. Set `region` to `all` for every enabled region, or enter one region key such
   as `berlin`.
5. Click **Run workflow**.

Run it manually once before relying on the schedule.

## 20. Review The Output

Each processed job creates a folder like:

```text
jobs/YYYY-MM-DD_company_role/
```

Inside you may see:

- `jd.md`: the job description.
- `resume_tailored.tex`: tailored resume source.
- `resume_tailored.pdf`: tailored resume PDF, if PDF compilation succeeded.
- `cover_letter.md`: generated cover letter.
- `cover_letter.pdf`: generated cover letter PDF, if generated.
- `meta.json`: score and matching details.

Always review the resume and cover letter before applying.

Each hunt run tailors at most 15 matched jobs. If more than 15 jobs pass the
score threshold, the pipeline processes the 15 highest-scoring matches first.

## 21. Faster GitHub Actions With The Runner Image

The hunt and tailor-links workflows use a prebuilt GHCR Docker image named
`job-hunt-runner`. It contains Python, the Python dependencies, Playwright
Chromium, and LaTeX. This avoids reinstalling LaTeX during every run.

By default, the workflows look for:

```text
ghcr.io/<your-github-owner>/job-hunt-runner:latest
```

If your organization provides a shared public image, set a repository variable
named `JOB_HUNT_RUNNER_IMAGE` to that full image name, for example:

```text
ghcr.io/job-network-projects/job-hunt-runner:latest
```

### A. Build The Image Once

After setup, build the image once:

1. Open your repository on GitHub.
2. Go to **Actions**.
3. Open **Build Runner Image**.
4. Click **Run workflow**.
5. Wait for the workflow to finish.

The image is also rebuilt automatically when `Dockerfile`, `.dockerignore`,
`requirements.txt`, or the build workflow changes.

If you are using a shared public image through `JOB_HUNT_RUNNER_IMAGE`, you do
not need to build your own image unless you changed `Dockerfile` or
`requirements.txt`.

### B. If The Image Is Missing

The daily hunt and tailor-links workflows will still run. They fall back to the
native install path, which is slower because LaTeX is installed during the job.

If you see a warning that the prebuilt runner image is unavailable:

1. Run **Actions -> Build Runner Image**.
2. Wait for it to complete.
3. Re-run **Job Hunt Pipeline** or **Tailor Links**.

### C. GitHub Packages Permission

The workflow publishes the image to GitHub Container Registry using the built-in
`GITHUB_TOKEN`. If image publishing fails, check:

1. Open your repository on GitHub.
2. Go to **Settings -> Actions -> General**.
3. Under **Workflow permissions**, choose **Read and write permissions**.
4. Save.
5. Re-run **Build Runner Image**.

The image is large because LaTeX font packages are large. If many users are in
one organization, prefer one shared public image instead of each user building a
private copy.

## 22. Getting Future Template Updates

Updates from the original template are not automatic in repositories created
with **Use this template**. This is intentional: your resume, story bank, jobs,
and configs are personal, so updates should arrive through a pull request that
you can review.

### A. Recommended: Use The Update Workflow

Use this when you want the latest code, workflows, dependencies, and docs without
typing Git commands.

1. Open your repository on GitHub.
2. Go to **Actions**.
3. Open **Update From Template**.
4. Click **Run workflow**.
5. Keep `upstream_repo` as `Job-Network-Projects/job-hunter-template`.
6. Keep `upstream_branch` as `main`.
7. Leave `update_config` turned off unless you want template config files to
   overwrite your current config files.
8. Click **Run workflow**.
9. Wait for the workflow to open a pull request.
10. Review the changed files and merge the pull request when ready.
11. Pull the merged changes to your laptop:

```bash
git checkout main
git pull origin main
```

If your local branch is named `master`, use:

```bash
git checkout master
git pull origin master
```

By default, the workflow preserves:

- resumes
- story bank
- project instructions
- generated jobs
- config files

If a release adds new config fields, read the pull request description and this
`SETUP.md`, then copy only the new fields you need into your own config files.

### B. If You Have Local Uncommitted Changes

Before pulling updates locally, check whether you have unsaved local changes:

```bash
git status
```

If Git says `nothing to commit, working tree clean`, you can pull normally:

```bash
git pull origin main
```

If Git shows changed files, save them first:

```bash
git add .
git commit -m "save my local changes"
git pull origin main
```

If Git says the branch has no upstream tracking branch, run:

```bash
git branch --set-upstream-to=origin/main main
git pull
```

### C. Manual Git Fallback

Use this only if the update workflow is unavailable or you prefer working from
your terminal.

Do this once:

```bash
git remote add upstream https://github.com/Job-Network-Projects/job-hunter-template.git
git remote -v
```

If Git says `remote upstream already exists`, continue.

Save your work:

```bash
git status
git add .
git commit -m "save my local changes"
```

If Git says `nothing to commit`, continue.

Create a backup branch:

```bash
git branch
git checkout -b backup-before-template-update
git checkout main
```

Use `master` instead of `main` if your repo uses `master`.

Fetch and merge updates:

```bash
git fetch upstream
git branch -r
git checkout main
git merge upstream/main
```

If Git says histories are unrelated, run:

```bash
git merge --allow-unrelated-histories upstream/main
```

Push after a successful merge:

```bash
git push origin main
```

Conflicts are normal if both you and the template changed the same file. In
VS Code, open **Source Control**, click each conflicted file, choose the version
you want to keep, save the file, then run:

```bash
git add .
git commit -m "merge template updates"
git push origin main
```

If the merge feels wrong before committing:

```bash
git merge --abort
```

## 23. Automatically Delete Merged PR Branches

If you use pull requests in your own repo, GitHub can delete the PR branch after
the PR is merged.

1. Open your repo on GitHub.
2. Go to **Settings -> General**.
3. Scroll to **Pull Requests**.
4. Turn on **Automatically delete head branches**.

This only deletes the temporary branch after a PR is merged. It does not delete
your `main` branch, your files, or branches from someone else's fork.

## Common Problems

**No jobs found**

Check `config/search_config.yml`. The company URLs or job titles may be too
narrow.

**Secret not found**

Check that the secret exists under GitHub repository **Settings -> Secrets and
variables -> Actions** and that the name exactly matches `config/api_config.yml`.

**PDF was not generated**

The `.tex` file is still saved. Check the workflow logs for the LaTeX error.
You can also edit the `.tex` file manually.

**Cover letter sounds too generic**

Add better, more specific stories to `story_bank.md` and improve
`candidate_background` in `config/cover_letter_config.yml`.
