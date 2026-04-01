"""Compliance and conformance checking against normative P2P models.

Implements 9 of the 10 rules from CONTEXT.md Section 7.3.
CR-004 (value matching) is skipped — event_value is cumulative net worth
at the time of the event (not per-transaction amount), making GR↔Invoice
value pairing intractable without additional ERP data.

Rule applicability:
  CR-001  3way_invoice_after_gr only
  CR-002  3way_invoice_before_gr only
  CR-003  consignment only
  CR-005  ALL (cases with "Create Purchase Order Item")
  CR-006  ALL
  CR-007  ALL
  CR-008  ALL
  CR-009  ALL
  CR-010  ALL
"""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)

# Compliance rule metadata
RULES: dict[str, dict] = {
    "CR-001": {
        "name": "GR before invoice clearance",
        "severity": "critical",
        "flow_types": {"3way_invoice_after_gr"},
    },
    "CR-002": {
        "name": "GR required before payment (invoice-before-GR flow)",
        "severity": "critical",
        "flow_types": {"3way_invoice_before_gr"},
    },
    "CR-003": {
        "name": "No invoice activities on consignment",
        "severity": "warning",
        "flow_types": {"consignment"},
    },
    "CR-005": {
        "name": "Create PO Item is first event",
        "severity": "warning",
        "flow_types": None,  # ALL
    },
    "CR-006": {
        "name": "Invoice received before clearance",
        "severity": "critical",
        "flow_types": None,
    },
    "CR-007": {
        "name": "Single vendor per purchasing document",
        "severity": "info",
        "flow_types": None,
    },
    "CR-008": {
        "name": "Throughput time within P95",
        "severity": "warning",
        "flow_types": None,
    },
    "CR-009": {
        "name": "No excessive rework (activity repeated > 2 times)",
        "severity": "warning",
        "flow_types": None,
    },
    "CR-010": {
        "name": "Proper closure (terminal activity present)",
        "severity": "info",
        "flow_types": None,
    },
}

# Activities used in rule logic
ACT_GR = "Record Goods Receipt"
ACT_SES = "Record Service Entry Sheet"
ACT_INVOICE_RECEIPT = "Record Invoice Receipt"
ACT_CLEAR = "Clear Invoice"
ACT_CREATE = "Create Purchase Order Item"
ACT_VENDOR_INVOICE = "Vendor creates invoice"
ACT_VENDOR_DEBIT = "Vendor creates debit memo"
ACT_REMOVE_BLOCK = "Remove Payment Block"
ACT_DELETE = "Delete Purchase Order Item"
ACT_CANCEL_IR = "Cancel Invoice Receipt"

INVOICE_ACTIVITIES = {ACT_INVOICE_RECEIPT, ACT_VENDOR_INVOICE, ACT_CLEAR, ACT_VENDOR_DEBIT}
TERMINAL_ACTIVITIES = {ACT_CLEAR, ACT_DELETE, ACT_REMOVE_BLOCK}


