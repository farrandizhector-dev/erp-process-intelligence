"""Tests for data quality checks and Pandera schema validation."""

from __future__ import annotations


def test_quality_placeholder_bronze_events_schema() -> None:
    """Placeholder: bronze_events Pandera schema must pass on valid data."""
    # TODO: implement after Phase 2 when schemas.py is built
    pass


def test_quality_placeholder_silver_events_null_rate() -> None:
    """Placeholder: silver_events null rate per column must be below threshold."""
    # TODO: implement after Phase 2
    pass


def test_config_paths_are_path_objects() -> None:
    """All path constants in config must be pathlib.Path objects."""
    from pathlib import Path

    from src import config

    path_attrs = [
        "ROOT_DIR", "DATA_DIR", "RAW_DIR", "BRONZE_DIR", "SILVER_DIR",
        "GOLD_DIR", "REFERENCE_DIR", "XES_FILE",
        "BRONZE_EVENTS", "BRONZE_CASES",
        "SILVER_EVENTS", "SILVER_CASES",
        "GOLD_FACT_CASE_SUMMARY", "GOLD_FACT_VARIANT_STATS",
    ]
    for attr in path_attrs:
        val = getattr(config, attr)
        assert isinstance(val, Path), f"config.{attr} is {type(val)}, expected Path"


def test_config_expected_counts_positive() -> None:
    """Expected event and case counts must be positive integers."""
    from src import config

    assert config.EXPECTED_EVENT_COUNT > 0
    assert config.EXPECTED_CASE_COUNT > 0
    assert config.EXPECTED_ACTIVITY_COUNT > 0


def test_config_tolerance_fraction() -> None:
    """ROW_COUNT_TOLERANCE must be between 0 and 1."""
    from src import config

    assert 0 < config.ROW_COUNT_TOLERANCE < 1


def test_config_sla_threshold_quantile_range() -> None:
    """SLA_THRESHOLD_QUANTILE must be in (0, 1)."""
    from src import config

    assert 0 < config.SLA_THRESHOLD_QUANTILE < 1


def test_config_bottleneck_threshold_positive() -> None:
    """BOTTLENECK_THRESHOLD_HOURS must be positive."""
    from src import config

    assert config.BOTTLENECK_THRESHOLD_HOURS > 0
