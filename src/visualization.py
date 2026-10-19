"""
Ten publication-quality matplotlib/seaborn charts.

Every chart takes the already-computed analysis frames so the dashboard, the
report and the PNGs can never disagree with each other.

Author: Harsha K S
"""

from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src import config
from src.utils import apply_matplotlib_theme, money_k, save_figure, setup_logging

LOGGER = setup_logging()
apply_matplotlib_theme()
sns.set_theme(style="whitegrid", rc={"axes.grid": True, "grid.color": config.GRID_COLOR})

STATUS_COLORS = {"Over budget": config.PALETTE["rose"], "On track": config.PALETTE["slate"], "Under budget": config.PALETTE["emerald"]}

# neutral fill for the "background" series in a two-series comparison
NEUTRAL_FILL = "#cbd5e1"


def _text_on(fill: str) -> str:
    """White or ink, whichever stays readable on the given fill colour.

    The category ramp runs dark to light, so a fixed white label would become
    invisible on the tail of the ramp.
    """
    r, g, b = (int(fill[i:i + 2], 16) / 255 for i in (1, 3, 5))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#ffffff" if luminance < 0.58 else config.TEXT_COLOR


def _category_color_map(categories) -> dict[str, str]:
    """Assign ramp steps in the order given, so the biggest category reads darkest.

    Callers pass categories in rank order (largest spend first). Mapping them by
    their position in `CATEGORY_BUDGETS` instead would make the ramp decorative
    rather than meaningful, because that order is just how the budgets were typed.
    """
    mapping: dict[str, str] = {}
    for category in categories:
        if category not in mapping:
            mapping[category] = config.CATEGORY_COLORS[len(mapping) % len(config.CATEGORY_COLORS)]
    return mapping


def chart_category_share(summary: pd.DataFrame, also_images: bool = True) -> None:
    """Horizontal bars of category share with the Pareto cumulative line."""
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = _category_color_map(summary["category"])
    positions = np.arange(len(summary))
    ax.barh(
        positions,
        summary["share_pct"],
        color=[colors[c] for c in summary["category"]],
        edgecolor="white",
    )
    ax.set_yticks(positions, labels=summary["category"])
    ax.set_xlabel("Share of total spend (%)")
    ax.set_title("Where the money goes - category share of total spend")
    ax.xaxis.grid(True)
    ax.yaxis.grid(False)
    for y, value in zip(positions, summary["share_pct"]):
        ax.text(value + 0.4, y, f"{value:.1f}%", va="center", fontsize=9, zorder=6)

    # Ride the cascade just above the bars: drawn through the centres it lands
    # squarely on the value labels and makes them unreadable.
    lift = 0.34
    twin = ax.twiny()
    twin.set_zorder(5)
    twin.patch.set_visible(False)
    twin.plot(
        summary["cumulative_pct"], positions - lift, color=config.PALETTE["slate"],
        marker="o", markersize=5, linewidth=1.8,
        path_effects=[pe.withStroke(linewidth=4, foreground="white")],
    )
    ax.set_ylim(len(summary) - 0.5, -1.0)
    twin.set_xlim(0, 105)
    twin.set_xlabel("Cumulative % (Pareto)", color=config.MUTED_COLOR)
    twin.tick_params(axis="x", colors=config.MUTED_COLOR)

    cut = summary.loc[summary["cumulative_pct"] <= config.PARETO_SHARE]
    if len(cut):
        ax.text(0.98, 0.02, f"Top {len(cut)} categories = {cut['cumulative_pct'].iloc[-1]:.0f}% of spend",
                transform=ax.transAxes, ha="right", fontsize=9, color=config.MUTED_COLOR)
    save_figure(fig, config.CHARTS_DIR / "01_category_share.png", also_images)


