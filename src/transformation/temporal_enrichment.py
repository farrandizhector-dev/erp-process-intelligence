"""Temporal feature derivation for silver layer events and cases.

All temporal computations assume bronze timestamps are already in UTC
(confirmed from Phase 1: pm4py outputs UTC-aware timestamps, tz-localized
to None before Polars import, then re-attached as UTC in bronze_writer).
"""

from __future__ import annotations

import hashlib
import logging

import polars as pl

from src import config

logger = logging.getLogger(__name__)


def enrich_events_temporal(events: pl.DataFrame) -> pl.DataFrame:
    """Add temporal enrichment columns to events DataFrame.

    Adds: timestamp_utc, date, hour, day_of_week, is_weekend,
    is_business_hours, is_timestamp_anomaly, event_order,
    time_since_case_start, time_since_prev_event.

    Args:
        events: Bronze events DataFrame with case_id, timestamp, resource.

    Returns:
        Enriched events DataFrame (same row count).
    """
    # Sort by case_id + timestamp so shift-based operations are correct
    df = events.sort(["case_id", "timestamp"])

    # ------------------------------------------------------------------
    # Timestamp derived columns
    # ------------------------------------------------------------------
    # timestamp_utc: ensure timezone is UTC (already UTC in bronze, make explicit)
    ts_col = pl.col("timestamp")
    if df["timestamp"].dtype == pl.Datetime("us", None):
        # tz-naive but known to be UTC — attach timezone
        df = df.with_columns(
            ts_col.dt.replace_time_zone("UTC").alias("timestamp_utc")
        )
    else:
        df = df.with_columns(ts_col.alias("timestamp_utc"))

    df = df.with_columns(
        [
            pl.col("timestamp").dt.date().alias("date"),
            pl.col("timestamp").dt.hour().cast(pl.Int8).alias("hour"),
            # weekday(): 0=Monday, 6=Sunday (Polars convention)
            pl.col("timestamp").dt.weekday().cast(pl.Int8).alias("day_of_week"),
            # Anomaly flag: 86 events with 1948-01-26 timestamp (ERP placeholder)
            (pl.col("timestamp").dt.year() < 2015).alias("is_timestamp_anomaly"),
        ]
    )

    df = df.with_columns(
        [
            (pl.col("day_of_week") >= 5).alias("is_weekend"),
        ]
    )

    df = df.with_columns(
        [
            (
                (pl.col("hour") >= config.BUSINESS_HOURS_START)
                & (pl.col("hour") < config.BUSINESS_HOURS_END)
                & (~pl.col("is_weekend"))
            ).alias("is_business_hours"),
        ]
    )

    # ------------------------------------------------------------------
    # Event ordering within case (1-indexed, by timestamp)
    # ------------------------------------------------------------------
    df = df.with_columns(
        pl.col("timestamp")
        .rank("ordinal")
        .over("case_id")
        .cast(pl.UInt32)
        .alias("event_order")
    )

    # ------------------------------------------------------------------
    # Time durations
    # ------------------------------------------------------------------
    # time_since_case_start: elapsed from first event in case
    df = df.with_columns(
        (pl.col("timestamp") - pl.col("timestamp").min().over("case_id"))
        .alias("time_since_case_start")
    )

    # time_since_prev_event: gap from previous event in same case (null for first)
    df = df.with_columns(
        pl.col("timestamp").diff().over("case_id").alias("time_since_prev_event")
    )

    logger.info(
        "Temporal enrichment complete: %d rows, added timestamp_utc/date/hour/"
        "day_of_week/is_weekend/is_business_hours/is_timestamp_anomaly/"
        "event_order/time_since_case_start/time_since_prev_event",
        len(df),
    )
    return df


def compute_case_metrics(events: pl.DataFrame) -> pl.DataFrame:
    """Compute case-level temporal and structural metrics.

    Groups events by case_id and produces one row per case with:
    case_start, case_end, case_duration_days, event_count,
    activity_count, resource_count, has_batch_activity, variant_id.

    Args:
        events: Events DataFrame with case_id, timestamp, activity, resource.

    Returns:
        DataFrame with one row per case (251,734 rows for BPI 2019).
    """
    df_sorted = events.sort(["case_id", "timestamp"])

    case_metrics = df_sorted.group_by("case_id").agg(
        [
            pl.col("timestamp").min().alias("case_start"),
            pl.col("timestamp").max().alias("case_end"),
            pl.len().alias("event_count"),
            pl.col("activity").n_unique().alias("activity_count"),
            pl.col("resource").n_unique().alias("resource_count"),
            # has_batch_activity: any event performed by a batch user
            pl.col("resource")
            .map_elements(
                lambda resources: any(
                    str(r).lower().startswith("batch_") for r in resources if r is not None
                ),
                return_dtype=pl.Boolean,
            )
            .alias("has_batch_activity"),
            # Activity sequence for variant_id computation
            pl.col("activity").alias("activity_sequence"),
        ]
    )

    # case_duration_days: floating point days
    case_metrics = case_metrics.with_columns(
        (
            (pl.col("case_end") - pl.col("case_start")).dt.total_seconds() / 86_400.0
        ).alias("case_duration_days")
    )

    # event_count cast to UInt32
    case_metrics = case_metrics.with_columns(
        [
            pl.col("event_count").cast(pl.UInt32),
            pl.col("activity_count").cast(pl.UInt32),
            pl.col("resource_count").cast(pl.UInt32),
        ]
    )

    # variant_id: MD5 hash of pipe-joined ordered activity sequence
    case_metrics = case_metrics.with_columns(
        pl.col("activity_sequence")
        .map_elements(_compute_variant_id, return_dtype=pl.Utf8)
        .alias("variant_id")
    )

    # Drop the intermediate activity_sequence column
    case_metrics = case_metrics.drop("activity_sequence")

    logger.info(
        "Case metrics computed: %d cases, %d unique variants",
        len(case_metrics),
        case_metrics["variant_id"].n_unique(),
    )
    return case_metrics


