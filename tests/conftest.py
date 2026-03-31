"""Shared pytest fixtures for all test modules.

All fixtures use synthetic data — no dependency on the 728 MB XES file.
Tests can run in CI without the raw dataset present.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import pytest


@pytest.fixture
def sample_bronze_events() -> pl.DataFrame:
    """Minimal bronze events for unit testing. 3 cases, 15 events.

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
                # Case 1: happy path 3-way after GR
                "Create Purchase Order Item",
                "Record Goods Receipt",
                "Record Invoice Receipt",
                "Clear Invoice",
                "Close Purchase Order",
                # Case 2: 2-way match
                "Create Purchase Order Item",
                "Record Invoice Receipt",
                "Clear Invoice",
                "Close Purchase Order",
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
                "user_001",
                "BATCH_001",
                "user_002",
                "BATCH_002",
                "BATCH_003",
                "user_001",
                "user_002",
                "BATCH_002",
                "BATCH_003",
                "user_001",
                "BATCH_001",
                "user_003",
                "user_003",
                "user_003",
                "BATCH_002",
            ],
            "event_value": [
                1000.0,
                1000.0,
                1000.0,
                1000.0,
                0.0,
                500.0,
                500.0,
                500.0,
                0.0,
                2000.0,
                2000.0,
                1800.0,
                -1800.0,
                2000.0,
                2000.0,
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
            "item": ["ITEM1", "ITEM2", "ITEM1"],
            "item_type": ["Standard", "Standard", "Standard"],
            "gr_based_iv": [True, False, True],
            "goods_receipt": [True, False, True],
            "source_system": ["SAP", "SAP", "SAP"],
            "doc_category_name": ["Standard PO", "Standard PO", "Standard PO"],
            "company": ["Company_A", "Company_A", "Company_B"],
            "spend_classification": ["Direct", "Direct", "Indirect"],
            "spend_area": ["Raw Materials", "Raw Materials", "Services"],
            "sub_spend_area": ["Chemicals", "Chemicals", "Logistics"],
            "vendor": ["Vendor_X", "Vendor_Y", "Vendor_X"],
            "vendor_name": ["Vendor X BV", "Vendor Y GmbH", "Vendor X BV"],
            "document_type": ["NB", "NB", "FO"],
            "item_category": [
                "3-way match, invoice after GR",
                "2-way match",
                "3-way match, invoice after GR",
            ],
        }
    )


@pytest.fixture
def sample_silver_events(sample_bronze_events: pl.DataFrame) -> pl.DataFrame:
    """Silver events with enrichment columns for testing analytics."""
    return sample_bronze_events.with_columns(
        [
            pl.col("resource")
            .map_elements(
                lambda r: "batch" if r.startswith("BATCH") else "human",
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
