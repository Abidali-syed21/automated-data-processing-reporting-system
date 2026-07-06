"""
Data cleaning & transformation logic using Pandas.

This module is intentionally decoupled from the database and file system
so its functions can be unit-tested with plain DataFrames.
"""

import pandas as pd
import numpy as np


REQUIRED_COLUMNS = [
    "order_id", "order_date", "customer_name", "region",
    "product_category", "product_name", "quantity",
    "unit_price", "discount", "payment_method",
]


def validate_schema(df: pd.DataFrame) -> None:
    """Raise a clear error if expected columns are missing."""
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Input data is missing required columns: {sorted(missing)}")


def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean a raw sales DataFrame.

    Steps:
      1. Validate required columns exist.
      2. Strip/normalize text columns (region, category, names).
      3. Parse order_date, drop unparsable rows.
      4. Drop rows with missing customer_name or unit_price (can't report on them).
      5. Drop duplicate order_id rows.
      6. Fix invalid quantity/unit_price/discount values.
      7. Compute total_amount, order_year, order_month.

    Returns:
        (cleaned_df, stats) where stats is a dict of row counts at each stage,
        used for the ETL audit log.
    """
    stats = {"rows_read": len(df)}
    df = df.copy()

    validate_schema(df)

    # --- Normalize text fields ---
    text_cols = ["region", "product_category", "product_name", "payment_method", "customer_name"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": np.nan, "": np.nan})
    df["region"] = df["region"].str.title()

    # --- Parse dates; invalid dates -> NaT and get dropped ---
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # --- Drop rows that can't be meaningfully reported on ---
    before = len(df)
    df = df.dropna(subset=["order_date", "customer_name", "unit_price"])
    rows_dropped_missing = before - len(df)

    # --- Remove duplicate orders (keep first occurrence) ---
    before = len(df)
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    rows_dropped_dupes = before - len(df)

    # --- Fix invalid numeric values ---
    # Negative/zero quantity is invalid -> drop
    before = len(df)
    df = df[df["quantity"] > 0]
    rows_dropped_bad_qty = before - len(df)

    # Negative unit_price is invalid -> drop
    before = len(df)
    df = df[df["unit_price"] >= 0]
    rows_dropped_bad_price = before - len(df)

    # Discount should be a fraction between 0 and 1; clip out-of-range values
    df["discount"] = df["discount"].fillna(0)
    df["discount"] = df["discount"].clip(lower=0, upper=1)

    # --- Derived columns ---
    df["total_amount"] = (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
    df["order_year"] = df["order_date"].dt.year
    df["order_month"] = df["order_date"].dt.month
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")

    df = df.reset_index(drop=True)

    stats.update({
        "rows_dropped_missing_required": int(rows_dropped_missing),
        "rows_dropped_duplicates": int(rows_dropped_dupes),
        "rows_dropped_bad_quantity": int(rows_dropped_bad_qty),
        "rows_dropped_bad_price": int(rows_dropped_bad_price),
        "rows_cleaned": len(df),
        "rows_rejected": stats["rows_read"] - len(df),
    })

    return df, stats


def aggregate_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue, order count, and average order value grouped by region."""
    summary = (
        df.groupby("region")
        .agg(
            total_orders=("order_id", "count"),
            total_quantity=("quantity", "sum"),
            total_revenue=("total_amount", "sum"),
        )
        .assign(avg_order_value=lambda x: (x["total_revenue"] / x["total_orders"]).round(2))
        .sort_values("total_revenue", ascending=False)
        .reset_index()
    )
    return summary


def aggregate_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and units sold grouped by product category."""
    summary = (
        df.groupby("product_category")
        .agg(
            total_orders=("order_id", "count"),
            units_sold=("quantity", "sum"),
            total_revenue=("total_amount", "sum"),
        )
        .sort_values("total_revenue", ascending=False)
        .reset_index()
    )
    return summary


def top_products(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N products by revenue."""
    summary = (
        df.groupby("product_name")
        .agg(
            units_sold=("quantity", "sum"),
            total_revenue=("total_amount", "sum"),
        )
        .sort_values("total_revenue", ascending=False)
        .head(n)
        .reset_index()
    )
    return summary


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly revenue trend across the full dataset."""
    tmp = df.copy()
    tmp["period"] = tmp["order_year"].astype(str) + "-" + tmp["order_month"].astype(str).str.zfill(2)
    summary = (
        tmp.groupby("period")
        .agg(total_orders=("order_id", "count"), total_revenue=("total_amount", "sum"))
        .reset_index()
        .sort_values("period")
    )
    return summary


def monthly_region_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Used to populate the monthly_region_summary MySQL table."""
    summary = (
        df.groupby(["order_year", "order_month", "region"])
        .agg(
            total_orders=("order_id", "count"),
            total_quantity=("quantity", "sum"),
            total_revenue=("total_amount", "sum"),
        )
        .assign(avg_order_value=lambda x: (x["total_revenue"] / x["total_orders"]).round(2))
        .reset_index()
    )
    return summary
