#!/usr/bin/env python3
"""Export gold layer parquet files to JSON for the React frontend.

Reads gold parquet tables, aggregates and transforms into the JSON contracts
defined in CONTEXT.md Section 10, and writes to frontend/public/data/.

Target total payload: < 10 MB uncompressed.

Usage:
  python scripts/export_for_frontend.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import polars as pl

from src import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def export_all() -> int:
    """Export all gold tables to frontend JSON files.

    Returns:
        Number of JSON files written.
    """
    config.FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Verify gold layer exists
    for path in [
        config.GOLD_FACT_CASE_SUMMARY,
        config.GOLD_FACT_VARIANT_STATS,
        config.GOLD_FACT_COMPLIANCE,
        config.GOLD_FACT_BOTTLENECK,
        config.GOLD_FACT_AUTOMATION,
        config.GOLD_DIM_ACTIVITY,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Gold file missing: {path}. Run --phase gold first.")

    # Load gold tables
    cases = pl.read_parquet(config.GOLD_FACT_CASE_SUMMARY)
    variants = pl.read_parquet(config.GOLD_FACT_VARIANT_STATS)
    compliance = pl.read_parquet(config.GOLD_FACT_COMPLIANCE)
    bottlenecks = pl.read_parquet(config.GOLD_FACT_BOTTLENECK)
    automation = pl.read_parquet(config.GOLD_FACT_AUTOMATION)
    dim_activity = pl.read_parquet(config.GOLD_DIM_ACTIVITY)
    dim_company = pl.read_parquet(config.GOLD_DIM_COMPANY)
    dim_vendor = pl.read_parquet(config.GOLD_DIM_VENDOR)
    event_log = pl.read_parquet(config.GOLD_FACT_EVENT_LOG)

    files_written = 0
    files_written += _export_executive_kpis(cases, compliance)
    files_written += _export_process_flow(bottlenecks, dim_activity, cases, event_log)
    files_written += _export_variants(variants, compliance)
    files_written += _export_compliance_summary(compliance, cases, dim_vendor)
    files_written += _export_bottlenecks(bottlenecks, dim_activity)
    files_written += _export_automation_candidates(automation, dim_activity)
    files_written += _export_case_summaries(cases, event_log)
    files_written += _export_company_benchmarks(cases, dim_company)
    files_written += _export_sla_risk()

    total_size = sum(
        p.stat().st_size
        for p in config.FRONTEND_DATA_DIR.glob("*.json")
    )
    logger.info(
        "Exported %d JSON files; total size: %.1f MB",
        files_written,
        total_size / 1e6,
    )
    return files_written


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------

def _export_executive_kpis(cases: pl.DataFrame, compliance: pl.DataFrame) -> int:
    """Export executive_kpis.json."""
    n_cases = len(cases)
    compliance_rate = round(float(compliance["passed"].mean()) * 100, 1)
    avg_duration = round(float(cases["case_duration_days"].mean()), 1)
    rework_rate = round(float(cases["has_rework"].mean()) * 100, 1)
    happy_rate = round(float(cases["is_happy_path"].mean()) * 100, 1)
    touchless_rate = round(
        float((cases["touchless_ratio"] == 1.0).mean()) * 100, 1
    )
    high_risk = round(
        float((cases["sla_risk"] == "high").mean()) * 100, 1
    )
    automation_coverage = round(
        float(cases["touchless_ratio"].mean()) * 100, 1
    )

    # Monthly trend: count cases by case_start month
    monthly = (
        cases.with_columns(
            pl.col("case_start").dt.strftime("%Y-%m").alias("month")
        )
        .filter(pl.col("case_start").dt.year() >= 2018)
        .group_by("month")
        .agg(
            [
                pl.len().alias("cases"),
                pl.col("case_duration_days").mean().alias("avg_duration"),
            ]
        )
        .sort("month")
    )

    # Join compliance by case month
    compliance_by_case = compliance.group_by("case_id").agg(
        pl.col("passed").mean().alias("case_compliance")
    )
    cases_with_comp = cases.join(compliance_by_case, on="case_id", how="left")
    monthly_compliance = (
        cases_with_comp.filter(pl.col("case_start").dt.year() >= 2018)
        .with_columns(pl.col("case_start").dt.strftime("%Y-%m").alias("month"))
        .group_by("month")
        .agg(pl.col("case_compliance").mean().alias("compliance_rate"))
        .sort("month")
    )

    monthly_joined = monthly.join(monthly_compliance, on="month", how="left")
    monthly_list = [
        {
            "month": row["month"],
            "cases": int(row["cases"]),
            "compliance_rate": round(float(row["compliance_rate"] or 0) * 100, 1),
            "avg_duration": round(float(row["avg_duration"] or 0), 1),
        }
        for row in monthly_joined.iter_rows(named=True)
    ]

    # SLA risk distribution
    sla_dist = (
        cases.group_by("sla_risk")
        .agg(pl.len().alias("count"))
        .sort("sla_risk")
    )
    sla_by_risk = {
        row["sla_risk"]: int(row["count"])
        for row in sla_dist.iter_rows(named=True)
    }

    payload = {
        "total_cases": n_cases,
        "total_events": 1_595_923,
        "compliance_rate": compliance_rate,
        "avg_case_duration_days": avg_duration,
        "rework_rate": rework_rate,
        "happy_path_rate": happy_rate,
        "touchless_rate": touchless_rate,
        "automation_coverage": automation_coverage,
        "high_sla_risk_rate": high_risk,
        "sla_risk_distribution": sla_by_risk,
        "monthly_trend": monthly_list,
    }
    _write_json(payload, config.FRONTEND_EXECUTIVE_KPIS)
    return 1


def _build_dfg_nodes_edges(
    event_log: pl.DataFrame,
    dim_activity: pl.DataFrame,
    min_count: int = 100,
) -> tuple[list[dict], list[dict]]:
    """Build DFG nodes and edges from an event log slice.

    Args:
        event_log: Slice of fact_event_log (may be filtered by flow_type).
        dim_activity: Activity dimension table (stage, frequency, etc.).
        min_count: Minimum transition count to include in edges.

    Returns:
        Tuple of (nodes list, edges list) dicts ready for JSON.
    """
    stage_map = dict(
        zip(dim_activity["activity"].to_list(), dim_activity["stage"].to_list(), strict=False)
    )
    activity_freq = dict(
        zip(dim_activity["activity"].to_list(), dim_activity["frequency"].to_list(), strict=False)
    )
    activity_duration = dict(
        zip(
            dim_activity["activity"].to_list(),
            (dim_activity["median_duration_to_next"] * 1.0).to_list(),
            strict=False,
        )
    )

    # Compute transitions: sort by case_id + event_order, shift activity to get next_activity
    transitions = (
        event_log.sort(["case_id", "event_order"])
        .with_columns(
            pl.col("activity").shift(-1).over("case_id").alias("next_activity"),
            pl.col("case_id").shift(-1).over("case_id").alias("next_case_id"),
            # Convert timedelta to total seconds (float) before shifting
            pl.col("time_since_prev_event")
            .cast(pl.Duration("us"))
            .cast(pl.Float64)
            .truediv(1_000_000)
            .shift(-1).over("case_id").alias("wait_to_next_s"),
        )
        .filter(pl.col("next_case_id") == pl.col("case_id"))  # drop case boundaries
        .filter(pl.col("next_activity").is_not_null())
        .group_by(["activity", "next_activity"])
        .agg([
            pl.len().alias("count"),
            pl.col("wait_to_next_s").median().alias("median_wait_s"),
            pl.col("wait_to_next_s").quantile(0.9).alias("p90_wait_s"),
        ])
        .filter(pl.col("count") >= min_count)
        .sort("count", descending=True)
    )

    if len(transitions) == 0:
        return [], []

    # Determine bottleneck threshold: p90 > 7 days
    bottleneck_threshold_s = 7 * 24 * 3600

    edges = [
        {
            "source": row["activity"],
            "target": row["next_activity"],
            "count": int(row["count"]),
            "median_wait_hours": round(float(row["median_wait_s"] or 0) / 3600, 2),
            "is_bottleneck": bool((row["p90_wait_s"] or 0) > bottleneck_threshold_s),
        }
        for row in transitions.iter_rows(named=True)
    ]

    activities_in_dfg = set(
        transitions["activity"].to_list() + transitions["next_activity"].to_list()
    )
    nodes = [
        {
            "id": act,
            "stage": stage_map.get(act, "S0"),
            "stage_name": _stage_name(stage_map.get(act, "S0")),
            "frequency": int(activity_freq.get(act, 0)),
            "avg_duration_hours": round(float(activity_duration.get(act, 0) or 0), 2),
        }
        for act in sorted(activities_in_dfg)
    ]
    return nodes, edges


def _export_process_flow(
    bottlenecks: pl.DataFrame,
    dim_activity: pl.DataFrame,
    cases: pl.DataFrame,
    event_log: pl.DataFrame,
) -> int:
    """Export process_flow.json (DFG for Sankey visualization)."""
    stage_map = dict(
        zip(dim_activity["activity"].to_list(), dim_activity["stage"].to_list(), strict=False)
    )
    activity_freq = dict(
        zip(dim_activity["activity"].to_list(), dim_activity["frequency"].to_list(), strict=False)
    )
    activity_duration = dict(
        zip(
            dim_activity["activity"].to_list(),
            (dim_activity["median_duration_to_next"] * 1.0).to_list(),
            strict=False,
        )
    )

    # Nodes: all activities present in transitions
    activities_in_dfg = set(
        bottlenecks["from_activity"].to_list() + bottlenecks["to_activity"].to_list()
    )
    nodes = [
        {
            "id": act,
            "stage": stage_map.get(act, "S0_UNKNOWN"),
            "stage_name": _stage_name(stage_map.get(act, "S0")),
            "frequency": int(activity_freq.get(act, 0)),
            "avg_duration_hours": round(float(activity_duration.get(act, 0) or 0), 2),
        }
        for act in sorted(activities_in_dfg)
    ]

    # Edges: all transitions (filter >100 occurrences already done in bottleneck table)
    edges = [
        {
            "source": row["from_activity"],
            "target": row["to_activity"],
            "count": int(row["transition_count"]),
            "median_wait_hours": round(float(row["median_wait_hours"] or 0), 2),
            "is_bottleneck": bool(row["is_bottleneck"]),
        }
        for row in bottlenecks.iter_rows(named=True)
    ]

    # Per-flow-type DFGs
    case_flow = cases.select(["case_id", "flow_type"])
    event_log_with_flow = event_log.join(case_flow, on="case_id", how="left")

    by_flow_type: dict[str, dict] = {}
    for flow in cases["flow_type"].unique().to_list():
        if not flow:
            continue
        subset = event_log_with_flow.filter(pl.col("flow_type") == flow)
        ft_nodes, ft_edges = _build_dfg_nodes_edges(subset, dim_activity, min_count=50)
        if ft_nodes:
            by_flow_type[flow] = {"nodes": ft_nodes, "edges": ft_edges}

    payload = {"nodes": nodes, "edges": edges, "by_flow_type": by_flow_type}
    _write_json(payload, config.FRONTEND_PROCESS_FLOW)
    return 1


def _export_variants(
    variants: pl.DataFrame, compliance: pl.DataFrame
) -> int:
    """Export variants.json (top 50 variants)."""
    top = variants.head(config.MAX_VARIANTS_EXPORTED)

    # Compliance rate per variant: join via case_id
    # variants has no case_id — derive from compliance × case_summary join is expensive
    # Use a simplified proxy: overall compliance rate for all variants
    overall_compliance = float(compliance["passed"].mean()) * 100

    top_list = []
    for row in top.iter_rows(named=True):
        seq = row.get("activity_sequence") or []
        top_list.append(
            {
                "variant_id": row["variant_id"],
                "sequence": list(seq) if seq else [],
                "case_count": int(row["case_count"]),
                "case_percentage": round(float(row["case_percentage"]), 2),
                "median_duration_days": round(float(row["median_duration_days"] or 0), 1),
                "p90_duration_days": round(float(row["p90_duration_days"] or 0), 1),
                "compliance_rate": round(overall_compliance, 1),
                "is_happy_path": bool(row["is_happy_path"]),
                "dominant_flow_type": row["dominant_flow_type"] or "",
            }
        )

    cum_pct = variants["case_percentage"]
    payload = {
        "total_variants": len(variants),
        "top_variants": top_list,
        "concentration": {
            "top5_coverage": round(float(cum_pct.head(5).sum()), 1),
            "top10_coverage": round(float(cum_pct.head(10).sum()), 1),
            "top20_coverage": round(float(cum_pct.head(20).sum()), 1),
        },
    }
    _write_json(payload, config.FRONTEND_VARIANTS)
    return 1


def _export_compliance_summary(
    compliance: pl.DataFrame,
    cases: pl.DataFrame,
    dim_vendor: pl.DataFrame,
) -> int:
    """Export compliance_summary.json."""
    overall_rate = round(float(compliance["passed"].mean()) * 100, 1)

    # By rule
    by_rule = (
        compliance.group_by(["rule_id", "rule_name", "severity"])
        .agg(
            [
                pl.col("passed").mean().alias("pass_rate"),
                (~pl.col("passed")).sum().alias("violation_count"),
            ]
        )
        .sort("rule_id")
    )
    by_rule_list = [
        {
            "rule_id": row["rule_id"],
            "rule_name": row["rule_name"],
            "severity": row["severity"],
            "pass_rate": round(float(row["pass_rate"]) * 100, 1),
            "violation_count": int(row["violation_count"]),
        }
        for row in by_rule.iter_rows(named=True)
    ]

    # By company: join compliance with cases
    case_comp = compliance.group_by("case_id").agg(
        [
            pl.col("passed").mean().alias("comp_score"),
            (pl.col("severity") == "critical").filter(~pl.col("passed")).sum().alias("crit_viol"),
        ]
    )
    cases_with_company = cases.select(["case_id", "company"]).join(
        case_comp, on="case_id", how="left"
    )
    by_company = (
        cases_with_company.group_by("company")
        .agg(
            [
                pl.col("comp_score").mean().alias("compliance_rate"),
                pl.len().alias("case_count"),
                pl.col("crit_viol").sum().alias("critical_violations"),
            ]
        )
        .sort("compliance_rate")
    )
    by_company_list = [
        {
            "company": row["company"],
            "compliance_rate": round(float(row["compliance_rate"] or 0) * 100, 1),
            "case_count": int(row["case_count"]),
            "critical_violations": int(row["critical_violations"] or 0),
        }
        for row in by_company.iter_rows(named=True)
    ]

    # By flow type
    cases_flow = cases.select(["case_id", "flow_type"]).join(case_comp, on="case_id", how="left")
    by_flow = (
        cases_flow.group_by("flow_type")
        .agg(
            [
                pl.col("comp_score").mean().alias("compliance_rate"),
                pl.len().alias("case_count"),
            ]
        )
    )
    by_flow_dict: dict = {}
    for row in by_flow.iter_rows(named=True):
        by_flow_dict[row["flow_type"]] = {
            "compliance_rate": round(float(row["compliance_rate"] or 0) * 100, 1),
            "case_count": int(row["case_count"]),
            "top_violation": "N/A",
        }

    # Heatmap: company × flow_type
    heatmap_data = (
        cases.select(["case_id", "company", "flow_type"])
        .join(case_comp, on="case_id", how="left")
        .group_by(["company", "flow_type"])
        .agg(
            [
                pl.col("comp_score").mean().alias("compliance_rate"),
                pl.len().alias("case_count"),
            ]
        )
        .sort(["company", "flow_type"])
    )
    heatmap_list = [
        {
            "company": row["company"],
            "flow_type": row["flow_type"],
            "compliance_rate": round(float(row["compliance_rate"] or 0) * 100, 1),
            "case_count": int(row["case_count"]),
        }
        for row in heatmap_data.iter_rows(named=True)
    ]

    # Top violating vendors
    cases_vendor = cases.select(["case_id", "vendor", "vendor_name"])
    vendor_comp = cases_vendor.join(case_comp, on="case_id", how="left")
    top_vendors = (
        vendor_comp.group_by(["vendor", "vendor_name"])
        .agg(
            [
                pl.len().alias("case_count"),
                (~pl.col("comp_score").round(0).cast(pl.Boolean)).sum().alias("violation_count"),
            ]
        )
        .with_columns(
            (pl.col("violation_count").cast(pl.Float64) / pl.col("case_count").cast(pl.Float64))
            .alias("violation_rate")
        )
        .sort("violation_count", descending=True)
        .head(config.MAX_TOP_VIOLATING_VENDORS)
    )
    top_vendors_list = [
        {
            "vendor": row["vendor"],
            "vendor_name": row["vendor_name"],
            "violation_count": int(row["violation_count"] or 0),
            "case_count": int(row["case_count"]),
            "violation_rate": round(float(row["violation_rate"] or 0), 3),
        }
        for row in top_vendors.iter_rows(named=True)
    ]

    payload = {
        "overall_rate": overall_rate,
        "by_rule": by_rule_list,
        "by_company": by_company_list,
        "by_flow_type": by_flow_dict,
        "heatmap": heatmap_list,
        "monthly_trend": [],
        "top_violating_vendors": top_vendors_list,
    }
    _write_json(payload, config.FRONTEND_COMPLIANCE_SUMMARY)
    return 1


def _export_bottlenecks(
    bottlenecks: pl.DataFrame, dim_activity: pl.DataFrame
) -> int:
    """Export bottlenecks.json."""
    stage_map = dict(
        zip(dim_activity["activity"].to_list(), dim_activity["stage"].to_list(), strict=False)
    )

    transitions_list = [
        {
            "from_activity": row["from_activity"],
            "to_activity": row["to_activity"],
            "from_stage": stage_map.get(row["from_activity"], "S0"),
            "to_stage": stage_map.get(row["to_activity"], "S0"),
            "count": int(row["transition_count"]),
            "median_wait_hours": round(float(row["median_wait_hours"] or 0), 2),
            "p90_wait_hours": round(float(row["p90_wait_hours"] or 0), 2),
            "max_wait_hours": round(float(row["max_wait_hours"] or 0), 2),
            "is_bottleneck": bool(row["is_bottleneck"]),
            "bottleneck_rank": int(row["bottleneck_rank"]) if row["bottleneck_rank"] else None,
        }
        for row in bottlenecks.iter_rows(named=True)
    ]

    top_bottlenecks = bottlenecks.filter(pl.col("is_bottleneck")).sort(
        "p90_wait_hours", descending=True
    ).head(config.MAX_TOP_BOTTLENECKS)
    top_list = [
        {
            "from_activity": row["from_activity"],
            "to_activity": row["to_activity"],
            "count": int(row["transition_count"]),
            "p90_wait_hours": round(float(row["p90_wait_hours"] or 0), 2),
            "impact_score": round(
                float(row["transition_count"]) * float(row["median_wait_hours"] or 0), 0
            ),
        }
        for row in top_bottlenecks.iter_rows(named=True)
    ]

    payload = {
        "transitions": transitions_list,
        "top_bottlenecks": top_list,
        "by_flow_type": {},
    }
    _write_json(payload, config.FRONTEND_BOTTLENECKS)
    return 1


def _export_automation_candidates(
    automation: pl.DataFrame, dim_activity: pl.DataFrame
) -> int:
    """Export automation_candidates.json."""
    stage_map = dict(
        zip(dim_activity["activity"].to_list(), dim_activity["stage"].to_list(), strict=False)
    )

    activities_list = [
        {
            "activity": row["activity"],
            "stage": stage_map.get(row["activity"], "S0"),
            "total_executions": int(row["total_executions"]),
            "human_executions": int(row["human_executions"]),
            "batch_ratio": round(float(row["batch_ratio"]), 3),
            "volume_score": round(float(row["volume_score"]), 3),
            "batch_gap_score": round(float(row["batch_gap_score"]), 3),
            "input_uniformity": round(float(row["input_uniformity"]), 3),
            "timing_regularity": round(float(row["timing_regularity"]), 3),
            "error_reduction": round(float(row["error_reduction"]), 3),
            "wait_reduction": round(float(row["wait_reduction"]), 3),
            "automation_score": round(float(row["automation_score"]), 3),
            "automation_tier": row["automation_tier"],
            "estimated_hours_saved_monthly": round(
                float(row["estimated_hours_saved_monthly"]), 0
            ),
        }
        for row in automation.iter_rows(named=True)
    ]

    payload = {"activities": activities_list}
    _write_json(payload, config.FRONTEND_AUTOMATION)
    return 1


def _export_case_summaries(cases: pl.DataFrame, event_log: pl.DataFrame) -> int:
    """Export case_summaries.json (sample of 1000 cases with event timelines)."""
    sample = cases.sample(
        n=min(config.MAX_CASE_SUMMARIES_SAMPLE, len(cases)),
        seed=42,
    )
    sampled_ids = set(sample["case_id"].to_list())

    # Build event timeline lookup: case_id → sorted list of events
    events_subset = (
        event_log.filter(pl.col("case_id").is_in(list(sampled_ids)))
        .sort(["case_id", "event_order"])
    )
    event_rows_by_case: dict[str, list[dict]] = {}
    for row in events_subset.iter_rows(named=True):
        cid = row["case_id"]
        if cid not in event_rows_by_case:
            event_rows_by_case[cid] = []
        ts = row.get("timestamp")
        raw_wait = row.get("time_since_prev_event")
        if hasattr(raw_wait, "total_seconds"):
            wait_hours = raw_wait.total_seconds() / 3600
        elif raw_wait is not None:
            # Duration stored as microseconds integer
            wait_hours = float(raw_wait) / 3_600_000_000
        else:
            wait_hours = 0.0
        event_rows_by_case[cid].append({
            "activity": row["activity"],
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "resource": row.get("resource", ""),
            "resource_type": row.get("resource_type", ""),
            "stage": row.get("process_stage", ""),
            "time_since_prev_hours": round(wait_hours, 2),
        })

    cases_list = []
    for row in sample.iter_rows(named=True):
        cid = row["case_id"]
        cases_list.append(
            {
                "case_id": cid,
                "flow_type": row.get("flow_type", ""),
                "company": row.get("company", ""),
                "vendor": row.get("vendor", ""),
                "vendor_name": row.get("vendor_name", ""),
                "duration_days": round(float(row.get("case_duration_days") or 0), 1),
                "event_count": int(row.get("event_count") or 0),
                "compliance_score": round(float(row.get("compliance_score") or 1.0), 3),
                "has_rework": bool(row.get("has_rework", False)),
                "variant_id": row.get("variant_id", ""),
                "is_happy_path": bool(row.get("is_happy_path", False)),
                "sla_risk": row.get("sla_risk", "low"),
                "events": event_rows_by_case.get(cid, []),
            }
        )

    payload = {
        "total_cases": len(cases),
        "sample_cases": cases_list,
    }
    _write_json(payload, config.FRONTEND_CASE_SUMMARIES)
    return 1


def _export_company_benchmarks(
    cases: pl.DataFrame, dim_company: pl.DataFrame
) -> int:
    """Export company_benchmarks.json."""
    company_stats = (
        cases.group_by("company")
        .agg(
            [
                pl.len().alias("case_count"),
                pl.col("case_duration_days").mean().alias("avg_duration_days"),
                pl.col("case_duration_days").median().alias("median_duration_days"),
                pl.col("has_rework").mean().alias("rework_rate"),
                pl.col("touchless_ratio").mean().alias("automation_coverage"),
                pl.col("is_happy_path").mean().alias("happy_path_rate"),
                pl.col("compliance_score").mean().alias("compliance_rate"),
                pl.col("flow_type").mode().first().alias("primary_flow_type"),
            ]
        )
        .sort("case_count", descending=True)
    )

    # Normalize for radar chart
    max_dur = float(company_stats["avg_duration_days"].max() or 1)
    max_vol = float(company_stats["case_count"].max() or 1)

    companies_list = []
    for row in company_stats.iter_rows(named=True):
        avg_dur = float(row["avg_duration_days"] or 0)
        companies_list.append(
            {
                "company": row["company"],
                "case_count": int(row["case_count"]),
                "avg_duration_days": round(avg_dur, 1),
                "median_duration_days": round(float(row["median_duration_days"] or 0), 1),
                "compliance_rate": round(float(row["compliance_rate"] or 0) * 100, 1),
                "rework_rate": round(float(row["rework_rate"] or 0) * 100, 1),
                "touchless_rate": round(float(row["automation_coverage"] or 0) * 100, 1),
                "automation_coverage": round(float(row["automation_coverage"] or 0) * 100, 1),
                "primary_flow_type": row["primary_flow_type"] or "",
                "radar": {
                    "speed": round(1.0 - avg_dur / max_dur, 3),
                    "compliance": round(float(row["compliance_rate"] or 0), 3),
                    "efficiency": round(1.0 - float(row["rework_rate"] or 0), 3),
                    "automation": round(float(row["automation_coverage"] or 0), 3),
                    "volume": round(float(row["case_count"]) / max_vol, 3),
                },
            }
        )

    payload = {
        "companies": companies_list,
        "peer_comparison_dimensions": [
            "speed", "compliance", "efficiency", "automation", "volume",
        ],
    }
    _write_json(payload, config.FRONTEND_COMPANY_BENCHMARKS)
    return 1


def _export_sla_risk() -> int:
    """Export sla_risk.json — model metrics + top at-risk cases.

    Returns 0 if fact_sla_risk.parquet does not exist (predict phase not run).
    """
    if not config.GOLD_FACT_SLA_RISK.exists():
        logger.warning("fact_sla_risk.parquet not found — skipping sla_risk.json export.")
        return 0
    if not config.SLA_MODEL_PATH.exists():
        logger.warning("Model artifact not found — skipping sla_risk.json export.")
        return 0

    import pickle  # noqa: PLC0415

    sla = pl.read_parquet(config.GOLD_FACT_SLA_RISK)
    with open(config.SLA_MODEL_PATH, "rb") as fh:
        artifact = pickle.load(fh)  # noqa: S301

    metrics = artifact["metrics"]
    feat_imp = artifact["feature_importance"]

    # Top 100 highest-risk cases
    top_risk = (
        sla.sort("sla_risk_score", descending=True)
        .head(100)
    )
    at_risk_list = [
        {
            "case_id": row["case_id"],
            "flow_type": row["flow_type"],
            "sla_risk_actual": row["sla_risk"],
            "sla_risk_score": round(float(row["sla_risk_score"]), 4),
            "sla_risk_predicted": row["sla_risk_predicted"],
        }
        for row in top_risk.iter_rows(named=True)
    ]

    payload = {
        "model_metrics": {
            "auc_roc": round(metrics["auc_roc"], 4),
            "pr_auc": round(metrics["pr_auc"], 4),
            "precision": round(metrics["precision"], 4),
            "recall": round(metrics["recall"], 4),
            "f1": round(metrics["f1"], 4),
            "n_train": metrics["n_train"],
            "n_test": metrics["n_test"],
            "positive_rate": round(metrics["positive_rate_overall"] * 100, 1),
        },
        "feature_importance": [
            {"feature": fname, "importance": round(imp, 1)}
            for fname, imp in feat_imp
        ],
        "at_risk_cases": at_risk_list,
    }
    _write_json(payload, config.FRONTEND_SLA_RISK)
    return 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(data: object, path: Path) -> None:
    """Serialize data to JSON and write to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=_json_serial)
    size_kb = path.stat().st_size / 1024
    logger.info("  Written: %s (%.0f KB)", path.name, size_kb)


def _json_serial(obj: object) -> object:
    """JSON serializer for types not natively handled by json.dump."""
    import datetime

    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _stage_name(stage_id: str) -> str:
    """Map stage ID to human-readable name."""
    names = {
        "S1": "Requisition & Creation",
        "S2": "Approval & Release",
        "S3": "Vendor Interaction",
        "S4": "Goods & Services Receipt",
        "S5": "Invoice Processing",
        "S6": "Payment Block Management",
        "S7": "Payment & Clearing",
        "S8": "Exception & Rework",
        "S9": "Closure",
    }
    return names.get(stage_id, stage_id)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        files_written = export_all()
        logger.info(
            "Export complete: %d JSON files in %s",
            files_written,
            config.FRONTEND_DATA_DIR,
        )
    except FileNotFoundError as exc:
        logger.error("Export failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
