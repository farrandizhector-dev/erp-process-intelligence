"""Write bronze layer parquet files from parsed XES DataFrames.

Validates row counts and schema before writing.
"""

from __future__ import annotations

import logging

import polars as pl

from src import config

logger = logging.getLogger(__name__)

# TODO: implement in Phase 1


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

    logger.info("Writing bronze_events.parquet (%d rows)", len(events_df))
    events_df.write_parquet(config.BRONZE_EVENTS, compression="zstd")

    logger.info("Writing bronze_cases.parquet (%d rows)", len(cases_df))
    cases_df.write_parquet(config.BRONZE_CASES, compression="zstd")

    if not skip_validation:
        _validate_bronze(events_df, cases_df)

    logger.info("Bronze layer written successfully.")


def _validate_bronze(events_df: pl.DataFrame, cases_df: pl.DataFrame) -> None:
    """Run quality gates on bronze DataFrames.

    Args:
        events_df: Bronze events DataFrame.
        cases_df: Bronze cases DataFrame.

    Raises:
        ValueError: If any quality gate fails.
    """
    tolerance = int(config.EXPECTED_EVENT_COUNT * config.ROW_COUNT_TOLERANCE)

    if abs(len(events_df) - config.EXPECTED_EVENT_COUNT) > tolerance:
        raise ValueError(
            f"Event count {len(events_df)} outside expected range "
            f"{config.EXPECTED_EVENT_COUNT} ± {tolerance}"
        )

    if events_df["case_id"].null_count() > 0:
        raise ValueError("Bronze events contain null case_id values.")

    if events_df["activity"].null_count() > 0:
        raise ValueError("Bronze events contain null activity values.")

    logger.info("Bronze quality gates passed.")
