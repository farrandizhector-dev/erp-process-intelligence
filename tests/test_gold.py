"""Tests for gold layer analytical marts."""

from __future__ import annotations

import polars as pl
import pytest

from src.analytics.conformance import run_all_rules
from src.analytics.process_discovery import compute_variant_stats, detect_rework
from src.gold.facts import build_fact_case_summary, build_touchless_ratio


def test_gold_placeholder_fact_case_summary(
    sample_silver_events: pl.DataFrame,
    sample_silver_cases: pl.DataFrame,
) -> None:
    """fact_case_summary must have one row per case."""
    from src.analytics.conformance import compute_case_compliance_scores
    from src.analytics.process_discovery import build_is_happy_path_column

    rework_df = detect_rework(sample_silver_events)
    variant_stats = compute_variant_stats(sample_silver_events, sample_silver_cases)
    compliance_checks = run_all_rules(sample_silver_events, sample_silver_cases)
    compliance_scores = compute_case_compliance_scores(compliance_checks)
    touchless_df = build_touchless_ratio(sample_silver_events)
    is_happy_path_df = build_is_happy_path_column(sample_silver_cases, variant_stats)

    fact = build_fact_case_summary(
        cases=sample_silver_cases,
        rework_df=rework_df,
        compliance_scores=compliance_scores,
        touchless_df=touchless_df,
        is_happy_path_df=is_happy_path_df,
    )
    assert len(fact) == len(sample_silver_cases)
    assert "compliance_score" in fact.columns
    assert "has_rework" in fact.columns
    assert "sla_risk" in fact.columns


def test_gold_placeholder_fact_variant_stats(
    sample_silver_events: pl.DataFrame,
    sample_silver_cases: pl.DataFrame,
) -> None:
    """fact_variant_stats case_percentage must sum to ~100%."""
    variant_stats = compute_variant_stats(sample_silver_events, sample_silver_cases)
    total_pct = variant_stats["case_percentage"].sum()
    assert abs(total_pct - 100.0) < 1.0, f"Variant percentages sum to {total_pct}"


def test_gold_placeholder_dim_activity_all_activities_present() -> None:
    """dim_activity must contain all 42 activities (integration check via config)."""
    from src import config

    assert config.EXPECTED_ACTIVITY_COUNT == 42


def test_rework_detection_all_cases_present(
    sample_silver_events: pl.DataFrame,
) -> None:
    """detect_rework must return one row per case even if no rework."""
    rework = detect_rework(sample_silver_events)
    n_cases = sample_silver_events["case_id"].n_unique()
    assert len(rework) == n_cases


def test_touchless_ratio_range(sample_silver_events: pl.DataFrame) -> None:
    """touchless_ratio must be between 0 and 1 for all cases."""
    touchless = build_touchless_ratio(sample_silver_events)
    assert (touchless["touchless_ratio"] >= 0.0).all()
    assert (touchless["touchless_ratio"] <= 1.0).all()


def test_compliance_checks_have_required_columns(
    sample_silver_events: pl.DataFrame,
    sample_silver_cases: pl.DataFrame,
) -> None:
    """fact_compliance_checks must have all required schema columns."""
    required = {"case_id", "rule_id", "rule_name", "passed", "severity", "detail"}
    checks = run_all_rules(sample_silver_events, sample_silver_cases)
    assert required.issubset(set(checks.columns))


def test_compliance_passed_is_boolean(
    sample_silver_events: pl.DataFrame,
    sample_silver_cases: pl.DataFrame,
) -> None:
    """The 'passed' column in compliance checks must be boolean."""
    checks = run_all_rules(sample_silver_events, sample_silver_cases)
    assert checks["passed"].dtype == pl.Boolean


@pytest.mark.integration
def test_gold_fact_case_summary_row_count() -> None:
    """fact_case_summary must have one row per case (same as bronze_cases)."""
    from src import config

    assert config.BRONZE_CASES.exists(), "Run ingestion phase first."
    assert config.GOLD_FACT_CASE_SUMMARY.exists(), "Run gold phase first."
    bronze_count = len(pl.read_parquet(config.BRONZE_CASES))
    gold_count = len(pl.read_parquet(config.GOLD_FACT_CASE_SUMMARY))
    assert gold_count == bronze_count


@pytest.mark.integration
def test_gold_fact_event_log_no_orphaned_cases() -> None:
    """Every case_id in fact_event_log must exist in fact_case_summary."""
    from src import config

    assert config.GOLD_FACT_EVENT_LOG.exists(), "Run gold phase first."
    assert config.GOLD_FACT_CASE_SUMMARY.exists(), "Run gold phase first."
    event_cases = set(pl.read_parquet(config.GOLD_FACT_EVENT_LOG)["case_id"].to_list())
    summary_cases = set(pl.read_parquet(config.GOLD_FACT_CASE_SUMMARY)["case_id"].to_list())
    orphaned = event_cases - summary_cases
    assert len(orphaned) == 0, f"{len(orphaned)} orphaned case_ids in event log"


@pytest.mark.integration
def test_gold_variant_stats_percentage_sum() -> None:
    """Variant case percentages must sum to approximately 100%."""
    from src import config

    assert config.GOLD_FACT_VARIANT_STATS.exists()
    df = pl.read_parquet(config.GOLD_FACT_VARIANT_STATS)
    total_pct = df["case_percentage"].sum()
    assert abs(total_pct - 100.0) < 1.0, f"Variant percentages sum to {total_pct}, expected ~100"
