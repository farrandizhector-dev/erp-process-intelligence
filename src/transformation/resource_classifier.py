"""Classify ERP resources as human, batch, or unknown."""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)

# TODO: implement in Phase 2 after inspecting actual resource names in XES


def classify_resource(resource: str | None) -> str:
    """Classify a single resource identifier.

    Args:
        resource: Resource name from org:resource XES attribute.

    Returns:
        One of "human", "batch", or "unknown".
    """
    if resource is None or resource == "" or resource.upper() in ("NONE", "NULL"):
        return "unknown"
    # Batch users have names starting with "BATCH" — confirmed after Phase 1 inspection
    if resource.upper().startswith("BATCH"):
        return "batch"
    return "human"


def classify_resources_column(events: pl.DataFrame) -> pl.DataFrame:
    """Add resource_type column to events DataFrame.

    Args:
        events: Events DataFrame with 'resource' column.

    Returns:
        Events DataFrame with added 'resource_type' column.
    """
    return events.with_columns(
        pl.col("resource")
        .map_elements(classify_resource, return_dtype=pl.Utf8)
        .alias("resource_type")
    )
