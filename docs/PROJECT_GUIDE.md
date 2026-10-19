# Project Guide - Explanation, Planning & Proof Building

**Author:** [Harsha K S](https://github.com/harshaks17-ai) · **Repo:** [Expense-Tracker-App](https://github.com/harshaks17-ai/Expense-Tracker-App) · **v1.0.0**

# Part 1 - Project explanation

## What is an Expense Tracker App?

A tool that turns a year of raw, messy transaction records into a clear picture of where the money went.

**Input:** one row per transaction (date, category, amount, merchant, payment method) for 50 synthetic users across 12 months, plus an income file.

**Output:** spend by category, per-user budget variance, monthly trends, savings-rate swings, weekend and time-of-day patterns, top merchants, a Pareto of spend concentration, segments, anomalous days, and a clickable dashboard.

## Simple explanation (for a non-technical listener)

> Imagine 50 people hand you a year of receipts: crumpled pages, amounts written as words, blank categories, duplicates. You cannot answer "who is overspending?" from that pile. This app cleans it, checks every transaction against that person's own budget, and shows the average person spends ₹62,105 a month against a ₹53,500 budget, five categories soak up 77.3% of spending, and 657 days were genuinely unusual - all as charts and a clickable dashboard.

## Technical explanation (for a technical listener)

> A six-stage pipeline (`generate → clean → analyze → visualize → insights → dashboard`) over `transaction_id × user_id × date × category × amount × merchant × payment_method`, plus `income.csv`:
>
> 1. **Generate** - 50 users × 12 months (2025-10-01 to 2026-09-30, seed 42, INR), archetypes, rent days, festival scaling, 7,092 injected issues.
> 2. **Clean** - dedupe twice (duplicates differ by format), whitespace/casing normalisation, text-amount parsing, blank/unknown categories, outlier and future-date removal, ISO-first parsing.
> 3. **Analyse** - per-user budget variance, shares, Pareto, trends, savings rate, segments, robust-z anomalies (median + MAD).
> 4. **Visualise** 10 charts, **insights** a report, **present** a 5-tab Streamlit dashboard.
>
> 30 automated tests cover it: 27 pipeline, 2 headless AppTest, 1 browser suite of 17 checks.

## Why it matters

| Without it | With it |
| --- | --- |
| 17,176 dirty rows | 16,179 validated transactions (94.20% retention), with an audit trail |
| "I think I spend too much" | ₹62,105 monthly spend per user vs a ₹53,500 budget; savings rate +10.0% |
| Categories look equally guilty | Education +94.6%, Travel +84.6%, Misc +16.9% over budget; Rent & Utilities -4.4% under |
| One average user | 18% of users generate 37.5% of spend - a 4.5× gap to light users |

## How organisations use this

- **Expense-report auditing** - flag outliers, duplicates and impossible amounts.
- **Corporate-card spend policy** - actuals vs per-category policy limits.
- **Subscription / ops anomaly alerting** - robust z-scores catch billing spikes early.
- **Personal-finance apps** - category breakdowns, budgets, savings trends.
- **Fintech category classification** - merchant aggregation feeds classifier features.

## The workflow

`generate → clean → analyze → visualize → insights → dashboard`, driven by one CLI: `python main.py all|generate|clean|analyze|visualize|insights|dashboard`.

# Part 2 - Tech stack options

## Option A - Easy (beginner, ~2 days)

A single Jupyter notebook: pandas groupbys for category totals plus 3 static plots, with no dashboard, tests or package structure. Fast to learn from; reads as coursework, not a product.

## Option B - Intermediate (recommended, ~5 days) ✅ **selected**

| Aspect | Detail |
| --- | --- |
| Ambition | a modular, tested, documented pipeline (this project) |
| Tools | Python 3.10+, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Streamlit, Pytest |
| Output | `src/` package, 10 charts, insights report, 5-tab Streamlit dashboard, docs, 30 tests |

## Option C - Advanced (enterprise, ~3 weeks)

Cloud-deployed: Option B plus a database, scheduled ingestion, auth and ML forecasting, hosted for many users, with next-month spend forecasts.

## Why Option B is selected

1. **Best visible artefacts per day of build.** Five days buys 10 charts, a report, a dashboard and tests; A shows almost nothing, C takes three weeks.
2. **Every stage is independently testable.** Each CLI command runs one stage, so bugs are isolated instead of debugged end-to-end.
3. **It teaches what interviewers probe.** Data cleaning (94.20% retention) and correctly-scoped statistics (per-user budgets, matching numerators to denominators) separate a project from a tutorial.
4. **It scales into Option C cleanly.** `src/` maps 1:1 onto production: generator → ingestion, cleaning → ETL, analysis → metrics, dashboard → presentation.

# Part 3 - Architecture

## Input schema

`transactions.csv` (`amount` is sometimes text like "1,250"):

| Column | Type |
| --- | --- |
| `transaction_id` | str |
| `user_id` | str |
| `date` | str (3 mixed formats on purpose) |
| `category` | str |
| `amount` | str or float |
| `merchant` | str |
| `payment_method` | str |

`income.csv`: `user_id · year_month · income` (₹68,000 base per user per month).

**Budgets (₹53,500 per user per month):** Food & Dining ₹8,000 · Groceries ₹5,000 · Transport ₹4,000 · Rent & Utilities ₹18,000 · Shopping ₹6,000 · Entertainment ₹2,500 · Health ₹2,000 · Education ₹1,500 · Travel ₹5,000 · Miscellaneous ₹1,500.

## Processing

1. **Generate** - 50 users × 12 months (2025-10-01 → 2026-09-30, seed 42), heavy/moderate/light archetypes, rent days from the 1st to the 28th, festival months 2025-11 and 2026-03 scaled ×1.45, per-category weekend probability, 7,092 injected issues.
2. **Clean** - 867 whitespace, 590 casing, 238 text amounts, 205 blank amounts, 197 blank categories, 172 unknown categories, 79 zero/negative, 49 outliers, 76 future-dated rows, 183 + 36 duplicates, 0 unparseable dates; 17,176 → 16,179 rows.
3. **Analyse** - budget variance, shares, Pareto, monthly/weekday patterns, segments, robust-z anomalies (median + MAD, z > 2.5, ₹5,000 floor, ≥2 transactions/day, recurring bills excluded; daily median ₹71,595, MAD ₹17,523 → 657 flagged user-days).
4. **Visualise** 10 charts, **insights** savings rate, burn rate, top merchants, **dashboard** the 5-tab app.

## Output

`data/processed/` holds the cleaned CSVs; `outputs/charts/` the 10 PNGs (mirrored in `images/`); `outputs/reports/` the insights and data-quality reports; `outputs/test_evidence/` the captured evidence.

## Data-flow explanation

```
data_generator ──► data/raw/          17,176 rows, 7,092 injected issues
                      ▼
data_cleaning  ──► data/processed/    16,179 rows (retention 94.20%)
                      ▼
analysis       ──► budgets, shares, Pareto, segments, 657 anomaly days
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼
visualization (10 PNGs)     insights (written report)
        └──────────► dashboard.py (5 tabs, Plotly) ◄──┘
```

# Part 4 - Phase-wise implementation plan

### Phase 1 - Setup (Day 1)
- **Do / why / output:** folders, `requirements.txt`, `src/config.py` (paths, palette, budgets, merchants, noise rates), `src/utils.py` (logging, theme, money formatting), `.gitignore`, venv; config lives in one place and `python main.py --help` works from commit one.
- **Mistakes to avoid:**
  - **The ₹ crash.** Rupee amounts raised `UnicodeEncodeError` on a Windows cp1252 console. Fix: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` in `utils.py`.

### Phase 2 - Data creation (Day 2)
- **Do / why / output:** `data_generator.py` - archetypes, incomes, rent days, festival scaling, weekend probabilities, deliberate dirt; dirt makes cleaning meaningful, structure gives the analysis something to find, and you get 17,176 messy rows.
- **Mistakes to avoid:**
  - **Faking the signal.** The first dataset had no weekend behaviour (28.3% vs the 28.6% baseline) while a chart implied one. Fix: a per-category `WEEKEND_PROBABILITY` map makes the 32.9% share real. Never let a chart claim a signal the data does not support.

### Phase 3 - Cleaning (Day 3)
- **Do / why / output:** `data_cleaning.py` - the normalisation pipeline plus the data-quality report; every downstream number depends on it, and the report is your audit trail (16,179 clean rows, 94.20%).
- **Mistakes to avoid:**
  - **Silent date corruption.** `pd.to_datetime(format="mixed", dayfirst=True)` reads ISO `2025-10-01` as 10 January, corrupting every monthly chart. Fix: parse strict ISO `%Y-%m-%d %H:%M:%S` first, then mixed day-first for the rest. Guarded by `test_clean_dates_inside_window`.

### Phase 4 - EDA + analysis (Day 4)
- **Do / why / output:** `analysis.py` - budget variance, shares, Pareto, trends, segments, anomalies; headline numbers and every denominator mistake are born here, so hand-verify on two users (657 flagged user-days, 46 of 50 users).
- **Mistakes to avoid:**
  - **Aggregate vs per-user budgets.** Total spend against a per-user budget showed every category at roughly +5,000% over. Fix: normalise actuals per user. Guarded by `test_budget_is_compared_per_user_not_in_total`. Key lesson: numerator and denominator must describe the same population.
  - **Rent days flagged as fraud.** Rent & Utilities flagged every user on rent day - light spenders have a near-zero daily median, so rent looked like a 30× outlier. Fix: exclude recurring bills, baseline on active spending days, keep the ₹5,000 floor. Guarded by `test_recurring_bills_are_excluded_from_anomalies`.
  - **Missing MAD constant.** The threshold must be `median + 2.5 × 1.4826 × MAD`; 1.4826 converts MAD to a standard-deviation-equivalent. Omitting it made the threshold too tight.

### Phase 5 - Visualization (Day 5, part 1)
- **Do / why / output:** `visualization.py` - 10 charts, one palette, no chart-junk; charts are what a non-technical reader judges, and the 10 PNGs are listed in the Part 5 checklist.
- **Mistakes to avoid:**
  - **A chart contradicting its title.** The Pareto dual-axis chart plotted the cumulative line descending instead of cumulative-from-largest. Sort descending, draw cumulative from the largest, and check the end value matches the 77.3% claim.

### Phase 6 - Insights + dashboard (Day 5, part 2)
- **Do / why / output:** `insights.py` + `dashboard.py` - the report and the 5-tab app; the report turns numbers into decisions, the dashboard proves reuse (tabs: Overview, Categories, Trends, Patterns, Data).
- **Mistakes to avoid:**
  - **Burn-rate denominator.** The 30-day burn excluded recurring bills but divided by the full budget (82.8%); against the ₹35,500 variable budget it is ₹44,279 = 124.7% - the same population mismatch as the budget bug.
  - **A claim that outran its code.** The report said top merchants were "21.7% of variable spend" while the code divided by total spend (15.7%). Guarded by `test_merchant_share_claim_uses_the_right_denominator`.
  - **`StreamlitDuplicateElementId`** - every `st.plotly_chart` / `st.dataframe` needs a unique `key=`.
  - **`st.cache_data` must not read `st.session_state`** - pass uploaded bytes as an argument so the cache key is the file.
  - **KPI overflow on Total spend** - `money_compact` renders thousands short forms (`₹37,263.1 K`).

### Phase 7 - Tests + docs + push (Day 5, part 3)
- **Do / why / output:** `tests/` (27 pipeline + 2 headless AppTest + 1 browser entry point running 17 checks = 30 tests), README, docs, push; each worst bug is pinned by a named regression test, and the repo reproduces every number from seed 42 with `python main.py all`.
- **Mistakes to avoid:**
  - Dropping the guards: `test_clean_dates_inside_window`, `test_budget_is_compared_per_user_not_in_total`, `test_recurring_bills_are_excluded_from_anomalies`, `test_merchant_share_claim_uses_the_right_denominator`.
  - Trusting "it looked fine in the browser" over the headless AppTest and real-browser checks.

# Part 5 - Proof-building plan (5 days)

| Day | Goal / deliverable | Proof to capture |
| --- | --- | --- |
| **1** | Setup: structure, config, requirements, venv | Folder tree; `pip install` output |
| **2** | Dataset: generator + raw CSVs | Raw CSV: duplicates, blanks, mixed dates |
| **3** | Cleaning + analysis: cleaned CSV, quality report | 17,176 → 16,179 (94.20%); 657 anomalies |
| **4** | Charts: 10 PNGs | All 10 charts in `outputs/charts/` |
| **5** | Insights + dashboard + push: report, tests, repo | 5 tabs; test output; GitHub repo page |

### Commit per day

```bash
git commit -m "chore: scaffold, config budgets and requirements"
git commit -m "feat: synthetic expense generator with injected dirt"
git commit -m "feat: cleaning pipeline, ISO-first dates and data-quality report"
git commit -m "feat: budget, Pareto, segment and robust-z anomaly analysis"
git commit -m "feat: 10 charts, insights report, 5-tab dashboard and 30 tests"
```

Five commits = five days of visible, continuous work.

### Screenshot checklist

| # | What to capture |
| --- | --- |
| 1 | Console output of `python main.py all` with the headline numbers |
| 2 | Raw vs cleaned CSV preview (dirt visible, then gone); data-quality report |
| 3 | All 10 chart PNGs: category share, monthly trend, budget vs actual, donut, payment methods, weekday pattern, top merchants, savings trend, anomaly timeline, segment composition |
| 4 | Dashboard tabs: Overview, Categories, Trends, Patterns, Data |
| 5 | GitHub repo page (README rendered, images loading) |

# Part 6 - How to talk about it in one minute

> "I built an Expense Tracker App: a six-stage Python pipeline - generate, clean, analyze, visualize, insights, dashboard - turning a year of deliberately dirty data for 50 synthetic users into an analytics product. It cleans 17,176 raw rows to 16,179 validated transactions (94.20% retention), then computes per-user budget variance, category shares, a Pareto, segments, weekend patterns and robust-z anomaly detection that flags 657 unusual user-days. Headlines: ₹62,105 average monthly spend against a ₹53,500 budget, a +10.0% savings rate, five categories carrying 77.3% of spend, and 18% of users generating 37.5% of it.
>
> The part I'm proudest of is the statistics discipline: my first budget comparison said every category was 5,000% over, because I compared aggregate spend against a per-user budget - numerator and denominator described different populations. I fixed that, the same bug in the burn rate and the merchant-share claim, and pinned each fix with a regression test. The project carries 30 automated tests and reproduces every number from seed 42 with `python main.py all`."

**One-line version:** "An end-to-end expense analytics pipeline - dirty synthetic data in, cleaned per-user budget analysis, 10 charts and a Streamlit dashboard out, with 30 tests covering it."
