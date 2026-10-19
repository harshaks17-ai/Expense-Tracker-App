"""
Expense Tracker App - interactive Streamlit dashboard.

Run it with:
    python main.py dashboard
    # or
    streamlit run dashboard.py

The dashboard reads the cleaned dataset produced by `python main.py all`, and
re-runs the *same* analysis functions as the report and the charts, so nothing
can drift between the three.

Author: Harsha K S
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analysis, config, insights
from src.data_cleaning import clean_expenses, load_clean_data, load_income
from src.utils import money, money_compact, money_k

st.set_page_config(
    page_title=f"{config.DASHBOARD_TITLE} | {config.PROJECT_AUTHOR}",
    page_icon=config.DASHBOARD_ICON,
    layout=config.DASHBOARD_LAYOUT,
    initial_sidebar_state="expanded",
)

PLOT_CONFIG = {"displayModeBar": False}


# --------------------------------------------------------------------------- #
# Styling - light report mode: white canvas, hairline rules, one accent hue.
# Colour is reserved for meaning (red = over budget, green = under).
# --------------------------------------------------------------------------- #
def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-variant-numeric: tabular-nums;
        }}
        .stApp {{ background: {config.BG_COLOR}; }}
        /* clear Streamlit's fixed header, or the masthead slides under it */
        .block-container {{ padding-top: 4.4rem; padding-bottom: 4rem; max-width: 1220px; }}

        /* ---- masthead: type only, no gradient panels ---- */
        .report-head {{ border-bottom: 2px solid {config.TEXT_COLOR}; padding-bottom: 12px; margin-bottom: 26px; }}
        .report-head .eyebrow {{
            font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.13em;
            color: {config.MUTED_COLOR}; font-weight: 600;
        }}
        .report-head h1 {{
            margin: 6px 0 0 0; font-size: 1.72rem; font-weight: 700;
            letter-spacing: -0.02em; color: {config.TEXT_COLOR};
        }}
        .report-head p {{
            margin: 7px 0 0 0; font-size: 0.90rem; color: {config.MUTED_COLOR}; max-width: 76ch;
        }}

        /* ---- KPI row: flat figures under a rule, not floating cards ---- */
        .kpi {{ border-top: 2px solid {config.TEXT_COLOR}; padding: 9px 0 0 0; height: 100%; }}
        .kpi .label {{
            font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.10em;
            color: {config.MUTED_COLOR}; font-weight: 600; line-height: 1.5;
        }}
        .kpi .value {{
            font-size: 1.40rem; font-weight: 700; color: {config.TEXT_COLOR};
            line-height: 1.3; margin-top: 2px; letter-spacing: -0.02em;
        }}
        .kpi .delta {{ font-size: 0.76rem; margin-top: 2px; color: {config.MUTED_COLOR}; }}
        .kpi .delta.up {{ color: {config.PALETTE['rose']}; }}
        .kpi .delta.down {{ color: {config.PALETTE['emerald']}; }}
        .kpi .delta.flat {{ color: {config.MUTED_COLOR}; }}

        /* ---- findings: quiet text lines with a hairline marker ---- */
        .insight {{
            border-left: 2px solid {config.BORDER_COLOR};
            padding: 3px 0 3px 13px; margin: 0 0 9px 0;
            font-size: 0.89rem; color: {config.TEXT_COLOR}; line-height: 1.55;
        }}
        .insight b {{ font-weight: 650; }}
        .insight.rose {{ border-left-color: {config.PALETTE['rose']}; }}
        .insight.amber {{ border-left-color: {config.PALETTE['amber']}; }}
        .insight.teal {{ border-left-color: {config.PALETTE['primary']}; }}
        .insight.violet {{ border-left-color: {config.PALETTE['slate']}; }}

        .section {{
            font-size: 0.70rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.11em; color: {config.MUTED_COLOR};
            border-bottom: 1px solid {config.BORDER_COLOR};
            padding-bottom: 6px; margin: 22px 0 12px 0;
        }}

        [data-testid="stSidebar"] {{
            background: {config.CANVAS_COLOR};
            border-right: 1px solid {config.BORDER_COLOR};
        }}
        [data-testid="stSidebar"] .block-container {{ padding-top: 1.6rem; }}

        /* ---- tabs: plain underline, no filled pills ---- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 26px; border-bottom: 1px solid {config.BORDER_COLOR}; padding-bottom: 0;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: transparent; border: none; border-radius: 0; padding: 6px 0 10px 0;
            font-weight: 600; font-size: 0.90rem; color: {config.MUTED_COLOR};
        }}
        .stTabs [aria-selected="true"] {{
            color: {config.TEXT_COLOR} !important; background: transparent !important;
            box-shadow: inset 0 -2px 0 0 {config.PALETTE['primary']};
        }}
        .stTabs [data-baseweb="tab-highlight"] {{ background: transparent; }}

        [data-testid="stDataFrame"] {{ border: 1px solid {config.BORDER_COLOR}; }}
        [data-testid="stToolbar"] {{ display: none; }}
        footer, #MainMenu {{ visibility: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, delta: str = "", direction: str = "flat",
        color: str | None = None) -> str:
    """One flat figure in the KPI row.

    `direction` follows the earlier convention: "up" means the number needs
    attention (spend above budget) and renders red; "down" renders green.
    """
    delta_html = f'<div class="delta {direction}">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {delta_html}
    </div>
    """


