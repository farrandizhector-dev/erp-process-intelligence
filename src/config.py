"""Central configuration for the ERP Process Intelligence Platform.

All file paths and tunable constants live here. Import from this module
rather than hardcoding paths or magic numbers anywhere else.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Repository root
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
REFERENCE_DIR = DATA_DIR / "reference"

# ---------------------------------------------------------------------------
# Raw input
# ---------------------------------------------------------------------------
XES_FILE = RAW_DIR / "BPI_Challenge_2019.xes"

# ---------------------------------------------------------------------------
# Bronze parquet paths
# ---------------------------------------------------------------------------
BRONZE_EVENTS = BRONZE_DIR / "bronze_events.parquet"
BRONZE_CASES = BRONZE_DIR / "bronze_cases.parquet"

# ---------------------------------------------------------------------------
# Silver parquet paths
# ---------------------------------------------------------------------------
SILVER_EVENTS = SILVER_DIR / "silver_events.parquet"
SILVER_CASES = SILVER_DIR / "silver_cases.parquet"
SILVER_RESOURCES = SILVER_DIR / "silver_resources.parquet"
SILVER_ACTIVITIES = SILVER_DIR / "silver_activities.parquet"

# ---------------------------------------------------------------------------
# Gold parquet paths — facts
# ---------------------------------------------------------------------------
GOLD_FACT_EVENT_LOG = GOLD_DIR / "fact_event_log.parquet"
GOLD_FACT_CASE_SUMMARY = GOLD_DIR / "fact_case_summary.parquet"
GOLD_FACT_VARIANT_STATS = GOLD_DIR / "fact_variant_stats.parquet"
GOLD_FACT_COMPLIANCE = GOLD_DIR / "fact_compliance_checks.parquet"
GOLD_FACT_BOTTLENECK = GOLD_DIR / "fact_bottleneck_analysis.parquet"
GOLD_FACT_AUTOMATION = GOLD_DIR / "fact_automation_opportunities.parquet"
GOLD_FACT_SLA_RISK = GOLD_DIR / "fact_sla_risk.parquet"

# Gold parquet paths — dimensions
GOLD_DIM_ACTIVITY = GOLD_DIR / "dim_activity.parquet"
GOLD_DIM_COMPANY = GOLD_DIR / "dim_company.parquet"
GOLD_DIM_VENDOR = GOLD_DIR / "dim_vendor.parquet"
GOLD_DIM_RESOURCE = GOLD_DIR / "dim_resource.parquet"
GOLD_DIM_CALENDAR = GOLD_DIR / "dim_calendar.parquet"

# ---------------------------------------------------------------------------
# Reference data paths
# ---------------------------------------------------------------------------
ACTIVITY_STAGE_MAPPING = REFERENCE_DIR / "activity_stage_mapping.json"
NORMATIVE_MODELS = REFERENCE_DIR / "normative_models.json"

# ---------------------------------------------------------------------------
# Frontend JSON export paths
# ---------------------------------------------------------------------------
FRONTEND_DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"

FRONTEND_EXECUTIVE_KPIS = FRONTEND_DATA_DIR / "executive_kpis.json"
FRONTEND_PROCESS_FLOW = FRONTEND_DATA_DIR / "process_flow.json"
FRONTEND_VARIANTS = FRONTEND_DATA_DIR / "variants.json"
FRONTEND_COMPLIANCE_SUMMARY = FRONTEND_DATA_DIR / "compliance_summary.json"
FRONTEND_COMPLIANCE_DETAILS = FRONTEND_DATA_DIR / "compliance_details.json"
FRONTEND_BOTTLENECKS = FRONTEND_DATA_DIR / "bottlenecks.json"
FRONTEND_AUTOMATION = FRONTEND_DATA_DIR / "automation_candidates.json"
FRONTEND_CASE_SUMMARIES = FRONTEND_DATA_DIR / "case_summaries.json"
FRONTEND_COMPANY_BENCHMARKS = FRONTEND_DATA_DIR / "company_benchmarks.json"
FRONTEND_SLA_RISK = FRONTEND_DATA_DIR / "sla_risk.json"

# ---------------------------------------------------------------------------
# Model artifacts
# ---------------------------------------------------------------------------
MODELS_DIR = ROOT_DIR / "models"
SLA_MODEL_PATH = MODELS_DIR / "sla_risk_lgbm.pkl"

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
OUTPUTS_DIR = ROOT_DIR / "outputs"
PROFILING_REPORT = OUTPUTS_DIR / "profiling_report.md"

# ---------------------------------------------------------------------------
# Quality gates — expected values from BPI 2019 documentation
# ---------------------------------------------------------------------------
EXPECTED_EVENT_COUNT = 1_595_923
EXPECTED_CASE_COUNT = 251_734
EXPECTED_ACTIVITY_COUNT = 42
ROW_COUNT_TOLERANCE = 0.01  # ±1% tolerance

# ---------------------------------------------------------------------------
# Silver layer constants
# ---------------------------------------------------------------------------
BUSINESS_HOURS_START = 8   # 08:00 local time
BUSINESS_HOURS_END = 18    # 18:00 local time

# Resource classification: names matching this prefix are batch users
# Confirmed from Phase 1 XES inspection: lowercase "batch_" (batch_00, batch_01, ...)
BATCH_RESOURCE_PREFIX = "batch_"

# ---------------------------------------------------------------------------
# Compliance rules
# ---------------------------------------------------------------------------
# Maximum value mismatch allowed for GR ↔ Invoice matching
# (absolute tolerance OR 1% of GR value, whichever is larger)
VALUE_MATCH_ABS_TOLERANCE = 1.0
VALUE_MATCH_PCT_TOLERANCE = 0.01

# ---------------------------------------------------------------------------
# Bottleneck detection threshold
# ---------------------------------------------------------------------------
# A transition is flagged as a bottleneck if P90 wait time exceeds this
BOTTLENECK_THRESHOLD_HOURS = 7 * 24  # 7 days in hours

# ---------------------------------------------------------------------------
# Automation scoring weights
# ---------------------------------------------------------------------------
AUTOMATION_WEIGHTS = {
    "volume_score": 0.25,
    "batch_gap_score": 0.20,
    "input_uniformity": 0.20,
    "timing_regularity": 0.15,
    "error_reduction": 0.10,
    "wait_reduction": 0.10,
}
AUTOMATION_TIER_THRESHOLDS = {
    "quick_win": 0.70,
    "medium_effort": 0.50,
    "complex": 0.30,
    # below 0.30 → "not_recommended"
}
AUTOMATION_ALREADY_BATCH_THRESHOLD = 0.80  # >80% batch → "not_recommended"
AUTOMATION_VOLUME_QUANTILE_THRESHOLD = 0.75  # P75 for "quick_win" volume gate
MAX_HUMAN_PROCESSING_MINUTES = 30  # cap for estimated_hours_saved calculation

# ---------------------------------------------------------------------------
# Predictive layer
# ---------------------------------------------------------------------------
SLA_THRESHOLD_QUANTILE = 0.75  # P75 of duration per flow type defines "SLA breach"
TEMPORAL_SPLIT_CUTOFF = 0.80   # 80% of cases (by time) go to train set

# ---------------------------------------------------------------------------
# Dataset date range (updated after Phase 1 inspection)
# ---------------------------------------------------------------------------
DATASET_START_DATE: str | None = None  # Filled after Phase 1
DATASET_END_DATE: str | None = None    # Filled after Phase 1
DATASET_MONTHS: float | None = None    # Filled after Phase 1

# ---------------------------------------------------------------------------
# Frontend JSON size budget
# ---------------------------------------------------------------------------
MAX_CASE_SUMMARIES_SAMPLE = 1000  # rows exported to case_summaries.json
MAX_COMPLIANCE_DETAIL_CASES = 500  # worst-compliance cases exported
MAX_VARIANTS_EXPORTED = 50        # top N variants exported
MAX_BOTTLENECK_TRANSITIONS = None  # all transitions with >100 occurrences
MAX_TOP_BOTTLENECKS = 15
MAX_TOP_VIOLATING_VENDORS = 20
