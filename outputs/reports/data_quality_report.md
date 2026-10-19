# Data Quality Report

**Project:** Expense Tracker App v1.0.0  
**Author:** Harsha K S

## Summary

| Metric | Value |
| --- | --- |
| rows_in | 17,176 |
| duplicates_removed | 183 |
| duplicates_after_normalisation | 36 |
| whitespace_fixed | 867 |
| category_casing_fixed | 590 |
| amount_strings_parsed | 238 |
| blank_amount_removed | 205 |
| blank_category_removed | 197 |
| unknown_category_removed | 172 |
| unparseable_dates | 0 |
| zero_or_negative_removed | 79 |
| impossible_outlier_removed | 49 |
| future_date_removed | 76 |
| rows_out | 16,179 |
| retention_pct | 94.20% |
| date_min | 2025-10-01 |
| date_max | 2026-09-30 |
| users | 50 |
| categories | 10 |
| total_spend | ₹37,263,111.51 |

## What was fixed

| Issue | Action taken |
| --- | --- |
| Exact duplicate exports | `drop_duplicates()` on the raw row |
| Duplicates hidden behind formatting | Second `drop_duplicates()` after dates were parsed and labels canonicalised |
| Amounts stored as display text | Stripped `Rs.` / commas / spaces, then coerced to float |
| Mixed date formats | Strict ISO parse first, then `format="mixed", dayfirst=True` for the rest |
| Category casing drift | Case-insensitive lookup against the canonical 10 categories |
| Unknown category tokens | Dropped as out-of-scope (`Others`, `N/A`, `misc`, `unknown`, `-`) |
| Zero / negative / 100k+ amounts | Dropped as impossible values |
| Future-dated rows | Dropped as outside the reporting window |

> Note: the date column is parsed in **two stages** - strict ISO first, then the
> mixed set. Parsing everything at once with `dayfirst=True` silently reads an ISO
> date like `2025-10-01` as 10 January, which quietly corrupts the monthly trend.
> `tests/test_pipeline.py::test_clean_dates_inside_window` guards against it.

## Ground truth (injected on purpose)

The generator dirties the ledger on purpose so cleaning can be measured
instead of guessed. **7,092 issues** were injected:

| Issue | Injected |
| --- | --- |
| Exact duplicates | 254 |
| Blank amounts | 205 |
| Blank categories | 199 |
| Amounts as display strings | 324 |
| Category casing drift | 882 |
| Whitespace on text columns | 4,335 |
| Unknown category tokens | 175 |
| Zero / negative amounts | 82 |
| Impossible outliers | 49 |
| Future-dated rows | 79 |
| Mixed date formats | 508 |
