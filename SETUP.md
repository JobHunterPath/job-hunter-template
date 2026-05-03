# Setup Guide

This guide is written for people who are comfortable editing files in GitHub,
but who do not want to work deeply with code. Follow it from top to bottom.

## What This Tool Does

This repository can:

- Search for jobs from company career pages and job boards.
- Check whether each job looks relevant to your profile.
- Tailor your LaTeX resume for matching jobs.
- Write a cover letter using your own story bank.
- Save everything in a `jobs/` folder for review.

You will need to replace the example profile files with your own information
before running the automation.

## 1. Create Your Own Private Copy

1. Open the template repository on GitHub.
2. Click **Use this template**.
3. Choose **Create a new repository**.
4. Set visibility to **Private**.
5. Create the repository.

Your new private repository is now your personal job-hunt workspace.

## 2. Choose Your Resume Layout

This template includes two resume layouts:

- `resume_double_column.tex`: a polished double-column AltaCV resume.
- `resume_single_column.tex`: a simpler single-column resume that is easier for many applicant tracking systems to parse.

The automation uses the file selected in `config/api_config.yml`.

Open `config/api_config.yml` and find:

```yaml
profile:
  resume_tex: "resume_double_column.tex"
```

Keep this if you want the double-column resume. Change it to this if you want
the single-column resume:

```yaml
profile:
  resume_tex: "resume_single_column.tex"
```

## 3. Personalize Your Resume

Open the resume file you selected:

- `resume_double_column.tex`, or
- `resume_single_column.tex`

Replace all placeholder text such as:

- `Candidate Name`
- `candidate@example.com`
- `Target City`
- `Example Company`
- example bullet points

Use only real information you can defend in an interview. Do not invent
metrics, titles, skills, companies, or dates.

## 4. Fill In Your Story Bank

Open `story_bank.md`.

Replace the example stories with 3 to 10 real stories from your work,
education, projects, volunteering, or internships.

Each story should include:

- **Context:** What was the situation?
- **Action:** What did you personally do?
- **Result:** What changed because of your work?

Good results can be numbers, but they do not have to be. If you do not have a
verified number, use a concrete scope instead, such as team size, user group,
launch timeline, or process improvement.

## 5. Update Your Cover Letter Profile

Open `config/cover_letter_config.yml`.

Find:

```yaml
candidate_background:
```

Replace the example text with a short factual summary of your background.

Example:

```yaml
candidate_background: |
  Candidate Name, Product Manager based in Berlin.
  Background: Experience in SaaS products, customer discovery, roadmap planning, and cross-functional delivery.
  Currently targeting Product Manager and Product Owner roles in Berlin.
```

Also update the closing:

```yaml
closing:
  format: "Best regards,\nCandidate Name"
```

Replace `Candidate Name` with your name.

## 6. Choose Jobs And Companies To Search

Open `config/search_config.yml`.

Update these parts:

- `location`: your target city or region.
- `country`: your target country code, such as `DE`, `GB`, or `US`.
- `job_titles`: the roles you want.
- `companies`: companies you want the automation to check.
- `excluded_companies`: companies you never want to process.

Example company entry:

```yaml
- name: Example Company
  career_url: boards.greenhouse.io/example
```

The `career_url` should usually be the company career page or ATS page. Common
examples include:

- `boards.greenhouse.io/companyname`
- `jobs.lever.co/companyname`
- `jobs.smartrecruiters.com/companyname`
- `careers.companyname.com`

## 7. Set Your Scoring Rules

Open `config/scoring_config.yml`.

Important fields:

```yaml
min_fit_score: 70
max_years_experience_required: 5
```

Use a lower `min_fit_score` if you want more jobs to pass. Use a higher score
if you want stricter filtering.

## 8. Add API Keys In GitHub

The automation needs API keys. Do not paste keys into files.

In your GitHub repository:

