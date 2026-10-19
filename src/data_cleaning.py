"""
Data cleaning pipeline for the raw expense export.

The raw file is deliberately messy. Cleaning is scored against the injected
ground truth and written up as a Markdown data-quality report, so a reviewer
can see exactly what was wrong and what was done about it.

Author: Harsha K S
"""

from __future__ import annotations

import re

import pandas as pd

from src import config
from src.utils import ensure_directories, relative, setup_logging

LOGGER = setup_logging()

CURRENCY_JUNK = re.compile(r"(?i)\s*(?:rs\.?|inr|₹|,)\s*")

CANONICAL_CATEGORIES = {c.lower(): c for c in config.CATEGORY_BUDGETS}
CANONICAL_PAYMENTS = {p.lower(): p for p in config.PAYMENT_METHODS}


def parse_amount(series: pd.Series) -> pd.Series:
    """Turn display strings like 'Rs. 1,200.50' into floats."""
    text = series.astype("string").fillna("")
    cleaned = text.map(lambda v: CURRENCY_JUNK.sub("", str(v)).strip())
    cleaned = cleaned.replace({"": None, "-": None, "nan": None, "None": None})
    return pd.to_numeric(cleaned, errors="coerce")


def canonicalise(series: pd.Series, lookup: dict[str, str], default: str | None = None) -> pd.Series:
    """Case-insensitive mapping onto the canonical label list."""
    text = series.astype("string").fillna("").str.strip().str.lower()
    mapped = text.map(lookup)
    return mapped if default is None else mapped.fillna(default)


