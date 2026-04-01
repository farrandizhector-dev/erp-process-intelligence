"""Throughput time and bottleneck analysis.

Computes wait times between consecutive activities (transitions) and
identifies bottleneck transitions based on configurable P90 thresholds.
"""

from __future__ import annotations

import logging

import polars as pl

from src import config

logger = logging.getLogger(__name__)


def build_transitions(events: pl.DataFrame) -> pl.DataFrame:
    """Build all consecutive activity transitions with wait times.

    For each event in a case, computes the wait until the next event.
    Last event per case has no next event (dropped).

    Args:
        events: Silver events (case_id, activity, timestamp, flow_type if available).

    Returns:
        Transitions DataFrame: case_id, from_activity, to_activity,
        wait_hours, flow_type (if present in events).
    """
    df = events.sort(["case_id", "timestamp"])

    df = df.with_columns(
        [
            pl.col("activity").shift(-1).over("case_id").alias("to_activity"),
            pl.col("timestamp").shift(-1).over("case_id").alias("next_ts"),
        ]
    )
    df = df.filter(pl.col("to_activity").is_not_null())

    df = df.with_columns(
        (
            (pl.col("next_ts") - pl.col("timestamp")).dt.total_seconds() / 3600.0
        ).alias("wait_hours")
    )
    df = df.filter(pl.col("wait_hours") >= 0)

    # Select relevant columns
    select_cols = ["case_id", "activity", "to_activity", "wait_hours"]
    if "flow_type" in df.columns:
        select_cols.append("flow_type")

    df = df.select(select_cols).rename({"activity": "from_activity"})

    logger.info("Built %d transitions (excluding last event per case)", len(df))
    return df


def build_bottleneck_table(
    transitions: pl.DataFrame,
    min_transition_count: int = 100,
) -> pl.DataFrame:
    """Aggregate transitions into bottleneck analysis table.

    Groups transitions by (from_activity, to_activity), computes statistics,
    and flags bottlenecks where P90 wait time exceeds the configured threshold.

    Args:
        transitions: Output of build_transitions().
        min_transition_count: Minimum occurrences to include a transition.

    Returns:
        fact_bottleneck_analysis DataFrame with bottleneck flags and ranks.
    """
    agg = (
        transitions.group_by(["from_activity", "to_activity"])
        .agg(
            [
                pl.len().alias("transition_count"),
                pl.col("wait_hours").median().alias("median_wait_hours"),
                pl.col("wait_hours").quantile(0.90).alias("p90_wait_hours"),
                pl.col("wait_hours").max().alias("max_wait_hours"),
            ]
        )
        .filter(pl.col("transition_count") >= min_transition_count)
        .sort("transition_count", descending=True)
    )

    threshold = config.BOTTLENECK_THRESHOLD_HOURS
    agg = agg.with_columns(
        (pl.col("p90_wait_hours") > threshold).alias("is_bottleneck")
    )

    # Rank bottlenecks by impact = transition_count × median_wait_hours (more impact = worse)
    bottlenecks_only = agg.filter(pl.col("is_bottleneck"))
    if len(bottlenecks_only) > 0:
        agg = agg.with_columns(
            pl.when(pl.col("is_bottleneck"))
            .then(
                pl.col("p90_wait_hours")
                .rank("ordinal", descending=True)
                .over(pl.lit(True))
            )
            .otherwise(pl.lit(None))
            .cast(pl.UInt16)
            .alias("bottleneck_rank")
        )
    else:
        agg = agg.with_columns(pl.lit(None).cast(pl.UInt16).alias("bottleneck_rank"))

    n_bottlenecks = agg.filter(pl.col("is_bottleneck")).height
    logger.info(
        "Bottleneck table: %d transitions (threshold=%.0fh), %d bottlenecks",
        len(agg),
        threshold,
        n_bottlenecks,
    )
    return agg


def build_bottleneck_table_by_flow_type(
    transitions: pl.DataFrame,
    min_transition_count: int = 50,
) -> pl.DataFrame:
    """Build bottleneck table segmented by flow_type.

    Requires transitions to have a flow_type column (joined from cases).

    Args:
        transitions: Transitions with flow_type column.
        min_transition_count: Minimum occurrences per (flow_type, transition) pair.

    Returns:
        DataFrame: flow_type, from_activity, to_activity, transition_count,
        median_wait_hours, p90_wait_hours.
    """
    if "flow_type" not in transitions.columns:
        raise ValueError("transitions must have a flow_type column for segmented analysis.")

    agg = (
        transitions.group_by(["flow_type", "from_activity", "to_activity"])
        .agg(
            [
                pl.len().alias("transition_count"),
                pl.col("wait_hours").median().alias("median_wait_hours"),
                pl.col("wait_hours").quantile(0.90).alias("p90_wait_hours"),
            ]
        )
        .filter(pl.col("transition_count") >= min_transition_count)
        .sort(["flow_type", "median_wait_hours"], descending=[False, True])
    )
    return agg


def compute_case_active_waiting_time(
    events: pl.DataFrame,
) -> pl.DataFrame:
    """Compute active vs waiting time split per case.

    Active time = sum of waits during business hours.
    Waiting time = total duration - active time.

    Args:
        events: Silver events with time_since_prev_event, is_business_hours, case_id.

    Returns:
        DataFrame: case_id, total_wait_hours, business_hours_wait_hours.
    """
    ev = events.filter(pl.col("time_since_prev_event").is_not_null())

    # Convert Duration to hours (total_seconds / 3600)
    ev = ev.with_columns(
        (pl.col("time_since_prev_event").dt.total_seconds() / 3600.0).alias("wait_h")
    )

    result = (
        ev.group_by("case_id")
        .agg(
            [
                pl.col("wait_h").sum().alias("total_wait_hours"),
                pl.col("wait_h")
                .filter(pl.col("is_business_hours"))
                .sum()
                .alias("business_hours_wait_hours"),
            ]
        )
    )
    return result