1. Go to **Settings**.
2. Go to **Secrets and variables**.
3. Click **Actions**.
4. Click **New repository secret**.

Add the secrets you use:

- `ANTHROPIC_API_KEY`: required if using Anthropic.
- `BRAVE_API_KEY`: required for Brave Search.
- `RAPIDAPI_KEY`: optional, only if using JSearch.
- `GH_PAT`: optional, only if you want GitHub Actions to commit generated files back to your repository.

The secret names must match `config/api_config.yml`.

## 9. Run The Automation In GitHub

The easiest way to run this tool is through GitHub Actions.

1. Open your repository on GitHub.
2. Click **Actions**.
3. Select **Tailor Links** if you want to process specific job links.
4. Click **Run workflow**.
5. Paste one job URL into `url_1`.
6. Click **Run workflow**.

When the run finishes, check the `jobs/` folder in your repository.

For scheduled daily search, use the **Job Hunt Pipeline** workflow. Run it
manually once before relying on the schedule.

## 10. Review The Output

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

## 11. Set Up Your Computer

Set up your computer before relying on automation. This lets you edit files in
VS Code, preview LaTeX resumes, run tests locally, and catch basic setup issues
before GitHub Actions spends API credits.

### A. Install The Required Apps

Install these first:

1. **Git** from `https://git-scm.com/downloads`
2. **Visual Studio Code** from `https://code.visualstudio.com/`
3. **Python** from `https://www.python.org/downloads/`
4. **Docker Desktop** from `https://www.docker.com/products/docker-desktop/`

After installing Docker Desktop, open it once and wait until it says the Docker
engine is running.

### B. Set Up Git Name And Email

Git needs your name and email so your commits are labeled correctly.

Open VS Code, then open the terminal:

```text
Terminal -> New Terminal
```

Run these commands, replacing the example values:

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

### C. Clone Your GitHub Repository In VS Code

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

### D. Install Recommended VS Code Extensions

In VS Code, open **Extensions** and install:

- **Python** by Microsoft
- **Pylance** by Microsoft
- **YAML** by Red Hat
- **LaTeX Workshop** by James Yu
- **Docker** by Microsoft
- **GitHub Pull Requests and Issues** by GitHub

These make it easier to edit Python, YAML configs, LaTeX resumes, Docker setup,
and GitHub pull requests.

### E. Create The Python Environment

Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

On macOS/Linux, activate with:

```bash
source .venv/bin/activate
```

If VS Code asks which Python interpreter to use, choose the one inside `.venv`.

### F. Check Docker Works

Run:

```bash
docker --version
```

Then test the LaTeX Docker image:

```bash
docker run --rm texlive/texlive:latest pdflatex --version
```

The first run can take a while because Docker downloads the TeX Live image.

### G. Add VS Code LaTeX Build Settings

Create a folder named `.vscode` in the repository root if it does not exist.
Inside it, create a file named `settings.json`.

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

To build a resume PDF in VS Code:

1. Open `resume_double_column.tex` or `resume_single_column.tex`.
2. Open the Command Palette with `Ctrl+Shift+P`.
3. Run **LaTeX Workshop: Build LaTeX project**.

If Docker is not running, start Docker Desktop and try again.

### H. Run The Automation Locally

Run direct job links:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py --mode tailor-links --links "https://example.com/job"
```

Run the daily hunt locally:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py
```

Run tests:

```bash
python -m pytest -q
```

## 12. Getting Future Template Updates

Updates from the original template are not automatic in repositories created
with **Use this template**. This is intentional: your resume, story bank, and
configs are personal, so updates should not overwrite them without your review.

Use the steps below whenever you want to pull improvements from the shared
template into your own private repo.

### A. Open Your Repo In VS Code

1. Open VS Code.
2. Open your cloned repository folder.
3. Open a terminal:

```text
Terminal -> New Terminal
```

### B. Check Your Current Branch

Run:

