"""
Expense Tracker App - command line entry point.

    python main.py all         # generate -> clean -> analyse -> charts -> reports
    python main.py generate    # synthetic data only
    python main.py clean       # cleaning pipeline + data-quality report
    python main.py analyze     # analysis + JSON summary
    python main.py visualize   # the 10 charts
    python main.py insights    # Markdown insight report
    python main.py dashboard   # launch the Streamlit app

Author: Harsha K S
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from src import analysis, config, data_cleaning, data_generator, insights, visualization
from src.utils import ensure_directories, setup_logging

# The Windows console defaults to cp1252 and cannot print the INR symbol.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

LOGGER = setup_logging()


def _frame_to_records(frame: pd.DataFrame, limit: int | None = None) -> list[dict]:
    view = frame if limit is None else frame.head(limit)
    return json.loads(view.to_json(orient="records", date_format="iso"))


def cmd_generate() -> tuple[pd.DataFrame, dict[str, int]]:
    ensure_directories()
    dirty, counts = data_generator.generate_and_save()
    return dirty, counts


def cmd_clean(dirty: pd.DataFrame | None = None, counts: dict | None = None) -> tuple[pd.DataFrame, dict]:
    clean, report = data_cleaning.clean_expenses(dirty, counts)
    clean.to_csv(config.CLEAN_CSV_PATH, index=False)
    data_cleaning.write_quality_report(report)
    if config.INCOME_CSV_PATH.exists():
        income = pd.read_csv(config.INCOME_CSV_PATH)
        income.to_csv(config.CLEAN_INCOME_CSV_PATH, index=False)
    LOGGER.info("Clean dataset saved -> %s", config.CLEAN_CSV_PATH.relative_to(config.PROJECT_ROOT))
    return clean, report


def cmd_analyze(df: pd.DataFrame | None = None) -> dict:
    results = analysis.full_analysis(df)
    _write_summary_json(results)
    return results


def _write_summary_json(results: dict) -> None:
    payload = {
        "project": config.PROJECT_NAME,
        "version": config.PROJECT_VERSION,
        "author": config.PROJECT_AUTHOR,
        "seed": config.RANDOM_SEED,
        "overview": results["overview"],
        "categories": _frame_to_records(results["category"]),
        "monthly": _frame_to_records(results["monthly"]),
        "budget": _frame_to_records(results["budget"]),
        "segments": _frame_to_records(results["segments"]),
        "top_merchants": _frame_to_records(results["merchants"], limit=12),
        "anomalies": {
            "user_day_anomalies": results["anomalies"]["user_day_anomalies"],
            "users_flagged": results["anomalies"]["users_flagged"],
            "aggregate_anomaly_days": results["anomalies"]["aggregate_anomaly_days"],
            "median_daily_spend": results["anomalies"]["median_daily_spend"],
            "mad": results["anomalies"]["mad"],
            "z_threshold": results["anomalies"]["z_threshold"],
            "burn_rate_30d_per_user": results["anomalies"]["burn_rate_30d_per_user"],
            "variable_budget_per_user": results["anomalies"]["variable_budget_per_user"],
            "burn_vs_variable_budget_pct": results["anomalies"]["burn_vs_variable_budget_pct"],
            "burn_vs_budget_pct": results["anomalies"]["burn_vs_budget_pct"],
            "excluded_categories": results["anomalies"]["excluded_categories"],
        },
        "pareto_categories": list(results["pareto"]["category"]),
    }
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    config.SUMMARY_JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    LOGGER.info("JSON summary saved -> %s", config.SUMMARY_JSON_PATH.relative_to(config.PROJECT_ROOT))


def cmd_visualize(results: dict) -> list[str]:
    charts = visualization.render_all(results)
    LOGGER.info("%s charts rendered -> %s", len(charts), config.CHARTS_DIR.relative_to(config.PROJECT_ROOT))
    return charts


def cmd_insights(results: dict) -> str:
    insights.write_summary_csv(results)
    return insights.write_report(results)


def cmd_dashboard() -> int:
    import subprocess

    LOGGER.info("Starting the Streamlit dashboard on http://localhost:8501")
    return subprocess.call(
        [
            sys.executable, "-m", "streamlit", "run", "dashboard.py",
            "--server.headless", "true", "--browser.gatherUsageStats", "false",
        ],
        cwd=str(config.PROJECT_ROOT),
    )


def cmd_all() -> int:
    dirty, counts = cmd_generate()
    clean, report = cmd_clean(dirty, counts)
    results = cmd_analyze(clean)
    charts = cmd_visualize(results)
    cmd_insights(results)

    o = results["overview"]
    print()
    print("=" * 62)
    print(f"  {config.PROJECT_NAME} v{config.PROJECT_VERSION} - pipeline complete")
    print("=" * 62)
    print(f"  Raw rows ............ {report['rows_in']:,}")
    print(f"  Valid transactions .. {report['rows_out']:,}  ({report['retention_pct']:.2f}% retained)")
    print(f"  Users ............... {o['users']:,}      Categories ...... {o['categories']}")
    print(f"  Window .............. {o['date_from']} -> {o['date_to']}")
    print(f"  Total spend ......... {config.CURRENCY_SYMBOL}{o['total_spend']:,.2f}")
    print(f"  Per user / month .... {config.CURRENCY_SYMBOL}{o['avg_monthly_spend_per_user']:,.2f}")
    print(f"  Budget per user ..... {config.CURRENCY_SYMBOL}{o['monthly_budget_per_user']:,.2f}")
    print(f"  Savings rate ........ {(o['avg_monthly_income_per_user'] - o['avg_monthly_spend_per_user']) / o['avg_monthly_income_per_user'] * 100:+.1f}%")
    print(f"  Overspend alerts .... {results['anomalies']['user_day_anomalies']} user-days "
          f"({results['anomalies']['users_flagged']} users)")
    print(f"  Charts .............. {len(charts)}")
    print("=" * 62)
    print(f"  Dashboard: python main.py dashboard")
    print("=" * 62)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expense-tracker",
        description="Expense Tracker App - synthetic finance data, cleaning, analysis and dashboard.",
    )
    sub = parser.add_subparsers(dest="command")
    for name, help_text in [
        ("all", "run the entire pipeline"),
        ("generate", "create the raw synthetic export"),
        ("clean", "clean the raw export and write the quality report"),
        ("analyze", "run the analysis and write the JSON summary"),
        ("visualize", "render the 10 charts"),
        ("insights", "write the Markdown insight report"),
        ("dashboard", "launch the Streamlit dashboard"),
    ]:
        sub.add_parser(name, help=help_text)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = args.command or "all"
    LOGGER.info("Running command: %s", command)

    if command == "all":
        return cmd_all()

    if command == "generate":
        cmd_generate()
        return 0

    if command == "clean":
        cmd_clean()
        return 0

    if command == "analyze":
        cmd_analyze()
        return 0

    if command == "visualize":
        cmd_visualize(cmd_analyze())
        return 0

    if command == "insights":
        cmd_insights(cmd_analyze())
        return 0

    if command == "dashboard":
        return cmd_dashboard()

    build_parser().print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
