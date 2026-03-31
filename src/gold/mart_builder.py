"""Orchestrate gold mart creation from silver layer."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# TODO: implement in Phase 3


def build_gold_marts(skip_validation: bool = False) -> int:
    """Build all gold layer fact and dimension tables.

    Args:
        skip_validation: Skip Pandera schema checks.

    Returns:
        Total rows written across all gold tables.
    """
    raise NotImplementedError("mart_builder.build_gold_marts not yet implemented (Phase 3).")


def run_analytics() -> int:
    """Run process mining analytics and write analytics fact tables.

    Returns:
        Total rows written.
    """
    raise NotImplementedError("mart_builder.run_analytics not yet implemented (Phase 3-4).")
