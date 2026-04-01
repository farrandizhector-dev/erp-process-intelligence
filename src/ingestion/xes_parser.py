"""Parse a BPI Challenge 2019 XES file into Polars DataFrames.

Uses pm4py v2.7+ which returns a flat pandas DataFrame (one row per event,
case attributes repeated with 'case:' prefix). We split this into:
  - events_df: one row per event (event-level attributes + case_id)
  - cases_df:  one row per case  (case-level attributes, deduplicated)

Column mapping discovered from XES inspection (2026-03-31)
---------------------------------------------------------------
pm4py column                    → bronze column
----------------------------------------------------
Event-level:
  case:concept:name             → case_id
  concept:name                  → activity
  time:timestamp                → timestamp  (datetime64[ns,UTC] from pm4py)
  org:resource                  → resource
  User                          → user       (same as org:resource in this dataset)
  Cumulative net worth (EUR)    → event_value (float64)

Case-level (prefixed with 'case:' in pm4py output):
  case:concept:name             → case_id
  case:Purchasing Document      → purchasing_document
  case:Item                     → item
  case:Item Type                → item_type
  case:GR-Based Inv. Verif.     → gr_based_iv   (bool)
  case:Goods Receipt            → goods_receipt  (bool)
  case:Source                   → source_system
  case:Purch. Doc. Category name → doc_category_name
  case:Company                  → company
  case:Spend classification text → spend_classification
  case:Spend area text          → spend_area
  case:Sub spend area text      → sub_spend_area
  case:Vendor                   → vendor
  case:Name                     → vendor_name
  case:Document Type            → document_type
  case:Item Category            → item_category

Resource naming patterns:
  batch_00, batch_01, ...  → resource_type = "batch"
  user_000, user_001, ...  → resource_type = "human"
  NONE                     → resource_type = "unknown"
"""

from __future__ import annotations

import logging
import time
import warnings
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column rename maps
# ---------------------------------------------------------------------------
EVENT_RENAME: dict[str, str] = {
    "case:concept:name": "case_id",
    "concept:name": "activity",
    "time:timestamp": "timestamp",
    "org:resource": "resource",
    "User": "user",
    "Cumulative net worth (EUR)": "event_value",
}

CASE_RENAME: dict[str, str] = {
    "case:concept:name": "case_id",
    "case:Purchasing Document": "purchasing_document",
    "case:Item": "item",
    "case:Item Type": "item_type",
    "case:GR-Based Inv. Verif.": "gr_based_iv",
    "case:Goods Receipt": "goods_receipt",
    "case:Source": "source_system",
    "case:Purch. Doc. Category name": "doc_category_name",
    "case:Company": "company",
    "case:Spend classification text": "spend_classification",
    "case:Spend area text": "spend_area",
    "case:Sub spend area text": "sub_spend_area",
    "case:Vendor": "vendor",
    "case:Name": "vendor_name",
    "case:Document Type": "document_type",
    "case:Item Category": "item_category",
}

# Ordered final columns
EVENTS_COLS = [
    "case_id", "activity", "timestamp", "resource", "user", "event_value",
]
CASES_COLS = [
    "case_id", "purchasing_document", "item", "item_type",
    "gr_based_iv", "goods_receipt", "source_system", "doc_category_name",
    "company", "spend_classification", "spend_area", "sub_spend_area",
    "vendor", "vendor_name", "document_type", "item_category",
]