def run_all_rules(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """Run all compliance rules and return fact_compliance_checks DataFrame.

    Args:
        events: Silver events (case_id, activity, timestamp, ...).
        cases: Silver cases (case_id, flow_type, purchasing_document, vendor,
               case_duration_days, ...).

    Returns:
        DataFrame with columns: case_id, rule_id, rule_name, passed,
        severity, detail.
    """
    logger.info("Running compliance rules on %d cases...", len(cases))

    chunks: list[pl.DataFrame] = [
        _check_cr001(events, cases),
        _check_cr002(events, cases),
        _check_cr003(events, cases),
        _check_cr005(events, cases),
        _check_cr006(events, cases),
        _check_cr007(cases),
        _check_cr008(cases),
        _check_cr009(events, cases),
        _check_cr010(events, cases),
    ]

    result = pl.concat(chunks, how="diagonal")

    for rule_id in RULES:
        rule_rows = result.filter(pl.col("rule_id") == rule_id)
        pass_rate = rule_rows["passed"].mean() * 100 if len(rule_rows) > 0 else float("nan")
        logger.info(
            "  %-8s %-50s pass_rate=%.1f%% (%d cases)",
            rule_id,
            RULES[rule_id]["name"],
            pass_rate,
            len(rule_rows),
        )

    return result


def compute_case_compliance_scores(compliance_checks: pl.DataFrame) -> pl.DataFrame:
    """Aggregate per-case compliance scores from fact_compliance_checks.

    Args:
        compliance_checks: Output of run_all_rules().

    Returns:
        DataFrame with case_id, compliance_score (0-1),
        compliance_flags (list of failed rule names).
    """
    scores = (
        compliance_checks.group_by("case_id")
        .agg(
            [
                (pl.col("passed").sum().cast(pl.Float64) / pl.len().cast(pl.Float64)).alias(
                    "compliance_score"
                ),
                pl.col("rule_name").filter(~pl.col("passed")).alias("compliance_flags"),
            ]
        )
    )
    return scores


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

def _check_cr001(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """CR-001: In 3way_after_gr, Record Goods Receipt must precede Clear Invoice."""
    applicable_cases = cases.filter(
        pl.col("flow_type") == "3way_invoice_after_gr"
    ).select("case_id")

    ev = events.join(applicable_cases, on="case_id", how="inner")

    gr_ts = (
        ev.filter(pl.col("activity").is_in([ACT_GR, ACT_SES]))
        .group_by("case_id")
        .agg(pl.col("timestamp").min().alias("gr_min_ts"))
    )
    clear_ts = (
        ev.filter(pl.col("activity") == ACT_CLEAR)
        .group_by("case_id")
        .agg(pl.col("timestamp").min().alias("clear_min_ts"))
    )

    # Evaluate: GR must exist and GR_ts < clear_ts (or no clearance yet)
    merged = applicable_cases.join(gr_ts, on="case_id", how="left").join(
        clear_ts, on="case_id", how="left"
    )
    merged = merged.with_columns(
        [
            pl.when(pl.col("gr_min_ts").is_null())
            .then(pl.lit(False))
            .when(pl.col("clear_min_ts").is_null())
            .then(pl.lit(True))
            .otherwise(pl.col("gr_min_ts") < pl.col("clear_min_ts"))
            .alias("passed"),
            pl.when(pl.col("gr_min_ts").is_null())
            .then(pl.lit("No goods receipt found before invoice clearance"))
            .when(pl.col("clear_min_ts").is_null())
            .then(pl.lit("No invoice clearance yet (compliant)"))
            .otherwise(
                pl.when(pl.col("gr_min_ts") < pl.col("clear_min_ts"))
                .then(pl.lit("GR precedes clearance (compliant)"))
                .otherwise(pl.lit("Invoice cleared before goods receipt"))
            )
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-001")


def _check_cr002(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """CR-002: In 3way_before_gr, GR must occur before Clear Invoice."""
    applicable_cases = cases.filter(
        pl.col("flow_type") == "3way_invoice_before_gr"
    ).select("case_id")

    ev = events.join(applicable_cases, on="case_id", how="inner")

    gr_ts = (
        ev.filter(pl.col("activity").is_in([ACT_GR, ACT_SES]))
        .group_by("case_id")
        .agg(pl.col("timestamp").min().alias("gr_min_ts"))
    )
    clear_ts = (
        ev.filter(pl.col("activity") == ACT_CLEAR)
        .group_by("case_id")
        .agg(pl.col("timestamp").min().alias("clear_min_ts"))
    )

    merged = applicable_cases.join(gr_ts, on="case_id", how="left").join(
        clear_ts, on="case_id", how="left"
    )
    merged = merged.with_columns(
        [
            pl.when(pl.col("clear_min_ts").is_null())
            .then(pl.lit(True))
            .when(pl.col("gr_min_ts").is_null())
            .then(pl.lit(False))
            .otherwise(pl.col("gr_min_ts") < pl.col("clear_min_ts"))
            .alias("passed"),
            pl.when(pl.col("clear_min_ts").is_null())
            .then(pl.lit("No invoice clearance yet (compliant)"))
            .when(pl.col("gr_min_ts").is_null())
            .then(pl.lit("Invoice cleared without any goods receipt"))
            .otherwise(
                pl.when(pl.col("gr_min_ts") < pl.col("clear_min_ts"))
                .then(pl.lit("GR precedes clearance (compliant)"))
                .otherwise(pl.lit("Invoice cleared before goods receipt"))
            )
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-002")


def _check_cr003(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """CR-003: Consignment cases must have no invoice activities."""
    applicable_cases = cases.filter(pl.col("flow_type") == "consignment").select("case_id")

    ev = events.join(applicable_cases, on="case_id", how="inner")

    invoice_presence = (
        ev.filter(pl.col("activity").is_in(INVOICE_ACTIVITIES))
        .group_by("case_id")
        .agg(
            [
                pl.col("activity").first().alias("first_invoice_activity"),
                pl.len().alias("invoice_count"),
            ]
        )
    )

    merged = applicable_cases.join(invoice_presence, on="case_id", how="left")
    merged = merged.with_columns(
        [
            pl.col("invoice_count").is_null().alias("passed"),
            pl.when(pl.col("invoice_count").is_null())
            .then(pl.lit("No invoice activities (compliant)"))
            .otherwise(
                pl.concat_str(
                    [
                        pl.lit("Found "),
                        pl.col("invoice_count").cast(pl.Utf8),
                        pl.lit(" invoice events (e.g. "),
                        pl.col("first_invoice_activity"),
                        pl.lit(")"),
                    ]
                )
            )
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-003")


def _check_cr005(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """CR-005: If 'Create Purchase Order Item' is present, it must be the first event."""
    # Only applicable for cases that contain the create activity
    create_events = events.filter(pl.col("activity") == ACT_CREATE)
    applicable_cases = (
        create_events.select("case_id").unique().join(cases.select("case_id"), on="case_id")
    )

    ev = events.join(applicable_cases, on="case_id", how="inner")

    first_activity = (
        ev.sort(["case_id", "timestamp"])
        .group_by("case_id")
        .first()
        .select(["case_id", "activity"])
        .rename({"activity": "first_activity"})
    )

    merged = applicable_cases.join(first_activity, on="case_id", how="left")
    merged = merged.with_columns(
        [
            (pl.col("first_activity") == ACT_CREATE).alias("passed"),
            pl.when(pl.col("first_activity") == ACT_CREATE)
            .then(pl.lit("Create PO Item is first event (compliant)"))
            .otherwise(
                pl.concat_str(
                    [pl.lit("First event is '"), pl.col("first_activity"), pl.lit("'")]
                )
            )
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-005")


def _check_cr006(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """CR-006: Clear Invoice must only appear after Record Invoice Receipt."""
    # Only check cases that have Clear Invoice
    clear_cases = (
        events.filter(pl.col("activity") == ACT_CLEAR)
        .select("case_id")
        .unique()
        .join(cases.select("case_id"), on="case_id")
    )
    ev = events.join(clear_cases, on="case_id", how="inner")

    ir_ts = (
        ev.filter(pl.col("activity") == ACT_INVOICE_RECEIPT)
        .group_by("case_id")
        .agg(pl.col("timestamp").min().alias("ir_min_ts"))
    )
    clear_ts = (
        ev.filter(pl.col("activity") == ACT_CLEAR)
        .group_by("case_id")
        .agg(pl.col("timestamp").min().alias("clear_min_ts"))
    )

    merged = clear_cases.join(ir_ts, on="case_id", how="left").join(
        clear_ts, on="case_id", how="left"
    )
    merged = merged.with_columns(
        [
            pl.when(pl.col("ir_min_ts").is_null())
            .then(pl.lit(False))
            .otherwise(pl.col("ir_min_ts") <= pl.col("clear_min_ts"))
            .alias("passed"),
            pl.when(pl.col("ir_min_ts").is_null())
            .then(pl.lit("Invoice cleared without any Record Invoice Receipt event"))
            .otherwise(
                pl.when(pl.col("ir_min_ts") <= pl.col("clear_min_ts"))
                .then(pl.lit("Invoice receipt precedes clearance (compliant)"))
                .otherwise(pl.lit("Invoice cleared before invoice was recorded"))
            )
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-006")


def _check_cr007(cases: pl.DataFrame) -> pl.DataFrame:
    """CR-007: All cases under the same purchasing document must share the same vendor."""
    # Group by purchasing_document to find vendor consistency
    doc_vendors = (
        cases.group_by("purchasing_document")
        .agg(pl.col("vendor").n_unique().alias("vendor_count"))
    )
    # Join back to get per-case pass/fail
    merged = cases.select(["case_id", "purchasing_document"]).join(
        doc_vendors, on="purchasing_document", how="left"
    )
    merged = merged.with_columns(
        [
            (pl.col("vendor_count") == 1).alias("passed"),
            pl.when(pl.col("vendor_count") == 1)
            .then(pl.lit("Single vendor per document (compliant)"))
            .otherwise(
                pl.concat_str(
                    [
                        pl.lit("Document has "),
                        pl.col("vendor_count").cast(pl.Utf8),
                        pl.lit(" different vendors"),
                    ]
                )
            )
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-007")


def _check_cr008(cases: pl.DataFrame) -> pl.DataFrame:
    """CR-008: Case duration must be within P95 for the same flow_type."""
    # Compute P95 per flow_type
    p95_per_flow = (
        cases.group_by("flow_type")
        .agg(pl.col("case_duration_days").quantile(0.95).alias("p95_days"))
    )
    merged = cases.select(["case_id", "flow_type", "case_duration_days"]).join(
        p95_per_flow, on="flow_type", how="left"
    )
    merged = merged.with_columns(
        [
            (pl.col("case_duration_days") <= pl.col("p95_days")).alias("passed"),
            pl.when(pl.col("case_duration_days") <= pl.col("p95_days"))
            .then(pl.lit("Duration within P95 (compliant)"))
            .otherwise(
                pl.concat_str(
                    [
                        pl.lit("Duration "),
                        pl.col("case_duration_days").round(1).cast(pl.Utf8),
                        pl.lit("d exceeds P95 "),
                        pl.col("p95_days").round(1).cast(pl.Utf8),
                        pl.lit("d"),
                    ]
                )
            )
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-008")


def _check_cr009(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """CR-009: No activity should appear more than 2 times in a single case."""
    max_repeats = (
        events.group_by(["case_id", "activity"])
        .agg(pl.len().alias("count"))
        .group_by("case_id")
        .agg(pl.col("count").max().alias("max_activity_count"))
    )
    merged = cases.select("case_id").join(max_repeats, on="case_id", how="left")
    merged = merged.with_columns(
        pl.col("max_activity_count").fill_null(1)
    )
    merged = merged.with_columns(
        [
            (pl.col("max_activity_count") <= 2).alias("passed"),
            pl.when(pl.col("max_activity_count") <= 2)
            .then(pl.lit("No excessive rework (compliant)"))
            .otherwise(
                pl.concat_str(
                    [
                        pl.lit("An activity repeats "),
                        pl.col("max_activity_count").cast(pl.Utf8),
                        pl.lit(" times"),
                    ]
                )
            )
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-009")


def _check_cr010(events: pl.DataFrame, cases: pl.DataFrame) -> pl.DataFrame:
    """CR-010: Case must have at least one terminal activity."""
    has_terminal = (
        events.filter(pl.col("activity").is_in(TERMINAL_ACTIVITIES))
        .group_by("case_id")
        .agg(pl.col("activity").first().alias("terminal_found"))
    )
    merged = cases.select("case_id").join(has_terminal, on="case_id", how="left")
    merged = merged.with_columns(
        [
            pl.col("terminal_found").is_not_null().alias("passed"),
            pl.when(pl.col("terminal_found").is_not_null())
            .then(
                pl.concat_str(
                    [
                        pl.lit("Terminal activity '"),
                        pl.col("terminal_found").fill_null(""),
                        pl.lit("' present"),
                    ]
                )
            )
            .otherwise(pl.lit("No terminal activity found (case may be open)"))
            .alias("detail"),
        ]
    )
    return _format_rule(merged, "CR-010")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _format_rule(df: pl.DataFrame, rule_id: str) -> pl.DataFrame:
    """Standardize a rule result DataFrame into fact_compliance_checks format.

    Args:
        df: DataFrame with case_id, passed, detail columns.
        rule_id: Rule identifier string (e.g. "CR-001").

    Returns:
        DataFrame with: case_id, rule_id, rule_name, passed, severity, detail.
    """
    rule_meta = RULES[rule_id]
    return df.select(["case_id", "passed", "detail"]).with_columns(
        [
            pl.lit(rule_id).alias("rule_id"),
            pl.lit(rule_meta["name"]).alias("rule_name"),
            pl.lit(rule_meta["severity"]).alias("severity"),
        ]
    ).select(["case_id", "rule_id", "rule_name", "passed", "severity", "detail"])
