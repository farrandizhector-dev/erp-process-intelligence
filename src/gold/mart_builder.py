"""Orchestrate gold mart creation from silver layer.

Coordinates the full gold-layer build:
  Phase 3 (this module):
    - fact_event_log
    - fact_variant_stats
    - fact_compliance_checks
    - fact_bottleneck_analysis
    - fact_case_summary (partial: rework, compliance, SLA risk, happy path)
    - dim_activity, dim_company, dim_vendor, dim_calendar

  Phase 4 (extended in mart_builder):
    - fact_automation_opportunities
    - dim_resource
    - Updated fact_case_summary (automation_score, touchless_ratio)
"""

from __future__ import annotations

import logging

import polars as pl

from src import config
from src.analytics.automation_scoring import compute_automation_opportunities
from src.analytics.conformance import compute_case_compliance_scores, run_all_rules
from src.analytics.process_discovery import (
    build_is_happy_path_column,
    compute_variant_stats,
    detect_rework,
)
from src.analytics.resource_analysis import build_dim_resource, compute_handoff_metrics
from src.analytics.throughput import build_bottleneck_table, build_transitions
from src.gold.dimensions import (
    build_dim_activity,
    build_dim_calendar,
    build_dim_company,
    build_dim_vendor,
)
from src.gold.facts import (
    build_fact_bottleneck_analysis,
    build_fact_case_summary,
    build_fact_compliance_checks,
    build_fact_event_log,
    build_fact_variant_stats,
    build_touchless_ratio,
)

logger = logging.getLogger(__name__)


def build_gold_marts(skip_validation: bool = False) -> int:
    """Build all gold layer fact and dimension tables.

    Reads silver parquet files, runs all analytics, and writes gold tables.

    Args:
        skip_validation: Skip quality checks (faster for dev).

    Returns:
        Total rows written across all gold tables.

    Raises:
        FileNotFoundError: If silver parquet files are missing.
    """
    # ------------------------------------------------------------------
    # 1. Load silver
    # ------------------------------------------------------------------
    for path in [config.SILVER_EVENTS, config.SILVER_CASES, config.SILVER_ACTIVITIES]:
        if not path.exists():
            raise FileNotFoundError(
                f"Silver file not found: {path}. Run --phase silver first."
            )

    logger.info("Loading silver layer...")
    events = pl.read_parquet(config.SILVER_EVENTS)
    cases = pl.read_parquet(config.SILVER_CASES)
    silver_activities = pl.read_parquet(config.SILVER_ACTIVITIES)
    logger.info(
        "Loaded: events=%d, cases=%d, activities=%d",
        len(events),
        len(cases),
        len(silver_activities),
    )

    config.GOLD_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 2. Dimensions (needed early for fact_event_log)
    # ------------------------------------------------------------------
    logger.info("Building dimensions...")
    dim_activity = build_dim_activity(silver_activities)
    _write(dim_activity, config.GOLD_DIM_ACTIVITY, "dim_activity")

    dim_company = build_dim_company(cases)
    _write(dim_company, config.GOLD_DIM_COMPANY, "dim_company")

    dim_vendor = build_dim_vendor(cases)
    _write(dim_vendor, config.GOLD_DIM_VENDOR, "dim_vendor")

    date_min = events["date"].min()
    date_max = events.filter(~pl.col("is_timestamp_anomaly"))["date"].max()
    dim_calendar = build_dim_calendar(date_min, date_max)
    _write(dim_calendar, config.GOLD_DIM_CALENDAR, "dim_calendar")

    # ------------------------------------------------------------------
    # 3. fact_event_log
    # ------------------------------------------------------------------
    logger.info("Building fact_event_log...")
    fact_event_log = build_fact_event_log(events, cases, dim_activity)
    _write(fact_event_log, config.GOLD_FACT_EVENT_LOG, "fact_event_log")

    # ------------------------------------------------------------------
    # 4. Process discovery — variant stats + rework
    # ------------------------------------------------------------------
    logger.info("Computing variant statistics...")
    variant_stats = compute_variant_stats(events, cases)
    fact_variant_stats = build_fact_variant_stats(variant_stats)
    _write(fact_variant_stats, config.GOLD_FACT_VARIANT_STATS, "fact_variant_stats")

    logger.info("Detecting rework...")
    rework_df = detect_rework(events)

    is_happy_path_df = build_is_happy_path_column(cases, variant_stats)

    # ------------------------------------------------------------------
    # 5. Compliance checks
    # ------------------------------------------------------------------
    logger.info("Running compliance rules...")
    compliance_checks = run_all_rules(events, cases)
    fact_compliance = build_fact_compliance_checks(compliance_checks)
    _write(fact_compliance, config.GOLD_FACT_COMPLIANCE, "fact_compliance_checks")

    compliance_scores = compute_case_compliance_scores(compliance_checks)

    # ------------------------------------------------------------------
    # 6. Bottleneck analysis (DFG transitions)
    # ------------------------------------------------------------------
    logger.info("Computing bottleneck analysis...")
    # Join flow_type into events for transition analysis
    events_with_flow = events.join(
        cases.select(["case_id", "flow_type"]), on="case_id", how="left"
    )
    transitions = build_transitions(events_with_flow)
    bottleneck_table = build_bottleneck_table(transitions)
    fact_bottleneck = build_fact_bottleneck_analysis(bottleneck_table)
    _write(fact_bottleneck, config.GOLD_FACT_BOTTLENECK, "fact_bottleneck_analysis")

    # ------------------------------------------------------------------
    # 7. fact_case_summary
    # ------------------------------------------------------------------
    logger.info("Building fact_case_summary...")
    touchless_df = build_touchless_ratio(events)
    handoff_df = compute_handoff_metrics(events)
    fact_case_summary = build_fact_case_summary(
        cases=cases,
        rework_df=rework_df,
        compliance_scores=compliance_scores,
        touchless_df=touchless_df,
        is_happy_path_df=is_happy_path_df,
        handoff_df=handoff_df,
    )
    _write(fact_case_summary, config.GOLD_FACT_CASE_SUMMARY, "fact_case_summary")

    # ------------------------------------------------------------------
    # 8. Phase 4 — automation + resource dimension
    # ------------------------------------------------------------------
    logger.info("Computing automation opportunities...")
    fact_automation = compute_automation_opportunities(events, cases)
    _write(fact_automation, config.GOLD_FACT_AUTOMATION, "fact_automation_opportunities")

    logger.info("Building dim_resource...")
    silver_resources = pl.read_parquet(config.SILVER_RESOURCES)
    dim_resource = build_dim_resource(silver_resources)
    _write(dim_resource, config.GOLD_DIM_RESOURCE, "dim_resource")

    # ------------------------------------------------------------------
    # 9. Summary
    # ------------------------------------------------------------------
    total_rows = (
        len(fact_event_log)
        + len(fact_variant_stats)
        + len(fact_compliance)
        + len(fact_bottleneck)
        + len(fact_case_summary)
        + len(fact_automation)
        + len(dim_activity)
        + len(dim_company)
        + len(dim_vendor)
        + len(dim_calendar)
        + len(dim_resource)
    )
    logger.info("Gold layer complete: %d total rows across 11 tables.", total_rows)

    _log_kpis(fact_case_summary, fact_compliance)

    return total_rows


