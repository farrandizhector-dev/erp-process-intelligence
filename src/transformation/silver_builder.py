"""Build silver layer parquet files from bronze layer.

Applies normalization, enrichment, and classification transforms.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# TODO: implement in Phase 2


def build_silver(skip_validation: bool = False) -> tuple[int, int]:
    """Build silver layer from bronze parquet files.

    Args:
        skip_validation: If True, skip Pandera schema validation.

    Returns:
        Tuple of (rows_read, rows_written).
    """
    raise NotImplementedError("silver_builder.build_silver not yet implemented (Phase 2).")
