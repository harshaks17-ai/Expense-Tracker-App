"""
Central configuration for the Expense Tracker App.

Every number, colour, path and rate used anywhere in the project lives here,
so a reviewer can change the simulation with one edit and regenerate all
outputs deterministically.

Author: Harsha K S
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Project metadata
# --------------------------------------------------------------------------- #
PROJECT_NAME = "Expense Tracker App"
PROJECT_VERSION = "1.0.0"
PROJECT_AUTHOR = "Harsha K S"
PROJECT_GITHUB = "https://github.com/harshaks17-ai/Expense-Tracker-App"

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_CSV_PATH = DATA_DIR / "raw" / "expenses_raw.csv"
INCOME_CSV_PATH = DATA_DIR / "raw" / "income_raw.csv"
CLEAN_CSV_PATH = DATA_DIR / "processed" / "expenses_clean.csv"
CLEAN_INCOME_CSV_PATH = DATA_DIR / "processed" / "income_clean.csv"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
CHARTS_DIR = OUTPUT_DIR / "charts"
REPORTS_DIR = OUTPUT_DIR / "reports"
INSIGHTS_MD_PATH = REPORTS_DIR / "insights_report.md"
QUALITY_MD_PATH = REPORTS_DIR / "data_quality_report.md"
SUMMARY_JSON_PATH = REPORTS_DIR / "analysis_summary.json"
SUMMARY_CSV_PATH = REPORTS_DIR / "summary_in_thousands.csv"

IMAGES_DIR = PROJECT_ROOT / "images"
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"

# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #
RANDOM_SEED = 42

# --------------------------------------------------------------------------- #
# Simulation design
# --------------------------------------------------------------------------- #
N_USERS = 50
N_MONTHS = 12

# The 12-month window the simulation covers (inclusive).
WINDOW_START = "2025-10-01"
WINDOW_END = "2026-09-30"

# Monthly household income the users "earn" - used for the savings rate.
INCOME_BASE = 68_000.0
INCOME_NOISE_PCT = 0.06

CURRENCY = "INR"
CURRENCY_SYMBOL = "\u20b9"  # INR sign

# --------------------------------------------------------------------------- #
# Expense taxonomy: category -> monthly budget (INR) and realistic merchants
# --------------------------------------------------------------------------- #
CATEGORY_BUDGETS: dict[str, float] = {
    "Food & Dining": 8_000.0,
    "Groceries": 5_000.0,
    "Transport": 4_000.0,
    "Rent & Utilities": 18_000.0,
    "Shopping": 6_000.0,
    "Entertainment": 2_500.0,
    "Health": 2_000.0,
    "Education": 1_500.0,
    "Travel": 5_000.0,
    "Miscellaneous": 1_500.0,
}

CATEGORY_MERCHANTS: dict[str, tuple[str, ...]] = {
    "Food & Dining": ("Swiggy", "Zomato", "Starbucks", "Dominos", "Local Cafe"),
    "Groceries": ("BigBasket", "DMart", "Blinkit", "Reliance Fresh", "More Retail"),
    "Transport": ("Uber", "Ola", "Petrol Pump", "Metro Card", "Fastag"),
    "Rent & Utilities": ("Landlord", "BESCOM", "ACT Fibernet", "Water Board", "Gas Agency"),
    "Shopping": ("Amazon", "Flipkart", "Myntra", "Decathlon", "Croma"),
    "Entertainment": ("Netflix", "Spotify", "PVR Cinemas", "BookMyShow", "Prime Video"),
    "Health": ("Apollo Pharmacy", "Practo", "Cult Fit", "Lab Test", "Doctor Visit"),
    "Education": ("Coursera", "Udemy", "Textbook Store", "udemy", "Skillshare"),
    "Travel": ("IRCTC", "MakeMyTrip", "Yatra", "Airbnb", "IndiGo"),
    "Miscellaneous": ("Gift", "Donation", "Salon", "Amazon Pay", "Pet Shop"),
}

# How often each category is bought (relative frequency) and its typical
# transaction size, so the simulation looks like a real wallet, not a uniform
# random walk.
CATEGORY_WEIGHTS: dict[str, float] = {
    "Food & Dining": 0.26,
    "Groceries": 0.13,
    "Transport": 0.15,
    "Rent & Utilities": 0.05,
    "Shopping": 0.11,
    "Entertainment": 0.09,
    "Health": 0.05,
    "Education": 0.04,
    "Travel": 0.05,
    "Miscellaneous": 0.07,
}

CATEGORY_TX_RANGE: dict[str, tuple[float, float]] = {
    "Food & Dining": (120.0, 1_800.0),
    "Groceries": (250.0, 3_500.0),
    "Transport": (30.0, 1_200.0),
    "Rent & Utilities": (4_000.0, 22_000.0),
    "Shopping": (400.0, 9_000.0),
    "Entertainment": (99.0, 2_500.0),
    "Health": (150.0, 4_000.0),
    "Education": (200.0, 5_000.0),
    "Travel": (800.0, 15_000.0),
    "Miscellaneous": (100.0, 3_000.0),
}

# Rent is charged once a month, not randomly - keep it honest.
FIXED_MONTHLY_CATEGORIES = ("Rent & Utilities",)

PAYMENT_METHODS: tuple[str, ...] = (
    "UPI",
    "Credit Card",
    "Debit Card",
    "Cash",
    "Net Banking",
    "Wallet",
)
PAYMENT_WEIGHTS: tuple[float, ...] = (0.42, 0.22, 0.13, 0.11, 0.07, 0.05)

# Spend is skewed to evenings (dinner, rides, streaming).
PEAK_HOURS: tuple[int, ...] = (11, 12, 18, 19, 20, 21, 22)
OTHER_HOURS: tuple[int, ...] = tuple(h for h in range(24) if h not in PEAK_HOURS)

# Equal-width time buckets so the "busiest time of day" claim is not just an
# artefact of uneven bucket sizes.
HOUR_BUCKETS: tuple[tuple[int, int, str], ...] = (
    (0, 4, "Night (0-4)"),
    (5, 9, "Morning (5-9)"),
    (10, 14, "Midday (10-14)"),
    (15, 19, "Evening (15-19)"),
    (20, 23, "Late night (20-23)"),
)

# Probability that a purchase lands on a Saturday/Sunday. 2/7 days are weekends
# (28.6%), so anything above that is a genuine weekend effect. Discretionary
# categories skew to weekends; commuting does the opposite.
WEEKEND_PROBABILITY: dict[str, float] = {
    "Food & Dining": 0.38,
    "Groceries": 0.34,
    "Transport": 0.18,
    "Shopping": 0.40,
    "Entertainment": 0.45,
    "Health": 0.22,
    "Education": 0.25,
    "Travel": 0.42,
    "Miscellaneous": 0.35,
    "Rent & Utilities": 0.30,
}
BASELINE_WEEKEND_SHARE = 2 / 7  # 28.57% if spending were uniform across days

# A small share of users are "big spenders" - creates a realistic long tail.
HEAVY_SPENDER_SHARE = 0.18
LIGHT_SPENDER_SHARE = 0.22
HEAVY_MULTIPLIER = 1.75
LIGHT_MULTIPLIER = 0.55

# A festival / holiday spike so the trend chart has a story to tell.
SPIKE_MONTHS: tuple[str, ...] = ("2025-11", "2026-03")  # Diwali + wedding season
SPIKE_MULTIPLIER = 1.45

# --------------------------------------------------------------------------- #
# Injected dirt - the ground truth the cleaning pipeline is scored against
# --------------------------------------------------------------------------- #
DIRTY_DUPLICATE_RATE = 0.015   # exact duplicate rows
DIRTY_MISSING_RATE = 0.012     # blank amount or blank category
DIRTY_AMOUNT_STRING_RATE = 0.02  # amount stored as "Rs. 1,200.50"
DIRTY_CATEGORY_CASE_RATE = 0.05  # "food & dining", "Food & Dining "
DIRTY_WHITESPACE_RATE = 0.05   # leading/trailing spaces on text columns
DIRTY_DATE_FORMAT_RATE = 0.03  # dd/mm/yyyy and "Oct 14, 2025"
DIRTY_ZERO_OR_NEGATIVE_RATE = 0.004  # amount of 0 or a negative typo
DIRTY_OUTLIER_RATE = 0.003     # amount > 100000, a fat-finger typo
DIRTY_UNKNOWN_CATEGORY_RATE = 0.010  # "Others", "N/A", "misc"
DIRTY_FUTURE_DATE_RATE = 0.005  # a date past the reporting window

# A category is only "out of scope" if it is not in this set after
# normalisation - anything else is mapped, not thrown away.
UNKNOWN_CATEGORY_TOKENS: tuple[str, ...] = ("others", "n/a", "na", "misc", "misc.", "unknown", "null", "-")

# --------------------------------------------------------------------------- #
# Analysis parameters
# --------------------------------------------------------------------------- #
ROLLING_WINDOW_DAYS = 30       # rolling spend window
ANOMALY_Z_THRESHOLD = 2.5      # |z| above this flags an overspend day
ANOMALY_MIN_TX_PER_DAY = 2     # ignore one-off big single purchases
ANOMALY_MIN_USER_DAY_SPEND = 5_000.0  # a flagged user-day must also matter in rupees
PARETO_SHARE = 80.0            # "which categories make 80% of the spend"
BUDGET_TOLERANCE_PCT = 5.0     # within 5% of budget = "on track"

# --------------------------------------------------------------------------- #
# Theme - a restrained report look: ink and greys, one accent hue, and colour
# reserved for meaning. Red only means over budget, green only means under.
# --------------------------------------------------------------------------- #
PALETTE: dict[str, str] = {
    "primary":   "#0f766e",  # teal-700 - the single accent
    "secondary": "#115e59",  # teal-800
    "accent":    "#0e7490",  # cyan-700
    "teal":      "#0d9488",  # teal-600
    "slate":     "#334155",  # slate-700 - neutral series, charts' default grey
    "sky":       "#155e75",
    "amber":     "#b45309",  # amber-700 - warning, used sparingly
    "rose":      "#b91c1c",  # red-700   - over budget / negative only
    "emerald":   "#15803d",  # green-700 - under budget / positive only
    "orange":    "#9a3412",
}

# 10 steps of a single hue, darkest first, so the biggest category reads
# darkest and the chart communicates rank without a rainbow.
CATEGORY_COLORS: tuple[str, ...] = (
    "#0b4f4a", "#0e5f58", "#127066", "#178275", "#1f9584",
    "#35a894", "#5bbba9", "#85cec0", "#b0e0d6", "#d7efe9",
)

# Darker half of the same ramp, for charts that print text on top of a slice.
CATEGORY_COLORS_DARK: tuple[str, ...] = (
    "#0b4f4a", "#0d5b54", "#10675f", "#13736a", "#178275",
    "#1b9080", "#1f9e8b", "#25ac96", "#2bb9a1", "#33c6ac",
)

BG_COLOR = "#ffffff"
PAPER_COLOR = "#ffffff"
TEXT_COLOR = "#111827"
MUTED_COLOR = "#6b7280"
GRID_COLOR = "#eceff3"
BORDER_COLOR = "#e5e7eb"
CANVAS_COLOR = "#fafafa"

FONT_FAMILY = "DejaVu Sans"
TITLE_SIZE = 14
SUBTITLE_SIZE = 10

CHART_DPI = 140
CHART_FORMAT = "png"

# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
DASHBOARD_TITLE = "Expense Tracker App"
DASHBOARD_ICON = "\U0001f4b0"  # money bag
DASHBOARD_LAYOUT = "wide"
DASHBOARD_CHART_WIDTH = 900
DASHBOARD_CHART_HEIGHT = 420
