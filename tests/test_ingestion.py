"""Tests for XES ingestion and bronze layer.

Unit tests use synthetic fixtures from conftest.py.
Integration tests (marked with @pytest.mark.integration) require
the actual XES file and are skipped in CI if data is absent.
"""

from __future__ import annotations

import polars as pl
import pytest

from src import config

# ---------------------------------------------------------------------------
# Unit tests — schema and structure
# ---------------------------------------------------------------------------


def test_bronze_events_has_required_columns(sample_bronze_events: pl.DataFrame) -> None:
    """Bronze events must have all required columns."""
    required_columns = {"case_id", "activity", "timestamp", "resource", "event_value"}
    assert required_columns.issubset(set(sample_bronze_events.columns))


def test_bronze_cases_has_required_columns(sample_bronze_cases: pl.DataFrame) -> None:
    """Bronze cases must have all required columns."""
    required_columns = {
        "case_id",
        "purchasing_document",
        "item",
        "gr_based_iv",
        "goods_receipt",
        "company",
        "vendor",
        "item_category",
    }
    assert required_columns.issubset(set(sample_bronze_cases.columns))


def test_bronze_events_no_null_case_id(sample_bronze_events: pl.DataFrame) -> None:
    """No event may have a null case_id."""
    assert sample_bronze_events["case_id"].null_count() == 0


def test_bronze_events_no_null_activity(sample_bronze_events: pl.DataFrame) -> None:
    """No event may have a null activity."""
    assert sample_bronze_events["activity"].null_count() == 0


def test_bronze_events_no_null_timestamp(sample_bronze_events: pl.DataFrame) -> None:
    """All events must have a parseable timestamp."""
    assert sample_bronze_events["timestamp"].null_count() == 0


def test_bronze_cases_no_null_case_id(sample_bronze_cases: pl.DataFrame) -> None:
    """No case may have a null case_id."""
    assert sample_bronze_cases["case_id"].null_count() == 0


def test_bronze_referential_integrity(
    sample_bronze_events: pl.DataFrame, sample_bronze_cases: pl.DataFrame
) -> None:
    """Every event's case_id must exist in the cases table."""
    event_case_ids = set(sample_bronze_events["case_id"].to_list())
    case_ids = set(sample_bronze_cases["case_id"].to_list())
    orphaned = event_case_ids - case_ids
    assert len(orphaned) == 0, f"Events with no matching case: {orphaned}"


def test_bronze_events_row_count_matches_expected(
    sample_bronze_events: pl.DataFrame,
) -> None:
    """Fixture should have exactly 15 events (3 cases × avg 5)."""
    assert len(sample_bronze_events) == 15


def test_bronze_cases_row_count_matches_expected(
    sample_bronze_cases: pl.DataFrame,
) -> None:
    """Fixture should have exactly 3 cases."""
    assert len(sample_bronze_cases) == 3


def test_bronze_events_timestamp_type(sample_bronze_events: pl.DataFrame) -> None:
    """Timestamps must be datetime type, not strings."""
    assert sample_bronze_events["timestamp"].dtype in (
        pl.Datetime,
        pl.Datetime("us"),
        pl.Datetime("ns"),
        pl.Datetime("ms"),
    )


def test_bronze_cases_boolean_flags(sample_bronze_cases: pl.DataFrame) -> None:
    """GR-based IV and Goods Receipt columns must be boolean."""
    assert sample_bronze_cases["gr_based_iv"].dtype == pl.Boolean
    assert sample_bronze_cases["goods_receipt"].dtype == pl.Boolean


# ---------------------------------------------------------------------------
# Integration tests — require actual XES file
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_xes_file_exists() -> None:
    """XES file must be present at the configured path."""
    assert config.XES_FILE.exists(), (
        f"XES file not found at {config.XES_FILE}. "
        "Download from https://data.4tu.nl/datasets/769f25d0-e167-4a35-bbb6-7c96a8872593"
    )


@pytest.mark.integration
def test_bronze_events_production_row_count() -> None:
    """Bronze events file must have approximately 1,595,923 rows."""
    assert config.BRONZE_EVENTS.exists(), "Run ingestion phase first."
    df = pl.read_parquet(config.BRONZE_EVENTS)
    tolerance = int(config.EXPECTED_EVENT_COUNT * config.ROW_COUNT_TOLERANCE)
    assert abs(len(df) - config.EXPECTED_EVENT_COUNT) <= tolerance, (
        f"Expected ~{config.EXPECTED_EVENT_COUNT} events, got {len(df)}"
    )


@pytest.mark.integration
def test_bronze_cases_production_row_count() -> None:
    """Bronze cases file must have approximately 251,734 rows."""
    assert config.BRONZE_CASES.exists(), "Run ingestion phase first."
    df = pl.read_parquet(config.BRONZE_CASES)
    tolerance = int(config.EXPECTED_CASE_COUNT * config.ROW_COUNT_TOLERANCE)
    assert abs(len(df) - config.EXPECTED_CASE_COUNT) <= tolerance, (
        f"Expected ~{config.EXPECTED_CASE_COUNT} cases, got {len(df)}"
    )
