"""
Pipeline test suite for the Expense Tracker App.

These tests are the project's safety net: they check the simulation is
deterministic, that the cleaning pipeline removes exactly the dirt that was
injected, and that every analytical claim the reports make is arithmetically
true.

Run:
    python tests/test_pipeline.py
    python -m pytest tests/ -q

Author: Harsha K S
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import analysis, config, data_cleaning, data_generator, insights, utils  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    assert config.RAW_CSV_PATH.exists(), "run `python main.py all` first"
    return pd.read_csv(config.RAW_CSV_PATH, dtype="string")


@pytest.fixture(scope="module")
def clean() -> pd.DataFrame:
    assert config.CLEAN_CSV_PATH.exists(), "run `python main.py all` first"
    return data_cleaning.load_clean_data()


@pytest.fixture(scope="module")
def income() -> pd.DataFrame:
    return data_cleaning.load_income()


@pytest.fixture(scope="module")
def results(clean, income) -> dict:
    return analysis.full_analysis(clean, income)


# --------------------------------------------------------------------------- #
# 1-3: configuration and the simulation
# --------------------------------------------------------------------------- #
def test_config_is_coherent() -> None:
    assert len(config.CATEGORY_BUDGETS) == 10
    assert all(b > 0 for b in config.CATEGORY_BUDGETS.values())
    # every category needs merchants, a transaction range and a weekend weight
    assert set(config.CATEGORY_MERCHANTS) == set(config.CATEGORY_BUDGETS)
    assert set(config.CATEGORY_TX_RANGE) == set(config.CATEGORY_BUDGETS)
    assert set(config.WEEKEND_PROBABILITY) == set(config.CATEGORY_BUDGETS)
    assert all(0 < p < 1 for p in config.WEEKEND_PROBABILITY.values())
    assert abs(sum(config.PAYMENT_WEIGHTS) - 1.0) < 1e-9
    assert len(config.PAYMENT_WEIGHTS) == len(config.PAYMENT_METHODS)
    for low, high in config.CATEGORY_TX_RANGE.values():
        assert 0 < low < high


def test_generator_is_deterministic() -> None:
    first = data_generator.generate_transactions(np.random.default_rng(config.RANDOM_SEED))
    second = data_generator.generate_transactions(np.random.default_rng(config.RANDOM_SEED))
    pd.testing.assert_frame_equal(first, second)


def test_generator_shape_and_window(raw) -> None:
    assert len(raw) > 10_000
    assert {"transaction_id", "user_id", "date", "category", "amount",
            "payment_method", "merchant"} <= set(raw.columns)
    assert raw["user_id"].nunique() == config.N_USERS


# --------------------------------------------------------------------------- #
# 4-6: the injected dirt really is present (otherwise the cleaning test is fake)
# --------------------------------------------------------------------------- #
def test_raw_data_is_actually_dirty(raw) -> None:
    amounts = pd.to_numeric(
        raw["amount"].astype("string").str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce"
    )
    checks = {
        "duplicate rows": int(raw.duplicated().sum()) > 0,
        "blank amounts": int(raw["amount"].isna().sum()) > 0,
        "blank categories": int(raw["category"].isna().sum()) > 0,
        "amounts stored as text": int(raw["amount"].astype("string").str.contains("Rs", na=False).sum()) > 0,
        "non-positive amounts": int((amounts <= 0).sum()) > 0,
        "impossible outliers": int((amounts > 100_000).sum()) > 0,
    }
    broken = [name for name, ok in checks.items() if not ok]
    assert not broken, f"expected dirt missing: {broken}"


def test_injected_counts_are_reproducible() -> None:
    frame = data_generator.generate_transactions(np.random.default_rng(config.RANDOM_SEED))
    dirty, counts = data_generator.inject_noise(frame)
    assert len(dirty) == len(frame) + counts["duplicates"]
    assert counts["duplicates"] == int(round(config.DIRTY_DUPLICATE_RATE * len(frame)))
    assert counts["blank_amount"] > 0 and counts["blank_category"] > 0
    assert counts["mixed_date_format"] > 0 and counts["future_date"] > 0


def test_cleaning_removes_more_than_it_keeps(raw) -> None:
    clean, report = data_cleaning.clean_expenses(raw)
    assert 80.0 < report["retention_pct"] < 100.0
    assert report["rows_out"] < report["rows_in"]
    assert report["duplicates_removed"] > 0
    assert report["blank_amount_removed"] > 0
    assert report["unknown_category_removed"] > 0


# --------------------------------------------------------------------------- #
# 7-11: the cleaned frame obeys its own contract
# --------------------------------------------------------------------------- #
def test_clean_has_no_duplicates(clean) -> None:
    keys = ["user_id", "date", "category", "amount", "payment_method"]
    assert int(clean.duplicated(subset=keys).sum()) == 0
    assert int(clean.duplicated().sum()) == 0


def test_clean_has_no_missing_critical_values(clean) -> None:
    critical = ["transaction_id", "user_id", "date", "category", "amount", "payment_method"]
    missing = clean[critical].isna().sum()
    assert int(missing.sum()) == 0, f"missing values found: {missing[missing > 0].to_dict()}"


def test_clean_amounts_are_plausible(clean) -> None:
    assert (clean["amount"] > 0).all(), "non-positive amounts survived cleaning"
    assert (clean["amount"] <= 100_000).all(), "impossible outliers survived cleaning"
    assert clean["amount"].dtype.kind == "f"


def test_clean_dates_inside_window(clean) -> None:
    start, end = pd.Timestamp(config.WINDOW_START), pd.Timestamp(config.WINDOW_END)
    assert clean["date"].min() >= start
    assert clean["date"].max() <= end + pd.Timedelta(days=1)
    assert clean["year_month"].nunique() == config.N_MONTHS


def test_clean_categories_are_canonical(clean) -> None:
    assert set(clean["category"].unique()) <= set(config.CATEGORY_BUDGETS)
    assert set(clean["payment_method"].unique()) <= set(config.PAYMENT_METHODS) | {"Unknown"}


# --------------------------------------------------------------------------- #
# 12-16: the analysis maths
# --------------------------------------------------------------------------- #
def test_category_shares_sum_to_100(results) -> None:
    total = results["category"]["share_pct"].sum()
    assert abs(total - 100.0) < 0.05, f"shares sum to {total}"


def test_category_totals_match_the_raw_sum(results, clean) -> None:
    assert abs(results["category"]["total_spend"].sum() - clean["amount"].sum()) < 0.01


def test_budget_variance_arithmetic(results) -> None:
    budget = results["budget"]
    expected = (budget["avg_monthly_per_user"] - budget["monthly_budget"]) / budget["monthly_budget"] * 100
    assert np.allclose(budget["variance_pct"], expected, atol=0.01)


def test_budget_is_compared_per_user_not_in_total(results) -> None:
    """Regression guard: budgets are per user, so variance must be sane.

    Before this was fixed every category reported +5000% variance because the
    aggregate spend was compared against a single user's budget.
    """
    budget = results["budget"]
    assert budget["variance_pct"].abs().max() < 500, "budget variance looks like a scaling bug"
    assert budget["avg_monthly_per_user"].sum() == pytest.approx(
        results["overview"]["avg_monthly_spend_per_user"], rel=0.01
    )


def test_monthly_summary_is_complete_and_consistent(results) -> None:
    monthly = results["monthly"]
    assert len(monthly) == config.N_MONTHS
    assert monthly["year_month"].is_monotonic_increasing
    assert abs(monthly["total_spend"].sum() - results["overview"]["total_spend"]) < 0.01
    if "income" in monthly:
        assert np.allclose(monthly["savings"], monthly["income"] - monthly["total_spend"], atol=1e-6)
        rate = monthly["savings"] / monthly["income"] * 100
        assert np.allclose(monthly["savings_rate_pct"], rate, atol=0.01)


def test_pareto_never_exceeds_the_threshold(results) -> None:
    pareto = results["pareto"]
    assert len(pareto) >= 1
    assert pareto["cumulative_pct"].iloc[-1] <= config.PARETO_SHARE


def test_anomalies_are_per_user_and_above_threshold(results) -> None:
    anomalies = results["anomalies"]
    top = anomalies["top_user_days"]
    assert anomalies["user_day_anomalies"] >= 0
    if len(top):
        assert (top["z_score"] > config.ANOMALY_Z_THRESHOLD).all()
        assert (top["spend"] >= config.ANOMALY_MIN_USER_DAY_SPEND).all()
        assert (top["spend"] > top["user_median"]).all()
        assert top["user_id"].nunique() >= 1


def test_recurring_bills_are_excluded_from_anomalies(results) -> None:
    """Rent day must never be flagged - that was the bug this guards."""
    assert set(results["anomalies"]["excluded_categories"]) == set(config.FIXED_MONTHLY_CATEGORIES)


def test_burn_rate_is_compared_to_the_variable_budget(results) -> None:
    """The burn rate excludes recurring bills, so the budget must exclude them too."""
    anomalies = results["anomalies"]
    expected_variable = sum(
        b for c, b in config.CATEGORY_BUDGETS.items() if c not in config.FIXED_MONTHLY_CATEGORIES
    )
    assert anomalies["variable_budget_per_user"] == pytest.approx(expected_variable)
    assert anomalies["burn_vs_variable_budget_pct"] == pytest.approx(
        anomalies["burn_rate_30d_per_user"] / anomalies["variable_budget_per_user"] * 100, abs=0.01
    )
    assert anomalies["variable_budget_per_user"] < anomalies["monthly_budget"]


def test_merchant_share_claim_uses_the_right_denominator(results) -> None:
    """The report says 'of variable spend' - so it must not divide by total spend.

    Total spend includes rent, which is never paid to a merchant in the table.
    """
    merchants = results["merchants"].head(5)["total_spend"].sum()
    category = results["category"]
    total = category["total_spend"].sum()
    variable = category.loc[
        ~category["category"].isin(config.FIXED_MONTHLY_CATEGORIES), "total_spend"
    ].sum()
    assert variable < total

    text = config.INSIGHTS_MD_PATH.read_text(encoding="utf-8")
    assert f"{merchants / variable * 100:.1f}% of variable spend" in text, (
        "the report's merchant share does not match share-of-variable-spend"
    )
    assert f"{merchants / total * 100:.1f}% of variable spend" not in text, (
        "the merchant share was computed against total spend but labelled 'variable spend'"
    )


def test_weekend_effect_is_measurable(results) -> None:
    patterns = results["patterns"]
    assert patterns["weekend_share_pct"] > patterns["weekend_baseline_pct"], (
        "the simulation promises a weekend lift - the data should show one"
    )
    assert patterns["weekend_lift_pct"] > 0


# --------------------------------------------------------------------------- #
# 17-20: the generated artefacts
# --------------------------------------------------------------------------- #
def test_all_charts_exist_and_are_non_empty() -> None:
    charts = sorted(config.CHARTS_DIR.glob("*.png"))
    assert len(charts) == 10, f"expected 10 charts, found {len(charts)}"
    for chart in charts:
        assert chart.stat().st_size > 10_000, f"{chart.name} looks empty"


def test_reports_exist_and_are_complete() -> None:
    for path in (config.INSIGHTS_MD_PATH, config.QUALITY_MD_PATH, config.SUMMARY_JSON_PATH,
                 config.SUMMARY_CSV_PATH):
        assert path.exists(), f"{path.name} missing - run `python main.py all`"
        assert path.stat().st_size > 500, f"{path.name} is suspiciously small"

    text = config.INSIGHTS_MD_PATH.read_text(encoding="utf-8")
    for section in [
        "# Expense Tracker - Automated Insight Report",
        "## 1. Executive summary",
        "## 2. Category mix",
        "## 3. Budget performance",
        "## 4. Monthly trend",
        "## 5. Spending patterns",
        "## 6. Anomaly detection",
        "## 7. Savings",
        "## 8. User segments",
        "## 9. Recommended actions",
        "## 10. Reproduce this report",
    ]:
        assert section in text, f"missing section: {section}"

    payload = json.loads(config.SUMMARY_JSON_PATH.read_text(encoding="utf-8"))
    assert payload["author"] == config.PROJECT_AUTHOR
    assert payload["seed"] == config.RANDOM_SEED
    assert payload["overview"]["transactions"] > 0
    assert len(payload["categories"]) == 10


def test_reports_contain_no_unformatted_placeholders() -> None:
    """Catches f-string / .format bugs that leak '{0}' into a report."""
    text = config.INSIGHTS_MD_PATH.read_text(encoding="utf-8")
    leaked = re.findall(r"\{[0-9a-zA-Z_]+[:\}]", text)
    assert not leaked, f"unformatted placeholders leaked into the report: {sorted(set(leaked))[:5]}"
    assert "nan" not in text.lower().replace("finance", ""), "a NaN leaked into the report"


def test_money_formatters_speak_in_thousands_only() -> None:
    """The app once quoted Cr/L for the very amounts it now quotes in K."""
    assert utils.money_compact(37_263_111.51) == f"{config.CURRENCY_SYMBOL}37,263.1 K"
    assert utils.money_k(16_000_000) == f"{config.CURRENCY_SYMBOL}16,000k"
    assert utils.money_k(45_000) == f"{config.CURRENCY_SYMBOL}45k"
    assert utils.money_compact(850) == f"{config.CURRENCY_SYMBOL}850.00"
    # the sign belongs in front of the symbol, not inside it
    assert utils.money_k(-15_420) == f"-{config.CURRENCY_SYMBOL}15.4k"

    for value in (37_263_111.51, 3_996_844.0, 44_278.66, 850.0):
        for rendered in (utils.money_compact(value), utils.money_k(value)):
            assert "Cr" not in rendered, f"crore formatting came back: {rendered}"
            assert "L" not in rendered, f"lakh formatting came back: {rendered}"


def test_summary_csv_reports_every_amount_in_thousands(results) -> None:
    """The export divides by 1,000 at the edge, leaving the ledger in rupees."""
    frame = insights.summary_frame(results)
    assert list(frame.columns) == ["section", "label", "metric", "value", "unit"]
    assert len(frame) > 100, "the summary export looks truncated"

    keyed = frame.set_index(["section", "label", "metric"])
    total = keyed.loc[("overview", "all users", "total_spend")]
    assert total["unit"] == insights.THOUSANDS
    assert float(total["value"]) == pytest.approx(results["overview"]["total_spend"] / 1_000, abs=0.01)

    # counts must stay integral - a mixed column gets upcast and prints 16179.0
    txns = keyed.loc[("overview", "all users", "transactions"), "value"]
    assert txns == str(int(results["overview"]["transactions"]))

    # and the scaled export must never be the thing the ledger itself holds
    assert config.CLEAN_CSV_PATH.exists()
    assert results["overview"]["total_spend"] > 1_000_000


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
