"""
Analytics layer: category mix, trends, budget variance, anomalies and savings.

Everything here returns plain pandas objects so the dashboard, the report and
the tests all read from exactly the same numbers.

Author: Harsha K S
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import config
from src.data_cleaning import load_clean_data, load_income
from src.utils import setup_logging

LOGGER = setup_logging()

MONTH_ORDER = list(pd.period_range(config.WINDOW_START, config.WINDOW_END, freq="M").astype(str))


def overview(df: pd.DataFrame, income: pd.DataFrame | None = None) -> dict:
    """Top-line numbers for the KPI cards.

    Budgets and incomes in this project are defined *per user*, so anything
    compared against them is divided by the user count.
    """
    total = float(df["amount"].sum())
    n_months = max(1, df["year_month"].nunique())
    n_users = max(1, df["user_id"].nunique())
    monthly_spend = df.groupby("year_month")["amount"].sum()

    return {
        "total_spend": round(total, 2),
        "transactions": int(len(df)),
        "users": n_users,
        "categories": int(df["category"].nunique()),
        "avg_transaction": round(total / max(1, len(df)), 2),
        "avg_monthly_spend": round(total / n_months, 2),
        "avg_monthly_spend_per_user": round(total / n_months / n_users, 2),
        "monthly_budget_per_user": round(sum(config.CATEGORY_BUDGETS.values()), 2),
        "monthly_budget_all_users": round(sum(config.CATEGORY_BUDGETS.values()) * n_users, 2),
        "avg_monthly_income_per_user": (
            round(float(income["income_amount"].mean()), 2) if income is not None else None
        ),
        "spend_peak_month": str(monthly_spend.idxmax()),
        "spend_low_month": str(monthly_spend.idxmin()),
        "date_from": str(df["date"].min().date()),
        "date_to": str(df["date"].max().date()),
        "months": n_months,
    }


def category_summary(df: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
    """Spend, share and cumulative share per category (Pareto view).

    Absolute totals cover every user; the budget columns are reduced to a
    per-user figure so they line up with `config.CATEGORY_BUDGETS`.
    """
    total = df["amount"].sum()
    months = max(1, df["year_month"].nunique())
    n_users = max(1, df["user_id"].nunique())

    grouped = (
        df.groupby("category")
        .agg(
            total_spend=("amount", "sum"),
            transactions=("amount", "count"),
            avg_transaction=("amount", "mean"),
            max_transaction=("amount", "max"),
            users=("user_id", "nunique"),
        )
        .sort_values("total_spend", ascending=False)
        .reset_index()
    )
    grouped["share_pct"] = (grouped["total_spend"] / total * 100).round(2)
    grouped["cumulative_pct"] = grouped["share_pct"].cumsum().round(2)
    grouped["rank"] = range(1, len(grouped) + 1)
    grouped["monthly_budget"] = grouped["category"].map(config.CATEGORY_BUDGETS)
    grouped["avg_monthly_total"] = (grouped["total_spend"] / months).round(2)
    grouped["avg_monthly_per_user"] = (grouped["avg_monthly_total"] / n_users).round(2)
    grouped["budget_variance"] = (grouped["avg_monthly_per_user"] - grouped["monthly_budget"]).round(2)
    grouped["budget_variance_pct"] = (
        grouped["budget_variance"] / grouped["monthly_budget"] * 100
    ).round(2)
    return grouped if top_n is None else grouped.head(top_n)


def pareto_cut(summary: pd.DataFrame, threshold: float = config.PARETO_SHARE) -> pd.DataFrame:
    """The smallest set of categories that together reach `threshold`% of spend."""
    return summary.loc[summary["cumulative_pct"] <= threshold]


def monthly_summary(df: pd.DataFrame, income: pd.DataFrame | None = None) -> pd.DataFrame:
    """Month-by-month spend, month-over-month change and savings rate."""
    n_users = max(1, df["user_id"].nunique())
    spend = df.groupby("year_month").agg(
        total_spend=("amount", "sum"),
        transactions=("amount", "count"),
        avg_transaction=("amount", "mean"),
    )
    spend = spend.reindex(MONTH_ORDER).fillna(0.0)
    spend["spend_per_user"] = spend["total_spend"] / n_users
    spend["mom_change_pct"] = spend["total_spend"].pct_change() * 100
    spend["rolling_3m_avg"] = spend["total_spend"].rolling(3, min_periods=1).mean()

    budget_all = sum(config.CATEGORY_BUDGETS.values()) * n_users
    spend["budget"] = budget_all
    spend["budget_variance"] = spend["total_spend"] - budget_all
    spend["budget_variance_pct"] = spend["budget_variance"] / budget_all * 100

    if income is not None and len(income):
        monthly_income = income.groupby("month")["income_amount"].sum().reindex(MONTH_ORDER)
        spend["income"] = monthly_income
        spend["savings"] = spend["income"] - spend["total_spend"]
        spend["savings_rate_pct"] = spend["savings"] / spend["income"] * 100
    return spend.reset_index()


def budget_performance(df: pd.DataFrame, per_month: bool = False) -> pd.DataFrame:
    """Actual spend against the configured budget, per category.

    The budgets in `config` are per-user, so the actuals are divided by the
    user count before being compared - otherwise every category would look
    catastrophically over budget simply because there are 50 users.
    """
    months = max(1, df["year_month"].nunique())
    n_users = max(1, df["user_id"].nunique())
    actual = df.groupby("category")["amount"].sum().rename("actual_total")

    frame = pd.DataFrame({"category": list(config.CATEGORY_BUDGETS.keys())})
    frame["monthly_budget"] = frame["category"].map(config.CATEGORY_BUDGETS)
    frame["annual_budget"] = frame["monthly_budget"] * months
    frame["actual_total"] = frame["category"].map(actual).fillna(0.0)
    frame["avg_monthly_total"] = frame["actual_total"] / months
    frame["avg_monthly_per_user"] = frame["avg_monthly_total"] / n_users
    frame["variance"] = frame["avg_monthly_per_user"] - frame["monthly_budget"]
    frame["variance_pct"] = frame["variance"] / frame["monthly_budget"] * 100
    frame["status"] = np.select(
        [
            frame["variance_pct"] <= -config.BUDGET_TOLERANCE_PCT,
            frame["variance_pct"] >= config.BUDGET_TOLERANCE_PCT,
        ],
        ["Under budget", "Over budget"],
        default="On track",
    )
    return frame.sort_values("variance_pct", ascending=False).reset_index(drop=True)


def spending_patterns(df: pd.DataFrame) -> dict:
    """When and how people spend: weekday split, hour buckets, payment mix."""
    weekday = (
        df.groupby("weekday")["amount"]
        .sum()
        .reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )
        .fillna(0.0)
    )

    buckets = pd.cut(
        df["hour"],
        bins=[-1] + [hi for _, hi, _ in config.HOUR_BUCKETS[:4]] + [23],
        labels=[label for _, _, label in config.HOUR_BUCKETS],
    )
    hour_bucket = df.groupby(buckets, observed=False)["amount"].sum()

    split = df.groupby("is_weekend")["amount"].sum()
    weekend = float(split.get(True, 0.0))
    weekday_total = float(split.get(False, 0.0))
    weekend_share = weekend / max(1e-9, weekend + weekday_total) * 100
    baseline = config.BASELINE_WEEKEND_SHARE * 100

    payment = (
        df.groupby("payment_method")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    return {
        "weekday_spend": weekday,
        "hour_bucket_spend": hour_bucket,
        "weekend_spend": weekend,
        "weekday_spend_total": weekday_total,
        "weekend_share_pct": round(weekend_share, 2),
        "weekend_baseline_pct": round(baseline, 2),
        "weekend_lift_pct": round((weekend_share / baseline - 1) * 100, 2),
        "payment_spend": payment,
        "payment_count": df["payment_method"].value_counts(),
        "busiest_day": str(weekday.idxmax()),
        "busiest_bucket": str(hour_bucket.idxmax()),
        "top_payment": str(payment.idxmax()),
    }


def merchant_leaders(df: pd.DataFrame, per_category: bool = True) -> tuple[pd.DataFrame, dict]:
    """Overall top merchants plus the leader inside each category.

    Fixed monthly bills (rent, utilities) drown everything else in a spend
    ranking, so they are left out of the overall list and kept in the
    per-category leaders instead.
    """
    variable = df[~df["category"].isin(config.FIXED_MONTHLY_CATEGORIES)]
    overall = (
        variable.groupby(["merchant", "category"])["amount"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "total_spend", "count": "transactions"})
        .sort_values("total_spend", ascending=False)
        .reset_index()
        .head(12)
    )
    leaders: dict[str, str] = {}
    if per_category:
        for category, group in df.groupby("category"):
            leaders[category] = str(group.groupby("merchant")["amount"].sum().idxmax())
    return overall, leaders


def anomaly_detection(df: pd.DataFrame) -> dict:
    """Flag overspending on *discretionary* spend, per user and in aggregate.

    Two deliberate design choices:

    * **Recurring bills are excluded.** Rent and utilities are scheduled, not
      anomalous - counting them just flags every user on their rent day.
    * **The baseline is the user's own active days.** A user who spends on 20
      days a month would otherwise have a median day of almost zero, making an
      ordinary ₹900 day look like an outlier.

    The score is a robust z-score (median / MAD) rather than mean / std, so a
    single large booking cannot define what "normal" means.
    """
    spend_base = df.loc[~df["category"].isin(config.FIXED_MONTHLY_CATEGORIES)].copy()

    daily = spend_base.groupby(spend_base["date"].dt.date).agg(
        total_spend=("amount", "sum"), transactions=("amount", "count")
    )
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max()).date).fillna(0.0)

    median = float(daily["total_spend"].median())
    mad = float(np.median(np.abs(daily["total_spend"] - median)))
    scale = 1.4826 * mad if mad > 0 else float(daily["total_spend"].std() or 1.0)
    daily["z_score"] = (daily["total_spend"] - median) / scale
    daily["is_anomaly"] = (
        (daily["z_score"] > config.ANOMALY_Z_THRESHOLD)
        & (daily["transactions"] >= config.ANOMALY_MIN_TX_PER_DAY)
    )
    alert_threshold = median + config.ANOMALY_Z_THRESHOLD * scale
    daily["rolling_avg"] = daily["total_spend"].rolling(
        config.ROLLING_WINDOW_DAYS, min_periods=1
    ).mean()

    # ---- per-user detection (every row here is already an active day) ----- #
    user_daily = (
        spend_base.groupby(["user_id", spend_base["date"].dt.date])
        .agg(spend=("amount", "sum"), transactions=("amount", "count"))
        .reset_index()
        .rename(columns={"date": "day"})
    )

    group = user_daily.groupby("user_id")["spend"]
    user_median = group.transform("median")
    user_abs_dev = (user_daily["spend"] - user_median).abs()
    user_mad = user_abs_dev.groupby(user_daily["user_id"]).transform("median")
    user_scale = 1.4826 * user_mad
    user_scale = user_scale.where(user_scale > 0, group.transform("std"))
    user_scale = user_scale.fillna(1.0)

    user_daily["user_median"] = user_median
    user_daily["z_score"] = (user_daily["spend"] - user_median) / user_scale
    user_daily["is_anomaly"] = (
        (user_daily["z_score"] > config.ANOMALY_Z_THRESHOLD)
        & (user_daily["transactions"] >= config.ANOMALY_MIN_TX_PER_DAY)
        & (user_daily["spend"] >= config.ANOMALY_MIN_USER_DAY_SPEND)
    )
    flagged = user_daily.loc[user_daily["is_anomaly"]].sort_values("z_score", ascending=False)
    flagged = flagged.assign(vs_own_median_pct=(flagged["spend"] / flagged["user_median"] - 1) * 100)

    n_users = max(1, df["user_id"].nunique())
    burn_rate = float(daily["total_spend"].mean()) * config.ROLLING_WINDOW_DAYS
    month_budget = sum(config.CATEGORY_BUDGETS.values())
    variable_budget = sum(
        b for c, b in config.CATEGORY_BUDGETS.items() if c not in config.FIXED_MONTHLY_CATEGORIES
    )

    daily_out = daily.reset_index()
    daily_out = daily_out.rename(columns={daily_out.columns[0]: "date"})
    top_out = flagged.head(15).reset_index(drop=True)

    return {
        "daily": daily_out,
        "aggregate_anomaly_days": int(daily["is_anomaly"].sum()),
        "user_day_anomalies": int(len(flagged)),
        "users_flagged": int(flagged["user_id"].nunique()) if len(flagged) else 0,
        "top_user_days": top_out,
        "flagged_dates": sorted({str(d) for d in flagged["day"]}) if len(flagged) else [],
        "median_daily_spend": round(median, 2),
        "mad": round(mad, 2),
        "z_threshold": config.ANOMALY_Z_THRESHOLD,
        "alert_threshold": round(alert_threshold, 2),
        "min_user_day_spend": config.ANOMALY_MIN_USER_DAY_SPEND,
        "burn_rate_30d": round(burn_rate, 2),
        "burn_rate_30d_per_user": round(burn_rate / n_users, 2),
        "monthly_budget": round(month_budget, 2),
        "variable_budget_per_user": round(variable_budget, 2),
        "burn_vs_variable_budget_pct": round((burn_rate / n_users) / variable_budget * 100, 2),
        "burn_vs_budget_pct": round((burn_rate / n_users) / month_budget * 100, 2),
        "excluded_categories": list(config.FIXED_MONTHLY_CATEGORIES),
    }


def savings_analysis(df: pd.DataFrame, income: pd.DataFrame) -> pd.DataFrame:
    """Income vs spend per user-month, with the savings rate."""
    spend = (
        df.groupby(["user_id", "year_month"])["amount"]
        .sum()
        .rename("spend")
        .reset_index()
        .rename(columns={"year_month": "month"})
    )
    merged = spend.merge(income, on=["user_id", "month"], how="left")
    merged["savings"] = merged["income_amount"] - merged["spend"]
    merged["savings_rate_pct"] = merged["savings"] / merged["income_amount"] * 100
    return merged


def segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compare heavy / moderate / light spenders."""
    total = df["amount"].sum()
    out = (
        df.groupby("user_segment")
        .agg(
            total_spend=("amount", "sum"),
            transactions=("amount", "count"),
            avg_transaction=("amount", "mean"),
            users=("user_id", "nunique"),
        )
        .sort_values("total_spend", ascending=False)
    )
    out["share_pct"] = out["total_spend"] / total * 100
    out["spend_per_user"] = out["total_spend"] / out["users"]
    return out.reset_index()


def top_transactions(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """The single largest expenses - useful for a "where did the money go" view."""
    cols = ["date", "user_id", "category", "merchant", "amount", "payment_method"]
    return df.nlargest(n, "amount")[cols].reset_index(drop=True)


def full_analysis(df: pd.DataFrame | None = None, income: pd.DataFrame | None = None) -> dict:
    """Run every analysis and return one dictionary of results."""
    if df is None:
        df = load_clean_data()
    if income is None:
        income = load_income()

    cat = category_summary(df)
    anomalies = anomaly_detection(df)
    patterns = spending_patterns(df)
    overall, category_leaders = merchant_leaders(df)

    return {
        "overview": overview(df, income),
        "category": cat,
        "pareto": pareto_cut(cat),
        "monthly": monthly_summary(df, income),
        "budget": budget_performance(df),
        "patterns": patterns,
        "merchants": overall,
        "category_leaders": category_leaders,
        "anomalies": anomalies,
        "savings": savings_analysis(df, income),
        "segments": segment_summary(df),
        "top_transactions": top_transactions(df),
    }
