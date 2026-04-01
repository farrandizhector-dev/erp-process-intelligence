"""Build silver layer parquet files from bronze layer.

Reads bronze_events and bronze_cases, applies normalization,
enrichment, and classification, then writes four silver tables:
  - silver_events.parquet    (1,595,923 rows + enrichment columns)
  - silver_cases.parquet     (251,734 rows + flow_type + case metrics)
  - silver_resources.parquet (one row per unique resource)
  - silver_activities.parquet (one row per activity, 42 rows)

Silver transformations applied:
  1. Drop `user` column (identical to `resource` in this dataset)
  2. Classify resource_type from resource name pattern
  3. Classify flow_type from item_category
  4. Temporal enrichment (timestamp_utc, date, hour, weekday, etc.)
  5. Event ordering per case
  6. Time-since-prev-event per case
  7. Case-level metrics (start, end, duration, counts, variant_id)
  8. Aggregate resource and activity tables
"""

from __future__ import annotations

import logging

import polars as pl

from src import config
from src.transformation.flow_type_classifier import classify_flow_types_column
from src.transformation.resource_classifier import classify_resources_column
from src.transformation.temporal_enrichment import (
    compute_case_metrics,
    compute_silver_activities,
    compute_silver_resources,
    enrich_events_temporal,
)

logger = logging.getLogger(__name__)

# Ordered column list for silver_events
SILVER_EVENTS_COLS = [
    "case_id",
    "activity",
    "timestamp",
    "timestamp_utc",
    "date",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_business_hours",
    "is_timestamp_anomaly",
    "resource",
    "resource_type",
    "event_value",
    "event_order",
    "time_since_case_start",
    "time_since_prev_event",
]

# Ordered column list for silver_cases
SILVER_CASES_COLS = [
    "case_id",
    "purchasing_document",
    "item",
    "item_type",
    "gr_based_iv",
    "goods_receipt",
    "source_system",
    "doc_category_name",
    "company",
    "spend_classification",
    "spend_area",
    "sub_spend_area",
    "vendor",
    "vendor_name",
    "document_type",
    "item_category",
    "flow_type",
    "case_start",
    "case_end",
    "case_duration_days",
    "event_count",
    "activity_count",
    "resource_count",
    "has_batch_activity",
    "variant_id",
]


def build_silver(skip_validation: bool = False) -> tuple[int, int]:
    """Build silver layer from bronze parquet files.

    Reads bronze_events.parquet and bronze_cases.parquet, applies all
    silver-layer transformations, and writes four silver parquet tables.

    Args:
        skip_validation: If True, skip Pandera schema validation.

    Returns:
        Tuple of (rows_read, rows_written).

    Raises:
        FileNotFoundError: If bronze parquet files are missing.
        ValueError: If quality gates fail and skip_validation is False.
    """
    # ------------------------------------------------------------------
    # 1. Load bronze
    # ------------------------------------------------------------------
    if not config.BRONZE_EVENTS.exists() or not config.BRONZE_CASES.exists():
        raise FileNotFoundError(
            "Bronze parquet files not found. Run --phase ingest first."
        )

    logger.info("Loading bronze_events: %s", config.BRONZE_EVENTS)
    events = pl.read_parquet(config.BRONZE_EVENTS)
    logger.info("Loaded %d bronze events", len(events))

    logger.info("Loading bronze_cases: %s", config.BRONZE_CASES)
    cases = pl.read_parquet(config.BRONZE_CASES)
    logger.info("Loaded %d bronze cases", len(cases))

    rows_read = len(events) + len(cases)

    # ------------------------------------------------------------------
    # 2. Events: drop user column (redundant with resource)
    # ------------------------------------------------------------------
    if "user" in events.columns:
        events = events.drop("user")
        logger.info("Dropped 'user' column (identical to 'resource' in this dataset)")

    # ------------------------------------------------------------------
    # 3. Events: classify resource_type
    # ------------------------------------------------------------------
    events = classify_resources_column(events)
    rt_counts = events["resource_type"].value_counts()
    for row in rt_counts.iter_rows(named=True):
        logger.info("  resource_type %-10s: %d events", row["resource_type"], row["count"])

    # ------------------------------------------------------------------
    # 4. Events: temporal enrichment
    # ------------------------------------------------------------------
    events = enrich_events_temporal(events)

    # ------------------------------------------------------------------
    # 5. Reorder event columns
    # ------------------------------------------------------------------
    present_cols = [c for c in SILVER_EVENTS_COLS if c in events.columns]
    events = events.select(present_cols)

    # ------------------------------------------------------------------
    # 6. Cases: classify flow_type
    # ------------------------------------------------------------------
    cases = classify_flow_types_column(cases)
    flow_dist = cases["flow_type"].value_counts().sort("count", descending=True)
    for row in flow_dist.iter_rows(named=True):
        pct = row["count"] / len(cases) * 100
        logger.info("  flow_type %-35s: %6d cases (%.1f%%)", row["flow_type"], row["count"], pct)

    # ------------------------------------------------------------------
    # 7. Cases: compute case-level metrics (join from events)
    # ------------------------------------------------------------------
    case_metrics = compute_case_metrics(events)
    logger.info("Case metrics computed: %d rows", len(case_metrics))

    # Join case metrics into cases
    cases = cases.join(case_metrics, on="case_id", how="left")

    # Reorder case columns
    present_case_cols = [c for c in SILVER_CASES_COLS if c in cases.columns]
    cases = cases.select(present_case_cols)

    # ------------------------------------------------------------------
    # 8. Build silver_resources
    # ------------------------------------------------------------------
    resources = compute_silver_resources(events)

    # ------------------------------------------------------------------
    # 9. Build silver_activities
    # ------------------------------------------------------------------
    activities = compute_silver_activities(events, total_cases=len(cases))

    # ------------------------------------------------------------------
    # 10. Quality validation (pre-write)
    # ------------------------------------------------------------------
    if not skip_validation:
        errors = _validate_silver(events, cases)
        if errors:
            for err in errors:
                logger.error("Silver quality gate FAILED: %s", err)
            raise ValueError("Silver quality gates failed:\n" + "\n".join(errors))
        logger.info("All silver quality gates PASSED.")
    else:
        logger.warning("Skipping silver validation (--skip-validation flag).")

    # ------------------------------------------------------------------
    # 11. Write silver parquet files
    # ------------------------------------------------------------------
    config.SILVER_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Writing silver_events.parquet (%d rows)...", len(events))
    events.write_parquet(config.SILVER_EVENTS, compression="zstd")
    logger.info(
        "silver_events.parquet written: %.1f MB",
        config.SILVER_EVENTS.stat().st_size / 1e6,
    )

    logger.info("Writing silver_cases.parquet (%d rows)...", len(cases))
    cases.write_parquet(config.SILVER_CASES, compression="zstd")
    logger.info(
        "silver_cases.parquet written: %.1f MB",
        config.SILVER_CASES.stat().st_size / 1e6,
    )

    logger.info("Writing silver_resources.parquet (%d rows)...", len(resources))
    resources.write_parquet(config.SILVER_RESOURCES, compression="zstd")
    logger.info(
        "silver_resources.parquet written: %.1f MB",
        config.SILVER_RESOURCES.stat().st_size / 1e6,
    )

    logger.info("Writing silver_activities.parquet (%d rows)...", len(activities))
    activities.write_parquet(config.SILVER_ACTIVITIES, compression="zstd")
    logger.info(
        "silver_activities.parquet written: %.1f MB",
        config.SILVER_ACTIVITIES.stat().st_size / 1e6,
    )

    rows_written = len(events) + len(cases) + len(resources) + len(activities)
    logger.info("Silver layer complete: %d rows written across 4 tables.", rows_written)

    return rows_read, rows_written


