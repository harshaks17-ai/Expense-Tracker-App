"""
Synthetic expense data generator.

Rather than shipping a fake CSV, this module *simulates* a realistic personal
finance wallet and then deliberately dirties it, so every cleaning decision can
be scored against a known ground truth (exactly how you would test a real
ingestion pipeline before it ever sees production data).

Simulation model
----------------
1.  50 users, each assigned a spending archetype (heavy / moderate / light).
2.  12 months (2025-10-01 .. 2026-09-30) of transactions across 10 categories.
3.  Transaction counts are derived from each category's monthly budget divided
    by its typical ticket size, so a "moderate" user lands near budget.
4.  Two festival months get a spend spike - the trend chart has a story.
5.  Monthly income is generated alongside, scaled by the same archetype, so
    the savings rate is meaningful rather than random.

Author: Harsha K S
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import config
from src.utils import ensure_directories, relative, setup_logging

LOGGER = setup_logging()

DESC_TEMPLATES = {
    "Food & Dining": ("lunch order", "dinner delivery", "coffee run", "weekend brunch", "snacks"),
    "Groceries": ("weekly groceries", "monthly stock-up", "fruits & veg", "household items"),
    "Transport": ("cab to office", "fuel refill", "metro top-up", "auto ride", "toll"),
    "Rent & Utilities": ("monthly rent", "electricity bill", "broadband bill", "water bill", "gas refill"),
    "Shopping": ("online order", "apparel purchase", "electronics", "footwear", "home decor"),
    "Entertainment": ("streaming subscription", "movie tickets", "concert", "music subscription"),
    "Health": ("pharmacy", "doctor consultation", "gym membership", "lab test", "supplements"),
    "Education": ("online course", "books", "workshop fee", "subscription"),
    "Travel": ("train tickets", "flight booking", "hotel stay", "road trip fuel", "cab at destination"),
    "Miscellaneous": ("gift", "salon visit", "donation", "pet supplies", "courier"),
}


def _user_profiles(rng: np.random.Generator, n_users: int = config.N_USERS) -> pd.DataFrame:
    """Assign each user a spending archetype and a correlated income level."""
    n_heavy = int(round(n_users * config.HEAVY_SPENDER_SHARE))
    n_light = int(round(n_users * config.LIGHT_SPENDER_SHARE))
    n_moderate = n_users - n_heavy - n_light

    multipliers = np.concatenate(
        [
            np.full(n_heavy, config.HEAVY_MULTIPLIER),
            np.full(n_moderate, 1.0),
            np.full(n_light, config.LIGHT_MULTIPLIER),
        ]
    )
    rng.shuffle(multipliers)

    labels = np.where(
        multipliers >= config.HEAVY_MULTIPLIER,
        "Heavy spender",
        np.where(multipliers <= config.LIGHT_MULTIPLIER, "Light spender", "Moderate spender"),
    )

    # Income moves with spending so the savings-rate chart is not nonsense.
    income = config.INCOME_BASE * (0.6 + 0.4 * multipliers)

    return pd.DataFrame(
        {
            "user_id": [f"U{i + 1:03d}" for i in range(n_users)],
            "spend_multiplier": multipliers,
            "user_segment": labels,
            "monthly_income": income,
        }
    )


def _month_factor(month: str) -> float:
    """Seasonal multiplier: festival spike months spend more, summer less."""
    if month in config.SPIKE_MONTHS:
        return config.SPIKE_MULTIPLIER
    if month.endswith("-05") or month.endswith("-06"):  # summer travel lull
        return 0.9
    return 1.0


def _expected_count(category: str) -> float:
    """Transactions a moderate user makes per month in this category.

    Derived from budget / typical ticket size so the simulation is
    self-consistent: moderate users land roughly on budget.
    """
    low, high = config.CATEGORY_TX_RANGE[category]
    mid = (low + high) / 2
    return max(1.0, config.CATEGORY_BUDGETS[category] / mid)


def generate_transactions(rng: np.random.Generator | None = None) -> pd.DataFrame:
    """Simulate the clean expense ledger."""
    rng = rng or np.random.default_rng(config.RANDOM_SEED)
    profiles = _user_profiles(rng)

    start = pd.Timestamp(config.WINDOW_START)
    end = pd.Timestamp(config.WINDOW_END)
    months = pd.period_range(start, end, freq="M")

    rows: list[dict] = []
    txn_counter = 0

    for _, user in profiles.iterrows():
        user_multiplier = user["spend_multiplier"]
        # Every user has their own bill due date, exactly like real life.
        # Without this every rent payment lands in the first five days of the
        # month and the daily spend series becomes one spike per month.
        rent_day = int(rng.integers(1, 29))

        for period in months:
            month_label = str(period)
            month_start = period.to_timestamp()
            days_in_month = period.days_in_month
            factor = _month_factor(month_label)

            for category in config.CATEGORY_BUDGETS:
                if category in config.FIXED_MONTHLY_CATEGORIES:
                    n_tx = 1
                else:
                    lam = _expected_count(category) * user_multiplier * factor
                    n_tx = int(rng.poisson(lam))

                if n_tx <= 0:
                    continue

                low, high = config.CATEGORY_TX_RANGE[category]
                if category in config.FIXED_MONTHLY_CATEGORIES:
                    # Rent sits close to its budget, not spread over the range.
                    amounts = rng.uniform(
                        0.95 * config.CATEGORY_BUDGETS[category],
                        1.06 * config.CATEGORY_BUDGETS[category],
                        size=n_tx,
                    )
                else:
                    # Right-skewed amounts: many small purchases, few large ones.
                    amounts = rng.triangular(low, low + (high - low) * 0.35, high, size=n_tx)
                    amounts = amounts * user_multiplier

                for amount in amounts:
                    txn_counter += 1
                    if category in config.FIXED_MONTHLY_CATEGORIES:
                        day = min(rent_day, days_in_month)
                        hour = int(rng.integers(9, 18))
                    else:
                        # Weekend bias: pick a weekend with the category's
                        # probability, otherwise a weekday. This is what makes
                        # the day-of-week chart show a real pattern.
                        weekends = [
                            d for d in range(1, days_in_month + 1)
                            if pd.Timestamp(year=month_start.year, month=month_start.month, day=d).dayofweek >= 5
                        ]
                        weekdays = [
                            d for d in range(1, days_in_month + 1)
                            if d not in weekends
                        ]
                        weekend_p = config.WEEKEND_PROBABILITY.get(category, 0.29)
                        if weekends and rng.random() < weekend_p:
                            day = int(rng.choice(weekends))
                        else:
                            day = int(rng.choice(weekdays))
                        hour = int(
                            rng.choice(
                                config.PEAK_HOURS if rng.random() < 0.65 else config.OTHER_HOURS
                            )
                        )
                    minute = int(rng.integers(0, 60))

                    merchant = rng.choice(config.CATEGORY_MERCHANTS[category])
                    payment = rng.choice(config.PAYMENT_METHODS, p=config.PAYMENT_WEIGHTS)
                    description = rng.choice(DESC_TEMPLATES[category])

                    rows.append(
                        {
                            "transaction_id": f"TXN{txn_counter:06d}",
                            "user_id": user["user_id"],
                            "date": month_start
                            + pd.Timedelta(days=day - 1, hours=hour, minutes=minute),
                            "category": category,
                            "merchant": str(merchant),
                            "amount": round(float(amount), 2),
                            "payment_method": str(payment),
                            "description": description,
                            "user_segment": user["user_segment"],
                            "monthly_income": round(float(user["monthly_income"]), 2),
                        }
                    )

    return pd.DataFrame(rows)


def _random_mask(rng: np.random.Generator, size: int, rate: float) -> np.ndarray:
    return rng.random(size) < rate


def inject_noise(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Dirty the clean ledger and return (dirty data, injected-issue counts)."""
    rng = np.random.default_rng(config.RANDOM_SEED + 7)
    dirty = data.copy()
    n = len(dirty)
    counts: dict[str, int] = {}

    # 1. Exact duplicates - re-exported rows that slipped into the file.
    n_dupes = int(round(config.DIRTY_DUPLICATE_RATE * n))
    if n_dupes:
        dupes = dirty.sample(n=n_dupes, random_state=config.RANDOM_SEED)
        dirty = pd.concat([dirty, dupes], ignore_index=True)
    counts["duplicates"] = n_dupes
    n = len(dirty)

    # 2. Missing values - blank amount or blank category.
    blank_amount = _random_mask(rng, n, config.DIRTY_MISSING_RATE) & dirty["amount"].notna()
    blank_category = _random_mask(rng, n, config.DIRTY_MISSING_RATE) & dirty["category"].notna()
    dirty.loc[blank_amount, "amount"] = np.nan
    dirty.loc[blank_category, "category"] = np.nan
    counts["blank_amount"] = int(blank_amount.sum())
    counts["blank_category"] = int(blank_category.sum())

    # 3. Amounts stored as display strings ("Rs. 1,200.50") - object dtype keeps
    #    the numeric rows untouched, which is what a messy CSV really looks like.
    str_mask = _random_mask(rng, n, config.DIRTY_AMOUNT_STRING_RATE) & dirty["amount"].notna()
    numeric = pd.to_numeric(dirty.loc[str_mask, "amount"], errors="coerce")
    formatted = np.where(
        rng.random(str_mask.sum()) < 0.5,
        "Rs. " + numeric.map(lambda v: f"{v:,.2f}"),
        numeric.map(lambda v: f"{v:,.0f}"),
    )
    dirty["amount"] = dirty["amount"].astype(object)
    dirty.loc[str_mask, "amount"] = formatted
    counts["amount_as_string"] = int(str_mask.sum())

    # 4. Category casing and spelling drift.
    case_mask = _random_mask(rng, n, config.DIRTY_CATEGORY_CASE_RATE) & dirty["category"].notna()
    style_draw = rng.random(int(case_mask.sum()))
    idx = dirty.index[case_mask]
    labels = dirty.loc[idx, "category"].astype(str)
    for style, pick in (
        ("lower", style_draw < 0.34),
        ("upper", (style_draw >= 0.34) & (style_draw < 0.67)),
        ("title", style_draw >= 0.67),
    ):
        if not pick.any():
            continue
        subset = labels[pick]
        restyled = (
            subset.str.lower()
            if style == "lower"
            else subset.str.upper()
            if style == "upper"
            else subset.str.title()
        )
        dirty.loc[idx[pick], "category"] = restyled
    counts["category_casing"] = int(case_mask.sum())

    # 5. Unknown / out-of-scope category tokens.
    unk_mask = _random_mask(rng, n, config.DIRTY_UNKNOWN_CATEGORY_RATE) & dirty["category"].notna()
    dirty.loc[unk_mask, "category"] = rng.choice(
        ["Others", "N/A", "misc", "unknown", "-"], size=int(unk_mask.sum())
    )
    counts["unknown_category"] = int(unk_mask.sum())

    # 6. Leading/trailing whitespace on every text column.
    ws_mask = _random_mask(rng, n, config.DIRTY_WHITESPACE_RATE)
    for col in ("category", "merchant", "payment_method", "description", "user_segment"):
        if col not in dirty.columns:
            continue
        text = dirty[col].astype("string")
        padded = " " + text.fillna("") + " "
        dirty.loc[ws_mask, col] = padded[ws_mask]
    counts["whitespace"] = int(ws_mask.sum()) * 5

    # 7. Impossible values: zero, negative and fat-finger amounts.
    zero_mask = _random_mask(rng, n, config.DIRTY_ZERO_OR_NEGATIVE_RATE) & dirty["amount"].notna()
    zero_idx = dirty.index[zero_mask]
    half = rng.random(len(zero_idx)) < 0.5
    dirty.loc[zero_idx[half], "amount"] = 0.0
    dirty.loc[zero_idx[~half], "amount"] = -1.0
    counts["zero_or_negative"] = int(zero_mask.sum())

    outlier_mask = _random_mask(rng, n, config.DIRTY_OUTLIER_RATE) & dirty["amount"].notna()
    dirty.loc[outlier_mask, "amount"] = rng.uniform(120_000, 450_000, size=int(outlier_mask.sum()))
    counts["impossible_outlier"] = int(outlier_mask.sum())

    # 8. Future-dated transactions - the classic "someone typed 2027" error.
    future_mask = _random_mask(rng, n, config.DIRTY_FUTURE_DATE_RATE)
    dirty.loc[future_mask, "date"] = dirty.loc[future_mask, "date"] + pd.Timedelta(days=400)
    counts["future_date"] = int(future_mask.sum())

    # 9. Mixed date formats. The column MUST become text first, otherwise
    #    pandas silently re-coerces "14/10/2025" straight back to a timestamp.
    dates = pd.to_datetime(dirty["date"], errors="coerce")
    dirty["date"] = dates.dt.strftime("%Y-%m-%d %H:%M:%S").astype("string")
    alt = _random_mask(rng, n, config.DIRTY_DATE_FORMAT_RATE) & dates.notna()
    alt_dates = dates[alt]
    pick = rng.random(int(alt.sum())) < 0.5
    out = pd.Series(index=alt_dates.index, dtype="string")
    out[pick] = alt_dates[pick].dt.strftime("%d/%m/%Y %H:%M")
    out[~pick] = alt_dates[~pick].dt.strftime("%b %d, %Y %I:%M %p")
    dirty.loc[alt, "date"] = out
    counts["mixed_date_format"] = int(alt.sum())

    dirty = dirty.reset_index(drop=True)
    LOGGER.info(
        "Injected noise: %s duplicates, %s blank amounts, %s blank categories, "
        "%s casing, %s whitespace, %s amount strings, %s zero/negative, "
        "%s outliers, %s unknown categories, %s mixed dates, %s future dates",
        f"{counts['duplicates']:,}",
        counts["blank_amount"],
        counts["blank_category"],
        counts["category_casing"],
        counts["whitespace"],
        counts["amount_as_string"],
        counts["zero_or_negative"],
        counts["impossible_outlier"],
        counts["unknown_category"],
        counts["mixed_date_format"],
        counts["future_date"],
    )
    return dirty, counts


def generate_and_save() -> tuple[pd.DataFrame, dict[str, int]]:
    """Generate, dirty and persist the raw expense + income files."""
    ensure_directories()

    clean = generate_transactions()
    LOGGER.info(
        "Generated %s clean transactions for %s users",
        f"{len(clean):,}",
        clean["user_id"].nunique(),
    )

    dirty, counts = inject_noise(clean)
    dirty.to_csv(config.RAW_CSV_PATH, index=False)
    LOGGER.info("Raw expense export saved -> %s", relative(config.RAW_CSV_PATH))

    income = (
        clean.assign(month=clean["date"].dt.strftime("%Y-%m"))
        .groupby(["user_id", "month"], as_index=False)
        .agg(income_amount=("monthly_income", "first"))
    )
    income.to_csv(config.INCOME_CSV_PATH, index=False)
    LOGGER.info("Raw income export saved -> %s", relative(config.INCOME_CSV_PATH))

    return dirty, counts


if __name__ == "__main__":  # pragma: no cover - manual execution
    generate_and_save()
