# Interview Preparation

**Author:** [Harsha K S](https://github.com/harshaks17-ai)

**Project:** Expense Tracker App v1.0.0 — [repository](https://github.com/harshaks17-ai/Expense-Tracker-App). Stack: Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Streamlit, Pytest. Synthetic ledger: seed 42, 50 users, 10 categories, window 2025-10-01 to 2026-09-30, currency INR.

## Part A - HR / behavioural

### Q1. "Tell me about this project."

This is Expense Tracker App v1.0.0: a CLI pipeline plus a Streamlit dashboard that turns twelve months of raw expense records into budget analysis, savings analysis, per-user anomaly alerts and a written insight report. The data is synthetic — seed 42, 50 users, 10 categories, October 2025 to September 2026, in rupees. The pipeline is generate, clean, analyze, visualize, insights, dashboard, invoked as seven CLI subcommands through `python main.py`.

It takes 17,176 raw rows to 16,179 cleaned transactions, a 94.20% retention rate, and the headline output is ₹37,263,112 of total spend analysed against budgets of ₹53,500 per user per month, with a +10.0% overall savings rate. A weaker candidate would list tools and stop; I would rather say what the tool answers and how I know the numbers are right.

### Q2. "Why did you choose this project?"

I wanted one project where every stage of the workflow was visible and testable — generation, cleaning, analysis, visualisation, reporting, testing — instead of a notebook that loads an already-clean CSV. Expenses give the project a natural ground truth: budgets, so "over budget" can be defined precisely rather than rhetorically.

The real draw was anomaly detection: finding unusual spending days per user is a hard, contested problem because one large purchase can redefine "normal", which forced me to use robust statistics. I also chose INR and a festival-heavy calendar deliberately — the seasonality makes budget analysis realistic, and it later exposed a genuine weakness in flat monthly budgets.

### Q3. "What would you do differently if you started again?"

Four things I would do differently:

- Decide the anomaly-detection definition before writing a single chart, because that definition ended up changing charts downstream.
- Write the test for a metric at the same moment as the metric; four of the bugs in Q10 were denominator or definition mistakes, not coding errors.
- Make budgets seasonal instead of one flat ₹53,500 monthly figure, since that is precisely why the two festival months blow past them.
- Separate fixed commitments from discretionary spend at the data-model level, rather than filtering recurring bills at analysis time, where an exclusion can leak into the wrong metric.

None of these is a rewrite; each is an earlier decision, not more code.

### Q4. "How did you make sure your code is correct?"

30 automated tests, all run by one command: `python -m pytest tests/ -q`. Twenty-seven pipeline tests cover generator determinism under seed 42, proof that the injected dirt really exists, the cleaning contract, arithmetic identities such as category shares summing to 100 and savings equalling income minus spend, budget-variance maths, the Pareto bound, anomaly thresholds, chart and report completeness, plus regression guards for specific past bugs.

Two headless Streamlit AppTest tests cover the dashboard components, and one pytest entry point starts its own server and runs 17 checks in a real Chromium browser: every tab renders, filters apply and clear, CSV upload works, no console errors. A weaker candidate says "I ran it manually"; here a change either passes the suite or fails it.

## Part B - Technical

### Q5. "Walk me through your data pipeline."

Six stages, seven CLI subcommands under `python main.py`. `generate` builds the seed-42 ledger. `clean` takes 17,176 raw rows down to 16,179 transactions. `analyze` computes budgets, savings, segments and anomalies. `visualize` renders charts, `insights` writes the report, `dashboard` serves the app. Every number in the report and on the dashboard traces back to `data/processed/expenses_clean.csv` and routines in `src/analysis.py`.

The analysis stage is where the questions get answered: total spend ₹37,263,112, average transaction ₹2,303, heavy spenders 9 of 50 users but 37.5% of all spend, at ₹1,550,728 a year versus ₹345,327 for light spenders — a 4.5× gap. UPI carries 41.9% of value and the busiest bucket is Midday, 10 to 14. Cleaning and analysis stay separate artefacts so the two can never hide behind each other.

### Q6. "How do you decide which category is over budget, and what is the denominator?"

The denominator is a per-user monthly budget, normalised across users — not a total. My first version compared aggregate spend to the per-user figure and reported every category about +5,000% over; the fix normalises per user, and `test_budget_is_compared_per_user_not_in_total` holds it there. The lesson I keep: always verify the numerator and denominator describe the same population.

Budgets total ₹53,500 per user per month across 10 categories; Rent & Utilities is the largest at ₹18,000 and the only recurring category. Actual average monthly spend is ₹62,105. Worst overruns: Education +94.6%, Travel +84.6%. Best controlled: Rent & Utilities, −4.4%. Five of ten categories carry 77.3% of all spend, and the peak month 2026-03 held ₹3,996,844 of spend and a −15.9% savings rate, so no over-budget number is read without seasonal context.

### Q7. "How does your anomaly detection work, and why not just use z-scores with the mean?"

The default answer is mean and standard deviation, but that lets one large booking define "normal", which is exactly the failure this project exists to avoid. I use a per-user robust z-score: z = (day spend − user median) / (1.4826 × MAD); the 1.4826 is the normal-consistency constant, which I originally omitted, making alerts far too tight. A day is flagged only when z > 2.5, spend is at least ₹5,000, and there are at least 2 transactions.

Recurring bills are excluded and each user's baseline uses active spending days only — including rent flagged every light spender on rent day. Result: 657 flagged user-days across 46 of 50 users, about 1.1 alerts per user per month. Most extreme: U050 on 2026-07-05 spent ₹54,773 against a ₹3,507 median, z = 18.6; U044 reached z = 20.7.

### Q8. "How did you clean the data? What was actually in there?"

The raw file had exact duplicate exports; amounts stored as text such as `Rs. 1,299` and comma-formatted numbers; three date formats; category casing drift like `food & dining` and `FOOD & DINING`; padding whitespace; blank amounts and blank categories; unknown category tokens; zero and negative amounts; impossible outliers above ₹100,000; and future-dated rows outside the window.

I injected 7,092 defects on purpose, so cleaning could be measured rather than guessed. Seed-42 counters: 183 exact duplicates plus 36 more after normalisation, 867 whitespace fixes, 590 casing fixes, 238 text amounts parsed, 205 blank amounts, 197 blank categories, 172 unknown categories, 79 zero or negative, 49 outliers, 76 future-dated rows, 0 unparseable dates. Retention: 94.20%. A weaker candidate just drops bad rows; I account for every category of dirt, which is what makes the numbers auditable.

### Q9. "You said your data is synthetic. Doesn't that make the project fake?"

Fair question. The honest answer is that the generator is not random noise: it encodes incomes, per-category budgets, user archetypes, festival-month multipliers, per-category weekend probabilities and merchant distributions, then injects a known set of defects so cleaning can be measured as a percentage. What it demonstrates is method and engineering, not real consumer behaviour, and I state that limitation plainly rather than hiding it.

The compensating advantage is ground truth. I know exactly how many defects were injected, I know which days are anomalous by construction, and I can verify recovery precisely — the 94.20% retention rate and the 657 anomaly flags are provable facts here, which is impossible with real data. A weaker candidate gets defensive; the right answer is to bound the claim instead of overselling it.

### Q10. "What bugs did you find, and how?"

Ten in total; most came from refusing to accept a number that looked wrong:

- Budget variance showed every category +5,000% over: aggregate spend against a per-user budget; fixed by normalising per user.
- `pd.to_datetime(format="mixed", dayfirst=True)` read the ISO date 2025-10-01 as 10 January, corrupting the monthly trend.
- Rent in anomaly detection flagged everyone on rent day; fixed by excluding bills and using active days only.
- The burn rate divided ₹44,279 by the full budget (82.8%) instead of the variable budget (124.7%).
- A report claim "of variable spend" divided by total spend: 15.7% instead of 21.7%.
- The Pareto line contradicted its own chart title; printing ₹ crashed on cp1252; duplicate Streamlit IDs needed unique `key=` args.
- The MAD threshold omitted the 1.4826 constant.
- A chart implied a weekend effect the data lacked: 28.3% share against a 28.6% baseline.

Each is now a named regression test, so none of them can return quietly.

### Q11. "How would you scale this / handle a much bigger dataset?"

The code is vectorised pandas with no Python-level row loops in the hot paths, so scale is mostly an I/O and memory question. Next steps, in order: Parquet instead of CSV; chunked processing or DuckDB/Polars; partitioning by month; incremental runs that clean only new files; and folding the per-user robust statistics into a single groupby aggregation instead of repeated passes.

The Streamlit layer would move to a cached pre-aggregated layer instead of recomputing from raw on every interaction. At 16,179 rows none of this hurts yet — which is exactly why the decisions belong in the design now, not after the data grows. A weaker candidate says "buy a bigger machine"; the honest answer is that the bottlenecks are format, partitioning and recomputation.

### Q12. "How do you know your charts are honest?"

Three concrete safeguards. Every chart number traces back to `data/processed/expenses_clean.csv` and the routines in `src/analysis.py`, so any figure can be reproduced. Tests assert arithmetic identities rather than eyeballed values — category shares sum to 100, savings equals income minus spend — so a chart cannot silently disagree with the source. And where a metric excludes recurring bills, the report prints the exclusion; a claim "of variable spend" that divided by total spend (15.7% instead of 21.7%) is guarded by `test_merchant_share_claim_uses_the_right_denominator`.

One more, because honesty cuts both ways: a chart implied a weekend effect, but the data had a 28.3% weekend share against a 28.6% baseline. Instead of softening the caption I fixed the generator with per-category weekend probabilities; the weekend share is now 32.9%. If the data cannot support a claim, you change the data or drop the claim — never the label on the chart.

## One-line HR explanation (memorise this)

I built a tool that takes a year of messy expense records and turns them into clear, checked answers: where the money goes, how much is actually overspent, and which users need a warning.

## One-line technical explanation

The pipeline runs generate, clean, analyze, visualize, insights and dashboard as seven CLI subcommands, and the two hardest parts are data cleaning with measured defect recovery (7,092 injected defects, 94.20% retention) and per-user robust anomaly detection with correctly-scoped denominators.