def _validate_silver(
    events: pl.DataFrame,
    cases: pl.DataFrame,
) -> list[str]:
    """Run quality gates on silver DataFrames before writing.

    Args:
        events: Silver events DataFrame.
        cases: Silver cases DataFrame.

    Returns:
        List of error messages (empty if all gates pass).
    """
    errors: list[str] = []

    # --- Event count preserved from bronze ---
    tolerance = int(config.EXPECTED_EVENT_COUNT * config.ROW_COUNT_TOLERANCE)
    if abs(len(events) - config.EXPECTED_EVENT_COUNT) > tolerance:
        errors.append(
            f"Silver event count {len(events):,} differs from bronze expected "
            f"{config.EXPECTED_EVENT_COUNT:,} by more than {tolerance:,}"
        )
    else:
        logger.info("Silver event row count OK: %d", len(events))

    # --- Case count preserved ---
    tolerance_c = int(config.EXPECTED_CASE_COUNT * config.ROW_COUNT_TOLERANCE)
    if abs(len(cases) - config.EXPECTED_CASE_COUNT) > tolerance_c:
        errors.append(
            f"Silver case count {len(cases):,} differs from expected "
            f"{config.EXPECTED_CASE_COUNT:,} by more than {tolerance_c:,}"
        )
    else:
        logger.info("Silver case row count OK: %d", len(cases))

    # --- flow_type assigned for 100% of cases ---
    null_flow = cases["flow_type"].null_count()
    if null_flow > 0:
        errors.append(f"flow_type is null for {null_flow:,} cases")
    else:
        logger.info("flow_type: no nulls OK")

    # --- resource_type classified for all events ---
    null_rt = events["resource_type"].null_count()
    if null_rt > 0:
        errors.append(f"resource_type is null for {null_rt:,} events")
    else:
        logger.info("resource_type: no nulls OK")

    valid_rt = {"human", "batch", "unknown"}
    bad_rt = set(events["resource_type"].drop_nulls().unique().to_list()) - valid_rt
    if bad_rt:
        errors.append(f"Unexpected resource_type values: {bad_rt}")

    # --- event_order is positive ---
    if events["event_order"].min() < 1:
        errors.append("event_order has values < 1")
    else:
        logger.info("event_order min=1 OK")

    # --- case_duration_days >= 0 ---
    neg_dur = cases.filter(pl.col("case_duration_days") < 0)
    if len(neg_dur) > 0:
        errors.append(f"{len(neg_dur):,} cases have negative case_duration_days")
    else:
        logger.info("case_duration_days: all >= 0 OK")

    # --- No null variant_id ---
    null_vid = cases["variant_id"].null_count()
    if null_vid > 0:
        errors.append(f"variant_id is null for {null_vid:,} cases")
    else:
        logger.info("variant_id: no nulls OK")

    # --- Timestamp anomaly count sanity check ---
    n_anomalous = events.filter(pl.col("is_timestamp_anomaly")).height
    logger.info("Timestamp anomalies flagged: %d events (expected ~86)", n_anomalous)

    return errors
