#!/usr/bin/env python3
"""Generate a profiling report for the bronze layer data.

Outputs outputs/profiling_report.md with column types, null rates,
value distributions, activity frequencies, and timestamp range.

Usage:
  python scripts/profile_data.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import polars as pl

from src import config

logger = logging.getLogger(__name__)

# TODO: implement after Phase 1 (bronze parquet files must exist)


def main() -> None:
    """Entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not config.BRONZE_EVENTS.exists() or not config.BRONZE_CASES.exists():
        logger.error(
            "Bronze parquet files not found. Run --phase ingest first."
        )
        sys.exit(1)

    logger.info("Loading bronze data...")
    events = pl.read_parquet(config.BRONZE_EVENTS)
    cases = pl.read_parquet(config.BRONZE_CASES)
    logger.info("Events: %d rows, Cases: %d rows", len(events), len(cases))

    # TODO: generate full profiling report
    logger.warning("profile_data.py is a stub — full profiling not yet implemented.")


if __name__ == "__main__":
    main()
