"""Shared pytest fixtures for all test modules.

All fixtures use synthetic data — no dependency on the 728 MB XES file.
Tests can run in CI without the raw dataset present.

Resource naming patterns confirmed from Phase 1 XES inspection:
  - Batch: batch_00, batch_01, ..., batch_13  (lowercase "batch_" prefix)
  - Human: user_000, user_001, ...            (lowercase "user_" prefix)
  - Unknown: "NONE"                           (vendor-initiated events)

Activity names are actual names from BPI Challenge 2019 XES (Phase 1 confirmed).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import pytest


@pytest.fixture
def sample_bronze_events() -> pl.DataFrame:
    """Minimal bronze events for unit testing. 3 cases, 15 events.

    Uses actual activity names and resource patterns from BPI 2019 XES.

    Cases:
    - DOC1_ITEM1: happy path 3-way match after GR (5 events)
    - DOC1_ITEM2: 2-way match (4 events)
    - DOC2_ITEM1: rework case — invoice cancelled and re-entered (6 events)
    """
    base_time = datetime(2018, 6, 1, 9, 0, 0)
    return pl.DataFrame(
        {
            "case_id": (
                ["DOC1_ITEM1"] * 5 + ["DOC1_ITEM2"] * 4 + ["DOC2_ITEM1"] * 6
            ),
            "activity": [
                # Case 1: happy path 3-way after GR (5 distinct activities)
                "Create Purchase Order Item",
                "Record Goods Receipt",
                "Vendor creates invoice",
                "Record Invoice Receipt",
                "Clear Invoice",
                # Case 2: 2-way match (4 distinct activities)
                "Create Purchase Order Item",
                "Vendor creates invoice",
                "Record Invoice Receipt",
                "Clear Invoice",
                # Case 3: rework — invoice cancelled then re-entered
                "Create Purchase Order Item",
                "Record Goods Receipt",
                "Record Invoice Receipt",
                "Cancel Invoice Receipt",
                "Record Invoice Receipt",
                "Clear Invoice",
            ],
            "timestamp": (
                [base_time + timedelta(hours=i * 24) for i in range(5)]
                + [base_time + timedelta(hours=i * 24) for i in range(4)]
                + [base_time + timedelta(hours=i * 24) for i in range(6)]
            ),
            "resource": [
                # Case 1 — mix of user_, batch_, and NONE (vendor)
                "user_001", "batch_06", "NONE", "user_002", "batch_00",
                # Case 2
                "user_001", "NONE", "user_002", "batch_00",
                # Case 3 — rework by human, cleared by batch
                "user_001", "batch_06", "user_003", "user_003", "user_003", "batch_00",
            ],
            "user": [
                "user_001", "batch_06", "NONE", "user_002", "batch_00",
                "user_001", "NONE", "user_002", "batch_00",
                "user_001", "batch_06", "user_003", "user_003", "user_003", "batch_00",
            ],
            "event_value": [
                1000.0, 1000.0, 1000.0, 1000.0, 0.0,
                500.0, 500.0, 500.0, 0.0,
                2000.0, 2000.0, 1800.0, -1800.0, 2000.0, 2000.0,
            ],
        }
    )


@pytest.fixture
def sample_bronze_cases() -> pl.DataFrame:
    """Minimal bronze cases matching sample_bronze_events."""
    return pl.DataFrame(
        {
            "case_id": ["DOC1_ITEM1", "DOC1_ITEM2", "DOC2_ITEM1"],
            "purchasing_document": ["DOC1", "DOC1", "DOC2"],
            "item": ["00001", "00002", "00001"],
            "item_type": ["Standard", "Standard", "Standard"],
            "gr_based_iv": [True, False, True],
            "goods_receipt": [True, False, True],
            "source_system": ["sourceSystemID_0000", "sourceSystemID_0000", "sourceSystemID_0001"],
            "doc_category_name": ["Purchase order", "Purchase order", "Purchase order"],
            "company": ["companyID_0000", "companyID_0000", "companyID_0001"],
            "spend_classification": ["NPR", "NPR", "PR"],
            "spend_area": ["Raw Materials", "Raw Materials", "Services"],
            "sub_spend_area": ["Chemicals", "Chemicals", "Logistics"],
            "vendor": ["vendorID_0000", "vendorID_0001", "vendorID_0000"],
            "vendor_name": ["vendor_0000", "vendor_0001", "vendor_0000"],
            "document_type": ["EC Purchase order", "EC Purchase order", "EC Purchase order"],
            "item_category": [
                "3-way match, invoice after GR",
                "2-way match",
                "3-way match, invoice after GR",
            ],
        }
    )


@pytest.fixture
def sample_silver_events(sample_bronze_events: pl.DataFrame) -> pl.DataFrame:
    """Silver events with enrichment columns for testing analytics.

    resource_type uses real patterns:  batch_ → "batch",  user_ → "human",  NONE → "unknown"
    """
    return sample_bronze_events.with_columns(
        [
            pl.col("resource")
            .map_elements(
                lambda r: (
                    "batch" if str(r).lower().startswith("batch_")
                    else "human" if str(r).lower().startswith("user_")
                    else "unknown"
                ),
                return_dtype=pl.Utf8,
            )
            .alias("resource_type"),
            pl.lit("S1").alias("process_stage"),  # simplified for tests
            pl.col("timestamp")
            .rank("ordinal")
            .over("case_id")
            .cast(pl.UInt32)
            .alias("event_order"),
            pl.col("timestamp")
            .dt.replace_time_zone("UTC")
            .alias("timestamp_utc"),
            pl.col("timestamp").dt.date().alias("date"),
            pl.col("timestamp").dt.hour().cast(pl.Int8).alias("hour"),
            pl.col("timestamp")
            .dt.weekday()
            .cast(pl.Int8)
            .alias("day_of_week"),
        ]
    )


@pytest.fixture
def sample_silver_cases(sample_bronze_cases: pl.DataFrame) -> pl.DataFrame:
    """Silver cases with flow_type and case metrics for testing analytics."""
    return sample_bronze_cases.with_columns(
        [
            pl.Series(
                "flow_type",
                [
                    "3way_invoice_after_gr",
                    "2way",
                    "3way_invoice_after_gr",
                ],
            ),
            pl.Series(
                "case_start",
                [
                    datetime(2018, 6, 1, 9, 0, 0),
                    datetime(2018, 6, 1, 9, 0, 0),
                    datetime(2018, 6, 1, 9, 0, 0),
                ],
            ),
            pl.Series(
                "case_end",
                [
                    datetime(2018, 6, 5, 9, 0, 0),
                    datetime(2018, 6, 4, 9, 0, 0),
                    datetime(2018, 6, 6, 9, 0, 0),
                ],
            ),
            pl.Series("case_duration_days", [4.0, 3.0, 5.0]),
            pl.Series("event_count", [5, 4, 6], dtype=pl.UInt32),
            pl.Series("activity_count", [5, 4, 5], dtype=pl.UInt32),
            pl.Series("resource_count", [3, 3, 3], dtype=pl.UInt32),
            pl.Series("has_batch_activity", [True, True, True]),
            pl.Series(
                "variant_id",
                ["VARIANT_A", "VARIANT_B", "VARIANT_C"],
            ),
        ]
    )
