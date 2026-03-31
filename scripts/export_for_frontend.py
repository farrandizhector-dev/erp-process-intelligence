#!/usr/bin/env python3
"""Export gold layer parquet files to JSON for the React frontend.

Reads gold parquet tables, aggregates and transforms them into the
JSON contracts defined in CONTEXT.md Section 10, and writes to
frontend/public/data/.

Target total payload: < 10 MB.

Usage:
  python scripts/export_for_frontend.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config

logger = logging.getLogger(__name__)

# TODO: implement after Phase 4 (gold layer must be complete)


def export_all() -> int:
    """Export all gold tables to frontend JSON files.

    Returns:
        Number of JSON files written.
    """
    logger.warning("export_for_frontend.py is a stub — implement after Phase 4.")
    return 0


def main() -> None:
    """Entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config.FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    files_written = export_all()
    logger.info("Exported %d JSON files to %s", files_written, config.FRONTEND_DATA_DIR)


if __name__ == "__main__":
    main()
