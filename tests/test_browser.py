"""
Real-browser end-to-end test for the Expense Tracker dashboard.

Starts Streamlit itself (if it is not already running), drives a real Chromium
through every tab, applies filters, uploads a CSV, checks the download button
and fails on any console or page error. Screenshots are saved into images/ for
the README and into outputs/test_evidence/ as test evidence.

Run standalone:
    python tests/test_browser.py

Or as part of the suite (the server is managed automatically):
    python -m pytest tests/ -q

Author: Harsha K S
"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

URL = "http://localhost:8501"
EVIDENCE = ROOT / "outputs" / "test_evidence"
IMAGES = ROOT / "images"
RAW_CSV = ROOT / "data" / "raw" / "expenses_raw.csv"

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  {mark}  {name}" + (f" -> {detail}" if detail else ""), flush=True)
    return bool(ok)


def wait_for_server(timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(URL, timeout=3)
            return True
        except Exception:
            time.sleep(1.5)
    return False


def visible_charts(page) -> int:
    """Count Plotly charts that are actually on screen."""
    return (
        page.evaluate(
            "[...document.querySelectorAll('.js-plotly-plot')]"
            ".filter(el => el.getBoundingClientRect().width > 0).length"
        )
        or 0
    )


def wait_for_charts(page, settle: int = 3000) -> int:
    page.wait_for_timeout(settle)
    rendered = 0
    for _ in range(20):
        rendered = visible_charts(page)
        if rendered:
            break
        page.wait_for_timeout(800)
    page.wait_for_timeout(2500)
    return rendered


def run_checks() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1500, "height": 1150}, device_scale_factor=2)
        page.set_default_timeout(25_000)

        console_errors: list[str] = []
        page_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        page.goto(URL, wait_until="domcontentloaded")
        wait_for_charts(page, 5000)

        record("hero heading visible", page.get_by_text("Expense Tracker App").first.is_visible())
        kpis = page.locator(".kpi .label")
        record("KPI cards rendered", kpis.count() == 6, f"{kpis.count()} cards")

        tabs = ["Overview", "Categories", "Trends", "Patterns", "Data"]
        for index, name in enumerate(tabs):
            page.get_by_role("tab", name=name).click()
            charts = wait_for_charts(page, 2500)
            ok = charts >= 1 or name == "Data"
            record(f"tab '{name}' renders", ok, f"{charts} chart(s)")
            slug = name.lower().replace(" ", "_")
            page.screenshot(path=str(EVIDENCE / f"tab_{slug}.png"), full_page=True)
            if index < 4:
                # the tab click leaves the page scrolled, which clipped the
                # masthead in the README screenshots
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(400)
                page.screenshot(path=str(IMAGES / f"dashboard_{slug}.png"), full_page=False)

        # ---- filter: narrow to a single category -------------------------- #
        # The menu only materialises the options that fit its height, and
        # "Travel" sorts last, so it is not in the DOM until we search for it.
        # Typing first is both what a user does and immune to that clamping.
        page.get_by_role("tab", name="Overview").click()
        page.wait_for_timeout(1500)
        search = page.get_by_label("Category").first
        search.click()
        page.wait_for_timeout(500)
        search.press_sequentially("Travel", delay=80)
        page.wait_for_timeout(800)
        option = page.get_by_role("option", name="Travel").first
        record("category option is reachable", option.count() > 0)
        if option.count():
            option.click()
        page.wait_for_timeout(800)
        page.keyboard.press("Escape")
        wait_for_charts(page, 3000)
        sidebar_text = page.locator("[data-testid='stSidebar']").inner_text()
        record("category filter applies", "Travel" in sidebar_text)
        page.screenshot(path=str(EVIDENCE / "filter_category_travel.png"))

        # ---- reset the filter --------------------------------------------- #
        page.get_by_label("Category").first.click()
        page.wait_for_timeout(700)
        clear = page.get_by_role("button", name="Clear all").first
        record("clear-all control is present", clear.count() > 0)
        if clear.count():
            clear.click()
            page.wait_for_timeout(900)
        page.keyboard.press("Escape")
        wait_for_charts(page, 2500)
        reset_text = page.locator("[data-testid='stSidebar']").inner_text()
        record("filter clears back to the full ledger", "16,179 of 16,179" in reset_text)

        # ---- CSV upload --------------------------------------------------- #
        if RAW_CSV.exists():
            uploader = page.locator("input[type='file']")
            uploader.first.set_input_files(str(RAW_CSV))
            page.wait_for_timeout(12000)
            body = page.inner_text("body")
            record("CSV upload accepted", RAW_CSV.name in body or "Loaded and cleaned" in body)
            page.screenshot(path=str(EVIDENCE / "csv_uploaded.png"), full_page=False)
        else:
            record("CSV upload accepted", False, "raw csv missing - run python main.py all")

        # ---- data tab: table + downloads ---------------------------------- #
        page.get_by_role("tab", name="Data").click()
        page.wait_for_timeout(3000)
        record("data preview table", page.locator("[data-testid='stDataFrame']").count() >= 1)
        downloads = page.locator("[data-testid='stDownloadButton']")
        record("download buttons present", downloads.count() >= 1, f"{downloads.count()} buttons")

        record("no page errors", not page_errors, "; ".join(page_errors[:2]))
        record("no console errors", not console_errors, "; ".join(console_errors[:2]))

        browser.close()


def _server_up() -> bool:
    try:
        urllib.request.urlopen(URL, timeout=3)
        return True
    except Exception:
        return False


def main() -> int:
    RESULTS.clear()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)

    if not wait_for_server():
        record("server reachable", False, f"{URL} did not respond")
        return 1
    record("server reachable", True, URL)

    run_checks()

    print()
    print("=" * 64)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"{passed}/{len(RESULTS)} checks passed")
    print("=" * 64)
    failed = [name for name, ok, _ in RESULTS if not ok]
    if failed:
        print("failed:", ", ".join(failed))
    print(f"evidence screenshots -> {EVIDENCE.relative_to(ROOT)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------- #
# Pytest entry point - manages the Streamlit server lifecycle
# --------------------------------------------------------------------------- #
def test_browser_dashboard_end_to_end() -> None:
    """Drive a real browser through the dashboard, managing the server."""
    launched = None
    if not _server_up():
        launched = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", "dashboard.py",
                "--server.headless", "true", "--browser.gatherUsageStats", "false",
            ],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    try:
        rc = main()
        assert rc == 0, f"{sum(1 for _, ok, _ in RESULTS if not ok)} browser check(s) failed"
    finally:
        if launched is not None:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(launched.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
