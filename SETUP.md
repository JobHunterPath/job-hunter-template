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

## Optional: Run Locally On Your Computer

This section is only for people comfortable using a terminal.

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

Run direct job links:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py --mode tailor-links --links "https://example.com/job"
```

Run the daily hunt locally:

```bash
PYTHONPATH=scripts python scripts/pipeline/orchestrator.py
```

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
