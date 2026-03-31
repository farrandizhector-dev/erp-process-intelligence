"""Classify P2P cases into the four BPI 2019 flow types."""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)

# Flow type constants
FLOW_3WAY_AFTER_GR = "3way_invoice_after_gr"
FLOW_3WAY_BEFORE_GR = "3way_invoice_before_gr"
FLOW_2WAY = "2way"
FLOW_CONSIGNMENT = "consignment"

# TODO: validate these rules against actual item_category values in Phase 1
# The item_category attribute in the XES may contain the four flow type strings directly.
ITEM_CATEGORY_TO_FLOW: dict[str, str] = {
    "3-way match, invoice after GR": FLOW_3WAY_AFTER_GR,
    "3-way match, invoice before GR": FLOW_3WAY_BEFORE_GR,
    "2-way match": FLOW_2WAY,
    "Consignment": FLOW_CONSIGNMENT,
}


def classify_flow_type(item_category: str | None) -> str:
    """Classify a case's flow type from its item_category attribute.

    Args:
        item_category: item_category trace attribute value.

    Returns:
        Flow type string or FLOW_3WAY_AFTER_GR as fallback.
    """
    if item_category is None:
        logger.debug("Null item_category — defaulting to 3way_after_gr")
        return FLOW_3WAY_AFTER_GR
    return ITEM_CATEGORY_TO_FLOW.get(item_category, FLOW_3WAY_AFTER_GR)


def classify_flow_types_column(cases: pl.DataFrame) -> pl.DataFrame:
    """Add flow_type column to cases DataFrame.

    Args:
        cases: Bronze cases DataFrame with 'item_category' column.

    Returns:
        Cases DataFrame with added 'flow_type' column.
    """
    return cases.with_columns(
        pl.col("item_category")
        .map_elements(classify_flow_type, return_dtype=pl.Utf8)
        .alias("flow_type")
    )
