# Architecture — ERP Process Intelligence Platform

## Design Principles

1. **Medallion Architecture** — Bronze (raw) → Silver (clean) → Gold (analytics-ready). Clear data lineage, no magic transformations.
2. **Reproducibility** — Every transformation is scripted and tested. Re-running the pipeline from the XES file produces identical outputs.
3. **Separation of concerns** — Ingestion, transformation, analytics, and presentation are isolated modules.
4. **No notebooks as deliverables** — All logic lives in `.py` modules with unit tests.
5. **Dimensional modeling at Gold** — Fact + dimension tables optimized for BI consumption.

---

## Data Flow

```
data/raw/BPI_Challenge_2019.xes   (728 MB)
         │
         │  src/ingestion/xes_parser.py     ← pm4py parses IEEE-XES XML
         │  src/ingestion/bronze_writer.py  ← writes parquet with Polars
         ▼
data/bronze/
  bronze_events.parquet   (~100 MB)   — one row per event
  bronze_cases.parquet    (~20 MB)    — one row per case (trace attributes)
         │
         │  src/transformation/silver_builder.py
         │  src/transformation/temporal_enrichment.py
         │  src/transformation/resource_classifier.py
         │  src/transformation/flow_type_classifier.py
         ▼
data/silver/
  silver_events.parquet   — timestamps normalized, event ordering, resource type
  silver_cases.parquet    — flow_type, variant_id, case metrics
  silver_resources.parquet — resource profiles
  silver_activities.parquet — activity-level aggregates
         │
         │  src/analytics/process_discovery.py
         │  src/analytics/conformance.py
         │  src/analytics/throughput.py
         │  src/analytics/resource_analysis.py
         │  src/analytics/automation_scoring.py
         │  src/analytics/predictive.py
         │  src/gold/mart_builder.py
         │  src/gold/facts.py
         │  src/gold/dimensions.py
         ▼
data/gold/
  fact_event_log.parquet         — enriched event-level fact
  fact_case_summary.parquet      — one row per case with all KPIs
  fact_variant_stats.parquet     — process variant statistics
  fact_compliance_checks.parquet — one row per case × rule
  fact_bottleneck_analysis.parquet — activity transition metrics
  fact_automation_opportunities.parquet — automation scoring per activity
  fact_sla_risk.parquet          — predictive risk scores
  dim_activity.parquet
  dim_company.parquet
  dim_vendor.parquet
  dim_resource.parquet
  dim_calendar.parquet
         │
         │  scripts/export_for_frontend.py
         ▼
frontend/public/data/
  executive_kpis.json
  process_flow.json
  variants.json
  compliance_summary.json
  compliance_details.json
  bottlenecks.json
  automation_candidates.json
  case_summaries.json
  company_benchmarks.json
  sla_risk.json
         │
         ▼
React Dashboard (7 pages, ECharts)
```

---

## Technology Choices

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| XES Parsing | **pm4py** | Industry-standard Python process mining library; handles IEEE-XES natively |
| Data Processing | **Polars** | Columnar, Rust-backed, memory-efficient for 1.6M events; lazy evaluation |
| Analytical SQL | **DuckDB** | In-process SQL over parquet for complex aggregations; no server required |
| Schema Validation | **Pandera (Polars backend)** | Schema contracts between layers; catches type errors early |
| ML | **LightGBM + scikit-learn** | Gradient boosting for SLA risk; only used in predictive layer |
| Testing | **pytest** | Standard, clean fixture model |
| Frontend | **React 18 + TypeScript** | Type-safe component architecture |
| Styling | **Tailwind CSS** | Utility-first; rapid iteration without custom CSS |
| Charts | **ECharts** | Rich library: Sankey diagrams, heatmaps, gauges, radar charts |
| Build | **Vite** | Fast HMR, tree-shaking, ECharts chunking |
| CI | **GitHub Actions** | Lint + test on push; build frontend |

---

## Parquet Strategy

All parquet files use **zstd compression** (Polars default). No partitioning at this scale (1.6M events fits in memory with Polars). If the dataset were 10× larger, `fact_event_log` would be partitioned by `flow_type`.

---

## Process Stage Model

42 raw activities are grouped into 9 semantic P2P stages:

| Stage | Name | Role |
|-------|------|------|
| S1 | Requisition & Creation | PO creation and setup |
| S2 | Approval & Release | Authorization |
| S3 | Vendor Interaction | PO sent, vendor acknowledges |
| S4 | Goods Receipt | Physical receipt |
| S5 | Invoice Processing | Invoice receipt and entry |
| S6 | Matching & Verification | 2-way / 3-way matching |
| S7 | Payment & Clearing | Financial settlement |
| S8 | Exception & Rework | Corrections, cancellations |
| S9 | Closure | Administrative close |

The mapping from activity names → stages is stored in `data/reference/activity_stage_mapping.json` (created during Phase 1 after inspecting the actual XES activity names).

---

## Compliance Engine

10 rules derived from BPI 2019 challenge documentation and standard P2P compliance patterns. Rules are evaluated per case and produce a compliance score (0–1). See `docs/kpi_catalog.md` for rule definitions.

---

## Frontend Data Strategy

- Gold parquet → JSON via `scripts/export_for_frontend.py`
- JSON files served as static assets (`frontend/public/data/`)
- Target: < 10 MB total, < 5 MB largest file
- Lazy loading: each page loads its own JSON on first visit
- No backend required — fully static deployment (GitHub Pages)