def chart_monthly_trend(monthly: pd.DataFrame, also_images: bool = True) -> None:
    """Monthly spend with a 3-month average and the budget baseline."""
    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = pd.to_datetime(monthly["year_month"] + "-01")

    ax.plot(x, monthly["total_spend"], color=config.PALETTE["primary"], marker="o", linewidth=2.4, label="Total spend")
    ax.plot(x, monthly["rolling_3m_avg"], color=config.PALETTE["sky"], linewidth=2, linestyle="--", label="3-month average")
    ax.axhline(monthly["budget"].iloc[0], color=config.PALETTE["slate"], linewidth=1.6, linestyle=":", label="Budget (all users)")

    over_mask = monthly["total_spend"] > monthly["budget"].iloc[0]
    under_mask = ~over_mask
    ax.fill_between(x, monthly["total_spend"], monthly["budget"].iloc[0],
                    where=over_mask, color=config.PALETTE["rose"], alpha=0.12,
                    label="Over budget" if over_mask.any() else "_nolegend_")
    ax.fill_between(x, monthly["total_spend"], monthly["budget"].iloc[0],
                    where=under_mask, color=config.PALETTE["emerald"], alpha=0.12,
                    label="Under budget" if under_mask.any() else "_nolegend_")

    peak = monthly.loc[monthly["total_spend"].idxmax(), "year_month"]
    ax.set_title(
        f"Monthly spend vs budget - over budget in {int(over_mask.sum())} of {len(monthly)} months, "
        f"worst {peak}"
    )
    ax.set_ylabel("Spend")
    ax.yaxis.set_major_formatter(lambda v, _: money_k(v))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.legend(loc="upper left", ncol=2)
    fig.autofmt_xdate()
    save_figure(fig, config.CHARTS_DIR / "02_monthly_trend.png", also_images)


