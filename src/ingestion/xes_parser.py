"""Parse a BPI Challenge 2019 XES file into Polars DataFrames.

Uses pm4py for IEEE-XES standard parsing. Extracts trace-level (case)
attributes and event-level attributes into separate DataFrames.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

# TODO: implement in Phase 1


def parse_xes(xes_path: Path) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Parse XES file and return (events_df, cases_df).

    Args:
        xes_path: Path to the .xes file.

    Returns:
        Tuple of (events DataFrame, cases DataFrame) in bronze schema.

    Raises:
        FileNotFoundError: If xes_path does not exist.
        RuntimeError: If pm4py parsing fails.
    """
    if not xes_path.exists():
        raise FileNotFoundError(f"XES file not found: {xes_path}")

    logger.info("Parsing XES file: %s", xes_path)
    # TODO: implement using pm4py
    raise NotImplementedError("xes_parser.parse_xes is not yet implemented (Phase 1 task).")
