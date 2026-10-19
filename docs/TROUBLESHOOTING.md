# Troubleshooting

**Author:** [Harsha K S](https://github.com/harshaks17-ai)

Every entry below is a real problem hit while building this project - the symptom as it appeared, the cause, the fix, and where the fix is guarded.

## 1. Environment & setup

### ModuleNotFoundError: No module named 'pandas'
**Symptom** - `ModuleNotFoundError: No module named 'pandas'` on the first `python main.py` or `pytest` run.
**Cause** - the dependencies were never installed for the interpreter actually running the commands, which is often a different environment from the one you installed into.
**Fix** - activate the project virtualenv and run `pip install -r requirements.txt` with that same interpreter.
**Guarded by** - covered in the README Limitations section.

### ModuleNotFoundError: No module named 'src'
**Symptom** - `ModuleNotFoundError: No module named 'src'` as soon as a module under `src/` imports another project module.
**Cause** - the command was run from inside a subfolder, so the project root never made it onto `sys.path`.
**Fix** - run everything from the repo root (`python main.py all`, `python -m pytest tests/ -q`); `python -m pytest` puts the current directory on the path.
**Guarded by** - covered in the README Limitations section.

### A dependency has no wheel for your Python version
**Symptom** - pip falls back to a source build and ends with `error: Microsoft Visual C++ 14.0 or greater is required` or `ERROR: No matching distribution found for pandas==3.0.2`.
**Cause** - the project pins pandas 3.0.2 and numpy 2.4.4 on Python 3.14; an unpinned or mismatched interpreter has no prebuilt wheel for those versions.
**Fix** - use the pinned versions from `requirements.txt` on a matching Python 3.14 interpreter, or install a compiler toolchain and let pip build from source.
**Guarded by** - covered in the README Limitations section.

### Charts render blank with UserWarning: Matplotlib is currently using agg
**Symptom** - `UserWarning: Matplotlib is currently using agg, which is a non-GUI backend, so cannot show the figure.` followed by a blank chart window.
**Cause** - the terminal session is headless, so there is no GUI backend and nothing can be shown interactively.
**Fix** - select the backend deliberately with `matplotlib.use("Agg")` and always `fig.savefig(...)` into `outputs/` instead of calling `plt.show()`.
**Guarded by** - covered in the README Limitations section.

### OSError: [Errno 22] Invalid argument when saving a chart
**Symptom** - `OSError: [Errno 22] Invalid argument` raised at the `fig.savefig(...)` call.
**Cause** - the output path contained characters illegal in Windows filenames; a colon borrowed from a chart title is the usual culprit.
**Fix** - build paths with `Path("outputs") / name`, sanitise generated filenames before writing, and create parents with `mkdir(parents=True, exist_ok=True)`.
**Guarded by** - covered in the README Limitations section.

### Playwright Chromium is not installed
**Symptom** - `StaleElementReferenceException` and the backup-dictionary error in the scraping step, even though `import playwright` succeeds.
**Cause** - the Playwright package was installed but its Chromium binary was never downloaded, so every element handle goes stale the moment it is used.
**Fix** - reinstall the package and fetch the browser: `pip install playwright` then `python -m playwright install chromium`.
**Guarded by** - covered in the README Limitations section.

### H. UnicodeEncodeError when printing the rupee symbol
**Symptom** - `UnicodeEncodeError: 'charmap' codec can't encode character '\u20b9' in position 17: character maps to <undefined>` as soon as a rupee figure reaches the console.
**Cause** - the Windows console defaults to cp1252, which cannot encode the rupee sign.
**Fix** - `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at the start of the CLI entry point. Generated markdown files already render the rupee sign correctly because they are written as UTF-8; only the console stream needed fixing. ConEmu and older terminals may still show mojibake, and a replacement glyph in a PowerShell `Get-Content` dump is a display artefact, not a file problem.
**Guarded by** - covered in the README Limitations section.

## 2. Data bugs (the interesting ones)

### A. ISO dates silently corrupted by the day-first fallback
**Symptom** - the monthly trend chart shows bars in the wrong months; `2025-10-01` reads back as `2025-01-10`; a 12-month window reports 13 or 11 year-months.
**Cause** - `pd.to_datetime(series, format="mixed", dayfirst=True)` applies day-first interpretation to strings that are already unambiguous ISO, so `2025-10-01` becomes 10 January.
**Fix** - parse in two stages: strict ISO first with `format="%Y-%m-%d %H:%M:%S"`, then `format="mixed", dayfirst=True` on only the rows that failed.
```python
iso = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce")
failed = iso.isna()
iso.loc[failed] = pd.to_datetime(s.loc[failed], format="mixed", dayfirst=True)
```
**Guarded by** - `test_clean_dates_inside_window`.

### G. The Pareto dual-axis line contradicted its own title
**Symptom** - the cumulative share line started at 100% and ended at 28%, while the title claimed the chart showed which categories reach 80% of spend.
**Cause** - the cumulative sum was plotted before sorting descending, so it accumulated from the smallest category.
**Fix** - sort descending by total spend first, then take the cumulative sum and plot it on the secondary axis.
**Guarded by** - `test_pareto_never_exceeds_the_threshold`.

### K. The weekend effect did not exist in the data
**Symptom** - the weekday chart was titled around weekend behaviour, but the weekend share of spend was 28.3% against a 28.6% baseline - no effect at all.
**Cause** - day-of-week assignment was uniform, so the chart's implied claim was unsupported.
**Fix** - added a `WEEKEND_PROBABILITY` map so each category carries its own weekend weight; the weekend share is now 32.9% against 28.6%, a +15.2% lift.
**Guarded by** - `test_weekend_effect_is_measurable`.

### P. Hour buckets had unequal widths
**Symptom** - the time-of-day chart looked like it had a spike that turned out to be an artefact of overlapping or uneven bins.
**Cause** - the bucket edges were unevenly spaced while the chart implied equal-length periods.
**Fix** - define equal-width buckets and label each with its true range.
**Guarded by** - covered in the README Limitations section.

## 3. Money, budgets and denominators

### B. Every category reported as roughly +5,000% over budget
**Symptom** - the budget table shows variance of +5000% for all ten categories, and the "worst overrun" is whichever category happens to be largest.
**Cause** - aggregate spend across 50 users was compared against a budget defined for a single user.
**Fix** - divide actuals by the user count so both sides describe one user-month; the fix reduced the largest variance to a believable +94.6%. This is the project's central lesson: verify the numerator and the denominator describe the same population.
**Guarded by** - `test_budget_is_compared_per_user_not_in_total`.

### C. Rent day flagged as an anomaly for every user
**Symptom** - the anomaly table was entirely rent payments; 927 user-days flagged across all 50 users; every user's most extreme day was their rent day.
**Cause** - the baseline was a user's median daily spend including zero-spend days, so a light spender's median was around ₹600 while rent is around ₹18,000; rent is also scheduled, so it is not anomalous behaviour at all.
**Fix** - exclude recurring bills (`FIXED_MONTHLY_CATEGORIES`), compute each user's median and MAD over their active days only, and require spend of at least ₹5,000; the result fell to 657 genuine flagged user-days across 46 users, about 1.1 per user per month.
**Guarded by** - `test_recurring_bills_are_excluded_from_anomalies`.

### D. Burn rate divided by the wrong budget
**Symptom** - the report said the 30-day burn rate was 82.8% of budget, which contradicted the surrounding narrative of overspending.
**Cause** - the burn rate excludes recurring bills from the numerator but was divided by the full ₹53,500 budget; the correct denominator is the ₹35,500 variable budget, which makes the figure 124.7%.
**Fix** - added a `variable_budget_per_user` figure and a `burn_vs_variable_budget_pct` metric; the full-budget comparison is retained only for reference.
**Guarded by** - `test_burn_rate_is_compared_to_the_variable_budget`.

### E. A report sentence labelled a share "of variable spend" but divided by total spend
**Symptom** - the report claimed the top 5 merchants were 15.7% of variable spend; recomputing by hand gave 21.7%.
**Cause** - the denominator used total spend including rent, which is never paid to those merchants.
**Fix** - divide by the sum of non-fixed categories; the report now reads 21.7%.
**Guarded by** - `test_merchant_share_claim_uses_the_right_denominator`.

### F. The robust threshold forgot the 1.4826 constant
**Symptom** - the alert threshold was far too tight and the flagged-day count was dominated by ordinary days.
**Cause** - for a normal distribution the median absolute deviation must be multiplied by 1.4826 to be comparable to a standard deviation; computing `median + 2.5 × MAD` understates the threshold substantially.
**Fix** - `threshold = median + z × 1.4826 × MAD`, with an explicit fallback to the standard deviation when MAD is zero.
**Guarded by** - `test_anomalies_are_per_user_and_above_threshold`.

## 4. Pandas 3.x / NumPy 2.x specifics

### I. KeyError: 'date' after a groupby with reset_index
**Symptom** - `KeyError: 'date'` when the anomaly table was built, even though the analysis clearly produced a date column.
**Cause** - after `groupby(...).agg(...).reset_index()` the grouping key can be named differently depending on pandas version and whether the group key was a Series.
**Fix** - rename explicitly and defensively after the reset, and reference the column through a single variable rather than by string literal in several places.
**Guarded by** - `test_anomalies_are_per_user_and_above_threshold`.

### J. The walrus operator inside an f-string is a syntax error
**Symptom** - `SyntaxError` on a line that looks like a tidy f-string.
**Cause** - an assignment expression `(x := ...)` was written inside an f-string expression, which is invalid.
**Fix** - hoist the assignment onto its own line before the f-string.
**Guarded by** - covered in the README Limitations section.

### Q. The top-level anomalies table kept only the top rows but the code referenced the full frame
**Symptom** - `KeyError` on a column that existed in one code path but not another.
**Cause** - the returned summary exposed a truncated head while downstream code expected the full frame.
**Fix** - return both a full flagged frame and a documented head, and have every consumer reference only the documented keys.
**Guarded by** - the pipeline tests that run against the saved report files.

## 5. Streamlit

### L. StreamlitDuplicateElementId
**Symptom** - `StreamlitDuplicateElementId: multiple plotly_chart elements with the same auto-generated ID`.
**Cause** - Streamlit derives widget IDs from element parameters, so two charts of the same type on one page collide.
**Fix** - pass a unique `key=` to every `st.plotly_chart` and `st.dataframe` call.
**Guarded by** - covered in the README Limitations section.

### M. st.cache_data reading session state
**Symptom** - uploaded files were ignored, or Streamlit raised an unhashable/`CachedStFunctionWarning` style error.
**Cause** - the cached function read `st.session_state`; a cached function must be pure with respect to its arguments, and session state is not part of the cache key.
**Fix** - pass the uploaded bytes into the cached function as a parameter so the cache key is the file content itself. Related: `use_container_width` is deprecated on newer Streamlit, so a small `stretch_kwargs()` helper returns `width="stretch"` on newer versions and `use_container_width=True` on older ones.
**Guarded by** - covered in the README Limitations section.

### N. KPI card text overflow
**Symptom** - the first KPI tile showed a wrapped, truncated number; a full figure such as ₹3,72,63,111.51 is too wide for a sixth-width column.
**Cause** - the tile printed the full formatted amount instead of a compact form.
**Fix** - a `money_compact` helper renders a thousands short form (`₹37,263.1 K`) for KPI tiles while tables keep exact amounts. Every money axis in the app and in the saved charts uses the same thousands scale, so no figure is quoted in a different unit from the one beside it.
**Guarded by** - covered in the README Limitations section.

### O. Legend collisions on the pie and merchant charts
**Symptom** - pie-chart labels overlapped into an unreadable pile; merchant names ran off the axes.
**Cause** - labels were placed inside a 10-slice pie with Indian category names of varying length.
**Fix** - move the legend outside the axes, use `labeldistance`, and switch the merchant chart to a horizontal bar chart so names read left to right.
**Guarded by** - covered in the README Limitations section.

### U. The dashboard starts but shows no charts, only grey boxes
**Symptom** - the Streamlit dashboard loads, but every chart area is a grey placeholder box.
**Cause** - the dashboard was opened before `main.py` produced the cleaned data, or `data/processed/expenses_clean.csv` is missing.
**Fix** - run `python main.py all` first, or upload a CSV through the sidebar, which runs the same cleaning pipeline in memory.
**Guarded by** - covered in the README Limitations section.

## 6. Tests & regenerated artefacts

### R. Tests pass but the charts in outputs/ are from a different run
**Symptom** - tests are green, but the saved PNGs and reports disagree with the console numbers.
**Cause** - `python main.py analyze` was run without re-running `visualize`/`insights`, so the artefacts came from different executions.
**Fix** - always finish with `python main.py all`, then `python -m pytest tests/ -q`; the chart test asserts there are exactly 10 non-empty PNGs and the report test asserts every section exists, which catches a partial run.
**Guarded by** - the chart-count and report-section pipeline tests.

### S. python tests/test_pipeline.py fails with the dataset missing
**Symptom** - `AssertionError: run 'python main.py all' first`.
**Cause** - the committed `data/` folder is present but `data/processed/` was cleaned by a fresh clone, or the raw file was never generated.
**Fix** - run `python main.py all` once; the test suite intentionally asserts on the saved artefacts so it validates what was actually shipped, not a re-computation in memory.
**Guarded by** - the test suite's own assertion message.

## 7. If the numbers look wrong on a fresh clone

### T. The seed changed and the README numbers no longer match
**Symptom** - a fresh clone reproduces different totals from the ones in the README.
**Cause** - `config.RANDOM_SEED` was changed, or the environment's pandas/numpy version produces a different random draw.
**Fix** - keep the seed at 42 and re-run `python main.py all` before comparing; the README numbers were produced with Python 3.14, pandas 3.0.2 and numpy 2.4.4, and the headline figures are the ones the shipped artefacts were generated with.
**Guarded by** - `test_generator_is_deterministic`, which asserts the same seed gives a byte-identical ledger.

### Sanity check on a fresh clone
Run `python main.py all` and confirm the console prints `Raw rows 17,176`, `Valid transactions 16,179 (94.20% retained)` and `Overspend alerts 657 user-days (46 users)`. Then run `python -m pytest tests/ -q` and expect `28 passed`. If any of those figures differ, re-run the pipeline before trusting any number.
