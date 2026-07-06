"""
Automated Data Processing & Reporting System — CLI entry point.

Usage:
    python main.py etl --source data/raw_sales_data.csv
    python main.py report
    python main.py run-all --source data/raw_sales_data.csv
    python main.py schedule --source data/raw_sales_data.csv --time 02:00
"""

import argparse
import time
import schedule as schedule_lib

from src.etl_pipeline import run_pipeline
from src.report_generator import generate_full_report
from src.logger import get_logger

logger = get_logger(__name__)


def cmd_etl(args):
    result = run_pipeline(args.source, args.config)
    logger.info(f"ETL result: {result}")


def cmd_report(args):
    result = generate_full_report(args.config)
    logger.info(f"Report generated: {result}")


def cmd_run_all(args):
    cmd_etl(args)
    cmd_report(args)


def cmd_schedule(args):
    logger.info(f"Scheduling full pipeline daily at {args.time} ...")

    def job():
        logger.info("Running scheduled ETL + report job...")
        try:
            cmd_run_all(args)
        except Exception as e:
            logger.error(f"Scheduled run failed: {e}")

    schedule_lib.every().day.at(args.time).do(job)
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    while True:
        schedule_lib.run_pending()
        time.sleep(30)


def build_parser():
    parser = argparse.ArgumentParser(description="Automated Data Processing & Reporting System")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_etl = sub.add_parser("etl", help="Run extract-transform-load only")
    p_etl.add_argument("--source", default="data/raw_sales_data.csv", help="Path to raw CSV file")
    p_etl.set_defaults(func=cmd_etl)

    p_report = sub.add_parser("report", help="Generate Excel/chart reports from MySQL data")
    p_report.set_defaults(func=cmd_report)

    p_run_all = sub.add_parser("run-all", help="Run ETL then generate reports")
    p_run_all.add_argument("--source", default="data/raw_sales_data.csv", help="Path to raw CSV file")
    p_run_all.set_defaults(func=cmd_run_all)

    p_schedule = sub.add_parser("schedule", help="Run ETL + reports on a daily schedule")
    p_schedule.add_argument("--source", default="data/raw_sales_data.csv", help="Path to raw CSV file")
    p_schedule.add_argument("--time", default="02:00", help="Daily run time, 24h HH:MM")
    p_schedule.set_defaults(func=cmd_schedule)

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