```bash
git branch
```

The branch with `*` is your current branch. Most repositories use `main`.
Some older repositories use `master`.

The examples below use `main`. If your branch is `master`, replace `main` with
`master` in the commands.

### C. Add The Template Repo As Upstream

You only need to do this once.

```bash
git remote add upstream https://github.com/Job-Network-Projects/job-hunter-template.git
git remote -v
```

You should see both:

```text
origin    your private repo
upstream  the shared template repo
```

If Git says `remote upstream already exists`, that is fine. Continue to the
next step.

### D. Save Your Current Work First

Before pulling template updates, save your own changes:

```bash
git status
git add .
git commit -m "save my local changes"
```

If Git says `nothing to commit`, that is fine.

### E. Create A Backup Branch

This gives you an easy way back if anything goes wrong:

```bash
git checkout -b backup-before-template-update
git checkout main
```

Again, use `master` instead of `main` if your repo uses `master`.

### F. Pull And Merge Template Updates

First fetch the latest template branches:

```bash
git fetch upstream
git branch -r
```

Look for one of these lines:

```text
upstream/main
upstream/master
```

Use the branch that actually appears. Do not run `git merge upstream` by
itself. `upstream` is only the remote name; you must merge a branch such as
`upstream/main`.

If you see `upstream/main`, run:

```bash
git checkout main
git merge upstream/main
```

If this is your first time merging from the template and Git says the histories
are unrelated, run:

```bash
git merge --allow-unrelated-histories upstream/main
```

If there are no conflicts, Git will complete the merge automatically.

Then push the updated repo back to GitHub:

```bash
git push origin main
```

If your branch is `master`, use:

```bash
git fetch upstream
git checkout master
git merge upstream/master
git push origin master
```

If Git says `upstream/main - not something we can merge`, run:

```bash
git branch -r
```

Then check what the upstream branch is actually called. If the output shows
`upstream/master`, use `upstream/master`. If it shows no `upstream/...` branches,
the remote URL or your GitHub access to the template repo is not set up
correctly.

### G. If Git Reports Merge Conflicts

Merge conflicts mean both you and the template changed the same part of a file.
This is normal for files like configs, resumes, and documentation.

In VS Code:

1. Open the **Source Control** panel.
2. Click each file listed under **Merge Changes**.
3. VS Code will show buttons such as:
   - **Accept Current Change**: keep your version.
   - **Accept Incoming Change**: use the template version.
   - **Accept Both Changes**: keep both and edit manually.
4. Save the file after choosing.
5. Repeat for every conflicted file.

After all conflicts are fixed:

```bash
git add .
git commit -m "merge template updates"
git push origin main
```

Use `master` instead of `main` if needed.

### H. If You Want To Cancel A Bad Merge

If the merge feels wrong and you have not committed it yet, run:

```bash
git merge --abort
```

You can also go back to your backup branch:

```bash
git checkout backup-before-template-update
```

### What Usually Merges Cleanly

Updates to reusable automation code usually merge cleanly:

- `scripts/`
- `tests/`
- `.github/workflows/`
- `requirements.txt`
- documentation

### Files You Should Review Carefully

These files often contain your personal setup, so Git may show conflicts if both
you and the template changed them:

- `config/*.yml`
- `resume_double_column.tex`
- `resume_single_column.tex`
- `resume.tex`
- `story_bank.md`
- `README.md`
- `SETUP.md`

### How Merge Conflicts Work

If Git cannot combine changes automatically, it marks the file with conflict
blocks:

```text
<<<<<<< HEAD
your version
=======
template version
>>>>>>> upstream/main
```

Open the file in VS Code, choose which parts to keep, remove the conflict
markers, then save the file.

After resolving conflicts:

```bash
git add .
git commit -m "merge template updates"
```

If you are unsure, keep your personal resume, story bank, and config values, and
copy only the useful new comments or options from the template.

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
