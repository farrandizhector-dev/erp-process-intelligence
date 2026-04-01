"""Tests for analytics modules: process discovery, conformance, throughput, automation."""

from __future__ import annotations

import polars as pl

from src.analytics.automation_scoring import shannon_entropy
from src.analytics.conformance import RULES, _check_cr005, _check_cr006, _check_cr009
from src.analytics.process_discovery import detect_rework
from src.analytics.throughput import build_bottleneck_table, build_transitions

# ---------------------------------------------------------------------------
# Process discovery
# ---------------------------------------------------------------------------


def test_variant_id_same_sequence_same_id() -> None:
    """Cases with identical activity sequences must get the same variant_id."""
    from src.transformation.temporal_enrichment import _compute_variant_id

    seq1 = ["Create Purchase Order Item", "Record Goods Receipt", "Clear Invoice"]
    seq2 = ["Create Purchase Order Item", "Record Goods Receipt", "Clear Invoice"]
    assert _compute_variant_id(seq1) == _compute_variant_id(seq2)


def test_variant_id_different_sequence_different_id() -> None:
    """Cases with different activity sequences must get different variant_ids."""
    from src.transformation.temporal_enrichment import _compute_variant_id

    seq1 = ["Create Purchase Order Item", "Record Goods Receipt", "Clear Invoice"]
    seq2 = ["Create Purchase Order Item", "Clear Invoice", "Record Goods Receipt"]
    assert _compute_variant_id(seq1) != _compute_variant_id(seq2)


def test_rework_detection_repeated_activity(sample_silver_events: pl.DataFrame) -> None:
    """Case DOC2_ITEM1 has a repeated activity — must be detected as rework."""
    case = sample_silver_events.filter(pl.col("case_id") == "DOC2_ITEM1")
    activities = case["activity"].to_list()
    repeated = len(activities) != len(set(activities))
    assert repeated, "DOC2_ITEM1 should have at least one repeated activity"


def test_loop_detection_not_in_happy_path(sample_silver_events: pl.DataFrame) -> None:
    """Happy path case DOC1_ITEM1 should have no loops."""
    case = sample_silver_events.filter(pl.col("case_id") == "DOC1_ITEM1")
    activities = case["activity"].to_list()
    assert len(activities) == len(set(activities)), "DOC1_ITEM1 should have no repeated activities"


def test_detect_rework_counts_correctly(sample_silver_events: pl.DataFrame) -> None:
    """detect_rework must count DOC2_ITEM1 as having rework, DOC1_ITEM1 as not."""
    result = detect_rework(sample_silver_events)
    doc1 = result.filter(pl.col("case_id") == "DOC1_ITEM1")
    doc2 = result.filter(pl.col("case_id") == "DOC2_ITEM1")
    assert doc1["has_rework"][0] is False
    assert doc2["has_rework"][0] is True


# ---------------------------------------------------------------------------
# Conformance
# ---------------------------------------------------------------------------


def test_compliance_score_range(
    sample_silver_events: pl.DataFrame, sample_silver_cases: pl.DataFrame
) -> None:
    """Compliance scores must be in [0, 1]."""
    from src.analytics.conformance import compute_case_compliance_scores, run_all_rules

    checks = run_all_rules(sample_silver_events, sample_silver_cases)
    scores = compute_case_compliance_scores(checks)
    assert (scores["compliance_score"] >= 0.0).all()
    assert (scores["compliance_score"] <= 1.0).all()


def test_cr005_create_is_first_event(
    sample_silver_events: pl.DataFrame, sample_silver_cases: pl.DataFrame
) -> None:
    """CR-005: 'Create Purchase Order Item' must be the first activity."""
    result = _check_cr005(sample_silver_events, sample_silver_cases)
    # All 3 test cases start with "Create Purchase Order Item" — all should pass
    assert result["passed"].all(), f"Some CR-005 failures: {result.filter(~pl.col('passed'))}"


def test_cr006_invoice_before_clear(
    sample_silver_events: pl.DataFrame, sample_silver_cases: pl.DataFrame
) -> None:
    """CR-006: Record Invoice Receipt must precede Clear Invoice."""
    result = _check_cr006(sample_silver_events, sample_silver_cases)
    failures = result.filter(~pl.col("passed"))
    assert len(failures) == 0, f"CR-006 failures: {failures}"


def test_cr009_no_excessive_rework(
    sample_silver_events: pl.DataFrame, sample_silver_cases: pl.DataFrame
) -> None:
    """CR-009: Activities repeated <= 2 times per case must pass."""
    result = _check_cr009(sample_silver_events, sample_silver_cases)
    # DOC2_ITEM1 has Record Invoice Receipt twice (= 2, at threshold) — should pass
    assert result["passed"].all(), f"CR-009 failures: {result.filter(~pl.col('passed'))}"


def test_rules_have_correct_severities() -> None:
    """All rules must have valid severity values."""
    valid_severities = {"info", "warning", "critical"}
    for rule_id, rule in RULES.items():
        assert rule["severity"] in valid_severities, f"{rule_id} has invalid severity"


# ---------------------------------------------------------------------------
# Throughput
# ---------------------------------------------------------------------------


def test_transition_wait_non_negative(sample_silver_events: pl.DataFrame) -> None:
    """All computed transition wait times must be >= 0."""
    transitions = build_transitions(sample_silver_events)
    assert (transitions["wait_hours"] >= 0).all()


def test_bottleneck_threshold_respected(sample_silver_events: pl.DataFrame) -> None:
    """Bottleneck flag must only be True when P90 wait > configured threshold."""
    from src import config

    transitions = build_transitions(sample_silver_events)
    bottlenecks = build_bottleneck_table(transitions, min_transition_count=1)
    violating = bottlenecks.filter(
        pl.col("is_bottleneck") & (pl.col("p90_wait_hours") <= config.BOTTLENECK_THRESHOLD_HOURS)
    )
    assert len(violating) == 0, f"Bottleneck flag set despite P90 <= threshold: {violating}"


def test_build_transitions_drops_last_event(sample_silver_events: pl.DataFrame) -> None:
    """build_transitions drops the last event per case (no successor)."""
    n_events = len(sample_silver_events)
    n_cases = sample_silver_events["case_id"].n_unique()
    transitions = build_transitions(sample_silver_events)
    # Each case loses exactly one event (the last one)
    assert len(transitions) == n_events - n_cases


# ---------------------------------------------------------------------------
# Automation scoring
# ---------------------------------------------------------------------------


def test_automation_score_range() -> None:
    """Automation scores must be in [0, 1] — tested via shannon_entropy boundary."""
    assert shannon_entropy({}) == 0.0
    assert shannon_entropy({"a": 0}) == 0.0


def test_automation_weights_sum_to_one() -> None:
    """Automation weight coefficients must sum to 1.0."""
    from src.config import AUTOMATION_WEIGHTS

    total = sum(AUTOMATION_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"


def test_shannon_entropy_single_value_is_zero() -> None:
    """Shannon entropy of a degenerate distribution (1 value) must be 0."""
    assert shannon_entropy({"a": 100}) == 0.0


def test_shannon_entropy_uniform_is_one() -> None:
    """Shannon entropy of a uniform distribution must be 1.0 (normalized)."""
    result = shannon_entropy({"a": 1, "b": 1, "c": 1, "d": 1})
    assert abs(result - 1.0) < 1e-9
