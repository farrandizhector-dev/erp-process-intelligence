"""Temporal feature derivation for silver layer events and cases."""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)

# TODO: implement in Phase 2


def enrich_events_temporal(events: pl.DataFrame) -> pl.DataFrame:
    """Add temporal columns to events DataFrame.

    Args:
        events: Bronze events DataFrame with timestamp column.

    Returns:
        Events DataFrame with added: timestamp_utc, date, hour,
        day_of_week, is_weekend, is_business_hours.
    """
    raise NotImplementedError("temporal_enrichment not yet implemented (Phase 2).")


def compute_case_metrics(events: pl.DataFrame) -> pl.DataFrame:
    """Compute case-level temporal metrics from event timestamps.

    Args:
        events: Events DataFrame with case_id and timestamp columns.

    Returns:
        DataFrame with one row per case: case_start, case_end,
        case_duration_days, event_count, activity_count, resource_count.
    """
    raise NotImplementedError("temporal_enrichment not yet implemented (Phase 2).")
