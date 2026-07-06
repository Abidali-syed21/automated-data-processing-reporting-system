import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_processor import (
    clean_data,
    aggregate_by_region,
    aggregate_by_category,
    top_products,
    monthly_trend,
    validate_schema,
)


@pytest.fixture
def sample_raw_df():
    return pd.DataFrame([
        # valid row
        {"order_id": "A1", "order_date": "2024-01-15", "customer_name": "Alice",
         "region": " north ", "product_category": "Electronics", "product_name": "Mouse",
         "quantity": 2, "unit_price": 20.0, "discount": 0.1, "payment_method": "UPI"},
        # duplicate of A1
        {"order_id": "A1", "order_date": "2024-01-15", "customer_name": "Alice",
         "region": " north ", "product_category": "Electronics", "product_name": "Mouse",
         "quantity": 2, "unit_price": 20.0, "discount": 0.1, "payment_method": "UPI"},
        # missing customer name
        {"order_id": "A2", "order_date": "2024-02-01", "customer_name": None,
         "region": "South", "product_category": "Office Supplies", "product_name": "Pens",
         "quantity": 3, "unit_price": 5.0, "discount": 0, "payment_method": "Cash"},
        # invalid quantity
        {"order_id": "A3", "order_date": "2024-02-05", "customer_name": "Bob",
         "region": "East", "product_category": "Furniture", "product_name": "Chair",
         "quantity": -1, "unit_price": 100.0, "discount": 0, "payment_method": "Card"},
        # invalid date
        {"order_id": "A4", "order_date": "not_a_date", "customer_name": "Carol",
         "region": "West", "product_category": "Groceries", "product_name": "Coffee",
         "quantity": 1, "unit_price": 15.0, "discount": 0, "payment_method": "UPI"},
        # valid row, different region
        {"order_id": "A5", "order_date": "2024-03-10", "customer_name": "Dave",
         "region": "South", "product_category": "Electronics", "product_name": "Speaker",
         "quantity": 1, "unit_price": 50.0, "discount": 0.2, "payment_method": "Card"},
    ])


def test_validate_schema_passes(sample_raw_df):
    validate_schema(sample_raw_df)  # should not raise


def test_validate_schema_fails_on_missing_column(sample_raw_df):
    bad_df = sample_raw_df.drop(columns=["region"])
    with pytest.raises(ValueError):
        validate_schema(bad_df)


def test_clean_data_removes_duplicates(sample_raw_df):
    clean_df, stats = clean_data(sample_raw_df)
    assert clean_df["order_id"].is_unique
    assert stats["rows_dropped_duplicates"] == 1


def test_clean_data_drops_missing_and_invalid_rows(sample_raw_df):
    clean_df, stats = clean_data(sample_raw_df)
    # A2 (missing name), A3 (bad qty), A4 (bad date) should all be dropped
    remaining_ids = set(clean_df["order_id"])
    assert remaining_ids == {"A1", "A5"}
    assert stats["rows_read"] == 6
    assert stats["rows_cleaned"] == 2


def test_clean_data_normalizes_region_text(sample_raw_df):
    clean_df, _ = clean_data(sample_raw_df)
    assert clean_df.loc[clean_df["order_id"] == "A1", "region"].iloc[0] == "North"


def test_total_amount_calculation(sample_raw_df):
    clean_df, _ = clean_data(sample_raw_df)
    row = clean_df[clean_df["order_id"] == "A1"].iloc[0]
    # 2 * 20.0 * (1 - 0.1) = 36.0
    assert row["total_amount"] == pytest.approx(36.0)


def test_aggregate_by_region(sample_raw_df):
    clean_df, _ = clean_data(sample_raw_df)
    region_summary = aggregate_by_region(clean_df)
    assert set(region_summary["region"]) == {"North", "South"}
    assert region_summary["total_orders"].sum() == 2


def test_aggregate_by_category(sample_raw_df):
    clean_df, _ = clean_data(sample_raw_df)
    cat_summary = aggregate_by_category(clean_df)
    assert "Electronics" in set(cat_summary["product_category"])


def test_top_products_limits_results(sample_raw_df):
    clean_df, _ = clean_data(sample_raw_df)
    result = top_products(clean_df, n=1)
    assert len(result) == 1


def test_monthly_trend_has_period_column(sample_raw_df):
    clean_df, _ = clean_data(sample_raw_df)
    trend = monthly_trend(clean_df)
    assert "period" in trend.columns
    assert set(trend["period"]) == {"2024-01", "2024-03"}
