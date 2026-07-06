"""
MySQL connection layer built on SQLAlchemy + mysql-connector-python.

Wraps the boilerplate for connecting, bulk-loading DataFrames, and running
read queries back into DataFrames, so the rest of the pipeline never has
to write raw connection/cursor code.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class MySQLConnector:
    def __init__(self, config: dict):
        """
        Args:
            config: the "database" section of config.yaml, e.g.
                {"host": ..., "port": ..., "user": ..., "password": ..., "database": ...}
        """
        self.config = config
        self.engine: Engine = self._build_engine()

    def _build_engine(self) -> Engine:
        cfg = self.config
        url = (
            f"mysql+mysqlconnector://{cfg['user']}:{cfg['password']}"
            f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
        )
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600)

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def run_query(self, query: str, params: dict | None = None) -> pd.DataFrame:
        """Run a SELECT query and return the result as a DataFrame."""
        with self.engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)

    def execute(self, query: str, params: dict | None = None) -> None:
        """Run a non-SELECT statement (DDL/DML)."""
        with self.engine.begin() as conn:
            conn.execute(text(query), params or {})

    def load_dataframe(self, df: pd.DataFrame, table: str, if_exists: str = "append",
                        chunk_size: int = 5000) -> int:
        """
        Bulk-load a DataFrame into a MySQL table.

        Uses `if_exists="append"` by default so repeated ETL runs accumulate
        history; the UNIQUE KEY on order_id in schema.sql prevents true
        duplicates from being re-inserted (use INSERT IGNORE semantics via
        a staging table if you need upsert behaviour at scale).

        Returns:
            number of rows written.
        """
        df.to_sql(
            name=table,
            con=self.engine,
            if_exists=if_exists,
            index=False,
            chunksize=chunk_size,
            method="multi",
        )
        return len(df)

    def upsert_monthly_summary(self, df: pd.DataFrame) -> int:
        """
        Upsert into monthly_region_summary (ON DUPLICATE KEY UPDATE),
        since this table should reflect the latest aggregate, not history.
        """
        if df.empty:
            return 0

        insert_sql = """
            INSERT INTO monthly_region_summary
                (order_year, order_month, region, total_orders,
                 total_quantity, total_revenue, avg_order_value)
            VALUES
                (:order_year, :order_month, :region, :total_orders,
                 :total_quantity, :total_revenue, :avg_order_value)
            ON DUPLICATE KEY UPDATE
                total_orders = VALUES(total_orders),
                total_quantity = VALUES(total_quantity),
                total_revenue = VALUES(total_revenue),
                avg_order_value = VALUES(avg_order_value)
        """
        records = df.to_dict(orient="records")
        with self.engine.begin() as conn:
            for row in records:
                conn.execute(text(insert_sql), row)
        return len(records)

    def log_etl_run(self, source_file: str, rows_read: int, rows_cleaned: int,
                     rows_rejected: int, rows_loaded: int, status: str,
                     started_at, finished_at, error_message: str | None = None) -> None:
        duration = (finished_at - started_at).total_seconds()
        self.execute(
            """
            INSERT INTO etl_run_log
                (source_file, rows_read, rows_cleaned, rows_rejected, rows_loaded,
                 status, error_message, started_at, finished_at, duration_seconds)
            VALUES
                (:source_file, :rows_read, :rows_cleaned, :rows_rejected, :rows_loaded,
                 :status, :error_message, :started_at, :finished_at, :duration_seconds)
            """,
            {
                "source_file": source_file,
                "rows_read": rows_read,
                "rows_cleaned": rows_cleaned,
                "rows_rejected": rows_rejected,
                "rows_loaded": rows_loaded,
                "status": status,
                "error_message": error_message,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_seconds": duration,
            },
        )
