"""
ETL orchestrator: Extract (CSV) -> Transform (Pandas) -> Load (MySQL).

Run directly:
    python -m src.etl_pipeline data/raw_sales_data.csv
"""

import sys
import os
from datetime import datetime

import pandas as pd

from src.config_loader import load_config
from src.db_connector import MySQLConnector
from src.data_processor import clean_data, monthly_region_summary
from src.logger import get_logger

logger = get_logger(__name__)


def extract(source_path: str) -> pd.DataFrame:
    """Read raw data from a CSV file."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")
    logger.info(f"Extracting data from {source_path}")
    return pd.read_csv(source_path)


def run_pipeline(source_path: str, config_path: str = "config/config.yaml") -> dict:
    """
    Run the full ETL pipeline once and return a summary dict.
    Any failure is logged to etl_run_log with status FAILED (if the DB
    connection itself is reachable) and re-raised.
    """
    started_at = datetime.now()
    config = load_config(config_path)
    db = MySQLConnector(config["database"])

    rows_read = rows_cleaned = rows_rejected = rows_loaded = 0
    status = "FAILED"
    error_message = None

    try:
        # 1. EXTRACT
        raw_df = extract(source_path)
        rows_read = len(raw_df)

        # 2. TRANSFORM
        logger.info("Cleaning and transforming data with Pandas...")
        clean_df, stats = clean_data(raw_df)
        rows_cleaned = stats["rows_cleaned"]
        rows_rejected = stats["rows_rejected"]
        logger.info(f"Cleaning stats: {stats}")

        # 3. LOAD
        logger.info(f"Loading {len(clean_df)} rows into MySQL table 'sales_transactions'...")
        load_cols = [
            "order_id", "order_date", "customer_name", "region", "product_category",
            "product_name", "quantity", "unit_price", "discount", "payment_method",
            "total_amount", "order_year", "order_month",
        ]
        rows_loaded = db.load_dataframe(clean_df[load_cols], "sales_transactions",
                                         chunk_size=config["etl"]["chunk_size"])

        # 4. Refresh aggregate table used by fast reports
        summary_df = monthly_region_summary(clean_df)
        db.upsert_monthly_summary(summary_df)
        logger.info(f"Refreshed monthly_region_summary with {len(summary_df)} rows.")

        status = "SUCCESS"
        logger.info("ETL pipeline completed successfully.")

    except Exception as exc:
        error_message = str(exc)
        logger.error(f"ETL pipeline failed: {error_message}", exc_info=True)
        raise
    finally:
        finished_at = datetime.now()
        try:
            db.log_etl_run(
                source_file=source_path,
                rows_read=rows_read,
                rows_cleaned=rows_cleaned,
                rows_rejected=rows_rejected,
                rows_loaded=rows_loaded,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                error_message=error_message,
            )
        except Exception as log_exc:
            # Don't let audit-logging failure mask the original error
            logger.warning(f"Could not write to etl_run_log: {log_exc}")

    return {
        "rows_read": rows_read,
        "rows_cleaned": rows_cleaned,
        "rows_rejected": rows_rejected,
        "rows_loaded": rows_loaded,
        "status": status,
        "duration_seconds": (finished_at - started_at).total_seconds(),
    }


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "data/raw_sales_data.csv"
    result = run_pipeline(source)
    print(result)
