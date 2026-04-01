"""Write bronze layer parquet files from parsed XES DataFrames.

Validates row counts and schema before writing.
Logs schema, row counts, and key quality metrics.
"""

from __future__ import annotations

import logging

import polars as pl

from src import config

logger = logging.getLogger(__name__)


def write_bronze(
    events_df: pl.DataFrame,
    cases_df: pl.DataFrame,
    skip_validation: bool = False,
) -> None:
    """Write bronze parquet files and validate quality gates.

    Args:
        events_df: Events DataFrame from xes_parser.
        cases_df: Cases DataFrame from xes_parser.
        skip_validation: If True, skip row count and schema checks.

    Raises:
        ValueError: If quality gates fail and skip_validation is False.
    """
    config.BRONZE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Writing bronze_events.parquet (%d rows)…", len(events_df))
    events_df.write_parquet(config.BRONZE_EVENTS, compression="zstd")
    logger.info("bronze_events.parquet written: %.1f MB", config.BRONZE_EVENTS.stat().st_size / 1e6)
    _log_schema("bronze_events", events_df)

    logger.info("Writing bronze_cases.parquet (%d rows)…", len(cases_df))
    cases_df.write_parquet(config.BRONZE_CASES, compression="zstd")
    logger.info("bronze_cases.parquet written: %.1f MB", config.BRONZE_CASES.stat().st_size / 1e6)
    _log_schema("bronze_cases", cases_df)

    if not skip_validation:
        errors = validate_bronze(events_df, cases_df)
        if errors:
            for err in errors:
                logger.error("Quality gate FAILED: %s", err)
            raise ValueError("Bronze quality gates failed:\n" + "\n".join(errors))
        logger.info("All bronze quality gates PASSED.")
    else:
        logger.warning("Skipping bronze validation (--skip-validation flag).")

    logger.info("Bronze layer written successfully.")


def validate_bronze(events_df: pl.DataFrame, cases_df: pl.DataFrame) -> list[str]:
    """Run quality gates on bronze DataFrames.

    Args:
        events_df: Bronze events DataFrame.
        cases_df: Bronze cases DataFrame.

    Returns:
        List of error messages (empty if all gates pass).
    """
    errors: list[str] = []

    # --- Row count: events ---
    tolerance = int(config.EXPECTED_EVENT_COUNT * config.ROW_COUNT_TOLERANCE)
    if abs(len(events_df) - config.EXPECTED_EVENT_COUNT) > tolerance:
        errors.append(
            f"Event count {len(events_df):,} outside expected range "
            f"{config.EXPECTED_EVENT_COUNT:,} ± {tolerance:,}"
        )
    else:
        logger.info(
            "Event row count OK: %d (expected ~%d)",
            len(events_df),
            config.EXPECTED_EVENT_COUNT,
        )

    # --- Row count: cases ---
    tolerance_c = int(config.EXPECTED_CASE_COUNT * config.ROW_COUNT_TOLERANCE)
    if abs(len(cases_df) - config.EXPECTED_CASE_COUNT) > tolerance_c:
        errors.append(
            f"Case count {len(cases_df):,} outside expected range "
            f"{config.EXPECTED_CASE_COUNT:,} ± {tolerance_c:,}"
        )
    else:
        logger.info(
            "Case row count OK: %d (expected ~%d)",
            len(cases_df),
            config.EXPECTED_CASE_COUNT,
        )

    # --- No null case_id in events ---
    null_case_ids = events_df["case_id"].null_count()
    if null_case_ids > 0:
        errors.append(f"bronze_events has {null_case_ids:,} null case_id values.")
    else:
        logger.info("No null case_id in events: OK")

    # --- No null activity ---
    null_activity = events_df["activity"].null_count()
    if null_activity > 0:
        errors.append(f"bronze_events has {null_activity:,} null activity values.")
    else:
        logger.info("No null activity: OK")

    # --- Timestamp not null ---
    null_ts = events_df["timestamp"].null_count()
    null_rate = null_ts / len(events_df)
    if null_rate > 0.001:  # allow <0.1%
        errors.append(
            f"Timestamp null rate {null_rate:.3%} exceeds 0.1% threshold "
            f"({null_ts:,} nulls)."
        )
    else:
        logger.info("Timestamp null rate %.4f%%: OK", null_rate * 100)

    # --- All activities present (check against expected count) ---
    activity_count = events_df["activity"].n_unique()
    if activity_count < config.EXPECTED_ACTIVITY_COUNT:
        errors.append(
            f"Only {activity_count} unique activities found, expected "
            f"≥ {config.EXPECTED_ACTIVITY_COUNT}."
        )
    else:
        logger.info("Activity count %d ≥ %d: OK", activity_count, config.EXPECTED_ACTIVITY_COUNT)

    # --- Referential integrity ---
    event_case_ids = set(events_df["case_id"].drop_nulls().unique().to_list())
    case_ids = set(cases_df["case_id"].drop_nulls().unique().to_list())
    orphaned = event_case_ids - case_ids
    if orphaned:
        errors.append(
            f"{len(orphaned):,} event case_ids have no matching case row."
        )
    else:
        logger.info("Referential integrity OK: all event case_ids exist in cases.")

    return errors


def _log_schema(name: str, df: pl.DataFrame) -> None:
    """Log column names and dtypes for a DataFrame.

    Args:
        name: Table name for logging.
        df: DataFrame to describe.
    """
    logger.info("%s schema (%d cols):", name, len(df.columns))
    for col in df.columns:
        null_count = df[col].null_count()
        null_pct = null_count / len(df) * 100 if len(df) > 0 else 0
        logger.info("  %-40s %s  nulls=%d (%.1f%%)", col, df[col].dtype, null_count, null_pct)
