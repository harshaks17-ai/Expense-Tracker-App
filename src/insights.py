"""
Automated Markdown insight report.

The report is written from the same analysis frames the dashboard uses, so the
numbers a reviewer reads in GitHub are the numbers they see in the app.

Author: Harsha K S
"""

from __future__ import annotations

import pandas as pd

from src import config
from src.utils import money, money_k, pct, relative, setup_logging

LOGGER = setup_logging()


def _budget_table(budget: pd.DataFrame) -> list[str]:
    lines = [
        "| Category | Budget | Actual (per user) | Variance | Status |",
        "| --- | ---: | ---: | ---: | :--- |",
    ]
    for _, row in budget.sort_values("variance_pct", ascending=False).iterrows():
        lines.append(
            f"| {row['category']} | {money(row['monthly_budget'])} | {money(row['avg_monthly_per_user'])} | "
            f"{row['variance_pct']:+.1f}% | {row['status']} |"
        )
    return lines


def _monthly_table(monthly: pd.DataFrame) -> list[str]:
    lines = [
        "| Month | Spend | MoM | Savings rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for _, row in monthly.iterrows():
        mom = "-" if pd.isna(row["mom_change_pct"]) else f"{row['mom_change_pct']:+.1f}%"
        rate = f"{row['savings_rate_pct']:+.1f}%" if "savings_rate_pct" in row and pd.notna(row.get("savings_rate_pct")) else "-"
        lines.append(f"| {row['year_month']} | {money(row['total_spend'])} | {mom} | {rate} |")
    return lines


def build_report(results: dict) -> str:
    """Assemble the full Markdown report as a string."""
    o = results["overview"]
    cat = results["category"]
    monthly = results["monthly"]
    budget = results["budget"]
    patterns = results["patterns"]
    anomalies = results["anomalies"]
    segments = results["segments"]
    pareto = results["pareto"]

    top = cat.iloc[0]
    worst = budget.iloc[0]
    best = budget.sort_values("variance_pct").iloc[0]
    peak = monthly.loc[monthly["total_spend"].idxmax()]
    trough = monthly.loc[monthly["total_spend"].idxmin()]
    overall_savings_rate = (
        (monthly["income"].sum() - monthly["total_spend"].sum()) / monthly["income"].sum() * 100
        if "income" in monthly else float("nan")
    )

    heavy = segments.loc[segments["user_segment"] == "Heavy spender"]
    heavy_line = (
        f"{pct(heavy['share_pct'].iloc[0] / 100)} of spend from "
        f"{pct(heavy['users'].iloc[0] / segments['users'].sum())} of users"
        if len(heavy) else "n/a"
    )

    merchant_head = results["merchants"].head(5)
    variable_total = cat.loc[
        ~cat["category"].isin(config.FIXED_MONTHLY_CATEGORIES), "total_spend"
    ].sum()
    # a filter that keeps only recurring bills leaves no variable spend to divide by
    merchant_share = (
        merchant_head["total_spend"].sum() / variable_total * 100 if variable_total > 0 else float("nan")
    )
    merchant_share_txt = f"{merchant_share:.1f}%" if merchant_share == merchant_share else "n/a"
    worst_gap = money(abs(float(worst["variance"])))
    median_monthly = float(monthly["total_spend"].median())
    spike_lift = (float(peak["total_spend"]) / median_monthly - 1) * 100

    lines = [
        "# Expense Tracker - Automated Insight Report",
        "",
        f"**Project:** {config.PROJECT_NAME} v{config.PROJECT_VERSION}  ",
        f"**Author:** {config.PROJECT_AUTHOR}  ",
        f"**Window:** {o['date_from']} to {o['date_to']} ({o['months']} months)  ",
        f"**Users:** {o['users']:,}  ",
        f"**Transactions analysed:** {o['transactions']:,}",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        f"- **Total spend:** {money(o['total_spend'])} across {o['transactions']:,} transactions "
        f"({o['categories']} categories, {o['users']} users).",
        f"- **Average transaction:** {money(o['avg_transaction'])}; **average monthly spend per user:** "
        f"{money(o['avg_monthly_spend_per_user'])} against a {money(o['monthly_budget_per_user'])} budget.",
        f"- **30-day burn rate per user:** {money(anomalies['burn_rate_30d_per_user'])} - "
        f"{anomalies['burn_vs_variable_budget_pct']:.1f}% of the {money(anomalies['variable_budget_per_user'])} "
        "per-user *variable* budget, i.e. the wallet is running hot.",
        f"- **Overall savings rate:** {overall_savings_rate:+.1f}%.",
        f"- **Spend is concentrated:** {len(pareto)} of {len(cat)} categories account for "
        f"{pareto['cumulative_pct'].iloc[-1]:.1f}% of every rupee spent.",
        "",
        "## 2. Category mix",
        "",
        f"**{top['category']}** is the single largest category at **{top['share_pct']:.1f}%** of total spend "
        f"({money(top['total_spend'])} over {int(top['transactions']):,} transactions).",
        "",
        "| Rank | Category | Spend | Share | Cumulative | Txns | Avg txn |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in cat.iterrows():
        lines.append(
            f"| {int(row['rank'])} | {row['category']} | {money(row['total_spend'])} | "
            f"{row['share_pct']:.1f}% | {row['cumulative_pct']:.1f}% | {int(row['transactions']):,} | "
            f"{money(row['avg_transaction'])} |"
        )

    lines += [
        "",
        f"> **Pareto:** the top {len(pareto)} categories "
        f"({', '.join(pareto['category'])}) cover {pareto['cumulative_pct'].iloc[-1]:.1f}% of spend. "
        "A budget review should start there and nowhere else.",
        "",
        "## 3. Budget performance",
        "",
        "Budgets are per user per month. Actuals are the per-user average.",
        "",
        *_budget_table(budget),
        "",
        f"- **Worst overrun:** {worst['category']} at {worst['variance_pct']:+.1f}% "
        f"({worst_gap} per user per month above budget).",
        f"- **Best controlled:** {best['category']} at {best['variance_pct']:+.1f}%.",
        "",
        "## 4. Monthly trend",
        "",
        f"- **Peak month:** {peak['year_month']} at {money(peak['total_spend'])}.",
        f"- **Lowest month:** {trough['year_month']} at {money(trough['total_spend'])}.",
        f"- **Peak vs trough swing:** {((peak['total_spend'] / trough['total_spend']) - 1) * 100:.1f}%.",
        "",
        *_monthly_table(monthly),
        "",
        "## 5. Spending patterns",
        "",
        f"- **Busiest day of the week:** {patterns['busiest_day']}.",
        f"- **Weekend share of spend:** {patterns['weekend_share_pct']:.1f}%.",
        f"- **Busiest time bucket:** {patterns['busiest_bucket']}.",
        f"- **Top payment method:** {patterns['top_payment']} "
        f"({patterns['payment_spend'].iloc[0] / patterns['payment_spend'].sum() * 100:.1f}% of value).",
        "",
        "### Top merchants (fixed bills excluded)",
        "",
        "| Merchant | Category | Spend | Txns |",
        "| --- | --- | ---: | ---: |",
    ]
    for _, row in results["merchants"].head(8).iterrows():
        lines.append(f"| {row['merchant']} | {row['category']} | {money(row['total_spend'])} | {int(row['transactions']):,} |")

    lines += [
        "",
        "## 6. Anomaly detection",
        "",
        f"A robust z-score (median / MAD) is computed **per user**, so a flagged day means "
        f"*that person* spent far more than *their own* normal day - not that the group average moved.",
        "",
        f"- **{anomalies['user_day_anomalies']} abnormal user-days** across "
        f"{anomalies['users_flagged']} of {o['users']} users.",
        f"- Threshold: robust z > {anomalies['z_threshold']} **and** spend >= "
        f"{money(anomalies['min_user_day_spend'])} **and** at least "
        f"{config.ANOMALY_MIN_TX_PER_DAY} transactions (so a single big booking alone does not flag a day).",
        f"- Median daily discretionary spend (all users): {money(anomalies['median_daily_spend'])}; "
        f"MAD: {money(anomalies['mad'])}.",
        f"- Recurring bills ({', '.join(anomalies['excluded_categories'])}) are excluded - "
        "paying rent on time is not an anomaly.",
        f"- 30-day burn rate: {money(anomalies['burn_rate_30d_per_user'])} per user, which is "
        f"**{anomalies['burn_vs_variable_budget_pct']:.1f}%** of the per-user *variable* budget "
        f"({money(anomalies['variable_budget_per_user'])}).",
        "",
        "### Most extreme user-days",
        "",
        "| Date | User | Spend | Their median day | z | Txns |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in anomalies["top_user_days"].head(10).iterrows():
        lines.append(
            f"| {pd.Timestamp(row['day']).date()} | {row['user_id']} | {money(row['spend'])} | "
            f"{money(row['user_median'])} | {row['z_score']:.1f} | {int(row['transactions'])} |"
        )

    lines += [
        "",
        "## 7. Savings",
        "",
        f"- Average monthly income per user: {money(o['avg_monthly_income_per_user'])}",
        f"- Average monthly spend per user: {money(o['avg_monthly_spend_per_user'])}",
        f"- Overall savings rate: **{overall_savings_rate:+.1f}%**",
        f"- Worst month: {monthly.loc[monthly['savings_rate_pct'].idxmin(), 'year_month']} "
        f"({monthly['savings_rate_pct'].min():+.1f}%)",
        f"- Best month: {monthly.loc[monthly['savings_rate_pct'].idxmax(), 'year_month']} "
        f"({monthly['savings_rate_pct'].max():+.1f}%)",
        "",
        "## 8. User segments",
        "",
        "| Segment | Users | Spend | Share | Spend / user |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in segments.iterrows():
        lines.append(
            f"| {row['user_segment']} | {int(row['users'])} | {money(row['total_spend'])} | "
            f"{row['share_pct']:.1f}% | {money(row['spend_per_user'])} |"
        )

    lines += [
        "",
        f"> {heavy_line}. A budgeting product should treat heavy spenders as the primary persona - "
        "they have the most to gain from an alert and the highest willingness to pay.",
        "",
        "## 9. Recommended actions",
        "",
        (f"1. **Cap the two categories that break the budget** - {budget.iloc[0]['category']} "
         f"({budget.iloc[0]['variance_pct']:+.0f}%) and {budget.iloc[1]['category']} "
         f"({budget.iloc[1]['variance_pct']:+.0f}%)."
         if len(budget) > 1 else
         f"1. **Cap the category that breaks the budget** - {budget.iloc[0]['category']} "
         f"({budget.iloc[0]['variance_pct']:+.0f}%)."),
        "2. **Set a pre-festival envelope.** The two spike months cost roughly "
        f"{spike_lift:.0f}% more than a normal month; "
        "saving into them in advance removes the negative savings rate.",
        f"3. **Alert on the {anomalies['user_day_anomalies']} anomalous user-days**, not on every transaction - "
        "a robust per-user threshold keeps the false-positive rate low.",
        "4. **Target heavy spenders first.** They generate the majority of value and are the ones "
        "whose budget variance actually matters in rupee terms.",
        f"5. **Watch the top {len(merchant_head)} merchants** - they alone represent "
        f"{merchant_share_txt} of variable spend.",
        "",
        "## 10. Reproduce this report",
        "",
        "```bash",
        "python main.py all       # regenerate data, clean, analyse, chart and write this report",
        "python main.py dashboard # interactive Streamlit dashboard",
        "```",
        "",
        f"Generated by {config.PROJECT_NAME} - every figure above traces back to "
        f"`{relative(config.CLEAN_CSV_PATH)}` and the statistical routines in `src/analysis.py`.",
        "",
    ]
    return "\n".join(lines)


def write_report(results: dict, path=config.INSIGHTS_MD_PATH) -> str:
    """Write the insight report to disk."""
    text = build_report(results)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    LOGGER.info("Insight report saved -> %s", relative(path))
    return text


SUMMARY_CSV_COLUMNS = ("section", "label", "metric", "value", "unit")
THOUSANDS = "INR thousands"


def summary_rows(results: dict) -> list[dict]:
    """Flatten every headline summary into one tidy table.

    Rupee figures are divided by 1,000 here rather than in the source data, so
    the ledger keeps its canonical rupee values and only this export is scaled.
    The `unit` column keeps scaled money distinguishable from counts and
    percentages sitting in the same `value` column.
    """
    rows: list[dict] = []

    def add(section: str, label: str, metric: str, value, unit: str) -> None:
        if value is None:
            return
        if unit == "count":
            try:
                rows.append({
                    "section": section, "label": label, "metric": metric,
                    "value": int(round(float(value))), "unit": unit,
                })
            except (TypeError, ValueError):
                pass
            return
        try:
            number = float(value)
        except (TypeError, ValueError):
            return
        if number != number:  # NaN, e.g. savings when no income file was joined
            return
        rows.append({
            "section": section,
            "label": label,
            "metric": metric,
            "value": round(number, 2),
            "unit": unit,
        })

    def add_money(section: str, label: str, metric: str, value) -> None:
        add(section, label, metric, None if value is None else float(value) / 1_000, THOUSANDS)

    o = results["overview"]
    add_money("overview", "all users", "total_spend", o["total_spend"])
    add_money("overview", "all users", "avg_transaction", o["avg_transaction"])
    add_money("overview", "all users", "avg_monthly_spend_per_user", o["avg_monthly_spend_per_user"])
    add_money("overview", "all users", "monthly_budget_per_user", o["monthly_budget_per_user"])
    add_money("overview", "all users", "avg_monthly_income_per_user", o.get("avg_monthly_income_per_user"))
    add("overview", "all users", "transactions", o["transactions"], "count")
    add("overview", "all users", "users", o["users"], "count")

    for _, row in results["category"].iterrows():
        add_money("category", row["category"], "total_spend", row["total_spend"])
        add("category", row["category"], "share_pct", row["share_pct"], "percent")
        add("category", row["category"], "transactions", row["transactions"], "count")

    for _, row in results["budget"].iterrows():
        add_money("budget", row["category"], "monthly_budget", row["monthly_budget"])
        add_money("budget", row["category"], "avg_monthly_per_user", row["avg_monthly_per_user"])
        add_money("budget", row["category"], "variance", row["variance"])
        add("budget", row["category"], "variance_pct", row["variance_pct"], "percent")
        add("budget", row["category"], "status", row["status"], "label")

    for _, row in results["monthly"].iterrows():
        month = str(row["year_month"])
        add_money("monthly", month, "total_spend", row["total_spend"])
        add_money("monthly", month, "budget", row["budget"])
        add_money("monthly", month, "income", row.get("income"))
        add_money("monthly", month, "savings", row.get("savings"))
        add("monthly", month, "savings_rate_pct", row.get("savings_rate_pct"), "percent")

    for _, row in results["segments"].iterrows():
        add_money("segment", row["user_segment"], "total_spend", row["total_spend"])
        add_money("segment", row["user_segment"], "spend_per_user", row["spend_per_user"])
        add("segment", row["user_segment"], "users", row["users"], "count")
        add("segment", row["user_segment"], "share_pct", row["share_pct"], "percent")

    for _, row in results["merchants"].iterrows():
        add_money("merchant", row["merchant"], "total_spend", row["total_spend"])
        add("merchant", row["merchant"], "transactions", row["transactions"], "count")

    a = results["anomalies"]
    add("anomaly", "all users", "user_day_anomalies", a["user_day_anomalies"], "count")
    add("anomaly", "all users", "users_flagged", a["users_flagged"], "count")
    add_money("anomaly", "all users", "burn_rate_30d_per_user", a["burn_rate_30d_per_user"])
    add_money("anomaly", "all users", "variable_budget_per_user", a["variable_budget_per_user"])
    add("anomaly", "all users", "burn_vs_variable_budget_pct", a["burn_vs_variable_budget_pct"], "percent")

    return rows


def _format_value(value, unit: str) -> str:
    """Render one value for export: counts stay integral, money keeps 2 decimals."""
    if unit == "count":
        return str(int(round(float(value))))
    if unit in (THOUSANDS, "percent"):
        return f"{float(value):.2f}"
    return str(value)


def summary_frame(results: dict) -> pd.DataFrame:
    """The tidy thousands summary as a DataFrame ready to write out.

    `value` is rendered as text rather than kept numeric because the column
    mixes counts, percentages and scaled money: pandas would upcast the whole
    column to float and print counts as "16179.0".
    """
    rows = summary_rows(results)
    for row in rows:
        row["value"] = _format_value(row["value"], row["unit"])
    return pd.DataFrame(rows, columns=list(SUMMARY_CSV_COLUMNS))


def write_summary_csv(results: dict, path=config.SUMMARY_CSV_PATH) -> str:
    """Write the headline summaries as a tidy CSV with every amount in thousands."""
    frame = summary_frame(results)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")
    LOGGER.info("Thousands summary saved -> %s (%s rows)", relative(path), len(frame))
    return str(path)
