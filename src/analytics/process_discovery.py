"""Process discovery: variants, happy path, loop/rework detection, DFG.

All functions operate on Polars DataFrames loaded from silver parquet files.
Heavy aggregations use efficient group_by operations; no pm4py required here.
"""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)


def compute_variant_stats(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """Compute per-variant statistics.

    A variant is the ordered sequence of activities in a case.
    The happy path per flow_type is the most frequent variant within that flow_type.

    Args:
        events: Silver events (case_id, activity, timestamp, ...).
        cases: Silver cases (case_id, variant_id, flow_type, case_duration_days, ...).

    Returns:
        fact_variant_stats DataFrame — one row per unique variant.
        Columns: variant_id, variant_sequence (list), variant_length, case_count,
        case_percentage, median_duration_days, p90_duration_days,
        dominant_flow_type, is_happy_path.
    """
    logger.info("Computing variant statistics...")

    # Reconstruct activity sequences per case (sorted by timestamp)
    sequences = (
        events.sort(["case_id", "timestamp"])
        .group_by("case_id")
        .agg(pl.col("activity").alias("activity_sequence"))
    )

    # Join with case data
    case_data = cases.select(["case_id", "variant_id", "flow_type", "case_duration_days"])
    seq_with_variant = sequences.join(case_data, on="case_id", how="left")

    # Representative sequence per variant (first occurrence — all are identical by definition)
    variant_sequences = (
        seq_with_variant.group_by("variant_id")
        .agg(pl.col("activity_sequence").first())
    )

    # Aggregate stats per variant
    variant_stats = (
        case_data.group_by("variant_id")
        .agg(
            [
                pl.len().alias("case_count"),
                pl.col("case_duration_days").median().alias("median_duration_days"),
                pl.col("case_duration_days").quantile(0.90).alias("p90_duration_days"),
                # Dominant flow_type = most common flow_type for this variant
                pl.col("flow_type").mode().first().alias("dominant_flow_type"),
            ]
        )
    )

    # Add sequences and length
    variant_stats = variant_stats.join(variant_sequences, on="variant_id", how="left")
    total_cases = len(cases)
    variant_stats = variant_stats.with_columns(
        [
            (pl.col("case_count").cast(pl.Float64) / total_cases * 100.0).alias(
                "case_percentage"
            ),
            pl.col("activity_sequence")
            .list.len()
            .cast(pl.UInt16)
            .alias("variant_length"),
        ]
    )

    # Happy path per flow_type = variant with highest case_count for that flow_type
    # Build a mapping: flow_type → best variant_id
    happy_variants = (
        case_data.group_by(["flow_type", "variant_id"])
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
        .group_by("flow_type")
        .first()
        .select(["flow_type", "variant_id"])
        .rename({"variant_id": "happy_variant_id"})
    )
    # Tag variant as happy path if it's the top variant for its dominant_flow_type
    variant_stats = variant_stats.join(
        happy_variants,
        left_on="dominant_flow_type",
        right_on="flow_type",
        how="left",
    )
    variant_stats = variant_stats.with_columns(
        (pl.col("variant_id") == pl.col("happy_variant_id")).alias("is_happy_path")
    ).drop("happy_variant_id")

    variant_stats = variant_stats.sort("case_count", descending=True)
    n_happy = variant_stats.filter(pl.col("is_happy_path"))["case_count"].sum()
    logger.info(
        "Variant stats: %d unique variants; top-10 cover %.1f%% of cases; "
        "happy-path cases: %d",
        len(variant_stats),
        variant_stats.head(10)["case_percentage"].sum(),
        n_happy,
    )
    return variant_stats


def detect_rework(events: pl.DataFrame) -> pl.DataFrame:
    """Detect rework (repeated activities) per case.

    Rework = any activity that appears more than once in a case.
    loop_count = total number of "extra" executions summed over all reworked activities.

    Args:
        events: Silver events DataFrame.

    Returns:
        DataFrame with columns: case_id, rework_count, loop_count, has_rework.
        One row per case (including cases with zero rework).
    """
    # Count occurrences of each (case_id, activity) pair
    activity_counts = (
        events.group_by(["case_id", "activity"])
        .agg(pl.len().cast(pl.UInt32).alias("occurrences"))
    )

    # Rework: activities that appear more than once
    rework = (
        activity_counts.filter(pl.col("occurrences") > 1)
        .group_by("case_id")
        .agg(
            [
                pl.len().cast(pl.UInt32).alias("rework_count"),  # distinct reworked activities
                (pl.col("occurrences") - 1).sum().cast(pl.UInt32).alias("loop_count"),
            ]
        )
    )

    # All cases, even those with no rework
    all_cases = events.select("case_id").unique()
    result = all_cases.join(rework, on="case_id", how="left").with_columns(
        [
            pl.col("rework_count").fill_null(0).cast(pl.UInt32),
            pl.col("loop_count").fill_null(0).cast(pl.UInt32),
        ]
    )
    result = result.with_columns(
        (pl.col("rework_count") > 0).alias("has_rework")
    )

    n_rework = result.filter(pl.col("has_rework")).height
    logger.info(
        "Rework detection: %d / %d cases have rework (%.1f%%)",
        n_rework,
        len(result),
        n_rework / len(result) * 100,
    )
    return result


def build_dfg(events: pl.DataFrame) -> pl.DataFrame:
    """Build directly-follows graph (DFG) from events.

    For each consecutive pair of activities (A → B) within a case,
    compute: transition_count, median_wait_hours, p90_wait_hours, max_wait_hours.

    Args:
        events: Silver events with case_id, activity, timestamp, flow_type
                (flow_type joined from cases before calling this).

    Returns:
        DFG DataFrame: from_activity, to_activity, transition_count,
        median_wait_hours, p90_wait_hours, max_wait_hours.
    """
    df = events.sort(["case_id", "timestamp"])

    # Next activity and next timestamp within case
    df = df.with_columns(
        [
            pl.col("activity").shift(-1).over("case_id").alias("to_activity"),
            pl.col("timestamp").shift(-1).over("case_id").alias("next_ts"),
        ]
    )

    # Drop rows where next_activity is null (last event per case)
    transitions = df.filter(pl.col("to_activity").is_not_null())

    # Wait time in hours
    transitions = transitions.with_columns(
        (
            (pl.col("next_ts") - pl.col("timestamp")).dt.total_seconds() / 3600.0
        ).alias("wait_hours")
    )
    transitions = transitions.filter(pl.col("wait_hours") >= 0)

    # Rename for clarity
    transitions = transitions.rename({"activity": "from_activity"})

    # Aggregate DFG
    dfg = (
        transitions.group_by(["from_activity", "to_activity"])
        .agg(
            [
                pl.len().alias("transition_count"),
                pl.col("wait_hours").median().alias("median_wait_hours"),
                pl.col("wait_hours").quantile(0.90).alias("p90_wait_hours"),
                pl.col("wait_hours").max().alias("max_wait_hours"),
            ]
        )
        .sort("transition_count", descending=True)
    )

    logger.info("DFG built: %d unique transitions", len(dfg))
    return dfg


def build_is_happy_path_column(
    cases: pl.DataFrame,
    variant_stats: pl.DataFrame,
) -> pl.DataFrame:
    """Add is_happy_path column to cases based on variant stats.

    Args:
        cases: Silver cases with flow_type, variant_id.
        variant_stats: Output of compute_variant_stats (has is_happy_path per variant).

    Returns:
        Cases DataFrame with added is_happy_path column.
    """
    hp_map = variant_stats.select(["variant_id", "is_happy_path"])
    return cases.join(hp_map, on="variant_id", how="left").with_columns(
        pl.col("is_happy_path").fill_null(False)
    )
