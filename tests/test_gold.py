"""Tests for gold layer analytical marts."""

from __future__ import annotations

import pytest


def test_gold_placeholder_fact_case_summary() -> None:
    """Placeholder: fact_case_summary must have one row per case."""
    # TODO: implement after Phase 3
    pass


def test_gold_placeholder_fact_variant_stats() -> None:
    """Placeholder: fact_variant_stats case_percentage must sum to ~100%."""
    # TODO: implement after Phase 3
    pass


def test_gold_placeholder_dim_activity_all_activities_present() -> None:
    """Placeholder: dim_activity must contain all 42 activities."""
    # TODO: implement after Phase 3
    pass


@pytest.mark.integration
def test_gold_fact_case_summary_row_count() -> None:
    """fact_case_summary must have one row per case (same as bronze_cases)."""
    import polars as pl

    from src import config

    assert config.BRONZE_CASES.exists(), "Run ingestion phase first."
    assert config.GOLD_FACT_CASE_SUMMARY.exists(), "Run gold phase first."
    bronze_count = len(pl.read_parquet(config.BRONZE_CASES))
    gold_count = len(pl.read_parquet(config.GOLD_FACT_CASE_SUMMARY))
    assert gold_count == bronze_count


@pytest.mark.integration
def test_gold_fact_event_log_no_orphaned_cases() -> None:
    """Every case_id in fact_event_log must exist in fact_case_summary."""
    import polars as pl

    from src import config

    assert config.GOLD_FACT_EVENT_LOG.exists(), "Run gold phase first."
    assert config.GOLD_FACT_CASE_SUMMARY.exists(), "Run gold phase first."
    event_cases = set(pl.read_parquet(config.GOLD_FACT_EVENT_LOG)["case_id"].to_list())
    summary_cases = set(
        pl.read_parquet(config.GOLD_FACT_CASE_SUMMARY)["case_id"].to_list()
    )
    orphaned = event_cases - summary_cases
    assert len(orphaned) == 0, f"{len(orphaned)} orphaned case_ids in event log"


@pytest.mark.integration
def test_gold_variant_stats_percentage_sum() -> None:
    """Variant case percentages must sum to approximately 100%."""
    import polars as pl

    from src import config

    assert config.GOLD_FACT_VARIANT_STATS.exists()
    df = pl.read_parquet(config.GOLD_FACT_VARIANT_STATS)
    total_pct = df["case_percentage"].sum()
    assert abs(total_pct - 100.0) < 1.0, f"Variant percentages sum to {total_pct}, expected ~100"
