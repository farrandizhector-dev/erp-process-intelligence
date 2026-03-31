"""Custom data quality assertions for layer transitions.

Used alongside Pandera schemas for business-rule validation.
"""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)

# TODO: implement in Phase 2


def check_referential_integrity(
    events: pl.DataFrame, cases: pl.DataFrame
) -> list[str]:
    """Check that every event's case_id exists in the cases table.

    Args:
        events: Events DataFrame with case_id column.
        cases: Cases DataFrame with case_id column.

    Returns:
        List of error messages (empty if no violations).
    """
    event_ids = set(events["case_id"].drop_nulls().unique().to_list())
    case_ids = set(cases["case_id"].drop_nulls().unique().to_list())
    orphaned = event_ids - case_ids
    if orphaned:
        return [f"Found {len(orphaned)} event case_ids with no matching case row."]
    return []


def check_null_rates(df: pl.DataFrame, max_null_rate: float = 0.01) -> list[str]:
    """Check that no column exceeds the maximum null rate.

    Args:
        df: DataFrame to check.
        max_null_rate: Maximum allowed fraction of nulls per column.

    Returns:
        List of error messages for columns exceeding the threshold.
    """
    errors = []
    total = len(df)
    if total == 0:
        return errors
    for col in df.columns:
        null_count = df[col].null_count()
        null_rate = null_count / total
        if null_rate > max_null_rate:
            errors.append(
                f"Column '{col}' null rate {null_rate:.1%} exceeds threshold {max_null_rate:.1%}"
            )
    return errors
