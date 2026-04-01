"""Classify ERP resources as human, batch, or unknown.

Resource naming patterns confirmed from XES inspection (Phase 1, 2026-03-31):
  - Batch users:   batch_00, batch_01, ..., batch_13   (prefix "batch_", lowercase)
  - Human users:   user_000, user_001, ..., user_XXX   (prefix "user_")
  - Unknown:       "NONE" string — used when the action is vendor-initiated
                   (e.g. "Vendor creates invoice", "Vendor creates debit memo")
"""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)


def classify_resource(resource: str | None) -> str:
    """Classify a single resource identifier.

    Args:
        resource: Resource name from org:resource XES attribute.

    Returns:
        One of "human", "batch", or "unknown".
    """
    if resource is None or resource == "" or resource == "NONE":
        return "unknown"
    # Confirmed from XES: batch users use lowercase "batch_" prefix
    if resource.lower().startswith("batch_"):
        return "batch"
    # Human users use "user_" prefix
    if resource.lower().startswith("user_"):
        return "human"
    # Fallback for any unexpected patterns
    logger.debug("Unexpected resource pattern, classifying as unknown: %s", resource)
    return "unknown"


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
