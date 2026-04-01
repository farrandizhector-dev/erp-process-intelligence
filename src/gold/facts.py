"""Gold layer fact table builders."""

from __future__ import annotations

import logging

import polars as pl

from src import config

logger = logging.getLogger(__name__)


def build_fact_event_log(
    events: pl.DataFrame,
    cases: pl.DataFrame,
    dim_activity: pl.DataFrame,
) -> pl.DataFrame:
    """Build fact_event_log: enriched event-level fact table.

    Joins silver_events with flow_type, company, vendor from silver_cases
    and process_stage from dim_activity.

    Args:
        events: Silver events.
        cases: Silver cases (for flow_type, company, vendor).
        dim_activity: dim_activity with stage column.

    Returns:
        fact_event_log DataFrame.
    """
    case_attrs = cases.select(["case_id", "flow_type", "company", "vendor"])
    act_stages = dim_activity.select(["activity", "stage"]).rename({"stage": "process_stage"})

    fact = (
        events
        .join(case_attrs, on="case_id", how="left")
        .join(act_stages, on="activity", how="left")
    )

    # Select and order columns
    cols = [
        "case_id", "activity", "process_stage", "timestamp", "timestamp_utc",
        "resource", "resource_type", "event_value",
        "event_order", "time_since_prev_event",
        "is_timestamp_anomaly", "is_business_hours",
        "flow_type", "company", "vendor",
    ]
    present = [c for c in cols if c in fact.columns]
    fact = fact.select(present)

    logger.info("fact_event_log: %d rows, %d columns", len(fact), len(fact.columns))
    return fact


def build_fact_case_summary(
    cases: pl.DataFrame,
    rework_df: pl.DataFrame,
    compliance_scores: pl.DataFrame,
    touchless_df: pl.DataFrame,
    is_happy_path_df: pl.DataFrame,
    handoff_df: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Build fact_case_summary: one row per case with all KPIs.

    Args:
        cases: Silver cases (base attributes + flow_type + case metrics).
        rework_df: Output of detect_rework() — case_id, rework_count, loop_count, has_rework.
        compliance_scores: Output of compute_case_compliance_scores() —
            case_id, compliance_score, compliance_flags.
        touchless_df: case_id, touchless_ratio.
        is_happy_path_df: case_id, is_happy_path.
        handoff_df: Optional case_id, handoff_count from compute_handoff_metrics().

    Returns:
        fact_case_summary DataFrame.
    """
    fact = (
        cases
        .join(rework_df.select(["case_id", "rework_count", "loop_count", "has_rework"]),
              on="case_id", how="left")
        .join(compliance_scores.select(["case_id", "compliance_score", "compliance_flags"]),
              on="case_id", how="left")
        .join(touchless_df.select(["case_id", "touchless_ratio"]),
              on="case_id", how="left")
        .join(is_happy_path_df.select(["case_id", "is_happy_path"]),
              on="case_id", how="left")
    )
    if handoff_df is not None:
        fact = fact.join(handoff_df.select(["case_id", "handoff_count"]),
                         on="case_id", how="left")

    # Fill nulls from left joins
    null_fills = [
        pl.col("rework_count").fill_null(0).cast(pl.UInt32),
        pl.col("loop_count").fill_null(0).cast(pl.UInt32),
        pl.col("has_rework").fill_null(False),
        pl.col("compliance_score").fill_null(1.0),
        pl.col("touchless_ratio").fill_null(0.0),
        pl.col("is_happy_path").fill_null(False),
    ]
    if "handoff_count" in fact.columns:
        null_fills.append(pl.col("handoff_count").fill_null(0).cast(pl.UInt32))
    fact = fact.with_columns(null_fills)

    # SLA risk: based on duration vs P75 per flow_type (threshold from config)
    p75_per_flow = (
        cases.group_by("flow_type")
        .agg(pl.col("case_duration_days").quantile(config.SLA_THRESHOLD_QUANTILE).alias("sla_threshold"))
    )
    fact = fact.join(p75_per_flow, on="flow_type", how="left")
    fact = fact.with_columns(
        pl.when(pl.col("case_duration_days") > pl.col("sla_threshold") * 1.5)
        .then(pl.lit("high"))
        .when(pl.col("case_duration_days") > pl.col("sla_threshold"))
        .then(pl.lit("medium"))
        .otherwise(pl.lit("low"))
        .alias("sla_risk")
    ).drop("sla_threshold")

    logger.info(
        "fact_case_summary: %d rows; rework_rate=%.1f%%; happy_path_rate=%.1f%%",
        len(fact),
        fact["has_rework"].mean() * 100,
        fact["is_happy_path"].mean() * 100,
    )
    return fact


def build_fact_variant_stats(variant_stats: pl.DataFrame) -> pl.DataFrame:
    """Persist variant stats DataFrame as gold fact table.

    Args:
        variant_stats: Output of compute_variant_stats().

    Returns:
        fact_variant_stats (same content, ensures correct column names).
    """
    logger.info("fact_variant_stats: %d variants", len(variant_stats))
    return variant_stats


def build_fact_compliance_checks(compliance_checks: pl.DataFrame) -> pl.DataFrame:
    """Persist compliance checks as gold fact table.

    Args:
        compliance_checks: Output of run_all_rules().

    Returns:
        fact_compliance_checks.
    """
    overall_pass_rate = compliance_checks["passed"].mean() * 100
    logger.info(
        "fact_compliance_checks: %d rows; overall_pass_rate=%.1f%%",
        len(compliance_checks),
        overall_pass_rate,
    )
    return compliance_checks


def build_fact_bottleneck_analysis(bottleneck_table: pl.DataFrame) -> pl.DataFrame:
    """Persist bottleneck table as gold fact table.

    Args:
        bottleneck_table: Output of build_bottleneck_table().

    Returns:
        fact_bottleneck_analysis.
    """
    n_bottlenecks = bottleneck_table.filter(pl.col("is_bottleneck")).height
    logger.info(
        "fact_bottleneck_analysis: %d transitions, %d flagged as bottlenecks",
        len(bottleneck_table),
        n_bottlenecks,
    )
    return bottleneck_table


def build_touchless_ratio(events: pl.DataFrame) -> pl.DataFrame:
    """Compute touchless_ratio per case.

    Touchless = 100% of events performed by batch resources.
    touchless_ratio = batch_events / total_events per case.

    Args:
        events: Silver events with resource_type, case_id.

    Returns:
        DataFrame: case_id, touchless_ratio (float 0-1).
    """
    return (
        events.group_by("case_id")
        .agg(
            [
                (pl.col("resource_type") == "batch").sum().cast(pl.Float64).alias("batch_count"),
                pl.len().cast(pl.Float64).alias("total_count"),
            ]
        )
        .with_columns(
            (pl.col("batch_count") / pl.col("total_count")).alias("touchless_ratio")
        )
        .select(["case_id", "touchless_ratio"])
    )
