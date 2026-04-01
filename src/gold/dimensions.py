"""Gold layer dimension table builders."""

from __future__ import annotations

import json
import logging
from datetime import date

import polars as pl

from src import config

logger = logging.getLogger(__name__)


def build_dim_activity(silver_activities: pl.DataFrame) -> pl.DataFrame:
    """Build dim_activity from silver_activities + activity_stage_mapping.json.

    Args:
        silver_activities: silver_activities.parquet (42 rows).

    Returns:
        dim_activity: activity, stage, frequency, case_coverage,
        typically_batch, typically_human, median_duration_to_next,
        p90_duration_to_next.
    """
    stage_map: dict[str, str] = {}
    if config.ACTIVITY_STAGE_MAPPING.exists():
        with config.ACTIVITY_STAGE_MAPPING.open(encoding="utf-8") as f:
            mapping_data = json.load(f)
        stage_map = mapping_data.get("mapping", {})

    dim = silver_activities.with_columns(
        pl.col("activity")
        .map_elements(
            lambda a: stage_map.get(str(a), "S0_UNKNOWN"), return_dtype=pl.Utf8
        )
        .alias("stage")
    )

    unknown_stages = dim.filter(pl.col("stage") == "S0_UNKNOWN")["activity"].to_list()
    if unknown_stages:
        logger.warning("Activities with unknown stage: %s", unknown_stages)
    else:
        logger.info("dim_activity: all %d activities mapped to stages.", len(dim))

    return dim.sort("frequency", descending=True)


def build_dim_company(cases: pl.DataFrame) -> pl.DataFrame:
    """Build dim_company from silver_cases.

    Args:
        cases: Silver cases with company, flow_type, case_duration_days,
               compliance-related columns (if present).

    Returns:
        dim_company: one row per company with aggregate metrics.
    """
    dim = (
        cases.group_by("company")
        .agg(
            [
                pl.len().alias("case_count"),
                pl.col("case_duration_days").mean().alias("avg_case_duration"),
                pl.col("case_duration_days").median().alias("median_case_duration"),
                pl.col("flow_type").mode().first().alias("primary_flow_type"),
            ]
        )
        .sort("case_count", descending=True)
    )
    logger.info("dim_company: %d companies", len(dim))
    return dim


def build_dim_vendor(cases: pl.DataFrame) -> pl.DataFrame:
    """Build dim_vendor from silver_cases.

    Args:
        cases: Silver cases with vendor, vendor_name, case_duration_days.

    Returns:
        dim_vendor: one row per vendor with aggregate metrics.
    """
    dim = (
        cases.group_by(["vendor", "vendor_name"])
        .agg(
            [
                pl.len().alias("case_count"),
                pl.col("case_duration_days").mean().alias("avg_case_duration"),
                pl.col("case_duration_days").median().alias("median_case_duration"),
            ]
        )
        .sort("case_count", descending=True)
    )
    logger.info("dim_vendor: %d vendors", len(dim))
    return dim


def build_dim_calendar(date_min: date, date_max: date) -> pl.DataFrame:
    """Build dim_calendar covering the date range of the dataset.

    Args:
        date_min: First date in dataset.
        date_max: Last date in dataset.

    Returns:
        dim_calendar: one row per date with temporal flags.
    """
    dates = pl.date_range(date_min, date_max, interval="1d", eager=True)
    dim = pl.DataFrame({"date": dates})
    dim = dim.with_columns(
        [
            pl.col("date").dt.year().alias("year"),
            pl.col("date").dt.month().cast(pl.Int8).alias("month"),
            pl.col("date").dt.quarter().cast(pl.Int8).alias("quarter"),
            pl.col("date").dt.weekday().cast(pl.Int8).alias("day_of_week"),
            (pl.col("date").dt.weekday() >= 5).alias("is_weekend"),
            (pl.col("date").dt.weekday() < 5).alias("is_business_day"),
        ]
    )
    logger.info("dim_calendar: %d dates (%s to %s)", len(dim), date_min, date_max)
    return dim