def chart_budget_vs_actual(budget: pd.DataFrame, also_images: bool = True) -> None:
    """Per-user monthly actual against budget, sorted by variance."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    order = budget.sort_values("variance_pct")["category"]
    data = budget.set_index("category").loc[order]

    y = np.arange(len(order))
    ax.barh(y - 0.2, data["monthly_budget"], height=0.38, color=config.PALETTE["slate"], label="Budget")
    ax.barh(y + 0.2, data["avg_monthly_per_user"], height=0.38,
            color=[STATUS_COLORS[s] for s in data["status"]], label="Actual (per user)")

    ax.set_yticks(y, order)
    ax.set_xlabel("Per-user monthly amount")
    ax.xaxis.set_major_formatter(lambda v, _: money_k(v))
    ax.set_title("Budget vs actual per user - variance % per category")
    for i, (actual, pct_) in enumerate(zip(data["avg_monthly_per_user"], data["variance_pct"])):
        ax.text(actual + 300, i + 0.2, f"{pct_:+.0f}%", va="center", fontsize=9,
                color=config.PALETTE["rose"] if pct_ > 0 else config.PALETTE["emerald"])
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, -0.10), ncol=2, frameon=False)
    save_figure(fig, config.CHARTS_DIR / "03_budget_vs_actual.png", also_images)


def chart_category_donut(summary: pd.DataFrame, also_images: bool = True) -> None:
    """Category mix as a donut, with the leader called out in the centre."""
    fig, ax = plt.subplots(figsize=(7.5, 7.5))
    colors = _category_color_map(summary["category"])
    wedges, _, autotexts = ax.pie(
        summary["total_spend"],
        labels=None,
        colors=[colors[c] for c in summary["category"]],
        autopct=lambda p: f"{p:.1f}%" if p > 3.5 else "",
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "white"},
        pctdistance=0.78,
    )
    for wedge, text in zip(wedges, autotexts):
        fill = "#{:02x}{:02x}{:02x}".format(*(int(255 * v) for v in wedge.get_facecolor()[:3]))
        text.set_color(_text_on(fill))
        text.set_fontsize(9)
        text.set_fontweight("bold")

    top = summary.iloc[0]
    ax.text(0, 0.08, top["category"], ha="center", fontsize=13, fontweight="bold")
    ax.text(0, -0.06, f"{top['share_pct']:.1f}% of spend", ha="center", fontsize=11, color=config.MUTED_COLOR)
    ax.text(0, -0.18, f"{top['transactions']:,} transactions", ha="center", fontsize=9, color=config.MUTED_COLOR)
    ax.set_title("Category mix")
    ax.legend(wedges, summary["category"], loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8.5)
    save_figure(fig, config.CHARTS_DIR / "04_category_donut.png", also_images)


def chart_payment_methods(patterns: dict, also_images: bool = True) -> None:
    """Payment mix by amount and by transaction count."""
    spend = patterns["payment_spend"]
    counts = patterns["payment_count"].reindex(spend.index)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))
    palette = list(config.CATEGORY_COLORS_DARK)

    bars = ax1.bar(spend.index, spend.values, color=palette[: len(spend)], edgecolor="white")
    ax1.set_title("Spend by payment method")
    ax1.set_ylabel("Total spend")
    ax1.yaxis.set_major_formatter(lambda v, _: money_k(v))
    ax1.tick_params(axis="x", rotation=25)
    for bar, value in zip(bars, spend.values):
        ax1.text(bar.get_x() + bar.get_width() / 2, value, f"{value / spend.sum() * 100:.0f}%",
                 ha="center", va="bottom", fontsize=9)

    bars2 = ax2.bar(counts.index, counts.values, color=palette[: len(counts)], edgecolor="white")
    ax2.set_title("Transaction count by payment method")
    ax2.set_ylabel("Transactions")
    ax2.tick_params(axis="x", rotation=25)
    for bar, value in zip(bars2, counts.values):
        ax2.text(bar.get_x() + bar.get_width() / 2, value, f"{int(value):,}", ha="center", va="bottom", fontsize=9)

    fig.suptitle(f"Payment mix - {patterns['top_payment']} leads on both volume and value",
                 fontweight="bold", y=1.02)
    save_figure(fig, config.CHARTS_DIR / "05_payment_methods.png", also_images)


def chart_weekday_pattern(patterns: dict, also_images: bool = True) -> None:
    """Day-of-week spend, with the weekend share called out."""
    weekday = patterns["weekday_spend"]
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [config.PALETTE["primary"] if d in ("Saturday", "Sunday") else NEUTRAL_FILL for d in weekday.index]
    bars = ax.bar(weekday.index, weekday.values, color=colors, edgecolor="white")
    ax.set_title(f"Spend by day of week - weekend lift of {patterns['weekend_lift_pct']:+.0f}% vs uniform")
    ax.set_ylabel("Total spend")
    ax.yaxis.set_major_formatter(lambda v, _: money_k(v))
    ax.tick_params(axis="x", rotation=20)
    for bar, value in zip(bars, weekday.values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, money_k(value), ha="center", va="bottom", fontsize=9)
    ax.text(0.99, 0.94, f"Weekends = {patterns['weekend_share_pct']:.1f}% of spend "
                        f"(vs {patterns['weekend_baseline_pct']:.1f}% if uniform)",
            transform=ax.transAxes, ha="right", fontsize=10, color=config.MUTED_COLOR)
    save_figure(fig, config.CHARTS_DIR / "06_weekday_pattern.png", also_images)


def chart_top_merchants(merchants: pd.DataFrame, also_images: bool = True) -> None:
    """Top merchants by value, excluding fixed monthly bills."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = _category_color_map(merchants["category"])
    data = merchants.sort_values("total_spend")
    bars = ax.barh(data["merchant"], data["total_spend"], color=[colors[c] for c in data["category"]], edgecolor="white")
    ax.set_xlabel("Total spend")
    ax.set_title("Top merchants by value (fixed bills excluded)")
    ax.set_yticks(range(len(data)), [f"{m}" for m in data["merchant"]])
    ax.xaxis.set_major_formatter(lambda v, _: money_k(v))
    ax.xaxis.grid(True)
    ax.yaxis.grid(False)
    for bar, value, count in zip(bars, data["total_spend"], data["transactions"]):
        ax.text(value + 20_000, bar.get_y() + bar.get_height() / 2, f"{money_k(value)}  ({count:,} tx)",
                va="center", fontsize=8.5)
    ax.set_xlim(0, float(data["total_spend"].max()) * 1.28)
    save_figure(fig, config.CHARTS_DIR / "07_top_merchants.png", also_images)


def chart_savings_trend(monthly: pd.DataFrame, also_images: bool = True) -> None:
    """Income vs spend with the savings rate underneath."""
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 7), height_ratios=[2.4, 1], sharex=True)
    x = pd.to_datetime(monthly["year_month"] + "-01")

    ax.fill_between(x, monthly["income"], monthly["total_spend"], color=config.PALETTE["emerald"], alpha=0.28, label="Savings")
    ax.plot(x, monthly["income"], color=config.PALETTE["slate"], linewidth=2, label="Income")
    ax.plot(x, monthly["total_spend"], color=config.PALETTE["primary"], linewidth=2, label="Spend")
    ax.set_title("Income vs spend, and the savings rate that follows")
    ax.set_ylabel("Amount")
    ax.yaxis.set_major_formatter(lambda v, _: money_k(v))
    ax.legend(loc="upper right", ncol=3)

    colors = [config.PALETTE["emerald"] if v >= 0 else config.PALETTE["rose"] for v in monthly["savings_rate_pct"]]
    ax2.bar(x, monthly["savings_rate_pct"], color=colors, width=18)
    ax2.axhline(0, color=config.GRID_COLOR, linewidth=1)
    ax2.set_ylabel("Savings rate %")
    ax2.set_title("Savings rate by month")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    fig.autofmt_xdate()
    save_figure(fig, config.CHARTS_DIR / "08_savings_trend.png", also_images)


