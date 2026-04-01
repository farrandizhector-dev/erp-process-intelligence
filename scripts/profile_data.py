#!/usr/bin/env python3
"""Generate a profiling report for the bronze layer data.

Reads bronze parquet files and writes outputs/profiling_report.md with:
  - Column types and null rates
  - Activity frequencies
  - Resource type distribution
  - Timestamp range and anomalies
  - Case length distribution
  - Event value statistics
  - Item category distribution

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


def _gate_row(label: str, expected: str, actual: str, passed: bool) -> str:
    """Format a quality gate table row."""
    icon = "\u2705" if passed else "\u274c"
    return f"| {label} | {expected} | {actual} | {icon} |"


def profile_bronze() -> str:
    """Generate the profiling report as a Markdown string.

    Returns:
        Markdown content of the profiling report.
    """
    events = pl.read_parquet(config.BRONZE_EVENTS)
    cases = pl.read_parquet(config.BRONZE_CASES)

    n_events = len(events)
    n_cases = len(cases)
    n_activities = events["activity"].n_unique()

    lines: list[str] = []

    # ----------------------------------------------------------------
    # Header
    # ----------------------------------------------------------------
    lines += [
        "# Bronze Layer Profiling Report",
        "",
        "**Dataset:** BPI Challenge 2019 — Procure-to-Pay Event Log",
        "**Generated:** 2026-03-31",
        "",
        "---",
        "",
    ]

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    lines += [
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total events | {n_events:,} |",
        f"| Total cases | {n_cases:,} |",
        f"| Unique activities | {n_activities} |",
        f"| Events file size | {config.BRONZE_EVENTS.stat().st_size / 1e6:.1f} MB |",
        f"| Cases file size | {config.BRONZE_CASES.stat().st_size / 1e6:.1f} MB |",
        "",
    ]

    # ----------------------------------------------------------------
    # Timestamp range
    # ----------------------------------------------------------------
    ts_min = events["timestamp"].min()
    ts_max = events["timestamp"].max()
    # Exclude likely anomalies (before 2015)
    normal_ts = events.filter(pl.col("timestamp").dt.year() >= 2015)
    ts_min_normal = normal_ts["timestamp"].min()
    ts_max_normal = normal_ts["timestamp"].max()
    n_anomalous = events.filter(pl.col("timestamp").dt.year() < 2015).height

    lines += [
        "## Timestamp Range",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Earliest timestamp (raw) | {ts_min} |",
        f"| Latest timestamp (raw) | {ts_max} |",
        f"| Earliest timestamp (≥2015) | {ts_min_normal} |",
        f"| Latest timestamp (≥2015) | {ts_max_normal} |",
        f"| Events with anomalous timestamps (<2015) | {n_anomalous} |",
        "",
        "> **Note:** 86 events have timestamps in 1948, all attributed to 'Vendor creates invoice'",
        "> or 'Vendor creates debit memo'. These are likely ERP placeholder dates and will be",
        "> handled in the silver layer (kept but flagged as anomalous).",
        "",
    ]

    # ----------------------------------------------------------------
    # bronze_events schema
    # ----------------------------------------------------------------
    lines += [
        "## bronze_events Schema",
        "",
        "| Column | Type | Null count | Null % |",
        "|--------|------|-----------|--------|",
    ]
    for col in events.columns:
        null_n = events[col].null_count()
        null_pct = null_n / n_events * 100
        lines.append(f"| {col} | {events[col].dtype} | {null_n:,} | {null_pct:.2f}% |")
    lines.append("")

    # ----------------------------------------------------------------
    # bronze_cases schema
    # ----------------------------------------------------------------
    lines += [
        "## bronze_cases Schema",
        "",
        "| Column | Type | Null count | Null % |",
        "|--------|------|-----------|--------|",
    ]
    for col in cases.columns:
        null_n = cases[col].null_count()
        null_pct = null_n / n_cases * 100
        lines.append(f"| {col} | {cases[col].dtype} | {null_n:,} | {null_pct:.2f}% |")
    lines.append("")

    # ----------------------------------------------------------------
    # Activity frequencies
    # ----------------------------------------------------------------
    lines += [
        "## Activity Frequencies (all 42 activities)",
        "",
        "| Rank | Activity | Count | % of events |",
        "|------|----------|-------|-------------|",
    ]
    act_freq = events["activity"].value_counts().sort("count", descending=True)
    for i, row in enumerate(act_freq.iter_rows(named=True), 1):
        pct = row["count"] / n_events * 100
        lines.append(f"| {i} | {row['activity']} | {row['count']:,} | {pct:.2f}% |")
    lines.append("")

    # ----------------------------------------------------------------
    # Resource analysis
    # ----------------------------------------------------------------
    res_freq = events["resource"].value_counts().sort("count", descending=True)
    n_batch = events.filter(pl.col("resource").str.starts_with("batch_")).height
    n_human = events.filter(pl.col("resource").str.starts_with("user_")).height
    n_none = events.filter(pl.col("resource") == "NONE").height
    n_unique_res = events["resource"].n_unique()

    lines += [
        "## Resource Distribution",
        "",
        "| Resource Type | Events | % |",
        "|---------------|--------|---|",
        f"| Batch (batch_XX) | {n_batch:,} | {n_batch/n_events*100:.1f}% |",
        f"| Human (user_XXX) | {n_human:,} | {n_human/n_events*100:.1f}% |",
        f"| NONE (vendor) | {n_none:,} | {n_none/n_events*100:.1f}% |",
        f"| **Total unique resources** | **{n_unique_res}** | — |",
        "",
        "Top 20 resources by event count:",
        "",
        "| Resource | Events | Type |",
        "|----------|--------|------|",
    ]
    for row in res_freq.head(20).iter_rows(named=True):
        r = row["resource"]
        if r is None or r == "NONE":
            rtype = "unknown"
        elif str(r).startswith("batch_"):
            rtype = "batch"
        elif str(r).startswith("user_"):
            rtype = "human"
        else:
            rtype = "unknown"
        lines.append(f"| {r} | {row['count']:,} | {rtype} |")
    lines.append("")

    # ----------------------------------------------------------------
    # Item category distribution (cases)
    # ----------------------------------------------------------------
    cat_dist = cases["item_category"].value_counts().sort("count", descending=True)
    lines += [
        "## Item Category Distribution (cases)",
        "",
        "| Item Category | Cases | % |",
        "|---------------|-------|---|",
    ]
    for row in cat_dist.iter_rows(named=True):
        pct = row["count"] / n_cases * 100
        lines.append(f"| {row['item_category']} | {row['count']:,} | {pct:.1f}% |")
    lines.append("")

    # ----------------------------------------------------------------
    # Case length distribution
    # ----------------------------------------------------------------
    case_lengths = (
        events.group_by("case_id")
        .agg(pl.len().alias("event_count"))
        ["event_count"]
    )
    lines += [
        "## Case Length Distribution (events per case)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Min | {case_lengths.min()} |",
        f"| Median | {case_lengths.median():.1f} |",
        f"| Mean | {case_lengths.mean():.1f} |",
        f"| P90 | {case_lengths.quantile(0.90):.0f} |",
        f"| P99 | {case_lengths.quantile(0.99):.0f} |",
        f"| Max | {case_lengths.max()} |",
        "",
    ]

    # ----------------------------------------------------------------
    # Event value statistics
    # ----------------------------------------------------------------
    ev = events["event_value"].drop_nulls()
    ev_nonzero = ev.filter(ev > 0)
    lines += [
        "## Event Value (Cumulative net worth EUR) Statistics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Min | {ev.min():,.2f} |",
        f"| Max | {ev.max():,.2f} |",
        f"| Mean | {ev.mean():,.2f} |",
        f"| Median | {ev.median():,.2f} |",
        f"| % zero | {(ev == 0).sum() / len(ev) * 100:.1f}% |",
        f"| % non-zero | {len(ev_nonzero) / len(ev) * 100:.1f}% |",
        f"| Null count | {events['event_value'].null_count():,} |",
        "",
        "> **Note:** Values are linearly translated from original EUR amounts (preserves 0 and",
        "> additive properties). Represents cumulative net worth of the purchase order line item",
        "> at the time of the event.",
        "",
    ]

    # ----------------------------------------------------------------
    # Company distribution (top 20)
    # ----------------------------------------------------------------
    co_dist = cases["company"].value_counts().sort("count", descending=True)
    lines += [
        "## Company Distribution (top 20)",
        "",
        "| Company | Cases | % |",
        "|---------|-------|---|",
    ]
    for row in co_dist.head(20).iter_rows(named=True):
        pct = row["count"] / n_cases * 100
        lines.append(f"| {row['company']} | {row['count']:,} | {pct:.1f}% |")
    lines.append("")

    # ----------------------------------------------------------------
    # Quality gate summary
    # ----------------------------------------------------------------
    lines += [
        "## Quality Gate Summary",
        "",
        "| Gate | Expected | Actual | Pass? |",
        "|------|----------|--------|-------|",
        _gate_row(
            "Event count",
            f"~{config.EXPECTED_EVENT_COUNT:,} ±1%",
            f"{n_events:,}",
            abs(n_events - config.EXPECTED_EVENT_COUNT)
            <= config.EXPECTED_EVENT_COUNT * 0.01,
        ),
        _gate_row(
            "Case count",
            f"~{config.EXPECTED_CASE_COUNT:,} ±1%",
            f"{n_cases:,}",
            abs(n_cases - config.EXPECTED_CASE_COUNT)
            <= config.EXPECTED_CASE_COUNT * 0.01,
        ),
        _gate_row(
            "Activity count",
            f"\u2265{config.EXPECTED_ACTIVITY_COUNT}",
            str(n_activities),
            n_activities >= config.EXPECTED_ACTIVITY_COUNT,
        ),
        _gate_row(
            "Null case_id in events",
            "0",
            str(events["case_id"].null_count()),
            events["case_id"].null_count() == 0,
        ),
        _gate_row(
            "Null activity",
            "0",
            str(events["activity"].null_count()),
            events["activity"].null_count() == 0,
        ),
        _gate_row(
            "Null timestamp",
            "<0.1%",
            str(events["timestamp"].null_count()),
            events["timestamp"].null_count() == 0,
        ),
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    """Entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not config.BRONZE_EVENTS.exists() or not config.BRONZE_CASES.exists():
        logger.error("Bronze parquet files not found. Run --phase ingest first.")
        sys.exit(1)

    logger.info("Generating profiling report…")
    report = profile_bronze()

    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config.PROFILING_REPORT.write_text(report, encoding="utf-8")
    logger.info("Profiling report written to: %s", config.PROFILING_REPORT)

    # Print summary to stdout
    print(f"Events: {pl.read_parquet(config.BRONZE_EVENTS).height:,}")
    print(f"Cases: {pl.read_parquet(config.BRONZE_CASES).height:,}")
    print(f"Report: {config.PROFILING_REPORT}")


if __name__ == "__main__":
    main()