def parse_xes(xes_path: Path) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Parse XES file and return (events_df, cases_df).

    Uses pm4py.read_xes() which returns a flat pandas DataFrame.
    Case attributes have a 'case:' prefix in pm4py output.

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

    logger.info(
        "Parsing XES file: %s (%.1f MB)", xes_path, xes_path.stat().st_size / 1e6
    )
    t0 = time.monotonic()

    try:
        import pm4py  # noqa: PLC0415

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pandas_df = pm4py.read_xes(str(xes_path))
    except Exception as exc:
        raise RuntimeError(f"pm4py failed to parse XES: {exc}") from exc

    elapsed = time.monotonic() - t0
    logger.info(
        "pm4py parsed XES in %.1fs — %d rows × %d cols",
        elapsed,
        len(pandas_df),
        len(pandas_df.columns),
    )
    logger.info("pm4py columns: %s", list(pandas_df.columns))

    t1 = time.monotonic()
    events_df = _build_events_df(pandas_df)
    cases_df = _build_cases_df(pandas_df)
    elapsed2 = time.monotonic() - t1
    logger.info(
        "Built bronze DataFrames in %.1fs — events=%d, cases=%d",
        elapsed2,
        len(events_df),
        len(cases_df),
    )

    return events_df, cases_df


def _build_events_df(pandas_df) -> pl.DataFrame:  # type: ignore[no-untyped-def]
    """Build bronze events DataFrame from flat pm4py output.

    Args:
        pandas_df: pandas DataFrame from pm4py.read_xes().

    Returns:
        Polars events DataFrame with bronze schema.
    """
    # Select only event-level columns (pm4py gives us all cols in one df)
    event_pm4py_cols = list(EVENT_RENAME.keys())
    present = [c for c in event_pm4py_cols if c in pandas_df.columns]
    df_pd = pandas_df[present].copy()

    # Convert timezone-aware timestamp to tz-naive UTC (Polars handles better)
    if "time:timestamp" in df_pd.columns:
        ts = df_pd["time:timestamp"]
        if hasattr(ts, "dt") and ts.dt.tz is not None:
            df_pd["time:timestamp"] = ts.dt.tz_convert("UTC").dt.tz_localize(None)

    # Rename columns
    df_pd = df_pd.rename(columns={k: v for k, v in EVENT_RENAME.items() if k in df_pd.columns})

    # Convert to Polars
    df = pl.from_pandas(df_pd)

    # Ensure timestamp is Datetime UTC
    if "timestamp" in df.columns and df["timestamp"].dtype != pl.Datetime("us", "UTC"):
        if df["timestamp"].dtype in (pl.Datetime("ns"), pl.Datetime("us"), pl.Datetime("ms")):
            df = df.with_columns(
                pl.col("timestamp").dt.replace_time_zone("UTC").alias("timestamp")
            )

    # Cast event_value to Float64
    if "event_value" in df.columns and df["event_value"].dtype != pl.Float64:
        df = df.with_columns(pl.col("event_value").cast(pl.Float64, strict=False))

    # Ensure column order
    present_out = [c for c in EVENTS_COLS if c in df.columns]
    df = df.select(present_out)

    return df


def _build_cases_df(pandas_df) -> pl.DataFrame:  # type: ignore[no-untyped-def]
    """Build bronze cases DataFrame (one row per case) from flat pm4py output.

    Deduplicates by case_id — all case: columns have the same value for
    each event within a case, so first() is safe.

    Args:
        pandas_df: pandas DataFrame from pm4py.read_xes().

    Returns:
        Polars cases DataFrame with bronze schema.
    """
    case_pm4py_cols = list(CASE_RENAME.keys())
    present = [c for c in case_pm4py_cols if c in pandas_df.columns]
    df_pd = pandas_df[present].drop_duplicates(subset=["case:concept:name"])

    df_pd = df_pd.rename(columns={k: v for k, v in CASE_RENAME.items() if k in df_pd.columns})

    df = pl.from_pandas(df_pd)

    # Cast boolean columns explicitly
    for col in ["gr_based_iv", "goods_receipt"]:
        if col in df.columns and df[col].dtype != pl.Boolean:
            df = df.with_columns(pl.col(col).cast(pl.Boolean, strict=False))

    # Ensure column order
    present_out = [c for c in CASES_COLS if c in df.columns]
    df = df.select(present_out)

    return df