def run_analytics() -> int:
    """Re-run analytics on existing silver layer (alias for build_gold_marts).

    Returns:
        Total rows written.
    """
    return build_gold_marts()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(df: pl.DataFrame, path, name: str) -> None:
    """Write a DataFrame to parquet and log size."""
    df.write_parquet(path, compression="zstd")
    logger.info(
        "%s written: %d rows, %.1f MB",
        name,
        len(df),
        path.stat().st_size / 1e6,
    )


def _log_kpis(fact_case_summary: pl.DataFrame, fact_compliance: pl.DataFrame) -> None:
    """Log key business KPIs from the gold layer."""
    n_cases = len(fact_case_summary)
    rework_rate = fact_case_summary["has_rework"].mean() * 100
    happy_rate = fact_case_summary["is_happy_path"].mean() * 100
    avg_duration = fact_case_summary["case_duration_days"].mean()
    compliance_rate = fact_compliance["passed"].mean() * 100
    touchless_rate = (fact_case_summary["touchless_ratio"] == 1.0).mean() * 100

    logger.info("=" * 60)
    logger.info("GOLD LAYER KPIs")
    logger.info("  Total cases:           %d", n_cases)
    logger.info("  Compliance rate:       %.1f%%", compliance_rate)
    logger.info("  Happy path rate:       %.1f%%", happy_rate)
    logger.info("  Rework rate:           %.1f%%", rework_rate)
    logger.info("  Touchless rate:        %.1f%%", touchless_rate)
    logger.info("  Avg case duration:     %.1f days", avg_duration)
    logger.info("=" * 60)
