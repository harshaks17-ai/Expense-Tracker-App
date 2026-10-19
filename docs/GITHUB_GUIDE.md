# GitHub Upload Guide

**Author:** [Harsha K S](https://github.com/harshaks17-ai)

Everything needed to take this project from your laptop to a public repo that looks intentional in a recruiter's 30-second glance.

---

## 1. Repo naming and description

| Field | Value |
| --- | --- |
| **Repo name** | `Expense-Tracker-App` |
| **Owner** | [`harshaks17-ai`](https://github.com/harshaks17-ai) |
| **Description** | `End-to-end expense analysis pipeline — cleaning, budgeting, per-user anomaly detection, charts and an interactive Streamlit dashboard (Python, Pandas, Plotly).` |
| **Visibility** | Public (it's portfolio work; the data is synthetic) |
| **Topics** | `python` `pandas` `data-analysis` `data-visualization` `plotly` `streamlit` `matplotlib` `seaborn` `personal-finance` `budget-analysis` `anomaly-detection` `dashboard` `eda` `data-science` |

Avoid: `expense-project`, `my-project`, `tracker123`, `New folder`.

---

## 2. Before you push — the checklist

```bash
# 1. Nothing secret, nothing local
git status --short

# 2. The pipeline actually runs from a clean clone
python main.py all

# 3. Tests pass
python -m pytest tests/ -q        # expect: 28 passed

# 4. .gitignore is in place BEFORE the first commit
cat .gitignore
```

The `.gitignore` in this project already excludes `__pycache__/`, `.venv/`, `venv/`, `.env`, `*.pyc`, `.ipynb_checkpoints/`, `.pytest_cache/`, `outputs/test_evidence/`, `.DS_Store` and the IDE folders.

**Decide once: do you commit `outputs/` or not?**

Committing the generated charts is what makes the repo convincing — the README images render immediately, with no setup needed. This project therefore commits `outputs/charts/` and `outputs/reports/` (they're regenerable, but they're also the proof). Keep `data/` committed too: the raw ledger is the "before" half of the story and the cleaned file is the "after".

The only generated artefacts deliberately **not** committed are the browser-test screenshots in `outputs/test_evidence/` — they're 800 KB each, they change on every test run, and they prove nothing a reader can't reproduce with one command.

---

## 3. First commit

```bash
cd Expense-Tracker-App

git init
git add .
git commit -m "feat: expense tracker app with cleaning, budgeting, anomaly detection and streamlit dashboard"
git branch -M main
```

Suggested commit message if you prefer conventional commits:

```text
feat: add expense tracker pipeline

- synthetic 50-user x 12-month ledger generator with budgets and injected dirt
- cleaning pipeline (dedupe x2, Rs. text amounts, 3 date formats, casing, outliers)
- analysis (category share, Pareto, per-user budget variance, savings, segments)
- per-user robust z-score anomaly detection over discretionary spend
- 10 matplotlib charts + interactive Plotly Streamlit dashboard
- insight report, data-quality report, JSON summary
- 27 pipeline tests + 2 headless dashboard tests + a 17-check browser test
```

---

## 4. Connect and push

```bash
git remote add origin https://github.com/harshaks17-ai/Expense-Tracker-App.git
git push -u origin main
```

Or with the GitHub CLI (no manual repo creation):

```bash
gh repo create Expense-Tracker-App --public --source=. --remote=origin --push
gh repo edit --add-topic python,pandas,data-analysis,data-visualization,plotly,streamlit,eda,dashboard,personal-finance,anomaly-detection
gh repo edit --description "End-to-end expense analysis pipeline - cleaning, budgeting, per-user anomaly detection, charts and an interactive Streamlit dashboard (Python, Pandas, Plotly)."
```

> If the repo was created on GitHub with an initial commit (a README from the template), use `git pull --rebase origin main` before your first push.

> **Windows note:** if `git push` asks for credentials and rejects your password, GitHub no longer accepts account passwords over HTTPS. Either let the Git Credential Manager open a browser sign-in, or use `gh auth login` first, or switch to an SSH remote.

---

## 5. Commit hygiene that recruiters notice

Good history looks like a project being *built*, not one that appeared:

```bash
git add src/config.py src/utils.py src/data_generator.py
git commit -m "feat: synthetic expense ledger generator with budgets and festival months"

git add src/data_cleaning.py
git commit -m "feat: cleaning pipeline with second dedupe pass after normalisation"

git add src/analysis.py
git commit -m "feat: category share, Pareto and per-user budget variance analysis"

git add src/analysis.py
git commit -m "feat: per-user robust z-score anomaly detection over discretionary spend"

git add src/visualization.py src/insights.py
git commit -m "feat: 10 charts and automated insight report"

git add dashboard.py main.py
git commit -m "feat: streamlit dashboard and CLI entry point"

git add tests/
git commit -m "test: add pipeline tests, screenshot test and 17-check browser test"

git add README.md docs/ images/ notebooks/
git commit -m "docs: README, project guide, interview prep and troubleshooting"
```

Also worth doing:

- **`git log --oneline`** — readable history is part of the deliverable.
- **One logical change per commit** — never "final final v2".
- **Never commit `.venv/`, `__pycache__/`, `.env`, or real personal bank data.** This is an expense tracker; the temptation to test it on your own statement is real. Don't. Keep the synthetic generator as the data source and upload real data only through the dashboard, which never writes it to disk.

---

## 6. README-first presentation order

What a recruiter sees, in order: repo name → description → README top. This README is ordered for exactly that:

1. Title + one-sentence value proposition + tech stack
2. Feature table
3. Problem → Solution with an architecture diagram
4. Quick start (copy-paste commands)
5. **Results with real numbers** — the proof it runs
6. Screenshots (charts + dashboard)
7. Testing section
8. Links to the docs

If you screenshot anything for a portfolio, capture the **dashboard** first — it's the most impressive artefact and it takes one command:

```bash
python main.py dashboard
```

---

## 7. Screenshots to capture (and where they go in the README)

| Artefact | Command | README location |
| --- | --- | --- |
| Raw dataset preview | open `data/raw/expenses_raw.csv` | Screenshots section |
| Cleaned dataset preview | open `data/processed/expenses_clean.csv` | Screenshots section |
| Console headline numbers | `python main.py all` | Results section |
| 10 charts | `outputs/charts/` | Screenshots grid |
| Dashboard tabs ×5 | `python main.py dashboard` | Dashboard walkthrough |
| Data-quality report | `outputs/reports/data_quality_report.md` | Results section |
| GitHub repo page | browser | Proof section of your portfolio / LinkedIn |

Copy the chart PNGs into `images/` so the README renders on GitHub regardless of where the repo is cloned:

```bash
cp outputs/charts/*.png images/    # Windows: Copy-Item "outputs\charts\*.png" images\
```

The browser test also captures its own evidence as it clicks through the app:

```bash
python tests/test_browser.py       # screenshots land in outputs/test_evidence/
```

---

## 8. Post-push polish

- **Pin the repo** on your GitHub profile.
- **Enable "About" description + topics** (see step 4).
- **Add a `LICENSE`** — MIT is already included.
- **LinkedIn post**: one screenshot of the dashboard, one sentence on what problem it solves, the repo link. Not "I built a project" — "here's what I made and why". The strongest hooks from this dataset are the 124.7% variable-budget burn rate, the 657 per-user anomaly alerts and the fact that 5 of 10 categories carry 77.3% of spend.
- **Star your own repo** and open one realistic issue to yourself (e.g. "add recurring-bill detection to separate fixed commitments from discretionary spend") — open issues with a clear scope read as active ownership.

---

## 9. If something goes wrong

| Problem | Fix |
| --- | --- |
| `fatal: remote origin already exists` | `git remote set-url origin https://github.com/<user>/<repo>.git` |
| `! [rejected] main -> main (fetch first)` | `git pull --rebase origin main` then push |
| `remote: Invalid username or token. Password authentication is not supported` | GitHub rejects account passwords; let Git Credential Manager open the browser sign-in, or run `gh auth login` |
| `fatal: not a git repository` | run `git init` from the project root |
| Pushed `.venv/` | `git rm -r --cached .venv` then `echo ".venv/" >> .gitignore` then `git commit -m "chore: ignore virtualenv"` |
| Pushed the 800 KB test screenshots | `git rm -r --cached outputs/test_evidence` (already in `.gitignore`) |
| Windows line endings everywhere | `git config --global core.autocrlf true` |
| README images not showing | image paths are case-sensitive on GitHub — keep the `images/` folder with the exact names used |
| Repo looks huge | check for committed real CSVs or test evidence: `git ls-files | xargs -I{} du -h {} | sort -rh | head` |