def _compute_variant_id(activities: list[str] | None) -> str:
    """Compute a short MD5 hash for an ordered activity sequence.

    Args:
        activities: Ordered list of activity names for a case.

    Returns:
        12-character hex string identifying the variant.
    """
    if activities is None or len(activities) == 0:
        return "empty"
    sequence = "|".join(str(a) for a in activities)
    return hashlib.md5(sequence.encode()).hexdigest()[:12]


def compute_silver_resources(events: pl.DataFrame) -> pl.DataFrame:
    """Aggregate resource-level statistics from enriched events.

    Args:
        events: Silver events DataFrame (must have resource_type column).

    Returns:
        silver_resources DataFrame (one row per unique resource).
    """
    resources = (
        events.group_by("resource")
        .agg(
            [
                pl.col("resource_type").first().alias("resource_type"),
                pl.col("timestamp").min().alias("first_seen"),
                pl.col("timestamp").max().alias("last_seen"),
                pl.len().cast(pl.UInt64).alias("event_count"),
                pl.col("case_id").n_unique().cast(pl.UInt64).alias("case_count"),
                pl.col("activity").unique().alias("activity_set"),
            ]
        )
        .sort("event_count", descending=True)
    )
    logger.info("Resource table built: %d unique resources", len(resources))
    return resources


def compute_silver_activities(events: pl.DataFrame, total_cases: int) -> pl.DataFrame:
    """Aggregate activity-level statistics from enriched events.

    Args:
        events: Silver events DataFrame (must have resource_type, time_since_prev_event).
        total_cases: Total number of cases (for case_coverage denominator).

    Returns:
        silver_activities DataFrame (one row per activity, 42 rows for BPI 2019).
    """
    # Time to next event: shift(-1) within case to get the wait AFTER this activity
    df = events.sort(["case_id", "timestamp"])
    df = df.with_columns(
        (
            pl.col("timestamp").shift(-1).over("case_id") - pl.col("timestamp")
        )
        .dt.total_seconds()
        .alias("_seconds_to_next")
    )

    activities = df.group_by("activity").agg(
        [
            pl.len().cast(pl.UInt64).alias("frequency"),
            pl.col("case_id").n_unique().alias("_case_count"),
            # Median/P90 time to next activity (seconds, then convert to hours)
            pl.col("_seconds_to_next")
            .drop_nulls()
            .median()
            .alias("median_duration_to_next_s"),
            pl.col("_seconds_to_next")
            .drop_nulls()
            .quantile(0.90)
            .alias("p90_duration_to_next_s"),
            # Batch/human breakdown
            (pl.col("resource_type") == "batch").sum().alias("_batch_count"),
            (pl.col("resource_type") == "human").sum().alias("_human_count"),
        ]
    )

    activities = activities.with_columns(
        [
            (pl.col("_case_count").cast(pl.Float64) / total_cases).alias("case_coverage"),
            (pl.col("_batch_count").cast(pl.Float64) / pl.len().cast(pl.Float64)).alias(
                "_batch_ratio"
            ),
        ]
    )

    activities = activities.with_columns(
        [
            (pl.col("_batch_ratio") > 0.5).alias("typically_batch"),
            (pl.col("_batch_ratio") <= 0.5).alias("typically_human"),
            (pl.col("median_duration_to_next_s") / 3600.0).alias(
                "median_duration_to_next"
            ),
            (pl.col("p90_duration_to_next_s") / 3600.0).alias("p90_duration_to_next"),
        ]
    )

    # Drop temp columns
    activities = activities.drop(
        [
            "_case_count",
            "_batch_count",
            "_human_count",
            "_batch_ratio",
            "median_duration_to_next_s",
            "p90_duration_to_next_s",
        ]
    )

    activities = activities.sort("frequency", descending=True)

    logger.info("Activity table built: %d unique activities", len(activities))
    return activities