def clean_expenses(
    raw: pd.DataFrame | None = None,
    injected_counts: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Run the full cleaning pipeline. Returns (clean frame, quality report)."""
    ensure_directories()
    if raw is None:
        raw = pd.read_csv(config.RAW_CSV_PATH, dtype="string")

    df = raw.copy()
    report: dict[str, int | str | float] = {"rows_in": int(len(df))}
    injected = injected_counts or {}

    # ---- 0. whitespace --------------------------------------------------- #
    text_cols = ["category", "merchant", "payment_method", "description", "user_segment"]
    had_ws = pd.Series(False, index=df.index)
    for col in text_cols:
        if col not in df.columns:
            continue
        before = df[col].astype("string").fillna("")
        stripped = before.str.strip()
        had_ws |= before != stripped
        df[col] = stripped
    report["whitespace_fixed"] = int(had_ws.sum())

    # ---- 1. exact duplicates, before any parsing ------------------------- #
    before = len(df)
    df = df.drop_duplicates()
    report["duplicates_removed"] = before - len(df)

    # ---- 2. parse the messy date column ---------------------------------- #
    # Two stages on purpose: strict ISO first, then the injected mixed formats.
    # Doing it the other way round lets dayfirst=True read "2025-10-01" as
    # 10 January 2025, which silently corrupts the whole timeline.
    iso = pd.to_datetime(df["date"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    needs_mixed = iso.isna()
    if needs_mixed.any():
        iso[needs_mixed] = pd.to_datetime(
            df.loc[needs_mixed, "date"], format="mixed", dayfirst=True, errors="coerce"
        )
    df["date"] = iso
    unparseable = df["date"].isna()
    report["unparseable_dates"] = int(unparseable.sum())
    df = df.loc[~unparseable].copy()

    # ---- 3. parse the messy amount column -------------------------------- #
    df["amount"] = parse_amount(df["amount"])
    was_string_amount = raw.loc[df.index, "amount"].astype("string").str.contains(
        r"(?i)rs\.?|inr|₹|,", regex=True, na=False
    )
    report["amount_strings_parsed"] = int(was_string_amount.sum())

    blank_amount = df["amount"].isna()
    report["blank_amount_removed"] = int(blank_amount.sum())
    df = df.loc[~blank_amount].copy()

    # ---- 4. canonicalise the categorical labels -------------------------- #
    raw_cat = df["category"].astype("string").fillna("")
    df["category"] = canonicalise(df["category"], CANONICAL_CATEGORIES)
    was_blank_before = raw_cat.str.strip() == ""
    report["category_casing_fixed"] = int(
        (
            df["category"].notna()
            & ~was_blank_before
            & (raw_cat != df["category"].astype("string").fillna(""))
        ).sum()
    )

    blank_cat = df["category"].isna()
    was_blank = raw_cat.str.strip() == ""
    report["blank_category_removed"] = int((blank_cat & was_blank).sum())
    report["unknown_category_removed"] = int(blank_cat.sum() - report["blank_category_removed"])
    df = df.loc[~blank_cat].copy()

    df["payment_method"] = canonicalise(df["payment_method"], CANONICAL_PAYMENTS, default="Unknown")

    # ---- 5. impossible values -------------------------------------------- #
    zero_or_negative = df["amount"] <= 0
    report["zero_or_negative_removed"] = int(zero_or_negative.sum())
    df = df.loc[~zero_or_negative].copy()

    outlier = df["amount"] > 100_000
    report["impossible_outlier_removed"] = int(outlier.sum())
    df = df.loc[~outlier].copy()

    window_end = pd.Timestamp(config.WINDOW_END) + pd.Timedelta(days=1)
    future = df["date"] > window_end
    report["future_date_removed"] = int(future.sum())
    df = df.loc[~future].copy()

    # ---- 6. duplicates that only became visible after normalisation ------ #
    before = len(df)
    df = df.drop_duplicates(
        subset=["user_id", "date", "category", "amount", "payment_method"]
    )
    report["duplicates_after_normalisation"] = before - len(df)

    # ---- 7. derived columns the analysis needs --------------------------- #
    df = df.reset_index(drop=True)
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    df["month_name"] = df["date"].dt.strftime("%b %Y")
    df["weekday"] = df["date"].dt.day_name()
    df["hour"] = df["date"].dt.hour.astype(int)
    df["is_weekend"] = df["date"].dt.dayofweek >= 5
    df["amount"] = df["amount"].astype(float)

    report["rows_out"] = int(len(df))
    report["retention_pct"] = round(100 * len(df) / max(1, int(report["rows_in"])), 2)
    report["date_min"] = str(df["date"].min().date())
    report["date_max"] = str(df["date"].max().date())
    report["users"] = int(df["user_id"].nunique())
    report["categories"] = int(df["category"].nunique())
    report["total_spend"] = round(float(df["amount"].sum()), 2)
    report["injected_ground_truth"] = injected

    return df[["transaction_id", "user_id", "date", "year_month", "month_name",
               "category", "merchant", "amount", "payment_method", "description",
               "user_segment", "weekday", "hour", "is_weekend"]], report


def write_quality_report(report: dict, path=config.QUALITY_MD_PATH) -> str:
    """Render the data-quality report as Markdown."""
    injected = report.get("injected_ground_truth", {}) or {}
    truth_total = sum(injected.values()) if injected else 0

    lines = [
        "# Data Quality Report",
        "",
        f"**Project:** {config.PROJECT_NAME} v{config.PROJECT_VERSION}  ",
        f"**Author:** {config.PROJECT_AUTHOR}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| rows_in | {report['rows_in']:,} |",
        f"| duplicates_removed | {report['duplicates_removed']:,} |",
        f"| duplicates_after_normalisation | {report['duplicates_after_normalisation']:,} |",
        f"| whitespace_fixed | {report['whitespace_fixed']:,} |",
        f"| category_casing_fixed | {report['category_casing_fixed']:,} |",
        f"| amount_strings_parsed | {report['amount_strings_parsed']:,} |",
        f"| blank_amount_removed | {report['blank_amount_removed']:,} |",
        f"| blank_category_removed | {report.get('blank_category_removed', 0):,} |",
        f"| unknown_category_removed | {report['unknown_category_removed']:,} |",
        f"| unparseable_dates | {report['unparseable_dates']:,} |",
        f"| zero_or_negative_removed | {report['zero_or_negative_removed']:,} |",
        f"| impossible_outlier_removed | {report['impossible_outlier_removed']:,} |",
        f"| future_date_removed | {report['future_date_removed']:,} |",
        f"| rows_out | {report['rows_out']:,} |",
        f"| retention_pct | {report['retention_pct']:.2f}% |",
        f"| date_min | {report['date_min']} |",
        f"| date_max | {report['date_max']} |",
        f"| users | {report['users']:,} |",
        f"| categories | {report['categories']:,} |",
        f"| total_spend | {config.CURRENCY_SYMBOL}{report['total_spend']:,.2f} |",
        "",
        "## What was fixed",
        "",
        "| Issue | Action taken |",
        "| --- | --- |",
        "| Exact duplicate exports | `drop_duplicates()` on the raw row |",
        "| Duplicates hidden behind formatting | Second `drop_duplicates()` after dates were parsed and labels canonicalised |",
        "| Amounts stored as display text | Stripped `Rs.` / commas / spaces, then coerced to float |",
        "| Mixed date formats | Strict ISO parse first, then `format=\"mixed\", dayfirst=True` for the rest |",
        "| Category casing drift | Case-insensitive lookup against the canonical 10 categories |",
        "| Unknown category tokens | Dropped as out-of-scope (`Others`, `N/A`, `misc`, `unknown`, `-`) |",
        "| Zero / negative / 100k+ amounts | Dropped as impossible values |",
        "| Future-dated rows | Dropped as outside the reporting window |",
        "",
        "> Note: the date column is parsed in **two stages** - strict ISO first, then the",
        "> mixed set. Parsing everything at once with `dayfirst=True` silently reads an ISO",
        "> date like `2025-10-01` as 10 January, which quietly corrupts the monthly trend.",
        "> `tests/test_pipeline.py::test_clean_dates_inside_window` guards against it.",
        "",
    ]

    if injected:
        lines += [
            "## Ground truth (injected on purpose)",
            "",
            "The generator dirties the ledger on purpose so cleaning can be measured",
            "instead of guessed. **{:,} issues** were injected:".format(truth_total),
            "",
            "| Issue | Injected |",
            "| --- | --- |",
        ]
        labels = {
            "duplicates": "Exact duplicates",
            "blank_amount": "Blank amounts",
            "blank_category": "Blank categories",
            "amount_as_string": "Amounts as display strings",
            "category_casing": "Category casing drift",
            "whitespace": "Whitespace on text columns",
            "unknown_category": "Unknown category tokens",
            "zero_or_negative": "Zero / negative amounts",
            "impossible_outlier": "Impossible outliers",
            "future_date": "Future-dated rows",
            "mixed_date_format": "Mixed date formats",
        }
        for key, label in labels.items():
            if key in injected:
                lines.append(f"| {label} | {injected[key]:,} |")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    LOGGER.info("Data-quality report saved -> %s", relative(path))
    return "\n".join(lines)


def load_clean_data(path=config.CLEAN_CSV_PATH) -> pd.DataFrame:
    """Load the cleaned ledger with the right dtypes."""
    df = pd.read_csv(path, parse_dates=["date"])
    # CSV round-trip turns booleans into text - make them real booleans again.
    if df["is_weekend"].dtype != bool:
        df["is_weekend"] = df["is_weekend"].astype(str).str.lower().map({"true": True, "false": False})
    df["is_weekend"] = df["is_weekend"].fillna(False).astype(bool)
    df["hour"] = df["hour"].astype(int)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    df["month_name"] = df["date"].dt.strftime("%b %Y")
    return df


def load_income(path=config.CLEAN_INCOME_CSV_PATH) -> pd.DataFrame:
    """Load the monthly income ledger."""
    return pd.read_csv(path)
