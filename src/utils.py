"""
Shared helpers: folders, logging, the matplotlib theme and formatting.

Author: Harsha K S
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from src import config

matplotlib.use("Agg")  # headless-safe: never try to open a GUI window

LOGGER = logging.getLogger("expense_tracker")


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the project logger once. Safe to call repeatedly."""
    if not LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)-5s %(message)s", "%H:%M:%S")
        )
        LOGGER.addHandler(handler)
    LOGGER.setLevel(level)
    LOGGER.propagate = False
    return LOGGER


def ensure_directories() -> None:
    """Create every folder the pipeline writes into."""
    for path in (
        config.DATA_DIR,
        config.DATA_DIR / "raw",
        config.DATA_DIR / "processed",
        config.CHARTS_DIR,
        config.REPORTS_DIR,
        config.IMAGES_DIR,
        config.NOTEBOOK_DIR,
    ):
        Path(path).mkdir(parents=True, exist_ok=True)


def apply_matplotlib_theme() -> None:
    """Apply the light-mode theme every static chart inherits."""
    plt.rcParams.update(
        {
            "figure.facecolor": config.BG_COLOR,
            "axes.facecolor": config.PAPER_COLOR,
            "savefig.facecolor": config.BG_COLOR,
            "text.color": config.TEXT_COLOR,
            "axes.labelcolor": config.TEXT_COLOR,
            "xtick.color": config.MUTED_COLOR,
            "ytick.color": config.MUTED_COLOR,
            "axes.edgecolor": config.GRID_COLOR,
            "axes.grid": True,
            "grid.color": config.GRID_COLOR,
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "font.family": config.FONT_FAMILY,
            "font.size": 10,
            "axes.titlesize": config.TITLE_SIZE,
            "axes.titleweight": "bold",
            "axes.titlecolor": config.TEXT_COLOR,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "figure.dpi": config.CHART_DPI,
            "savefig.dpi": config.CHART_DPI,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.25,
        }
    )


def money(value: float, decimals: int = 0) -> str:
    """Format a number as Indian-style currency, e.g. 12345 -> '\\u20b912,345'."""
    sign = "-" if value < 0 else ""
    body = f"{abs(float(value)):,.{decimals}f}"
    return f"{sign}{config.CURRENCY_SYMBOL}{body}"


def _thousands(value: float) -> str:
    """A number expressed in thousands, without a trailing '.0'.

    16_000_000 -> '16,000'; 45_000 -> '45'; 2_500 -> '2.5'
    """
    return f"{value / 1_000:,.1f}".rstrip("0").rstrip(".")


def money_k(value: float) -> str:
    """Compact currency for chart axes and labels, always in thousands.

    45_000 -> '\\u20b945k'; 16_000_000 -> '\\u20b916,000k'. The lakh/crore scale is
    dropped on purpose so every axis on every chart speaks one unit.
    """
    if abs(value) >= 1_000:
        sign = "-" if value < 0 else ""
        return f"{sign}{config.CURRENCY_SYMBOL}{_thousands(abs(value))}k"
    return money(value)


def money_compact(value: float) -> str:
    """Compact currency for KPI tiles, always in thousands.

    37_263_111 -> '\\u20b937,263.1 K'; 44_278 -> '\\u20b944.3 K'; 850 -> '\\u20b9850.00'.
    """
    amount = abs(float(value))
    sign = "-" if value < 0 else ""
    if amount >= 1_000:
        return f"{sign}{config.CURRENCY_SYMBOL}{_thousands(amount)} K"
    return f"{sign}{config.CURRENCY_SYMBOL}{amount:,.2f}"


def pct(value: float, decimals: int = 1) -> str:
    """Format a fraction (0-1) or an already-scaled percentage as a string."""
    scaled = value * 100 if abs(value) <= 1 else value
    return f"{scaled:.{decimals}f}%"


def save_figure(fig: plt.Figure, path: Path, also_images: bool = True) -> Path:
    """Save a chart into outputs/charts and, optionally, mirror it into images/."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=config.CHART_DPI, bbox_inches="tight")
    if also_images:
        config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(config.IMAGES_DIR / path.name, dpi=config.CHART_DPI, bbox_inches="tight")
    plt.close(fig)
    LOGGER.info("Chart saved -> %s", path.relative_to(config.PROJECT_ROOT))
    return path


def relative(path: Path) -> str:
    """Return a path relative to the project root, for pretty log lines."""
    try:
        return str(Path(path).relative_to(config.PROJECT_ROOT))
    except ValueError:
        return str(path)
