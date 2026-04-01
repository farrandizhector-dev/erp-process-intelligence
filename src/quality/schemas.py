"""Pandera schemas for data layer validation.

Defines structural contracts for silver layer DataFrames.
Used at layer transitions to catch schema drift early.

Usage:
    from src.quality.schemas import SilverEventsSchema
    SilverEventsSchema.validate(events_df)
"""

from __future__ import annotations

import pandera.polars as pa
import polars as pl

# ---------------------------------------------------------------------------
# Bronze schemas (reference — validation done in bronze_writer.py)
# ---------------------------------------------------------------------------

BronzeEventsSchema = pa.DataFrameSchema(
    {
        "case_id": pa.Column(pl.Utf8, nullable=False),
        "activity": pa.Column(pl.Utf8, nullable=False),
        "timestamp": pa.Column(pl.Datetime, nullable=False),
        "resource": pa.Column(pl.Utf8, nullable=True),
        "user": pa.Column(pl.Utf8, nullable=True),
        "event_value": pa.Column(pl.Float64, nullable=True),
    },
    name="bronze_events",
)

BronzeCasesSchema = pa.DataFrameSchema(
    {
        "case_id": pa.Column(pl.Utf8, nullable=False),
        "purchasing_document": pa.Column(pl.Utf8, nullable=True),
        "item": pa.Column(pl.Utf8, nullable=True),
        "item_type": pa.Column(pl.Utf8, nullable=True),
        "gr_based_iv": pa.Column(pl.Boolean, nullable=True),
        "goods_receipt": pa.Column(pl.Boolean, nullable=True),
        "item_category": pa.Column(pl.Utf8, nullable=True),
    },
    name="bronze_cases",
)


# ---------------------------------------------------------------------------
# Silver events schema
# ---------------------------------------------------------------------------

SilverEventsSchema = pa.DataFrameSchema(
    {
        "case_id": pa.Column(pl.Utf8, nullable=False),
        "activity": pa.Column(pl.Utf8, nullable=False),
        "timestamp": pa.Column(pl.Datetime, nullable=False),
        "timestamp_utc": pa.Column(pl.Datetime, nullable=False),
        "date": pa.Column(pl.Date, nullable=False),
        "hour": pa.Column(pl.Int8, nullable=False),
        "day_of_week": pa.Column(pl.Int8, nullable=False),
        "is_weekend": pa.Column(pl.Boolean, nullable=False),
        "is_business_hours": pa.Column(pl.Boolean, nullable=False),
        "is_timestamp_anomaly": pa.Column(pl.Boolean, nullable=False),
        "resource": pa.Column(pl.Utf8, nullable=True),
        "resource_type": pa.Column(
            pl.Utf8,
            nullable=False,
            checks=pa.Check.isin(["human", "batch", "unknown"]),
        ),
        "event_value": pa.Column(pl.Float64, nullable=True),
        "event_order": pa.Column(pl.UInt32, nullable=False, checks=pa.Check.ge(1)),
    },
    name="silver_events",
)


# ---------------------------------------------------------------------------
# Silver cases schema
# ---------------------------------------------------------------------------

SilverCasesSchema = pa.DataFrameSchema(
    {
        "case_id": pa.Column(pl.Utf8, nullable=False),
        "item_category": pa.Column(pl.Utf8, nullable=True),
        "flow_type": pa.Column(
            pl.Utf8,
            nullable=False,
            checks=pa.Check.isin(
                [
                    "3way_invoice_after_gr",
                    "3way_invoice_before_gr",
                    "2way",
                    "consignment",
                ]
            ),
        ),
        "case_start": pa.Column(pl.Datetime, nullable=False),
        "case_end": pa.Column(pl.Datetime, nullable=False),
        "case_duration_days": pa.Column(
            pl.Float64, nullable=False, checks=pa.Check.ge(0.0)
        ),
        "event_count": pa.Column(pl.UInt32, nullable=False, checks=pa.Check.ge(1)),
        "activity_count": pa.Column(pl.UInt32, nullable=False, checks=pa.Check.ge(1)),
        "resource_count": pa.Column(pl.UInt32, nullable=False, checks=pa.Check.ge(1)),
        "has_batch_activity": pa.Column(pl.Boolean, nullable=False),
        "variant_id": pa.Column(pl.Utf8, nullable=False),
    },
    name="silver_cases",
)