def chart_anomaly_timeline(anomalies: dict, also_images: bool = True) -> None:
    """Aggregate daily spend with the user-days that were flagged as abnormal."""
    daily = anomalies["daily"].copy()
    daily["date"] = pd.to_datetime(daily["date"])

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(daily["date"], daily["total_spend"], color=config.PALETTE["slate"], linewidth=0.9, alpha=0.7, label="Daily spend (all users)")
    ax.plot(daily["date"], daily["rolling_avg"], color=config.PALETTE["primary"], linewidth=2.2, label=f"{config.ROLLING_WINDOW_DAYS}-day rolling average")

    flagged_dates = pd.to_datetime(pd.Series(anomalies["flagged_dates"], dtype="string"), errors="coerce").dropna()
    hits = daily[daily["date"].isin(flagged_dates)]
    ax.scatter(hits["date"], hits["total_spend"], s=46, color=config.PALETTE["rose"], zorder=5,
               label=f"Day with a flagged user (n={anomalies['user_day_anomalies']} user-days)")

    ax.set_title(
        f"Discretionary spend timeline - {anomalies['user_day_anomalies']} abnormal user-days "
        f"across {anomalies['users_flagged']} of the users"
    )
    ax.set_ylabel("Daily spend (all users, recurring bills excluded)")
    ax.yaxis.set_major_formatter(lambda v, _: money_k(v))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.legend(loc="upper right", ncol=2, fontsize=8.5)
    fig.autofmt_xdate()
    save_figure(fig, config.CHARTS_DIR / "09_anomaly_timeline.png", also_images)


def chart_segments(segments: pd.DataFrame, also_images: bool = True) -> None:
    """Heavy / moderate / light spenders: share of wallet vs share of users."""
    fig, ax = plt.subplots(figsize=(9, 5.2))
    x = np.arange(len(segments))
    width = 0.38
    ax.bar(x - width / 2, segments["share_pct"], width, color=config.PALETTE["primary"], label="Share of spend")
    user_share = segments["users"] / segments["users"].sum() * 100
    ax.bar(x + width / 2, user_share, width, color=NEUTRAL_FILL, label="Share of users")

    ax.set_xticks(x, segments["user_segment"])
    ax.set_ylabel("Percent")
    ax.set_title("A fifth of the users drive a third of the spend")
    for i, (spend_share, users) in enumerate(zip(segments["share_pct"], user_share)):
        ax.text(i - width / 2, spend_share + 1, f"{spend_share:.1f}%", ha="center", fontsize=9)
        ax.text(i + width / 2, users + 1, f"{users:.1f}%", ha="center", fontsize=9)
    ax.set_ylim(0, max(segments["share_pct"].max(), user_share.max()) * 1.25)
    ax.legend()
    save_figure(fig, config.CHARTS_DIR / "10_segment_composition.png", also_images)


def render_all(results: dict, also_images: bool = True) -> list[str]:
    """Render every chart. Returns the chart file names."""
    charts = [
        ("01_category_share.png", lambda: chart_category_share(results["category"], also_images)),
        ("02_monthly_trend.png", lambda: chart_monthly_trend(results["monthly"], also_images)),
        ("03_budget_vs_actual.png", lambda: chart_budget_vs_actual(results["budget"], also_images)),
        ("04_category_donut.png", lambda: chart_category_donut(results["category"], also_images)),
        ("05_payment_methods.png", lambda: chart_payment_methods(results["patterns"], also_images)),
        ("06_weekday_pattern.png", lambda: chart_weekday_pattern(results["patterns"], also_images)),
        ("07_top_merchants.png", lambda: chart_top_merchants(results["merchants"], also_images)),
        ("08_savings_trend.png", lambda: chart_savings_trend(results["monthly"], also_images)),
        ("09_anomaly_timeline.png", lambda: chart_anomaly_timeline(results["anomalies"], also_images)),
        ("10_segment_composition.png", lambda: chart_segments(results["segments"], also_images)),
    ]
    written = []
    for name, plot in charts:
        plot()
        written.append(name)
    return written
