"""Resource workload, handoff, and batch/human pattern analysis."""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)


def build_dim_resource(silver_resources: pl.DataFrame) -> pl.DataFrame:
    """Build dim_resource from silver_resources.parquet.

    Args:
        silver_resources: silver_resources.parquet (one row per unique resource).

    Returns:
        dim_resource with computed primary_activities column (top 3 as string).
    """
    dim = silver_resources.with_columns(
        pl.col("activity_set")
        .list.sort()
        .list.head(3)
        .list.join(", ")
        .alias("primary_activities")
    ).drop("activity_set")

    logger.info(
        "dim_resource: %d resources (%d batch, %d human, %d unknown)",
        len(dim),
        dim.filter(pl.col("resource_type") == "batch").height,
        dim.filter(pl.col("resource_type") == "human").height,
        dim.filter(pl.col("resource_type") == "unknown").height,
    )
    return dim


def compute_handoff_metrics(events: pl.DataFrame) -> pl.DataFrame:
    """Compute handoff count per case (transitions where resource changes).

    Args:
        events: Silver events with case_id, resource, timestamp.

    Returns:
        DataFrame: case_id, handoff_count (UInt32).
    """
    df = events.sort(["case_id", "timestamp"])
    df = df.with_columns(
        pl.col("resource").shift(1).over("case_id").alias("prev_resource")
    )
    # First event per case has no previous — exclude those nulls
    df = df.filter(pl.col("prev_resource").is_not_null())
    handoffs = (
        df.with_columns(
            (pl.col("resource") != pl.col("prev_resource")).alias("is_handoff")
        )
        .group_by("case_id")
        .agg(pl.col("is_handoff").sum().cast(pl.UInt32).alias("handoff_count"))
    )
    all_cases = events.select("case_id").unique()
    result = all_cases.join(handoffs, on="case_id", how="left").with_columns(
        pl.col("handoff_count").fill_null(0).cast(pl.UInt32)
    )
    avg_handoffs = result["handoff_count"].mean()
    logger.info("Handoff analysis: avg %.1f handoffs per case", avg_handoffs)
    return result