def insight(text: str, tone: str = "") -> None:
    st.markdown(f'<div class="insight {tone}">{text}</div>', unsafe_allow_html=True)


def report_head(df: pd.DataFrame | None = None) -> None:
    """Masthead: the file being read, in one line, with no decoration."""
    if df is None or df.empty:
        eyebrow, subtitle = "Expense analysis", "No ledger loaded."
    else:
        eyebrow = (
            f"{len(df):,} transactions &middot; {df['user_id'].nunique()} users &middot; "
            f"{df['category'].nunique()} categories &middot; "
            f"{df['date'].min():%b %Y} &ndash; {df['date'].max():%b %Y}"
        )
        subtitle = (
            "Cleaned ledger, per-user budget variance, per-user anomaly alerts and savings "
            "&mdash; every figure recomputed live from the data below."
        )
    st.markdown(
        f"""
        <div class="report-head">
            <div class="eyebrow">{eyebrow}</div>
            <h1>{config.DASHBOARD_TITLE}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stretch_kwargs() -> dict:
    """`width="stretch"` on new Streamlit, `use_container_width` on older ones."""
    try:
        major, minor = (int(p) for p in st.__version__.split(".")[:2])
        if (major, minor) >= (1, 49):
            return {"width": "stretch"}
    except Exception:  # pragma: no cover - defensive
        pass
    return {"use_container_width": True}


CHARTS = stretch_kwargs()


def category_colors(cat: pd.DataFrame) -> dict[str, str]:
    """Map categories to the sequential ramp.

    `cat` is always in rank order (largest first), and the ramp runs darkest
    first, so the biggest category reads darkest and rank is legible without
    ten unrelated hues.
    """
    return dict(zip(cat["category"], config.CATEGORY_COLORS))


def money_ticks(values, tick_count: int = 6) -> list[float]:
    """Round tick positions that split 0..max into at most `tick_count` steps."""
    top_value = max((abs(float(v)) for v in values), default=0.0)
    if not top_value > 0:
        return []
    step = 10.0 ** int(np.floor(np.log10(top_value / tick_count)))
    for multiplier in (1, 2, 2.5, 5, 10):
        if top_value / (step * multiplier) <= tick_count:
            step *= multiplier
            break
    top = np.ceil(top_value / step) * step
    return [float(v) for v in np.arange(0.0, top + step / 2, step)]


def axis_thousands(fig: go.Figure, axis: str, values) -> None:
    """Relabel a rupee axis in thousands.

    Plotly's own SI format jumps straight from k to M, which would contradict
    the "K" on the KPI row, so the tick text is written out. Labels only - the
    plotted values and the hover figures stay in rupees.
    """
    ticks = money_ticks(values)
    if not ticks:
        return
    fig.update_layout(**{f"{axis}axis": dict(
        tickmode="array",
        tickvals=ticks,
        ticktext=[money_k(v) for v in ticks],
    )})


def plot(fig: go.Figure, key: str, height: int | None = None) -> None:
    """Every chart gets its own key - Streamlit refuses duplicate element ids."""
    fig.update_layout(
        height=height or config.DASHBOARD_CHART_HEIGHT,
        margin=dict(l=10, r=10, t=48, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=config.FONT_FAMILY, color=config.TEXT_COLOR, size=12),
        title=dict(font=dict(size=13.5, color=config.TEXT_COLOR), x=0, xanchor="left"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=config.BORDER_COLOR,
                   ticks="outside", tickcolor=config.BORDER_COLOR),
        yaxis=dict(gridcolor=config.GRID_COLOR, zeroline=False, linecolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="white", bordercolor=config.BORDER_COLOR,
                        font=dict(color=config.TEXT_COLOR, size=12)),
    )
    st.plotly_chart(fig, key=key, config=PLOT_CONFIG, **CHARTS)



# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading the cleaned ledger...")
def get_data(uploaded_bytes: bytes | None = None) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Read the cleaned CSV produced by the pipeline.

    The uploaded payload is passed in as an argument on purpose so it becomes
    part of the cache key - reading session state inside a cached function
    would silently serve stale data.
    """
    if uploaded_bytes:
        raw = pd.read_csv(io.BytesIO(uploaded_bytes), dtype="string")
        clean, _ = clean_expenses(raw)
        return clean, None

    if not Path(config.CLEAN_CSV_PATH).exists():
        return pd.DataFrame(), None

    df = load_clean_data()
    income_path = Path(config.CLEAN_INCOME_CSV_PATH)
    income = load_income() if income_path.exists() else None
    return df, income


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Every filter the dashboard offers, all working on the same frame.

    Each multi-select defaults to *empty*, which means "no restriction". The
    earlier version pre-selected every value, so the sidebar rendered nineteen
    red chips and read as though everything was already filtered.
    """
    st.sidebar.markdown(
        f'<div class="section" style="margin-top:0">Filters</div>', unsafe_allow_html=True
    )

    months = sorted(df["year_month"].unique())
    picked_months = st.sidebar.select_slider(
        "Month range",
        options=months,
        value=(months[0], months[-1]),
        key="months_range",
    ) if months else None

    categories = sorted(df["category"].unique())
    picked_categories = st.sidebar.multiselect(
        "Category", categories, default=[], key="filter_categories",
        placeholder="All categories",
    )

    segments = sorted(df["user_segment"].dropna().unique()) if "user_segment" in df else []
    picked_segments = st.sidebar.multiselect(
        "User segment", segments, default=[], key="filter_segments",
        placeholder="All segments",
    )

    payments = sorted(df["payment_method"].unique())
    picked_payments = st.sidebar.multiselect(
        "Payment method", payments, default=[], key="filter_payments",
        placeholder="All methods",
    )

    if not any([picked_categories, picked_segments, picked_payments]) and (
        not picked_months or (picked_months[0] == months[0] and picked_months[1] == months[-1])
    ):
        st.sidebar.caption("No filters applied - showing every transaction.")

    view = df
    if picked_months:
        view = view[(view["year_month"] >= picked_months[0]) & (view["year_month"] <= picked_months[1])]
    if picked_categories:
        view = view[view["category"].isin(picked_categories)]
    if picked_segments and "user_segment" in view:
        view = view[view["user_segment"].isin(picked_segments)]
    if picked_payments:
        view = view[view["payment_method"].isin(picked_payments)]

    st.sidebar.caption(f"{len(view):,} of {len(df):,} transactions shown ({len(view) / max(1, len(df)) * 100:.1f}%)")
    return view


def sidebar_upload() -> None:
    st.sidebar.markdown('<div class="section">Source data</div>', unsafe_allow_html=True)
    upload = st.sidebar.file_uploader(
        "Upload a raw expenses CSV", type=["csv"], key="uploader"
    )
    if upload is not None:
        payload = upload.getvalue()
        if st.session_state.get("uploaded_bytes") != payload:
            st.session_state["uploaded_bytes"] = payload
            st.cache_data.clear()
            st.rerun()
        st.sidebar.success(f"Loaded and cleaned your export ({len(pd.read_csv(io.BytesIO(payload))):,} raw rows)")
    elif st.session_state.get("uploaded_bytes"):
        if st.sidebar.button("Reset to the bundled dataset", key="reset_upload"):
            st.session_state.pop("uploaded_bytes", None)
            st.cache_data.clear()
            st.rerun()
    else:
        st.sidebar.caption("Bundled synthetic ledger. Drop in your own export to replace it.")


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
def tab_overview(df: pd.DataFrame, results: dict) -> None:
    o = results["overview"]
    anomalies = results["anomalies"]
    monthly = results["monthly"]

    if monthly["savings_rate_pct"].notna().any():
        savings_rate = monthly["savings"].sum() / monthly["income"].sum() * 100
    else:
        savings_rate = None

    cols = st.columns(6)
    cards = [
        ("Total spend", money_compact(o["total_spend"]), f"{o['transactions']:,} transactions", "flat"),
        ("Spend / user / month", money(o["avg_monthly_spend_per_user"]),
         f"budget {money(o['monthly_budget_per_user'])}",
         "up" if o["avg_monthly_spend_per_user"] > o["monthly_budget_per_user"] else "down"),
        ("Average transaction", money(o["avg_transaction"]), f"{o['categories']} categories", "flat"),
        ("Savings rate", f"{savings_rate:+.1f}%" if savings_rate is not None else "n/a",
         f"income {money(o['avg_monthly_income_per_user'])}" if o["avg_monthly_income_per_user"] else "",
         "down" if (savings_rate or 0) >= 0 else "up"),
        ("30-day burn rate", money_compact(anomalies["burn_rate_30d_per_user"]),
         f"{anomalies['burn_vs_variable_budget_pct']:.0f}% of variable budget",
         "up" if anomalies["burn_vs_variable_budget_pct"] > 100 else "down"),
        ("Overspend alerts", f"{anomalies['user_day_anomalies']}",
         f"{anomalies['users_flagged']} users flagged", "flat"),
    ]
    for col, (label, value, delta, direction) in zip(cols, cards):
        with col:
            st.markdown(kpi(label, value, delta, direction), unsafe_allow_html=True)

    st.markdown("---")

    top = results["category"].iloc[0]
    worst = results["budget"].iloc[0]
    peak = monthly.loc[monthly["total_spend"].idxmax()]
    pareto = results["pareto"]
    insight(f"<b>{top['category']}</b> is the biggest category at <b>{top['share_pct']:.1f}%</b> of spend "
            f"({money(top['total_spend'])}).", "violet")
    insight(f"<b>{worst['category']}</b> is the worst budget overrun at <b>{worst['variance_pct']:+.0f}%</b> "
            f"({money(worst['variance'])} per user per month).", "rose")
    insight(f"<b>{peak['year_month']}</b> was the peak month at {money(peak['total_spend'])} — "
            f"festival demand, not a data error.", "amber")
    if len(pareto):
        insight(f"<b>{len(pareto)} of {len(results['category'])} categories</b> account for "
                f"{pareto['cumulative_pct'].iloc[-1]:.0f}% of every rupee spent — start the budget review there.", "teal")
    else:
        # a narrow filter can leave too few categories to cross the Pareto cut
        insight(f"Only <b>{len(results['category'])} categor{'y' if len(results['category']) == 1 else 'ies'}</b> "
                f"in view — clear the filters to see the full concentration picture.", "teal")

    left, right = st.columns([1.25, 1])
    with left:
        data = results["category"].sort_values("total_spend")
        fig = px.bar(
            data, x="total_spend", y="category", orientation="h",
            color="category", color_discrete_map=category_colors(results["category"]),
            text=data["share_pct"].map(lambda v: f"{v:.1f}%"),
            title="Category share of total spend",
            labels={"total_spend": "Total spend", "category": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False)
        fig.update_xaxes(range=[0, float(data["total_spend"].max()) * 1.14])
        axis_thousands(fig, "x", data["total_spend"])
        plot(fig, "overview_category_bar")
    with right:
        cat = results["category"]
        fig = px.pie(
            cat, names="category", values="total_spend", hole=0.56,
            color="category", color_discrete_map=category_colors(cat),
            title="Category mix",
        )
        # the ramp runs dark-to-light in rank order, so the only slices big
        # enough to carry white labels are the dark ones
        labels = [f"{p:.1f}%" if p >= 6 else "" for p in cat["share_pct"]]
        fig.update_traces(text=labels, textinfo="text", textposition="inside",
                          insidetextfont=dict(color="white", size=11.5))
        fig.update_layout(
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left",
                        x=1.0, font=dict(size=10.5)),
            margin=dict(t=48, b=10, l=10, r=10), height=config.DASHBOARD_CHART_HEIGHT,
        )
        st.plotly_chart(fig, key="overview_donut", config=PLOT_CONFIG, **CHARTS)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["year_month"], y=monthly["total_spend"], name="Total spend",
        mode="lines+markers", line=dict(color=config.PALETTE["primary"], width=2.6),
    ))
    fig.add_trace(go.Scatter(
        x=monthly["year_month"], y=monthly["rolling_3m_avg"], name="3-month average",
        mode="lines", line=dict(color=config.PALETTE["sky"], width=1.6, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=monthly["year_month"], y=monthly["budget"], name="Budget",
        mode="lines", line=dict(color=config.PALETTE["slate"], width=1.6, dash="dot"),
    ))
    fig.update_layout(title="Monthly spend against budget",
                      xaxis_title="", yaxis_title="Spend")
    axis_thousands(fig, "y", monthly["total_spend"])
    plot(fig, "overview_monthly_line")

    with st.expander("Show the results table"):
        show = results["category"][[
            "rank", "category", "total_spend", "share_pct", "cumulative_pct",
            "transactions", "avg_transaction", "monthly_budget", "avg_monthly_per_user", "budget_variance_pct",
        ]].rename(columns={
            "rank": "#", "category": "Category", "total_spend": "Total spend",
            "share_pct": "Share %", "cumulative_pct": "Cumulative %", "transactions": "Txns",
            "avg_transaction": "Avg txn", "monthly_budget": "Budget / month",
            "avg_monthly_per_user": "Actual / user / month", "budget_variance_pct": "Variance %",
        })
        st.dataframe(show, hide_index=True, key="overview_table", **CHARTS)


def tab_categories(df: pd.DataFrame, results: dict) -> None:
    budget = results["budget"]
    cat = results["category"]

    left, right = st.columns([1.1, 1])
    with left:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=budget["category"], x=budget["monthly_budget"], name="Budget",
            orientation="h", marker_color=config.PALETTE["slate"],
        ))
        colors = budget["variance_pct"].map(
            lambda v: config.PALETTE["rose"] if v > config.BUDGET_TOLERANCE_PCT
            else config.PALETTE["emerald"] if v < -config.BUDGET_TOLERANCE_PCT
            else config.PALETTE["slate"]
        )
        fig.add_trace(go.Bar(
            y=budget["category"], x=budget["avg_monthly_per_user"], name="Actual (per user)",
            orientation="h", marker_color=colors,
        ))
        fig.update_layout(
            barmode="group", title="Budget vs actual per user",
            xaxis_title="Per-user monthly amount", yaxis_title="",
        )
        axis_thousands(fig, "x", pd.concat([budget["monthly_budget"], budget["avg_monthly_per_user"]]))
        plot(fig, "categories_budget_grouped", height=520)
    with right:
        fig = px.bar(
            budget.sort_values("variance_pct"), x="variance_pct", y="category", orientation="h",
            color="status",
            color_discrete_map={"Over budget": config.PALETTE["rose"], "On track": config.PALETTE["slate"],
                                "Under budget": config.PALETTE["emerald"]},
            title="Budget variance % by category",
            labels={"variance_pct": "Variance %", "category": "", "status": ""},
        )
        fig.add_vline(x=0, line_color=config.MUTED_COLOR, line_width=1)
        plot(fig, "categories_variance_bar", height=520)

    fig = px.treemap(
        cat, path=[px.Constant("All categories"), "category"], values="total_spend",
        color="share_pct", color_continuous_scale=["#d7efe9", "#5bbba9", "#0b4f4a"],
        title="Where the money goes - treemap sized by spend",
    )
    fig.update_traces(textinfo="label+percent parent")
    fig.update_layout(coloraxis_showscale=False)
    plot(fig, "categories_treemap", height=500)

    st.markdown('<div class="section">Merchant leaders inside each category</div>', unsafe_allow_html=True)
    leaders = pd.DataFrame(
        [{"Category": k, "Top merchant": v} for k, v in results["category_leaders"].items()]
    )
    st.dataframe(leaders, hide_index=True, key="category_leaders_table", **CHARTS)


def tab_trends(df: pd.DataFrame, results: dict) -> None:
    monthly = results["monthly"]
    anomalies = results["anomalies"]

    has_income = monthly["savings_rate_pct"].notna().any()
    if has_income:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly["year_month"], y=monthly["income"], name="Income",
                             marker_color=config.PALETTE["slate"]))
        fig.add_trace(go.Bar(x=monthly["year_month"], y=monthly["total_spend"], name="Spend",
                             marker_color=config.PALETTE["primary"]))
        fig.add_trace(go.Scatter(x=monthly["year_month"], y=monthly["savings"], name="Savings",
                                 mode="lines+markers", line=dict(color=config.PALETTE["emerald"], width=2.6)))
        fig.update_layout(barmode="group", title="Income against spend, with savings",
                          xaxis_title="", yaxis_title="Amount")
        axis_thousands(fig, "y", pd.concat([monthly["income"], monthly["total_spend"]]))
        plot(fig, "trends_income_spend", height=460)

        colors = monthly["savings_rate_pct"].map(
            lambda v: config.PALETTE["emerald"] if v >= 0 else config.PALETTE["rose"]
        )
        fig = go.Figure(go.Bar(
            x=monthly["year_month"], y=monthly["savings_rate_pct"],
            marker_color=colors, name="Savings rate",
            text=monthly["savings_rate_pct"].map(lambda v: f"{v:+.1f}%"), textposition="outside",
        ))
        fig.update_layout(title="Savings rate by month", xaxis_title="", yaxis_title="Savings rate %")
        fig.add_hline(y=0, line_color=config.MUTED_COLOR, line_width=1)
        plot(fig, "trends_savings_rate", height=420)
    else:
        insight("No income file alongside this export, so the savings views are hidden.", "amber")

    daily = anomalies["daily"].copy()
    daily["date"] = pd.to_datetime(daily["date"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["total_spend"], name="Daily spend", mode="lines",
        line=dict(color="#cbd5e1", width=1),
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["rolling_avg"], name=f"{config.ROLLING_WINDOW_DAYS}-day average",
        mode="lines", line=dict(color=config.PALETTE["primary"], width=2.6),
    ))
    flagged_dates = pd.to_datetime(pd.Series(anomalies["flagged_dates"], dtype="string"), errors="coerce").dropna()
    hits = daily[daily["date"].isin(flagged_dates)]
    fig.add_trace(go.Scatter(
        x=hits["date"], y=hits["total_spend"], name="Day with a flagged user",
        mode="markers", marker=dict(color=config.PALETTE["rose"], size=9, line=dict(color="white", width=1.2)),
    ))
    fig.update_layout(title=f"Spend timeline - {anomalies['user_day_anomalies']} abnormal user-days",
                      xaxis_title="", yaxis_title="Daily spend")
    axis_thousands(fig, "y", daily["total_spend"])
    plot(fig, "trends_anomaly_timeline", height=470)

    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="section">Month-over-month change</div>', unsafe_allow_html=True)
        mom = monthly[["year_month", "total_spend", "mom_change_pct", "savings_rate_pct"]].copy()
        mom = mom.rename(columns={
            "year_month": "Month", "total_spend": "Spend",
            "mom_change_pct": "MoM %", "savings_rate_pct": "Savings rate %",
        }).round(2)
        st.dataframe(mom, hide_index=True, key="trends_mom_table", **CHARTS)
    with right:
        st.markdown('<div class="section">Most extreme user-days</div>', unsafe_allow_html=True)
        top = anomalies["top_user_days"].head(8).copy()
        top["day"] = pd.to_datetime(top["day"]).dt.strftime("%Y-%m-%d")
        top = top.rename(columns={"day": "Date", "user_id": "User", "spend": "Spend",
                                  "user_median": "Their median day", "z_score": "Robust z",
                                  "transactions": "Txns"})
        st.dataframe(top[["Date", "User", "Spend", "Their median day", "Robust z", "Txns"]].round(2),
                     hide_index=True, key="trends_anomaly_table", **CHARTS)


def tab_patterns(df: pd.DataFrame, results: dict) -> None:
    patterns = results["patterns"]

    left, right = st.columns([1.15, 1])
    with left:
        weekday = patterns["weekday_spend"].reset_index()
        weekday.columns = ["Weekday", "Spend"]
        weekday["is_weekend"] = weekday["Weekday"].isin(["Saturday", "Sunday"])
        fig = px.bar(
            weekday, x="Weekday", y="Spend", color="is_weekend",
            color_discrete_map={True: config.PALETTE["primary"], False: "#cbd5e1"},
            title=f"Spend by day of week - weekends are {patterns['weekend_share_pct']:.1f}% of spend",
            labels={"is_weekend": "Weekend"},
        )
        fig.update_layout(showlegend=False, xaxis_title="")
        axis_thousands(fig, "y", weekday["Spend"])
        plot(fig, "patterns_weekday", height=440)
    with right:
        payment = patterns["payment_spend"].reset_index()
        payment.columns = ["Method", "Spend"]
        fig = px.pie(
            payment, names="Method", values="Spend", hole=0.5,
            color_discrete_sequence=list(config.CATEGORY_COLORS_DARK),
            title=f"Payment mix - {patterns['top_payment']} leads",
        )
        shares = payment["Spend"] / payment["Spend"].sum() * 100
        fig.update_traces(text=[f"{s:.1f}%" if s >= 4 else "" for s in shares],
                          textinfo="text", textposition="inside",
                          insidetextfont=dict(color="white", size=11))
        fig.update_layout(
            title=dict(text=f"Payment mix - {patterns['top_payment']} leads", y=0.98),
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.0,
                        font=dict(size=10.5)),
            margin=dict(t=48, b=10, l=10, r=10), height=440,
        )
        st.plotly_chart(fig, key="patterns_payment_pie", config=PLOT_CONFIG, **CHARTS)

    left, right = st.columns([1, 1])
    with left:
        bucket = patterns["hour_bucket_spend"].reset_index()
        bucket.columns = ["Time of day", "Spend"]
        fig = px.bar(
            bucket, x="Time of day", y="Spend",
            title=f"Spend by time of day - {patterns['busiest_bucket']} is busiest",
        )
        fig.update_traces(marker_color=config.PALETTE["primary"])
        fig.update_layout(showlegend=False, xaxis_title="")
        axis_thousands(fig, "y", bucket["Spend"])
        plot(fig, "patterns_hour_bucket", height=430)
    with right:
        merchants = results["merchants"].head(10).sort_values("total_spend")
        fig = px.bar(
            merchants, x="total_spend", y="merchant", orientation="h",
            title="Top merchants by value (fixed bills excluded)",
            labels={"total_spend": "Total spend", "merchant": ""},
            hover_data={"transactions": True, "category": True},
        )
        fig.update_traces(marker_color=config.PALETTE["primary"])
        fig.update_layout(showlegend=False)
        axis_thousands(fig, "x", merchants["total_spend"])
        plot(fig, "patterns_merchants", height=430)

    seg = results["segments"].copy()
    seg["user_share_pct"] = seg["users"] / seg["users"].sum() * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(x=seg["user_segment"], y=seg["share_pct"], name="Share of spend",
                         marker_color=config.PALETTE["primary"]))
    fig.add_trace(go.Bar(x=seg["user_segment"], y=seg["user_share_pct"], name="Share of users",
                         marker_color="#cbd5e1"))
    fig.update_layout(barmode="group", title="Who drives the spend - share of wallet vs share of users",
                      yaxis_title="Percent", xaxis_title="")
    plot(fig, "patterns_segments", height=430)


def tab_data(df: pd.DataFrame, results: dict) -> None:
    st.markdown('<div class="section">Cleaned transactions</div>', unsafe_allow_html=True)
    st.caption(f"{len(df):,} rows after filters - download or inspect below.")

    left, right, third = st.columns([1, 1, 1])
    with left:
        st.download_button(
            "Filtered transactions (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="expenses_filtered.csv",
            mime="text/csv",
            key="download_filtered",
            **CHARTS,
        )
    with right:
        if Path(config.INSIGHTS_MD_PATH).exists():
            st.download_button(
                "Insight report (Markdown)",
                data=Path(config.INSIGHTS_MD_PATH).read_bytes(),
                file_name="insights_report.md",
                mime="text/markdown",
                key="download_report",
                **CHARTS,
            )
    with third:
        # the same summaries as a tidy table with every amount in thousands
        st.download_button(
            "Summary, amounts in thousands (CSV)",
            data=insights.summary_frame(results).to_csv(index=False).encode("utf-8"),
            file_name="summary_in_thousands.csv",
            mime="text/csv",
            key="download_summary_thousands",
            **CHARTS,
        )

    st.dataframe(df.head(500), hide_index=True, key="data_preview", **CHARTS)

    st.markdown('<div class="section">Largest single transactions</div>', unsafe_allow_html=True)
    top = results["top_transactions"].copy()
    top["date"] = pd.to_datetime(top["date"]).dt.strftime("%Y-%m-%d")
    st.dataframe(top, hide_index=True, key="top_transactions_table", **CHARTS)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    inject_css()

    df, income = get_data(st.session_state.get("uploaded_bytes"))
    if df.empty:
        report_head(None)
        st.warning(
            "No cleaned dataset found. Run **`python main.py all`** first, "
            "or upload a raw expenses CSV from the sidebar."
        )
        sidebar_upload()
        return

    report_head(df)
    sidebar_upload()
    view = sidebar_filters(df)

    if view.empty:
        st.warning("No transactions match the current filters. Widen them in the sidebar.")
        return

    results = analysis.full_analysis(view, income if income is not None else None)

    tabs = st.tabs(["Overview", "Categories", "Trends", "Patterns", "Data"])
    with tabs[0]:
        tab_overview(view, results)
    with tabs[1]:
        tab_categories(view, results)
    with tabs[2]:
        tab_trends(view, results)
    with tabs[3]:
        tab_patterns(view, results)
    with tabs[4]:
        tab_data(view, results)

    st.markdown("---")
    st.caption(
        f"{config.PROJECT_NAME} v{config.PROJECT_VERSION} · built by {config.PROJECT_AUTHOR} · "
        f"synthetic data, seed {config.RANDOM_SEED} · "
        f"[GitHub]({config.PROJECT_GITHUB})"
    )


if __name__ == "__main__":
    main()
