"""Tests for silver layer transformations."""

from __future__ import annotations

import polars as pl
import pytest


def test_silver_events_has_resource_type(sample_silver_events: pl.DataFrame) -> None:
    """Silver events must have resource_type column."""
    assert "resource_type" in sample_silver_events.columns


def test_silver_events_resource_type_values(sample_silver_events: pl.DataFrame) -> None:
    """resource_type must only contain 'human', 'batch', or 'unknown'."""
    valid_types = {"human", "batch", "unknown"}
    actual = set(sample_silver_events["resource_type"].drop_nulls().unique().to_list())
    assert actual.issubset(valid_types), f"Unexpected resource types: {actual - valid_types}"


def test_silver_events_batch_classification(sample_silver_events: pl.DataFrame) -> None:
    """Resources starting with 'BATCH' should be classified as 'batch'."""
    batch_rows = sample_silver_events.filter(pl.col("resource").str.starts_with("BATCH"))
    assert (batch_rows["resource_type"] == "batch").all()


def test_silver_events_human_classification(sample_silver_events: pl.DataFrame) -> None:
    """Resources not starting with 'BATCH' should be classified as 'human'."""
    human_rows = sample_silver_events.filter(~pl.col("resource").str.starts_with("BATCH"))
    assert (human_rows["resource_type"] == "human").all()


def test_silver_events_has_event_order(sample_silver_events: pl.DataFrame) -> None:
    """Silver events must have event_order column."""
    assert "event_order" in sample_silver_events.columns


def test_silver_events_event_order_positive(sample_silver_events: pl.DataFrame) -> None:
    """Event order values must be positive integers."""
    assert (sample_silver_events["event_order"] > 0).all()


def test_silver_cases_has_flow_type(sample_silver_cases: pl.DataFrame) -> None:
    """Silver cases must have flow_type column."""
    assert "flow_type" in sample_silver_cases.columns


def test_silver_cases_flow_type_valid_values(sample_silver_cases: pl.DataFrame) -> None:
    """flow_type must be one of the four known types."""
    valid_types = {
        "3way_invoice_after_gr",
        "3way_invoice_before_gr",
        "2way",
        "consignment",
    }
    actual = set(sample_silver_cases["flow_type"].drop_nulls().unique().to_list())
    assert actual.issubset(valid_types), f"Unexpected flow types: {actual - valid_types}"


def test_silver_cases_flow_type_no_nulls(sample_silver_cases: pl.DataFrame) -> None:
    """flow_type must be assigned for every case."""
    assert sample_silver_cases["flow_type"].null_count() == 0


def test_silver_cases_case_duration_non_negative(
    sample_silver_cases: pl.DataFrame,
) -> None:
    """case_duration_days must be >= 0 for all cases."""
    assert (sample_silver_cases["case_duration_days"] >= 0).all()


def test_silver_cases_event_count_positive(sample_silver_cases: pl.DataFrame) -> None:
    """event_count must be >= 1 for all cases."""
    assert (sample_silver_cases["event_count"] >= 1).all()


def test_silver_cases_has_variant_id(sample_silver_cases: pl.DataFrame) -> None:
    """Silver cases must have variant_id column."""
    assert "variant_id" in sample_silver_cases.columns


def test_silver_cases_no_null_variant_id(sample_silver_cases: pl.DataFrame) -> None:
    """variant_id must be assigned for every case."""
    assert sample_silver_cases["variant_id"].null_count() == 0


@pytest.mark.integration
def test_silver_events_production_row_count_preserved() -> None:
    """Silver events must preserve row count from bronze (no drops for clean rows)."""
    import polars as pl

    from src import config

    assert config.BRONZE_EVENTS.exists(), "Run ingestion phase first."
    assert config.SILVER_EVENTS.exists(), "Run silver phase first."
    bronze_count = len(pl.read_parquet(config.BRONZE_EVENTS))
    silver_count = len(pl.read_parquet(config.SILVER_EVENTS))
    # Allow small drop for malformed rows (<0.1%)
    assert silver_count >= bronze_count * 0.999, (
        f"Silver dropped too many rows: {bronze_count} → {silver_count}"
    )
