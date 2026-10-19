"""
Headless Streamlit smoke tests (AppTest).

These catch import errors, bad st.* arguments and rendering exceptions without
launching a browser - the browser suite lives in test_browser.py.

Author: Harsha K S
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DASHBOARD = str(ROOT / "dashboard.py")
TIMEOUT = 180


def _run() -> AppTest:
    app = AppTest.from_file(DASHBOARD, default_timeout=TIMEOUT)
    app.run()
    return app


def test_dashboard_runs() -> None:
    """The whole dashboard renders with zero exceptions."""
    app = _run()
    assert not app.exception, f"dashboard raised: {app.exception}"
    assert len(app.tabs) == 5, "expected five tabs"


def test_dashboard_filters() -> None:
    """Changing a filter re-renders cleanly."""
    app = _run()
    assert not app.exception

    # Narrow the category filter down to a single category.
    category_filter = app.multiselect(key="filter_categories")
    assert category_filter is not None and len(category_filter.options) >= 2
    category_filter.select(category_filter.options[0]).run()
    assert not app.exception, f"filtering raised: {app.exception}"

    # And narrow the month range.
    month_slider = app.select_slider(key="months_range")
    months = month_slider.options
    month_slider.set_value((months[0], months[1])).run()
    assert not app.exception, f"month range raised: {app.exception}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
