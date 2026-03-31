# CONTEXT.md — ERP Process Intelligence Platform
## Master Execution Guide for Claude Code

> **CRITICAL INSTRUCTION FOR CLAUDE CODE:**
> 1. READ this entire document before ANY work on ANY phase.
> 2. After completing each phase, REWRITE this document updating the `## Execution Status` section with what was built, decisions made, file paths created, and any deviations from plan.
> 3. This document is the SINGLE SOURCE OF TRUTH. If context window resets, this file restores full project awareness.
> 4. Never invent dataset facts. All data insights must come from inspecting the actual XES file.

---

## 1. Project Identity

**Name:** ERP Process Intelligence Platform
**Subtitle:** Procure-to-Pay Mining, Compliance & Automation Intelligence

**One-liner for CV:**
Built an end-to-end Procure-to-Pay process intelligence platform on top of a real enterprise event log (251K cases, 1.6M events), combining process mining, conformance/compliance analysis, bottleneck detection, automation opportunity scoring, SLA-risk modeling and executive BI dashboards for purchasing workflows.

**What this project IS:**
A platform that transforms raw ERP purchase-order event data into actionable process intelligence — the kind of deliverable a consulting firm like LIDER IT would sell to a client running SAP, Oracle, or Dynamics.

**What this project is NOT:**
- Not another ML/forecasting project (the portfolio already has AI Supply Chain Control Tower)
- Not an academic paper on process mining
- Not a notebook-centric analysis
- Not an impossible architecture that can't be built solo

---

## 2. Portfolio Strategy

**Owner:** Héctor Ferrándiz Sanchis — 1st year Data Science, Universidad Europea de Valencia
**LinkedIn:** linkedin.com/in/hectordata

**Existing portfolio projects:**
1. AI Supply Chain Control Tower — demand forecasting, LightGBM, hierarchical reconciliation, Monte Carlo, React dashboard (WRMSSE 0.551)
2. (Other university projects — visualization, pandas analytics)

**Gap this project fills:**
The portfolio lacks anything in the ERP / BI / process mining / compliance / automation space. This project demonstrates:
- Understanding of enterprise purchasing processes (Procure-to-Pay)
- Data architecture beyond ML pipelines (medallion layers, dimensional modeling)
- Business process analysis and compliance thinking
- Automation opportunity identification (relevant to RPA practices)
- Executive BI dashboarding for non-technical stakeholders
- Consulting-grade problem framing and documentation

**Target employer profile:** LIDER IT or similar firms operating in ERP, BI/Business Analytics, Microsoft Fabric, RPA/automation, and enterprise data integration.

**Differentiation message:**
"I can take a real enterprise process, build a clean data architecture around it, measure it, diagnose it, and present it in an executive layer that drives decisions. I don't just build models — I build analytical products."

---

## 3. Business Problem Statement

### The Problem
Organizations running ERP systems (SAP, Oracle, Dynamics) generate massive event logs from their transactional processes. The Procure-to-Pay (P2P) cycle — from purchase requisition through goods receipt, invoice verification, to payment — is one of the most critical and compliance-sensitive flows in any enterprise.

Despite having ERP systems, most companies cannot answer:
- **How does the purchasing process actually flow** vs. how it's supposed to flow?
- **Where do delays accumulate?** Which activities are bottlenecks?
- **Which purchase orders deviate** from the expected process? How severe are deviations?
- **Is the organization compliant** with its own purchasing policies (3-way matching, approval sequences, invoice verification)?
- **Which subsidiaries or vendors** create the most rework, delays, or exceptions?
- **Which manual steps** could be automated (RPA candidates)?
- **Which cases are at risk** of breaching SLA or payment terms?

### The Solution
This platform ingests a real Procure-to-Pay event log, reconstructs the actual process flows, measures performance, checks compliance, identifies automation opportunities, and delivers the results through an enterprise-grade BI application.

### Target Users (Simulated)
- **CFO / VP Procurement:** Executive KPIs, compliance rates, spend visibility
- **Process Owner / Operations Manager:** Bottleneck analysis, variant exploration, SLA monitoring
- **Internal Audit / Compliance:** Conformance checking, deviation severity, exception reports
- **RPA / Automation Team:** Automation candidate scoring, manual-step identification
- **IT / Data Team:** Data architecture documentation, pipeline reproducibility

---

## 4. Dataset Specification

### Source
- **Name:** BPI Challenge 2019
- **Provider:** TU/e (Eindhoven University of Technology) / 4TU.Centre for Research Data
- **Type:** IEEE-XES compliant event log
- **File:** `BPI_Challenge_2019.xes` (~728 MB)
- **Domain:** Real purchase order handling from a multinational coatings/paints company (Netherlands)
- **Download:** https://data.4tu.nl/datasets/769f25d0-e167-4a35-bbb6-7c96a8872593

### Dataset Dimensions (from documentation)
| Metric | Value |
|--------|-------|
| Purchase Documents | 76,349 |
| Line Items (Cases) | 251,734 |
| Events | 1,595,923 |
| Activities | 42 |
| Users | 627 (607 human + 20 batch) |

### Case ID Structure
Each case = `{Purchase Document ID}_{Item ID}`. A single purchase document can contain multiple line items, each tracked as a separate case.

### Four Process Flow Types
The dataset contains four fundamentally different P2P flows determined by item flags:

| Flow Type | GR-Based IV | Goods Receipt | Description |
|-----------|-------------|---------------|-------------|
| **3-way match, invoice after GR** | TRUE | TRUE | Standard: GR value matched against invoice and creation value |
| **3-way match, invoice before GR** | FALSE | TRUE | Invoice entered before goods arrive, blocked until GR received |
| **2-way match** | FALSE | FALSE | Invoice matched against creation value only, no GR needed |
| **Consignment** | FALSE (flag) | TRUE | No PO-level invoices; handled in separate process |

### Key Case-Level Attributes
- `concept:name` — Case ID (document + item)
- `Purchasing Document` — Document ID
- `Item` — Item ID within document
- `Item Type` — Type classification
- `GR-Based Inv. Verif.` — Boolean flag for GR-based invoicing
- `Goods Receipt` — Boolean flag for goods receipt requirement
- `Source` — Source ERP system
- `Doc. Category name` — Document category
- `Company` — Subsidiary identifier (anonymized)
- `Spend classification text` — Spend class
- `Spend area text` — Spend area
- `Sub spend area text` — Sub-area
- `Vendor` — Vendor ID (anonymized)
- `Name` — Vendor name (anonymized)
- `Document Type` — Document type code
- `Item Category` — Flow category (3-way GR, 3-way no GR, 2-way, consignment)

### Event-Level Attributes (expected, to be confirmed from XES)
- `concept:name` — Activity name
- `time:timestamp` — Event timestamp
- `org:resource` — User/resource (batch or human)
- `eventID` — Event identifier
- Monetary value attributes (anonymized via linear translation preserving 0)

### Key Compliance Questions (from BPI Challenge)
1. Can the process be described by a collection of models based on the four flow types?
2. What is the throughput of invoicing (time between GR, invoice receipt, payment)?
3. Which purchase documents deviate from expected process? How severe?
4. Which vendors/subsidiaries create rework due to incorrect invoices?

### Known Dataset Characteristics
- Anonymized but semantically consistent (company can decode)
- Monetary values use linear translation (preserves 0 and additive properties)
- Some events have empty/NONE user field
- Batch users vs. human users distinguishable by name pattern
- Multiple GR messages and invoices per line item are common (rent, logistical services)
- Amounts across GR messages and invoices must match line item value for compliance

---

## 5. Architecture Overview

### Design Principles
1. **Medallion Architecture** (Bronze → Silver → Gold) for clear data lineage
2. **Dimensional Modeling** at Gold layer for BI consumption
3. **Separation of concerns:** ingestion, transformation, analytics, presentation
4. **Reproducibility:** every transformation scripted, tested, logged
5. **No notebooks as deliverables** — all logic in `.py` modules with tests

### Repository Structure
```
erp-process-intelligence/
├── CONTEXT.md                          # THIS FILE — master guide
├── README.md                           # Public-facing project README
├── CLAUDE.md                           # Claude Code specific instructions
├── pyproject.toml                      # Python project config
├── .github/
│   └── workflows/
│       └── ci.yml                      # Linting + tests
│
├── docs/
│   ├── architecture.md                 # Architecture decisions and diagrams
│   ├── data_dictionary.md              # Complete field reference
│   ├── decision_log.md                 # Why we chose X over Y
│   ├── modeling_notes.md               # Process mining methodology notes
│   ├── limitations.md                  # Honest limitations
│   ├── runbook.md                      # How to run the full pipeline
│   └── kpi_catalog.md                  # KPI definitions and formulas
│
├── data/
│   ├── raw/                            # Bronze: original XES (gitignored, too large)
│   ├── bronze/                         # Parsed parquet files
│   ├── silver/                         # Cleaned, normalized tables
│   ├── gold/                           # Analytical marts
│   └── reference/                      # Static lookups, calendars
│
├── src/
│   ├── __init__.py
│   ├── config.py                       # Paths, constants, parameters
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── xes_parser.py              # XES → raw DataFrames
│   │   └── bronze_writer.py           # Write bronze parquet
│   ├── transformation/
│   │   ├── __init__.py
│   │   ├── silver_builder.py          # Bronze → Silver
│   │   ├── temporal_enrichment.py     # Timestamp derivations
│   │   ├── resource_classifier.py     # Batch vs human classification
│   │   └── flow_type_classifier.py    # 4-type flow classification
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── process_discovery.py       # Variants, happy path, loops
│   │   ├── conformance.py             # Compliance checks
│   │   ├── throughput.py              # Lead/cycle/wait times, bottlenecks
│   │   ├── resource_analysis.py       # Workload, handoffs, batch patterns
│   │   ├── automation_scoring.py      # Automation opportunity scoring
│   │   └── predictive.py             # SLA risk / case outcome prediction
│   ├── gold/
│   │   ├── __init__.py
│   │   ├── mart_builder.py           # Orchestrate gold mart creation
│   │   ├── facts.py                  # Fact table builders
│   │   └── dimensions.py            # Dimension table builders
│   ├── quality/
│   │   ├── __init__.py
│   │   ├── schemas.py                # Pandera schemas for validation
│   │   └── data_checks.py           # Custom quality assertions
│   └── pipeline/
│       ├── __init__.py
│       └── runner.py                 # Full pipeline orchestrator
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_silver.py
│   ├── test_gold.py
│   ├── test_analytics.py
│   └── test_quality.py
│
├── scripts/
│   ├── run_pipeline.py               # CLI entry point
│   ├── profile_data.py               # Generate profiling report
│   └── export_for_frontend.py        # Export gold → JSON for React app
│
├── frontend/                          # React + TypeScript + Tailwind + ECharts
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   ├── public/
│   │   └── data/                     # JSON exports from gold layer
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   ├── Header.tsx
│       │   │   └── PageContainer.tsx
│       │   ├── charts/
│       │   │   ├── ProcessMap.tsx        # Sankey/flow visualization
│       │   │   ├── VariantExplorer.tsx
│       │   │   ├── BottleneckHeatmap.tsx
│       │   │   ├── TimelineChart.tsx
│       │   │   ├── ComplianceGauge.tsx
│       │   │   └── KPICard.tsx
│       │   └── shared/
│       │       ├── FilterBar.tsx
│       │       └── DataTable.tsx
│       ├── pages/
│       │   ├── ExecutiveOverview.tsx
│       │   ├── ProcessMap.tsx
│       │   ├── ComplianceCenter.tsx
│       │   ├── BottleneckExplorer.tsx
│       │   ├── AutomationCandidates.tsx
│       │   ├── CaseDrilldown.tsx
│       │   └── SubsidiaryBenchmark.tsx
│       ├── hooks/
│       │   └── useData.ts
│       ├── types/
│       │   └── index.ts
│       └── utils/
│           ├── formatters.ts
│           └── colors.ts
│
└── outputs/                           # Generated reports, screenshots
    ├── profiling_report.md
    └── screenshots/
```

### Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Data Processing | **Polars** | Columnar, fast, memory-efficient for 1.6M events |
| Analytical Queries | **DuckDB** | SQL interface over parquet for complex aggregations |
| Process Mining | **pm4py** | Industry-standard Python process mining library |
| Data Validation | **Pandera** (Polars backend) | Schema contracts between layers |
| ML (if needed) | **scikit-learn**, **LightGBM** | Only for predictive layer |
| Testing | **pytest** | Unit + integration tests |
| Frontend | **React 18 + TypeScript** | Type-safe component architecture |
| Styling | **Tailwind CSS** | Utility-first, consistent design system |
| Charts | **ECharts** | Rich chart library with Sankey, heatmaps, gauges |
| Build | **Vite** | Fast dev server and build |
| CI | **GitHub Actions** | Lint + test on push |
| Deployment | **GitHub Pages** (frontend) + **Hugging Face Spaces** (optional) | Free, accessible |

---

## 6. Data Layer Design

### 6.1 Bronze Layer
**Purpose:** Faithful extraction from XES. No transformations, no filtering. Raw truth.

**Tables:**

#### `bronze_events.parquet`
| Column | Type | Source |
|--------|------|--------|
| case_id | String | `concept:name` from trace |
| activity | String | `concept:name` from event |
| timestamp | Datetime | `time:timestamp` from event |
| resource | String | `org:resource` from event |
| event_id | String | `eventID` attribute |
| lifecycle_transition | String | `lifecycle:transition` if present |
| event_value | Float64 | Monetary value attribute (name TBD from XES inspection) |
| _raw_attributes | String (JSON) | All other event-level attributes serialized |

#### `bronze_cases.parquet`
| Column | Type | Source |
|--------|------|--------|
| case_id | String | `concept:name` |
| purchasing_document | String | Trace attribute |
| item | String | Trace attribute |
| item_type | String | Trace attribute |
| gr_based_iv | Boolean | Trace attribute |
| goods_receipt | Boolean | Trace attribute |
| source_system | String | Trace attribute |
| doc_category_name | String | Trace attribute |
| company | String | Trace attribute |
| spend_classification | String | Trace attribute |
| spend_area | String | Trace attribute |
| sub_spend_area | String | Trace attribute |
| vendor | String | Trace attribute |
| vendor_name | String | Trace attribute |
| document_type | String | Trace attribute |
| item_category | String | Trace attribute |
| _raw_attributes | String (JSON) | All other trace-level attributes |

**Quality gates (Bronze):**
- Row count events ≈ 1,595,923 (±1%)
- Row count cases ≈ 251,734 (±1%)
- No null case_id
- No null activity
- Timestamp parseable for >99.9% of events
- All 42 activities present

### 6.2 Silver Layer
**Purpose:** Cleaned, normalized, enriched. Ready for analytics.

#### `silver_events.parquet`
All bronze_events columns plus:
| Column | Type | Derivation |
|--------|------|------------|
| timestamp_utc | Datetime (UTC) | Normalized timezone |
| date | Date | Extracted from timestamp |
| hour | Int8 | Hour of day |
| day_of_week | Int8 | 0=Monday |
| is_weekend | Boolean | Derived |
| is_business_hours | Boolean | 8-18 weekdays |
| resource_type | Enum("human","batch","unknown") | Classified from resource name pattern |
| activity_clean | String | Standardized activity name |
| event_order | UInt32 | Position within case (by timestamp) |
| time_since_case_start | Duration | timestamp - case_start |
| time_since_prev_event | Duration | timestamp - prev event in case |

#### `silver_cases.parquet`
All bronze_cases columns plus:
| Column | Type | Derivation |
|--------|------|------------|
| flow_type | Enum | One of: "3way_invoice_after_gr", "3way_invoice_before_gr", "2way", "consignment" |
| case_start | Datetime | Min timestamp for case |
| case_end | Datetime | Max timestamp for case |
| case_duration_days | Float64 | End - Start in days |
| event_count | UInt32 | Number of events |
| activity_count | UInt32 | Number of distinct activities |
| resource_count | UInt32 | Number of distinct resources |
| has_batch_activity | Boolean | Any batch user involved |
| variant_id | String | Activity sequence hash |

#### `silver_resources.parquet`
| Column | Type | Derivation |
|--------|------|------------|
| resource | String | Unique resource identifier |
| resource_type | Enum | "human" or "batch" or "unknown" |
| first_seen | Datetime | Earliest event |
| last_seen | Datetime | Latest event |
| event_count | UInt64 | Total events performed |
| case_count | UInt64 | Distinct cases touched |
| activity_set | List[String] | Activities performed |

#### `silver_activities.parquet`
| Column | Type | Derivation |
|--------|------|------------|
| activity | String | Activity name |
| frequency | UInt64 | Total occurrences |
| case_coverage | Float64 | % of cases containing this activity |
| median_duration_to_next | Float64 | Median time to next activity (seconds) |
| p90_duration_to_next | Float64 | P90 time to next |
| typically_batch | Boolean | >50% performed by batch users |
| typically_human | Boolean | >50% performed by human users |

**Quality gates (Silver):**
- No null timestamps after normalization
- flow_type assigned for 100% of cases
- resource_type classified for >95% of events with non-null resource
- event_order is contiguous per case (1, 2, 3...)
- All derived durations ≥ 0

### 6.3 Gold Layer — Analytical Marts
**Purpose:** Business-ready fact and dimension tables optimized for dashboard consumption.

#### Fact Tables

**`fact_event_log.parquet`** — Enriched event-level fact
Core join of silver_events + silver_cases. The foundational fact table for all analytics.
Key columns: case_id, activity, timestamp, resource, resource_type, flow_type, company, vendor, event_order, time_since_prev_event, process_stage (mapped from activity → stage enum)

**`fact_case_summary.parquet`** — One row per case with all KPIs
| Metric | Type | Description |
|--------|------|-------------|
| case_id | String | Primary key |
| flow_type | Enum | P2P flow classification |
| company | String | Subsidiary |
| vendor | String | Vendor |
| case_duration_days | Float64 | Total elapsed time |
| active_time_days | Float64 | Sum of inter-event gaps during business hours |
| waiting_time_days | Float64 | case_duration - active_time |
| event_count | UInt32 | Total events |
| rework_count | UInt32 | Number of repeated activities |
| loop_count | UInt32 | Number of detected loops |
| variant_id | String | Process variant identifier |
| is_happy_path | Boolean | Follows expected sequence |
| compliance_score | Float64 | 0-1 conformance score |
| compliance_flags | List[String] | List of violated rules |
| automation_score | Float64 | 0-1 automation potential |
| sla_risk | Enum | "low", "medium", "high" |
| has_rework | Boolean | Any repeated activities |
| touchless_ratio | Float64 | % of events by batch users |
| total_value | Float64 | Sum of monetary values |

**`fact_variant_stats.parquet`** — One row per process variant
| Metric | Type | Description |
|--------|------|-------------|
| variant_id | String | Variant identifier |
| variant_sequence | List[String] | Ordered activity list |
| variant_length | UInt16 | Number of steps |
| case_count | UInt64 | Cases following this variant |
| case_percentage | Float64 | % of total cases |
| median_duration_days | Float64 | Median case duration |
| p90_duration_days | Float64 | P90 case duration |
| compliance_rate | Float64 | % of cases in variant that are compliant |
| is_happy_path | Boolean | Matches expected sequence for flow type |
| dominant_flow_type | Enum | Most common flow type in variant |

**`fact_compliance_checks.parquet`** — One row per case × rule
| Column | Type | Description |
|--------|------|-------------|
| case_id | String | Case reference |
| rule_id | String | Compliance rule identifier |
| rule_name | String | Human-readable rule name |
| passed | Boolean | Did this case pass this rule? |
| severity | Enum | "info", "warning", "critical" |
| detail | String | Explanation of violation |

**`fact_bottleneck_analysis.parquet`** — Activity transition metrics
| Column | Type | Description |
|--------|------|-------------|
| from_activity | String | Source activity |
| to_activity | String | Target activity |
| flow_type | Enum | P2P flow type |
| transition_count | UInt64 | Number of times this transition occurs |
| median_wait_hours | Float64 | Median waiting time |
| p90_wait_hours | Float64 | P90 waiting time |
| max_wait_hours | Float64 | Maximum waiting time |
| is_bottleneck | Boolean | Flagged as bottleneck (p90 > threshold) |
| bottleneck_rank | UInt16 | Rank among bottlenecks |

**`fact_automation_opportunities.parquet`** — One row per activity
| Column | Type | Description |
|--------|------|-------------|
| activity | String | Activity name |
| total_executions | UInt64 | Volume |
| batch_ratio | Float64 | Already-automated percentage |
| human_executions | UInt64 | Manual execution count |
| avg_variants_involved | Float64 | How many variants use this activity |
| input_uniformity | Float64 | 0-1 score of input consistency |
| timing_regularity | Float64 | 0-1 score of execution time consistency |
| error_rate | Float64 | % cases with this activity that have rework |
| automation_score | Float64 | Composite 0-1 score |
| automation_tier | Enum | "quick_win", "medium_effort", "complex", "not_recommended" |
| estimated_hours_saved_monthly | Float64 | Projected time savings |

**`fact_sla_risk.parquet`** — Predictive risk per active/completed case
| Column | Type | Description |
|--------|------|-------------|
| case_id | String | Case reference |
| predicted_risk | Float64 | 0-1 probability of SLA breach |
| risk_category | Enum | "low", "medium", "high" |
| top_risk_factors | List[String] | Top 3 contributing features |
| predicted_remaining_days | Float64 | Estimated days to completion |
| model_confidence | Float64 | Prediction confidence |

#### Dimension Tables

**`dim_activity.parquet`**
activity, activity_group (process stage), is_milestone, typical_resource_type, description

**`dim_company.parquet`**
company, case_count, event_count, avg_case_duration, compliance_rate, primary_flow_type

**`dim_vendor.parquet`**
vendor, vendor_name, case_count, avg_case_duration, rework_rate, compliance_rate

**`dim_resource.parquet`**
resource, resource_type, event_count, case_count, primary_activities

**`dim_calendar.parquet`**
date, year, month, quarter, day_of_week, is_weekend, is_business_day

### 6.4 Process Stage Model (Activity → Stage Mapping)

**Purpose:** Map the 42 raw activities into semantic P2P process stages. This mapping is the backbone of the Sankey diagram, compliance engine, and bottleneck analysis. Without it, the project is just "events in a list."

**IMPORTANT:** The exact activity names below are PROVISIONAL. Claude Code MUST replace them with actual names discovered during Phase 1 XES inspection. The stage groupings are based on standard SAP MM/P2P terminology and BPI 2019 challenge reports.

#### Stage Definitions

| Stage ID | Stage Name | Description | Expected Activities (provisional) |
|----------|-----------|-------------|-----------------------------------|
| S1 | **Requisition & Creation** | Purchase order creation and line item setup | Create Purchase Order Item, Create Purchase Requisition Item, Record Purchase Order Item |
| S2 | **Approval & Release** | Authorization workflow | Approve Purchase Order, Release Purchase Order |
| S3 | **Vendor Interaction** | PO sent to vendor, vendor acknowledges | Send Purchase Order, Vendor creates invoice, Vendor creates debit memo |
| S4 | **Goods Receipt** | Physical receipt of goods or services | Record Goods Receipt, Record Service Entry Sheet, Receive Goods |
| S5 | **Invoice Processing** | Invoice receipt, verification, matching | Record Invoice Receipt, Scan Invoice, Enter Incoming Invoice, Record Subsequent Invoice |
| S6 | **Matching & Verification** | 2-way or 3-way matching logic | Match Invoice to GR, Match Invoice to PO, Block Invoice, Unblock Invoice |
| S7 | **Payment & Clearing** | Financial settlement | Clear Invoice, Schedule Payment, Execute Payment, Post Payment |
| S8 | **Exception & Rework** | Corrections, cancellations, changes | Change Price, Change Quantity, Delete Purchase Order Item, Cancel Goods Receipt, Cancel Invoice Receipt, Re-enter Invoice |
| S9 | **Closure** | Administrative closure | Close Purchase Order, Archive Document |

#### Stage Transition Rules (Normative Model)

The expected stage progression per flow type defines the "happy path" for compliance checking:

**3-way match, invoice after GR:**
```
S1 → S2 → S3 → S4 → S5 → S6 → S7 → S9
(Create → Approve → Send → GR → Invoice → Match → Pay → Close)
```

**3-way match, invoice before GR:**
```
S1 → S2 → S3 → S5 → S4 → S6 → S7 → S9
(Create → Approve → Send → Invoice [blocked] → GR → Unblock+Match → Pay → Close)
```

**2-way match:**
```
S1 → S2 → S3 → S5 → S6 → S7 → S9
(Create → Approve → Send → Invoice → Match → Pay → Close)
No S4 (no goods receipt required)
```

**Consignment:**
```
S1 → S2 → S3 → S4 → S9
(Create → Approve → Send → GR → Close)
No S5/S6/S7 (no invoice processing at PO level)
```

#### Conformance Checking Strategy

For each case, conformance is evaluated at two levels:

**Level 1 — Stage Order Conformance:**
Extract the stage sequence for the case (ignoring S8 exceptions). Check if stages appear in the expected order for the case's flow_type. A case where S5 appears before S4 in a 3way_after_gr flow is a stage-order violation.

**Level 2 — Rule-Based Conformance:**
Apply the specific rules from the Rule Catalog (Section 7) that operate at the activity level within stages.

> **Claude Code action:** During Phase 1, after discovering actual activity names, create a file `data/reference/activity_stage_mapping.json` that maps each of the 42 activities to its stage. Activities that don't fit cleanly get stage "S0_UNKNOWN" and are logged for manual review. This mapping MUST be validated by inspecting activity frequency and co-occurrence patterns, not just assumed from names.

### 6.5 Parquet Partitioning Strategy

**Purpose:** Optimize query performance for dashboard consumption and analytical workflows.

| Table | Partition By | Rationale |
|-------|-------------|-----------|
| `fact_event_log.parquet` | None (single file) | 1.6M rows is fast enough for Polars/DuckDB scan |
| `fact_case_summary.parquet` | None (single file) | 251K rows, always scanned fully for KPIs |
| `fact_compliance_checks.parquet` | None (single file) | ~2.5M rows (251K × ~10 rules), but simple schema |
| `fact_bottleneck_analysis.parquet` | None (single file) | Small table (~1K-2K transition pairs) |
| `fact_variant_stats.parquet` | None (single file) | Typically <10K unique variants |
| `fact_automation_opportunities.parquet` | None (single file) | 42 rows (one per activity) |

**Rationale for no partitioning:** All gold tables fit in memory with Polars. Partitioning adds complexity without performance gain at this data scale. If the dataset were 10x larger, partition `fact_event_log` by `flow_type` and `fact_compliance_checks` by `severity`.

**Compression:** Use `zstd` compression for all parquet files (Polars default). Expected disk sizes:
- Bronze events: ~80-120 MB
- Bronze cases: ~15-25 MB
- Silver events: ~100-150 MB (more columns)
- Gold fact tables: ~50-100 MB combined

---

## 7. Compliance Rules Engine

### 7.1 Normative Process Models (Reference Sequences)

Each flow type has an expected activity sequence that serves as the conformance reference. These are defined at the STAGE level (Section 6.4) because activity-level sequences vary too much across variants.

**Claude Code MUST:** After Phase 1, define concrete activity-level reference sequences per flow type based on the happy path (most frequent variant) within each flow type. Store these in `data/reference/normative_models.json`:

```json
{
  "3way_invoice_after_gr": {
    "expected_stages": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S9"],
    "mandatory_stages": ["S1", "S4", "S5", "S7"],
    "forbidden_stages": [],
    "stage_order_strict": [["S4", "S5"], ["S5", "S7"]],
    "notes": "GR (S4) MUST precede Invoice (S5). Invoice MUST precede Payment (S7)."
  },
  "3way_invoice_before_gr": {
    "expected_stages": ["S1", "S2", "S3", "S5", "S4", "S6", "S7", "S9"],
    "mandatory_stages": ["S1", "S4", "S5", "S7"],
    "forbidden_stages": [],
    "stage_order_strict": [["S5", "S6"], ["S4", "S6"], ["S6", "S7"]],
    "notes": "Invoice (S5) arrives before GR (S4), but both MUST precede Matching (S6)."
  },
  "2way": {
    "expected_stages": ["S1", "S2", "S3", "S5", "S6", "S7", "S9"],
    "mandatory_stages": ["S1", "S5", "S7"],
    "forbidden_stages": ["S4"],
    "stage_order_strict": [["S5", "S7"]],
    "notes": "No goods receipt. Invoice matched directly against PO value."
  },
  "consignment": {
    "expected_stages": ["S1", "S2", "S3", "S4", "S9"],
    "mandatory_stages": ["S1", "S4"],
    "forbidden_stages": ["S5", "S6", "S7"],
    "stage_order_strict": [],
    "notes": "No invoices at PO level. Only GR tracking."
  }
}
```

### 7.2 GR ↔ Invoice Matching Strategy

This is the hardest compliance check in the dataset (BPI Challenge Question 2). A single line item can have MULTIPLE goods receipts and MULTIPLE invoices (e.g., monthly rent = 12 GR + 12 invoices).

**Matching Algorithm:**
1. For each case, extract all GR events and all Invoice events with their timestamps and values
2. Sort both lists by timestamp
3. Apply sequential greedy matching: match each invoice to the nearest unmatched GR that preceded it (for 3way_after_gr) or to the nearest GR regardless of order (for 3way_before_gr)
4. For each matched pair, check value equality (within tolerance of ±1% due to anonymization rounding)
5. Unmatched invoices or GRs at the end indicate compliance issues

**Value Tolerance:** The dataset documentation states monetary values use a linear translation preserving 0, with possible small rounding errors. Use absolute tolerance: `abs(gr_value - invoice_value) < max(1.0, 0.01 * abs(gr_value))`.

**Output:** For each case, produce:
- `gr_invoice_pairs`: List of matched (GR_event, Invoice_event, value_match_ok) tuples
- `unmatched_grs`: GR events without a matching invoice
- `unmatched_invoices`: Invoice events without a matching GR
- `total_value_match`: Whether sum(GR values) ≈ sum(Invoice values) ≈ item creation value

### 7.3 Rule Catalog

These rules will be checked against each case. Rules are derived from the BPI 2019 challenge description and standard P2P compliance patterns.

| Rule ID | Rule Name | Flow Types | Logic | Severity |
|---------|-----------|------------|-------|----------|
| CR-001 | GR before invoice clearance | 3way_after_gr | Goods Receipt event timestamp < Invoice cleared timestamp | critical |
| CR-002 | Invoice before GR (blocked until GR) | 3way_before_gr | If invoice arrives before GR, must be blocked; unblocked only after GR | critical |
| CR-003 | No invoice on consignment | consignment | No invoice-related activities should appear | warning |
| CR-004 | Value match (GR + Invoice = PO) | 3way_*, 2way | Sum of invoice values ≈ sum of GR values ≈ item creation value | critical |
| CR-005 | Create before all other activities | ALL | "Create Purchase Order Item" is first event | warning |
| CR-006 | No payment without approval chain | ALL | Payment/clearing events preceded by proper approval sequence | critical |
| CR-007 | Single vendor per document | ALL | All items in same document have same vendor | info |
| CR-008 | Reasonable throughput time | ALL | Case duration < P95 for same flow type | warning |
| CR-009 | No excessive rework | ALL | Rework count ≤ 2 for same activity | warning |
| CR-010 | Proper closure | ALL | Case has a terminal event (payment, closure, deletion) | info |

> **NOTE:** Rules CR-001 through CR-004 are directly grounded in the dataset documentation. Rules CR-005 through CR-010 are standard P2P compliance patterns. Claude Code should validate rule applicability after inspecting the actual activity names in the XES.

---

## 8. KPI Catalog

### Executive KPIs (Overview Page)
| KPI | Formula | Target |
|-----|---------|--------|
| Total Cases Processed | COUNT(cases) | Context metric |
| Overall Compliance Rate | COUNT(fully_compliant_cases) / COUNT(cases) | >85% |
| Avg. Case Duration (days) | MEAN(case_duration_days) | Context metric |
| Touchless Processing Rate | COUNT(cases where touchless_ratio=1.0) / COUNT(cases) | >40% |
| Happy Path Adherence | COUNT(is_happy_path=true) / COUNT(cases) | >60% |
| Rework Rate | COUNT(has_rework=true) / COUNT(cases) | <15% |
| Automation Coverage | SUM(batch_events) / SUM(all_events) | Context metric |
| Cases at SLA Risk | COUNT(sla_risk IN ("medium","high")) / COUNT(active_cases) | <10% |

### Operational KPIs
| KPI | Scope | Formula |
|-----|-------|---------|
| Median Throughput Time | By flow type | MEDIAN(case_duration_days) GROUP BY flow_type |
| P90 Throughput Time | By flow type | P90(case_duration_days) GROUP BY flow_type |
| Bottleneck Wait Time | By transition | P90(wait_hours) for flagged bottlenecks |
| Variant Concentration | Overall | % cases in top 5 variants |
| Resource Utilization | By resource | events_per_resource / median_events_per_resource |
| Subsidiary Performance | By company | Composite of duration, compliance, rework |
| Vendor Reliability Score | By vendor | Inverse of rework_rate weighted by volume |
| Automation Opportunity Value | By activity | human_executions × avg_time × frequency |

---

## 9. Process Mining Module Design

### 9.1 Process Discovery
**Objective:** Reconstruct the actual P2P process from event data.

**Approach:**
1. Extract activity sequences per case → variant identification
2. Compute variant frequencies (expect long tail — top 10-20 variants cover ~60-80% of cases)
3. Identify "happy path" per flow type (most frequent variant within each flow type)
4. Detect loops: any activity appearing >1 time in a case
5. Detect rework: repeated activity after other activities have occurred
6. Build directly-follows graph (DFG) with frequency and performance overlays
7. Optionally use pm4py's Alpha Miner or Heuristic Miner for Petri net discovery (for documentation, not dashboard)

**Output:** `fact_variant_stats.parquet`, DFG data for frontend Sankey visualization

### 9.2 Conformance / Compliance
**Objective:** Check each case against expected behavior.

**Approach:**
1. Define expected activity sequences per flow type (from dataset documentation)
2. For each case, check all applicable rules from Rule Catalog (Section 7)
3. Compute case-level compliance score: passed_rules / applicable_rules
4. Flag deviations with severity and detail
5. Aggregate compliance by flow_type, company, vendor, time period

**Output:** `fact_compliance_checks.parquet`, aggregated compliance metrics in `fact_case_summary`

### 9.3 Throughput & Bottleneck Analysis
**Objective:** Measure where time is spent and where it accumulates.

**Approach:**
1. For each case: lead_time = last_event - first_event
2. For each transition (activity A → activity B): wait_time = timestamp_B - timestamp_A
3. Aggregate transitions: median, P90, max wait times
4. Flag bottlenecks: transitions where P90 > configurable threshold (e.g., 7 days)
5. Rank bottlenecks by impact: frequency × median_wait
6. Segment by flow_type, company, vendor for comparative analysis

**Output:** `fact_bottleneck_analysis.parquet`, transition metrics in gold layer

### 9.4 Resource & Work Pattern Analysis
**Objective:** Understand who does what, workload distribution, batch vs. human patterns.

**Approach:**
1. Classify resources as batch/human/unknown based on naming patterns
2. Compute per-resource: event count, case count, active days, activities performed
3. Identify handoff patterns: transitions where resource changes
4. Compute handoff count per case
5. Analyze batch user patterns: timing, frequency, activities covered
6. Workload concentration: Gini coefficient or similar across human resources

**Output:** `silver_resources.parquet`, `dim_resource.parquet`, resource metrics

### 9.5 Automation Opportunity Scoring
**Objective:** Identify which manual activities are best candidates for RPA.

**Scoring Model (rule-based, not ML):**

Each dimension is computed as a 0-1 normalized score:

```python
# 1. Volume Score (0-1): How frequently is this activity executed?
volume_score = (activity_count - min_count) / (max_count - min_count)
# where min/max are across all activities

# 2. Batch Gap Score (0-1): How much room is there for automation?
batch_gap_score = 1.0 - batch_ratio
# batch_ratio = batch_executions / total_executions
# Already 100% batch → score 0 (no room). 0% batch → score 1 (full room)

# 3. Input Uniformity Score (0-1): How consistent are the contexts in which this activity appears?
# Measures whether the activity always appears at the same position in the process
# and is preceded/followed by the same activities (low variance = high uniformity)
predecessor_entropy = shannon_entropy(predecessor_activity_distribution)
successor_entropy = shannon_entropy(successor_activity_distribution)
position_cv = std(event_order_positions) / mean(event_order_positions)
input_uniformity = 1.0 - min(1.0, (predecessor_entropy + successor_entropy + position_cv) / 3.0)
# Normalize: low entropy and low position variance → high uniformity → good for RPA

# 4. Timing Regularity Score (0-1): How predictable is the execution time?
# Measured by coefficient of variation of time_since_prev_event for this activity
timing_cv = std(time_to_this_activity) / mean(time_to_this_activity)
timing_regularity = 1.0 - min(1.0, timing_cv)
# Low CV → very regular timing → high score → good for scheduled automation

# 5. Error Reduction Potential (0-1): Does this activity appear in cases with rework?
cases_with_rework = count(cases containing this activity AND has_rework=True)
cases_total = count(cases containing this activity)
error_rate = cases_with_rework / cases_total
error_reduction = min(1.0, error_rate * 2)
# Higher rework association → more value in automating to reduce errors

# 6. Wait Reduction Potential (0-1): How much waiting time precedes this activity?
avg_wait_before = mean(time_since_prev_event for this activity)
max_avg_wait = max(avg_wait across all activities)
wait_reduction = avg_wait_before / max_avg_wait
# Long waits before activity → automation could trigger it faster

# Final composite score:
automation_score = (
    volume_score        * 0.25 +
    batch_gap_score     * 0.20 +
    input_uniformity    * 0.20 +
    timing_regularity   * 0.15 +
    error_reduction     * 0.10 +
    wait_reduction      * 0.10
)
```

**Shannon Entropy helper:**
```python
def shannon_entropy(distribution: dict[str, int]) -> float:
    """Compute Shannon entropy of a frequency distribution. Returns 0 for single-value distributions."""
    total = sum(distribution.values())
    probs = [count / total for count in distribution.values() if count > 0]
    return -sum(p * log2(p) for p in probs) / max(1, log2(len(probs)))  # normalize to 0-1
```

**Estimated Hours Saved Calculation:**
```python
# Assume average human processing time per execution = median(time_since_prev_event) 
# capped at 30 minutes (some waits are just queue time, not active work)
avg_human_minutes = min(30, median_time_since_prev_for_activity_minutes)
monthly_executions = human_executions / dataset_months
estimated_hours_saved_monthly = monthly_executions * avg_human_minutes / 60
```

**Tier Assignment:**
- Quick Win: score > 0.7, batch_ratio < 0.3, volume > P75
- Medium Effort: score 0.5-0.7
- Complex: score 0.3-0.5
- Not Recommended: score < 0.3 or already >80% batch

**Output:** `fact_automation_opportunities.parquet`

### 9.6 Predictive Layer (SLA Risk)
**Objective:** Predict which cases are likely to breach expected throughput time.

**Scope:** This is intentionally lightweight — 1 model, clear purpose, not the project's centerpiece.

**Approach:**
1. Define SLA threshold per flow type: P75 of case_duration_days for that flow type
2. Label: 1 if case_duration > SLA threshold, 0 otherwise
3. Features (from case-level attributes available at prediction point):
   - flow_type (encoded)
   - company (encoded)
   - vendor (high-cardinality: frequency-encode or top-N + other)
   - item_type
   - event_count_so_far
   - time_elapsed_so_far
   - current_activity
   - rework_count_so_far
   - has_batch_involvement
4. Model: LightGBM classifier (or logistic regression if dataset too small after split)
5. Evaluation: temporal split (train on earlier cases, test on later)
6. Explainability: feature importance, SHAP for top risk factors per prediction
7. Output: risk score per case, top contributing features

**Output:** `fact_sla_risk.parquet`, model artifacts in `models/` directory

**IMPORTANT:** If the predictive layer doesn't add clear value after initial analysis (e.g., SLA threshold is meaningless because there's no natural SLA), document this decision and skip the model. Intellectual honesty > model count.

---

## 10. Frontend Application Design

### Design Philosophy
- **Enterprise aesthetic:** Dark theme, clean typography, data-dense but not cluttered
- **7 pages, each with clear purpose**
- **Consistent filter bar:** Flow type, company, vendor, date range (where applicable)
- **ECharts for all visualizations** (Sankey, heatmaps, gauges, bar/line, treemap)
- **Responsive but desktop-first** (this is an enterprise analytics tool)

### Page Specifications

#### Page 1: Executive Overview
**Purpose:** C-level summary — "how is our P2P process performing?"

Components:
- KPI cards row: Total Cases, Compliance Rate, Avg Duration, Touchless Rate, Rework Rate, SLA Risk Cases
- Trend line: case volume and compliance rate over time (monthly)
- Donut: case distribution by flow type
- Bar: top 5 bottleneck transitions by impact score
- Bar: subsidiary comparison (top 10 by case volume, colored by compliance)
- Mini table: top 5 riskiest active cases (if predictive layer built)

#### Page 2: Process Map & Variants
**Purpose:** "Show me how the process actually flows"

Components:
- Sankey diagram (ECharts): full process flow with activity nodes and transition edges, thickness = frequency, color = avg wait time
- Variant table: top 20 variants with sparkline of activity sequence, case count, % total, median duration, compliance rate
- Toggle: view by flow type (4 sub-views)
- Happy path highlight: overlay expected vs. actual
- Loop detector: list of cases with loops, loop activity, loop count

#### Page 3: Compliance Center
**Purpose:** "Where are we non-compliant and how bad is it?"

Components:
- Gauge: overall compliance rate
- Rule violation breakdown: stacked bar per rule (CR-001 through CR-010), segmented by severity
- Heatmap: compliance rate by company × flow type
- Timeline: compliance trend over time
- Violation drilldown table: individual cases with violations, sortable/filterable
- Top violating vendors (bar chart)

#### Page 4: Bottleneck Explorer
**Purpose:** "Where does time accumulate?"

Components:
- Transition heatmap: activity × activity matrix, cell color = median wait time
- Top 10 bottleneck transitions: bar chart with P90 wait time
- Box plot: wait time distribution for selected transition
- Comparison selector: compare bottlenecks across flow types or companies
- Time decomposition: stacked bar showing active time vs. wait time per process stage

#### Page 5: Automation Candidates
**Purpose:** "What should we automate next?"

Components:
- Bubble chart: x = volume, y = automation score, size = estimated hours saved, color = tier
- Ranked table: activities sorted by automation score with all scoring dimensions
- Activity detail panel: click an activity → show its execution pattern, timing distribution, current batch ratio, related bottleneck impact
- ROI estimator: simple calculator — if this activity is automated, estimated impact on throughput

#### Page 6: Case Drilldown
**Purpose:** "Let me investigate a specific case"

Components:
- Search/filter bar: by case_id, company, vendor, flow type, compliance status
- Case timeline: horizontal timeline of events with activity labels, resource, time gaps
- Case metadata card: all case attributes
- Compliance check results: pass/fail per rule for selected case
- Similar cases: top 5 cases with same variant
- Risk score (if predictive layer built)

#### Page 7: Subsidiary Benchmarking
**Purpose:** "How do our subsidiaries compare?"

Components:
- Radar chart: comparing selected companies across 5 dimensions (duration, compliance, rework, automation, volume)
- Sortable table: all companies with key metrics
- Drill into company: select a company → show its specific process map, compliance, bottlenecks
- Peer comparison: select 2-3 companies for side-by-side

### Data Flow & JSON Contracts (Backend → Frontend)

Gold layer parquet files are post-processed by `scripts/export_for_frontend.py` into JSON files that the React app consumes. Each file has a strict schema defined below.

**Target:** Total JSON payload < 10 MB. Use aggregation aggressively. Case-level data is paginated or sampled.

#### `frontend/public/data/executive_kpis.json`
```typescript
{
  total_cases: number,
  compliance_rate: number,           // 0-1
  avg_duration_days: number,
  median_duration_days: number,
  touchless_rate: number,            // 0-1
  happy_path_rate: number,           // 0-1
  rework_rate: number,               // 0-1
  automation_coverage: number,       // 0-1
  sla_risk_count: number,
  total_events: number,
  total_vendors: number,
  total_companies: number,
  flow_type_distribution: {          // for donut chart
    [flow_type: string]: number      // case count per flow type
  },
  monthly_trends: Array<{            // for trend line
    month: string,                   // "2018-01"
    cases: number,
    compliance_rate: number,
    avg_duration: number
  }>
}
```

#### `frontend/public/data/process_flow.json`
```typescript
{
  nodes: Array<{
    id: string,                      // activity name
    stage: string,                   // stage ID (S1-S9)
    stage_name: string,
    frequency: number,
    avg_duration_hours: number
  }>,
  edges: Array<{
    source: string,                  // from activity
    target: string,                  // to activity
    count: number,                   // transition frequency
    median_wait_hours: number,
    is_bottleneck: boolean
  }>,
  // Separate DFG per flow type for toggle view
  by_flow_type: {
    [flow_type: string]: {
      nodes: Array<{id: string, frequency: number}>,
      edges: Array<{source: string, target: string, count: number}>
    }
  }
}
```

#### `frontend/public/data/variants.json`
```typescript
{
  total_variants: number,
  top_variants: Array<{              // top 50 variants
    variant_id: string,
    sequence: string[],              // ordered activity names
    case_count: number,
    case_percentage: number,
    median_duration_days: number,
    p90_duration_days: number,
    compliance_rate: number,
    is_happy_path: boolean,
    dominant_flow_type: string
  }>,
  concentration: {                   // for narrative
    top5_coverage: number,           // % cases in top 5
    top10_coverage: number,
    top20_coverage: number
  }
}
```

#### `frontend/public/data/compliance_summary.json`
```typescript
{
  overall_rate: number,
  by_rule: Array<{
    rule_id: string,
    rule_name: string,
    severity: "info" | "warning" | "critical",
    pass_rate: number,
    violation_count: number
  }>,
  by_company: Array<{
    company: string,
    compliance_rate: number,
    case_count: number,
    critical_violations: number
  }>,
  by_flow_type: {
    [flow_type: string]: {
      compliance_rate: number,
      case_count: number,
      top_violation: string
    }
  },
  heatmap: Array<{                   // company × flow_type matrix
    company: string,
    flow_type: string,
    compliance_rate: number,
    case_count: number
  }>,
  monthly_trend: Array<{
    month: string,
    compliance_rate: number
  }>,
  top_violating_vendors: Array<{     // top 20
    vendor: string,
    vendor_name: string,
    violation_count: number,
    case_count: number,
    violation_rate: number
  }>
}
```

#### `frontend/public/data/compliance_details.json`
```typescript
{
  cases: Array<{                     // top 500 worst compliance scores
    case_id: string,
    flow_type: string,
    company: string,
    vendor: string,
    compliance_score: number,
    violations: Array<{
      rule_id: string,
      rule_name: string,
      severity: string,
      detail: string
    }>
  }>
}
```

#### `frontend/public/data/bottlenecks.json`
```typescript
{
  transitions: Array<{              // all transitions with >100 occurrences
    from_activity: string,
    to_activity: string,
    from_stage: string,
    to_stage: string,
    count: number,
    median_wait_hours: number,
    p90_wait_hours: number,
    max_wait_hours: number,
    is_bottleneck: boolean,
    bottleneck_rank: number | null
  }>,
  top_bottlenecks: Array<{          // top 15 by impact
    from_activity: string,
    to_activity: string,
    count: number,
    p90_wait_hours: number,
    impact_score: number            // count × median_wait
  }>,
  by_flow_type: {
    [flow_type: string]: Array<{
      from_activity: string,
      to_activity: string,
      median_wait_hours: number
    }>
  },
  stage_time_decomposition: Array<{ // for stacked bar
    stage: string,
    stage_name: string,
    median_active_hours: number,
    median_wait_hours: number
  }>
}
```

#### `frontend/public/data/automation_candidates.json`
```typescript
{
  activities: Array<{               // all 42 activities
    activity: string,
    stage: string,
    total_executions: number,
    human_executions: number,
    batch_ratio: number,
    volume_score: number,
    batch_gap_score: number,
    input_uniformity: number,
    timing_regularity: number,
    error_reduction: number,
    wait_reduction: number,
    automation_score: number,
    automation_tier: "quick_win" | "medium_effort" | "complex" | "not_recommended",
    estimated_hours_saved_monthly: number
  }>
}
```

#### `frontend/public/data/case_summaries.json`
```typescript
{
  total_cases: number,
  sample_cases: Array<{             // random 1000 cases for drilldown browsing
    case_id: string,
    flow_type: string,
    company: string,
    vendor: string,
    vendor_name: string,
    duration_days: number,
    event_count: number,
    compliance_score: number,
    has_rework: boolean,
    variant_id: string,
    is_happy_path: boolean,
    sla_risk: string | null,
    events: Array<{                 // full event timeline for this case
      activity: string,
      timestamp: string,            // ISO format
      resource: string,
      resource_type: string,
      stage: string,
      time_since_prev_hours: number | null
    }>
  }>
}
// NOTE: This file will be the largest (~3-5 MB). If too large,
// split into case_index.json (metadata only) + case_details/{case_id}.json
```

#### `frontend/public/data/company_benchmarks.json`
```typescript
{
  companies: Array<{
    company: string,
    case_count: number,
    avg_duration_days: number,
    median_duration_days: number,
    compliance_rate: number,
    rework_rate: number,
    touchless_rate: number,
    automation_coverage: number,
    primary_flow_type: string,
    // normalized 0-1 scores for radar chart
    radar: {
      speed: number,                // inverse of duration, normalized
      compliance: number,
      efficiency: number,           // inverse of rework
      automation: number,
      volume: number                // normalized case count
    }
  }>,
  peer_comparison_dimensions: string[]  // ["speed","compliance","efficiency","automation","volume"]
}
```

#### `frontend/public/data/sla_risk.json` (only if predictive layer built)
```typescript
{
  model_metrics: {
    auc_roc: number,
    precision: number,
    recall: number,
    f1: number,
    threshold_used: number
  },
  feature_importance: Array<{
    feature: string,
    importance: number
  }>,
  at_risk_cases: Array<{            // top 100 highest risk
    case_id: string,
    predicted_risk: number,
    risk_category: string,
    top_factors: string[],
    current_duration_days: number,
    predicted_remaining_days: number
  }>
}
```

#### Lazy Loading Strategy for Frontend
- **Eagerly loaded** (on app mount): `executive_kpis.json`, `process_flow.json` (~200KB total)
- **Loaded on page visit**: Each page loads its own JSON when the user navigates to it
- **Implementation:** React `useEffect` + `fetch` in page components, with loading skeletons
- **Caching:** Once loaded, data stays in React state (no re-fetch on page revisit within session)
- **Error handling:** Each page shows a fallback message if JSON fails to load

---

## 11. Phased Execution Roadmap

### Phase 0: Project Setup & Context
**Goal:** Repository scaffolding, documentation foundations, CI pipeline.

**Claude Code Tasks:**
1. Initialize git repository with the directory structure from Section 5
2. Create `pyproject.toml` with all Python dependencies
3. Create `frontend/package.json` with all frontend dependencies
4. Write `CLAUDE.md` with instructions for Claude Code itself
5. Write initial `README.md` (project name, description, "under construction" badge)
6. Set up `.github/workflows/ci.yml` (lint with ruff, test with pytest)
7. Write `docs/architecture.md` (copy relevant architecture sections from this file)
8. Write `docs/decision_log.md` (start with stack decisions)
9. Create `src/config.py` with path constants and configuration
10. Write empty test files with placeholder test functions
11. Create `tests/conftest.py` with the synthetic fixtures from Section 13

**Pipeline Runner Interface (`scripts/run_pipeline.py`):**
```
Usage:
  python scripts/run_pipeline.py [OPTIONS]

Options:
  --phase PHASE       Run specific phase: ingest, silver, gold, analytics, predict, export
  --all               Run full pipeline (ingest → silver → gold → analytics → predict → export)
  --dry-run           Validate inputs and print plan without executing
  --skip-validation   Skip Pandera schema validation (faster, for dev)
  --log-level LEVEL   Set logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
  --log-file FILE     Write logs to file in addition to stdout
  --xes-path PATH     Override default XES file path
  --output-dir DIR    Override default output directory

Examples:
  python scripts/run_pipeline.py --phase ingest              # Run only ingestion
  python scripts/run_pipeline.py --phase silver --dry-run     # Check silver inputs exist
  python scripts/run_pipeline.py --all --log-file pipeline.log  # Full run with logging
```

**Implementation pattern:**
```python
# src/pipeline/runner.py
class PipelineRunner:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger("pipeline")
    
    def run_phase(self, phase: str, dry_run: bool = False) -> PhaseResult:
        """Run a single phase. Returns PhaseResult with status, duration, row counts."""
        ...
    
    def run_all(self, dry_run: bool = False) -> list[PhaseResult]:
        """Run all phases in order, stopping on failure."""
        ...
    
    def validate_inputs(self, phase: str) -> list[str]:
        """Check that required input files exist for a phase. Returns list of errors."""
        ...

@dataclass
class PhaseResult:
    phase: str
    status: Literal["success", "failed", "skipped"]
    duration_seconds: float
    rows_read: int
    rows_written: int
    errors: list[str]
    warnings: list[str]
```

**Phase dependency chain:**
```
ingest → silver → gold → analytics → predict → export
```
Each phase validates that its input files exist before running. If `--phase silver` is called but bronze parquets don't exist, it fails with a clear message.

**Entregables:** Working repo with CI, all documentation shells, clean structure, test fixtures.

**Update CONTEXT.md with:** Exact dependency versions installed, any structural decisions changed.

---

### Phase 1: XES Ingestion & Bronze Layer
**Goal:** Parse the 728MB XES file into clean bronze parquet tables.

**Claude Code Tasks:**
1. Inspect the XES file structure: read first ~1000 lines to understand XML schema, namespace, attribute names
2. **CRITICAL:** Document ALL actual attribute names found (they may differ from documentation). Update this CONTEXT.md with real names.
3. Build `src/ingestion/xes_parser.py`:
   - Use pm4py to read XES (it handles the standard well)
   - Extract trace-level (case) attributes → DataFrame
   - Extract event-level attributes → DataFrame
   - Handle memory: the file is 728MB, pm4py should handle this but monitor RAM
   - Log parsing stats: traces read, events read, parse time, errors
4. Build `src/ingestion/bronze_writer.py`:
   - Write `data/bronze/bronze_events.parquet` (Polars)
   - Write `data/bronze/bronze_cases.parquet` (Polars)
   - Add row counts and schema to logs
5. Run quality gates:
   - Validate row counts against expected (251K cases, 1.6M events)
   - Check for null case_ids
   - Check timestamp parsing
   - Verify all 42 activities present
   - Write `tests/test_ingestion.py` with these assertions
6. Generate profiling:
   - `scripts/profile_data.py` → `outputs/profiling_report.md`
   - Include: column types, null rates, value distributions, activity frequencies, timestamp range, case length distribution
7. Write `docs/data_dictionary.md` with actual column mappings

**Entregables:** Bronze parquet files, profiling report, data dictionary, passing tests.

**Update CONTEXT.md with:**
- Exact attribute names from XES (may differ from documentation)
- Actual row counts
- Any parsing issues or surprises
- Memory/performance notes
- Activity name list (all 42)

---

### Phase 2: Silver Layer
**Goal:** Clean, normalize, enrich, classify.

**Claude Code Tasks:**
1. Build `src/transformation/silver_builder.py`:
   - Read bronze parquet files
   - Normalize timestamps to UTC
   - Derive temporal fields (date, hour, day_of_week, is_weekend, is_business_hours)
   - Compute event ordering per case
   - Compute time_since_prev_event for each event
2. Build `src/transformation/resource_classifier.py`:
   - Inspect resource naming patterns (batch users vs. human)
   - Classify each resource as "human", "batch", or "unknown"
   - Document the classification logic
3. Build `src/transformation/flow_type_classifier.py`:
   - Use case attributes (GR-Based IV, Goods Receipt, Item Category) to assign flow_type
   - Validate distribution against expected (four flow types)
   - Handle edge cases where flags are inconsistent
4. Build `src/transformation/temporal_enrichment.py`:
   - case_start, case_end, case_duration_days per case
   - event_count, activity_count, resource_count per case
   - has_batch_activity per case
5. Compute variant_id per case:
   - variant = ordered list of activities for the case
   - hash or index for compact representation
6. Write silver parquet tables:
   - `silver_events.parquet`
   - `silver_cases.parquet`
   - `silver_resources.parquet`
   - `silver_activities.parquet`
7. Quality validation:
   - Pandera schemas in `src/quality/schemas.py`
   - Run all quality gates from Section 6.2
   - Write `tests/test_silver.py`

**Entregables:** Silver parquet files, Pandera schemas, quality report, passing tests.

**Update CONTEXT.md with:**
- Resource classification patterns found
- Flow type distribution (actual counts per type)
- Variant count and concentration stats
- Any data quality issues discovered

---

### Phase 3: Process Mining Core (Gold Layer — Part 1)
**Goal:** Produce the core process mining analytics.

**Claude Code Tasks:**
1. Build `src/analytics/process_discovery.py`:
   - Compute variant statistics: frequency, percentage, duration stats
   - Identify happy path per flow type
   - Detect loops per case
   - Detect rework per case
   - Build directly-follows graph (DFG): from_activity → to_activity with count and avg duration
2. Build `src/analytics/conformance.py`:
   - Implement compliance rules from Section 7
   - **IMPORTANT:** Adapt rule definitions to ACTUAL activity names found in Phase 1
   - Run all rules against all cases
   - Compute case-level compliance score
   - Aggregate by flow_type, company, vendor
3. Build `src/analytics/throughput.py`:
   - Compute transition wait times (all pairs of consecutive activities)
   - Identify bottleneck transitions (P90 > threshold)
   - Rank bottlenecks by impact
   - Segment by flow_type, company
4. Build gold fact tables:
   - `fact_variant_stats.parquet`
   - `fact_compliance_checks.parquet`
   - `fact_bottleneck_analysis.parquet`
   - `fact_case_summary.parquet` (partial — fields from discovery + conformance + throughput)
5. Build gold dimension tables:
   - `dim_activity.parquet`
   - `dim_company.parquet`
   - `dim_vendor.parquet`
   - `dim_calendar.parquet`
6. Write `tests/test_gold.py` and `tests/test_analytics.py`

**Entregables:** Gold layer part 1, analytics modules, tests.

**Update CONTEXT.md with:**
- Happy path sequences per flow type
- Top 10 variants with stats
- Compliance rates found
- Top bottlenecks identified
- Any rules that turned out to be inapplicable

---

### Phase 4: Business KPIs & Advanced Analytics (Gold Layer — Part 2)
**Goal:** Complete the gold layer with resource, automation, and business metrics.

**Claude Code Tasks:**
1. Build `src/analytics/resource_analysis.py`:
   - Workload distribution across resources
   - Handoff analysis per case
   - Batch vs. human activity split
   - Resource utilization metrics
2. Build `src/analytics/automation_scoring.py`:
   - Compute all scoring dimensions per activity (Section 9.5)
   - Calculate composite automation score
   - Assign tiers
   - Estimate hours saved (based on volume × avg handling time)
3. Complete `fact_case_summary.parquet`:
   - Add rework_count, loop_count, touchless_ratio, automation_score
   - Add all remaining fields from Section 6.3
4. Build `fact_automation_opportunities.parquet`
5. Build `dim_resource.parquet`
6. Write `docs/kpi_catalog.md` with definitions and actual values
7. Build `scripts/export_for_frontend.py`:
   - Read gold parquet files
   - Aggregate and transform to JSON format
   - Write to `frontend/public/data/`
   - Target < 10 MB total
8. Write `tests/test_analytics.py` (extend)

**Entregables:** Complete gold layer, KPI catalog, frontend JSON exports.

**Update CONTEXT.md with:**
- Key KPI values found
- Top automation candidates
- Resource distribution insights
- Any metrics that revealed unexpected patterns

---

### Phase 5: Predictive Layer (Optional)
**Goal:** Build lightweight SLA risk model if data supports it.

**Claude Code Tasks:**
1. Analyze if prediction is viable:
   - Check if there's a meaningful SLA threshold (P75 of duration per flow type)
   - Check class balance at that threshold
   - If not viable, document why and SKIP — this is fine
2. If viable:
   - Build `src/analytics/predictive.py`
   - Create train/test split (temporal)
   - Feature engineering from case-level attributes
   - Train LightGBM (or logistic regression)
   - Evaluate: AUC-ROC, precision-recall
   - Extract feature importances
   - Generate SHAP values for top cases
   - Build `fact_sla_risk.parquet`
3. Update `fact_case_summary` with sla_risk column
4. Update frontend JSON exports
5. Write `docs/modeling_notes.md` with methodology, results, limitations

**Entregables:** Predictive model (or documented decision to skip), updated gold tables.

**Update CONTEXT.md with:**
- Model performance metrics (or reason for skipping)
- Feature importance ranking
- SLA threshold values used

---

### Phase 6: Frontend Application
**Goal:** Build the 7-page enterprise dashboard.

**Claude Code Tasks:**
1. Initialize React + TypeScript + Vite + Tailwind project in `frontend/`
2. Install ECharts (`echarts`, `echarts-for-react`)
3. Build layout components:
   - `Sidebar.tsx` with navigation
   - `Header.tsx` with project title and global filters
   - `PageContainer.tsx` wrapper
4. Build shared components:
   - `KPICard.tsx`
   - `FilterBar.tsx` (flow type, company, vendor, date range)
   - `DataTable.tsx` (sortable, filterable)
5. Build chart components:
   - `ProcessMap.tsx` (Sankey diagram with ECharts)
   - `VariantExplorer.tsx` (table with sparklines)
   - `BottleneckHeatmap.tsx` (ECharts heatmap)
   - `ComplianceGauge.tsx` (ECharts gauge)
   - `TimelineChart.tsx` (line/area chart)
   - `BubbleChart.tsx` (for automation candidates)
   - `RadarChart.tsx` (for subsidiary benchmarking)
6. Build pages (Section 10 specifications):
   - ExecutiveOverview.tsx
   - ProcessMap.tsx
   - ComplianceCenter.tsx
   - BottleneckExplorer.tsx
   - AutomationCandidates.tsx
   - CaseDrilldown.tsx
   - SubsidiaryBenchmark.tsx
7. Implement data loading from JSON files
8. Dark theme with enterprise aesthetic
9. Responsive layout (desktop-first, functional on tablet)

**Design Direction:**
- Dark background (#0a0a0f or similar deep navy/black)
- Accent colors: teal/cyan primary, amber/orange for warnings, red for critical
- Font: clean sans-serif (JetBrains Mono for numbers, general sans for text)
- Card-based layout with subtle borders and depth
- Data-dense but organized — no wasted space

**Entregables:** Complete React application, all 7 pages functional with real data.

**Update CONTEXT.md with:**
- Final component list
- Any design decisions or deviations
- Performance notes (JSON load time, render time)

---

### Phase 7: Polish & Deployment
**Goal:** Make it portfolio-ready and deployable.

**Claude Code Tasks:**
1. Write definitive `README.md`:
   - Project title, subtitle, description
   - Screenshot gallery (3-4 key pages)
   - Architecture diagram (can be mermaid or ASCII)
   - Key findings section (3-5 business insights discovered)
   - Tech stack badges
   - Quick start instructions
   - Project structure overview
   - Limitations section
   - Author info + LinkedIn link
2. Write `docs/limitations.md`:
   - Anonymized dataset — cannot map to real business entities
   - Process is real but business semantics are partial
   - Predictive layer limited to available event log features
   - Automation recommendations are inferred, not validated in production
   - Single dataset snapshot — no real-time streaming
   - Frontend uses pre-computed JSON — not connected to live data
3. Write `docs/runbook.md`:
   - Prerequisites
   - Install steps
   - How to run pipeline
   - How to run frontend
   - How to run tests
4. Build `frontend/` for production: `npm run build`
5. Take screenshots of all 7 pages → `outputs/screenshots/`
6. Final CI check: all tests pass, linting clean
7. Prepare CV/LinkedIn content:
   - One-liner
   - 3-bullet description
   - Key metrics/findings to mention

**Deployment Pipeline:**

Option A — **GitHub Pages** (recommended for portfolio visibility):
```yaml
# .github/workflows/deploy.yml
name: Deploy Frontend
on:
  push:
    branches: [main]
    paths: ['frontend/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci && npm run build
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./frontend/dist
```

**Vite configuration for GitHub Pages:**
```typescript
// frontend/vite.config.ts
export default defineConfig({
  base: '/erp-process-intelligence/',  // repo name
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ['echarts'],        // separate chunk for large lib
          vendor: ['react', 'react-dom', 'react-router-dom'],
        }
      }
    }
  }
})
```

Option B — **Hugging Face Spaces** (alternative, good for discoverability):
```bash
# Create a static HF Space
# 1. Build frontend
cd frontend && npm run build
# 2. Create HF space directory
mkdir -p hf-space
cp -r dist/* hf-space/
# 3. Add HF metadata
echo '---\ntitle: ERP Process Intelligence Platform\nemoji: 📊\ncolorFrom: blue\ncolorTo: cyan\nsdk: static\n---' > hf-space/README.md
# 4. Push to HF
cd hf-space && git init && git add . && git commit -m "deploy"
# huggingface-cli repo create erp-process-intelligence --type space --space-sdk static
# git remote add hf https://huggingface.co/spaces/USERNAME/erp-process-intelligence
# git push hf main
```

**JSON Data Serving Strategy:**
- All JSON files live in `frontend/public/data/` and are served as static assets
- Vite copies `public/` to `dist/` at build time — no configuration needed
- JSON files are gzip-compressed by GitHub Pages / HF Spaces automatically via HTTP Content-Encoding
- Expected compressed sizes: ~10 MB uncompressed → ~2-3 MB gzipped
- No CDN or special hosting required

**Performance Budget:**
| Metric | Target |
|--------|--------|
| Initial bundle (JS) | < 500 KB gzipped |
| Largest JSON file | < 5 MB uncompressed |
| Time to first meaningful paint | < 2s on broadband |
| ECharts chunk | Loaded async, < 300 KB gzipped |

8. Update `CONTEXT.md` with final status: COMPLETE, deployed URL

**Entregables:** Deployed demo, README, screenshots, CV content, all docs finalized, CI/CD pipeline.

---

## 12. MVP vs. Premium Definition

### MVP (Minimum Viable Portfolio Piece)
Phases 0-3 + Phase 6 (pages 1-4 only):
- Bronze → Silver → Gold (partial)
- Process discovery + variants
- Basic compliance checking
- Bottleneck analysis
- 4-page dashboard: Executive, Process Map, Compliance, Bottlenecks
- README with architecture diagram

**This alone is already a strong portfolio piece.**

### Premium (Full Vision)
All 7 phases:
- Complete gold layer with all fact tables
- Automation scoring
- Predictive layer (if viable)
- Full 7-page dashboard
- Complete documentation
- Deployed demo
- LinkedIn-ready narrative

---

## 13. Quality Standards

### Code Quality
- All Python code passes `ruff` linting (line length 100, standard rules)
- Type hints on all function signatures
- Docstrings on all public functions (Google style)
- No `print()` in library code — use `logging`
- Constants in `config.py`, not hardcoded
- No notebooks as deliverables (scripts only)

### Data Quality
- Pandera schema validation at every layer transition
- Row count checks (Bronze → Silver should preserve events, may drop malformed)
- Null rate monitoring per column
- Referential integrity: every event's case_id exists in cases table
- Temporal consistency: events within a case are properly ordered

### Testing
- Unit tests for all transformation functions
- Integration tests for layer transitions
- At least 30 test functions total
- All tests pass in CI

#### Test Fixture Strategy
Tests MUST NOT depend on the 728MB XES file. Instead, use synthetic fixtures:

```python
# tests/conftest.py — shared fixtures

import polars as pl
import pytest
from datetime import datetime, timedelta

@pytest.fixture
def sample_bronze_events() -> pl.DataFrame:
    """Minimal bronze events for unit testing. 3 cases, ~15 events."""
    base_time = datetime(2018, 6, 1, 9, 0, 0)
    return pl.DataFrame({
        "case_id": ["DOC1_ITEM1"] * 5 + ["DOC1_ITEM2"] * 4 + ["DOC2_ITEM1"] * 6,
        "activity": [
            # Case 1: happy path 3-way after GR
            "Create Purchase Order Item", "Record Goods Receipt",
            "Record Invoice Receipt", "Clear Invoice", "Close Purchase Order",
            # Case 2: 2-way match
            "Create Purchase Order Item", "Record Invoice Receipt",
            "Clear Invoice", "Close Purchase Order",
            # Case 3: rework case
            "Create Purchase Order Item", "Record Goods Receipt",
            "Record Invoice Receipt", "Cancel Invoice Receipt",
            "Record Invoice Receipt", "Clear Invoice",
        ],
        "timestamp": [
            base_time + timedelta(hours=i*24) for i in range(5)
        ] + [
            base_time + timedelta(hours=i*24) for i in range(4)
        ] + [
            base_time + timedelta(hours=i*24) for i in range(6)
        ],
        "resource": [
            "user_001", "BATCH_001", "user_002", "BATCH_002", "BATCH_003",
            "user_001", "user_002", "BATCH_002", "BATCH_003",
            "user_001", "BATCH_001", "user_003", "user_003", "user_003", "BATCH_002",
        ],
        "event_value": [
            1000.0, 1000.0, 1000.0, 1000.0, 0.0,
            500.0, 500.0, 500.0, 0.0,
            2000.0, 2000.0, 1800.0, -1800.0, 2000.0, 2000.0,
        ],
    })

@pytest.fixture
def sample_bronze_cases() -> pl.DataFrame:
    """Minimal bronze cases matching sample_bronze_events."""
    return pl.DataFrame({
        "case_id": ["DOC1_ITEM1", "DOC1_ITEM2", "DOC2_ITEM1"],
        "purchasing_document": ["DOC1", "DOC1", "DOC2"],
        "item": ["ITEM1", "ITEM2", "ITEM1"],
        "item_type": ["Standard", "Standard", "Standard"],
        "gr_based_iv": [True, False, True],
        "goods_receipt": [True, False, True],
        "company": ["Company_A", "Company_A", "Company_B"],
        "vendor": ["Vendor_X", "Vendor_Y", "Vendor_X"],
        "item_category": [
            "3-way match, invoice after GR",
            "2-way match",
            "3-way match, invoice after GR",
        ],
    })

@pytest.fixture
def sample_silver_events(sample_bronze_events) -> pl.DataFrame:
    """Silver events with enrichment columns for testing analytics."""
    # Add silver-layer columns to bronze fixture
    return sample_bronze_events.with_columns([
        pl.col("resource").map_elements(
            lambda r: "batch" if r.startswith("BATCH") else "human",
            return_dtype=pl.Utf8,
        ).alias("resource_type"),
        pl.lit("S1").alias("process_stage"),  # simplified for tests
        pl.col("timestamp").rank("ordinal").over("case_id").alias("event_order"),
    ])
```

#### Test Categories
| Category | Count | What to test |
|----------|-------|-------------|
| Ingestion (unit) | 5+ | XES attribute extraction, type coercion, null handling |
| Ingestion (integration) | 3+ | Bronze row counts, schema match, referential integrity |
| Silver transforms (unit) | 6+ | Temporal derivations, resource classification, flow type assignment |
| Silver quality (integration) | 3+ | Pandera schema validation, null rates, event ordering |
| Analytics (unit) | 8+ | Variant computation, compliance rule evaluation, bottleneck detection, automation scoring formulas |
| Gold marts (integration) | 3+ | Fact table completeness, dimension referential integrity |
| Export (unit) | 2+ | JSON schema validation, file size checks |

### Documentation
- Every doc file has clear purpose and structure
- No placeholder content in final version
- Decision log has at least 10 entries
- Limitations are honest and specific

---

## 14. Interview Preparation

### How to explain this project to LIDER IT (or similar)

**30-second pitch:**
"I built a process intelligence platform for Procure-to-Pay on top of a real enterprise event log — 250,000 purchase order cases, 1.6 million events. It reconstructs how the process actually flows vs. how it should flow, measures compliance against purchasing rules, identifies where time accumulates, and scores which manual activities are best candidates for automation. The output is an executive BI dashboard that looks like something you'd deliver to a client."

**Why it matters for a consulting firm:**
"Companies invest in SAP or Dynamics but often don't know how their processes actually perform. This project bridges that gap — it's the kind of analysis you'd do before recommending process improvements, RPA implementations, or ERP reconfigurations. I designed the data architecture, the compliance rules, the KPIs, and the presentation layer end to end."

**Technical depth (if asked):**
- "I used a medallion architecture — raw XES to bronze parquet, then silver with normalization and classification, then gold with dimensional models and fact tables. All transformations are in Polars for performance, with DuckDB for complex aggregations."
- "The compliance engine checks 10 rules derived from the actual P2P process documentation — things like 3-way matching sequence, GR-before-clearance, value matching."
- "The automation scoring uses a composite of volume, input uniformity, timing regularity, error rate, and current batch coverage to rank activities by RPA potential."

**Honest limitations (shows maturity):**
"The dataset is anonymized, so I can't map findings to real business entities. The automation recommendations are inferred from process patterns, not validated in production. And the predictive layer is limited to what's available in the event log — in a real engagement you'd have richer feature sets."

---

## 15. Execution Status

> **Claude Code: Update this section after EVERY phase.**

| Phase | Status | Date Started | Date Completed | Notes |
|-------|--------|-------------|----------------|-------|
| Phase 0: Setup | **COMPLETE** | 2026-03-31 | 2026-03-31 | 47/47 unit tests pass; ruff clean; git init + first commit |
| Phase 1: Ingestion | NOT STARTED | — | — | — |
| Phase 2: Silver | NOT STARTED | — | — | — |
| Phase 3: Process Mining | NOT STARTED | — | — | — |
| Phase 4: Business KPIs | NOT STARTED | — | — | — |
| Phase 5: Predictive | NOT STARTED | — | — | — |
| Phase 6: Frontend | NOT STARTED | — | — | — |
| Phase 7: Polish | NOT STARTED | — | — | — |

### Phase 0 — What Was Built (2026-03-31)

**Directory structure created:**
```
src/{config.py, ingestion/, transformation/, analytics/, gold/, quality/, pipeline/}
tests/{conftest.py, test_ingestion.py, test_silver.py, test_gold.py, test_analytics.py, test_quality.py}
docs/{architecture.md, decision_log.md}
scripts/{run_pipeline.py, profile_data.py, export_for_frontend.py}
frontend/{package.json, tsconfig.json, vite.config.ts, tailwind.config.ts, postcss.config.cjs, index.html}
.github/workflows/ci.yml
pyproject.toml, README.md, .gitignore, .gitattributes
```

**Python env:** Installed with `pip install -e ".[dev]"` using Python 3.12.3. All core deps (polars, duckdb, pm4py, pandera, scikit-learn, lightgbm) listed in pyproject.toml.

**Test results:** 47 unit tests pass, 7 integration tests deselected by default (`-m 'not integration'`). Integration tests require bronze/silver/gold parquet files created in later phases.

**Lint:** `ruff check src/ tests/ scripts/` → all checks passed.

**Git:** Initialized, first commit `add70a3` — all 49 project files committed.

**Key source files created:**
- [src/config.py](src/config.py) — all path constants, quality gate thresholds, scoring weights
- [src/pipeline/runner.py](src/pipeline/runner.py) — PipelineRunner + PhaseResult dataclass
- [scripts/run_pipeline.py](scripts/run_pipeline.py) — CLI with `--phase`, `--all`, `--dry-run` flags
- [src/transformation/resource_classifier.py](src/transformation/resource_classifier.py) — `classify_resource()` implemented (BATCH_ prefix rule)
- [src/transformation/flow_type_classifier.py](src/transformation/flow_type_classifier.py) — maps item_category → flow_type enum
- [src/analytics/automation_scoring.py](src/analytics/automation_scoring.py) — `shannon_entropy()` implemented
- [src/quality/data_checks.py](src/quality/data_checks.py) — `check_referential_integrity()`, `check_null_rates()`

**Stub modules (implement in later phases):**
- xes_parser.py, bronze_writer.py (Phase 1)
- silver_builder.py, temporal_enrichment.py (Phase 2)
- process_discovery.py, conformance.py, throughput.py (Phase 3)
- resource_analysis.py, automation_scoring.py full impl (Phase 4)
- predictive.py (Phase 5)
- export_for_frontend.py full impl (Phase 4)

### Discovered Facts (from actual XES inspection)
> Claude Code: Fill this in during Phase 1.

- **Actual event count:** TBD (Phase 1)
- **Actual case count:** TBD (Phase 1)
- **Activity names (all 42):** TBD (Phase 1)
- **Attribute names found in XES:** TBD (Phase 1) — `concept:name`, `time:timestamp`, `org:resource`, `lifecycle:transition` assumed; verify
- **Timestamp range:** TBD (Phase 1)
- **Resource naming patterns:** TBD (Phase 1) — BATCH_ prefix assumed in classifier; must verify against real data
- **Flow type distribution:** TBD (Phase 1)
- **Known parsing issues:** TBD (Phase 1)

### Key Decisions Made
> Claude Code: Log decisions here as they're made.

1. Chose pm4py for XES parsing — handles IEEE-XES natively, manages memory for 728 MB files.
2. Chose Polars over pandas — 5-10× faster for columnar operations; required by CLAUDE.md.
3. Chose DuckDB for complex SQL aggregations over parquet — clean SQL interface, excellent pushdown.
4. No parquet partitioning — dataset fits in memory at this scale; revisit if 10× larger.
5. Rule-based automation scoring (not ML) — no ground-truth labels for "successfully automated activity" exist.
6. Integration tests deselected by default (`-m 'not integration'`) — CI runs fast without data files; run manually with `-m integration` after pipeline executes.
7. `pyproject.toml` build-backend fixed: `setuptools.build_meta` (not `setuptools.backends.legacy:build` which requires newer setuptools).
8. Python 3.12.3 in use (project targets 3.11+, fully compatible).

### Deviations from Plan
> Claude Code: Document any changes from the original design here.

1. `pyproject.toml` build-backend: Plan used `setuptools.backends.legacy:build` (too new for installed setuptools). Changed to `setuptools.build_meta` which works with any setuptools version.
2. `test_analytics.py`: `import polars as pl` moved inside individual test functions (not module-level) to avoid lint warning about unused import in test body.
3. pytest `addopts` includes `-m 'not integration'` to auto-skip integration tests in CI — integration tests that require actual parquet data won't run until Phase 1 completes.

---

## 16. File Checklist (Final Delivery)

### Core Files
- [x] `CONTEXT.md` (this file, fully updated — Phase 0)
- [x] `README.md` (initial version — Phase 0; portfolio-ready version in Phase 7)
- [x] `CLAUDE.md`
- [x] `pyproject.toml`
- [x] `.github/workflows/ci.yml`

### Documentation
- [x] `docs/architecture.md` (Phase 0)
- [ ] `docs/data_dictionary.md` (Phase 1)
- [x] `docs/decision_log.md` (Phase 0 — 11 decisions logged)
- [ ] `docs/modeling_notes.md` (Phase 5)
- [ ] `docs/limitations.md` (Phase 7)
- [ ] `docs/runbook.md` (Phase 7)
- [ ] `docs/kpi_catalog.md` (Phase 4)

### Data Pipeline
- [x] `src/config.py` (Phase 0 — full)
- [x] `src/ingestion/xes_parser.py` (Phase 0 — stub; implement Phase 1)
- [x] `src/ingestion/bronze_writer.py` (Phase 0 — stub; implement Phase 1)
- [x] `src/transformation/silver_builder.py` (Phase 0 — stub; implement Phase 2)
- [x] `src/transformation/temporal_enrichment.py` (Phase 0 — stub; implement Phase 2)
- [x] `src/transformation/resource_classifier.py` (Phase 0 — classify_resource() implemented)
- [x] `src/transformation/flow_type_classifier.py` (Phase 0 — classify_flow_type() implemented)
- [x] `src/analytics/process_discovery.py` (Phase 0 — stub; implement Phase 3)
- [x] `src/analytics/conformance.py` (Phase 0 — stub; implement Phase 3)
- [x] `src/analytics/throughput.py` (Phase 0 — stub; implement Phase 3)
- [x] `src/analytics/resource_analysis.py` (Phase 0 — stub; implement Phase 4)
- [x] `src/analytics/automation_scoring.py` (Phase 0 — shannon_entropy() implemented; rest Phase 4)
- [x] `src/analytics/predictive.py` (Phase 0 — stub; implement Phase 5)
- [x] `src/gold/mart_builder.py` (Phase 0 — stub; implement Phase 3)
- [x] `src/gold/facts.py` (Phase 0 — stub; implement Phase 3)
- [x] `src/gold/dimensions.py` (Phase 0 — stub; implement Phase 3)
- [x] `src/quality/schemas.py` (Phase 0 — stub; implement Phase 2)
- [x] `src/quality/data_checks.py` (Phase 0 — check_referential_integrity(), check_null_rates() implemented)
- [x] `src/pipeline/runner.py` (Phase 0 — PipelineRunner + PhaseResult full implementation)
- [x] `scripts/run_pipeline.py` (Phase 0 — full CLI with argparse)
- [x] `scripts/profile_data.py` (Phase 0 — stub; implement Phase 1)
- [x] `scripts/export_for_frontend.py` (Phase 0 — stub; implement Phase 4)

### Tests
- [x] `tests/conftest.py` (Phase 0 — sample_bronze_events, sample_bronze_cases, sample_silver_events, sample_silver_cases fixtures)
- [x] `tests/test_ingestion.py` (Phase 0 — 11 unit tests + 3 integration stubs)
- [x] `tests/test_silver.py` (Phase 0 — 13 unit tests + 1 integration stub)
- [x] `tests/test_gold.py` (Phase 0 — 3 placeholder tests + 3 integration stubs)
- [x] `tests/test_analytics.py` (Phase 0 — 13 tests including rework/loop detection + automation weights)
- [x] `tests/test_quality.py` (Phase 0 — 7 tests for config validation)

### Frontend
- [x] `frontend/package.json` (Phase 0)
- [ ] `frontend/src/App.tsx`
- [ ] `frontend/src/pages/ExecutiveOverview.tsx`
- [ ] `frontend/src/pages/ProcessMap.tsx`
- [ ] `frontend/src/pages/ComplianceCenter.tsx`
- [ ] `frontend/src/pages/BottleneckExplorer.tsx`
- [ ] `frontend/src/pages/AutomationCandidates.tsx`
- [ ] `frontend/src/pages/CaseDrilldown.tsx`
- [ ] `frontend/src/pages/SubsidiaryBenchmark.tsx`

### Outputs
- [ ] `outputs/profiling_report.md`
- [ ] `outputs/screenshots/` (7 pages)
- [ ] Deployed demo URL

---

*Last updated: Phase 0 — Initial design by Claude Opus*
*Document version: 2.0 — All architectural gaps closed*
*Gaps addressed in v2.0: process stage model, normative sequences per flow type, GR↔Invoice matching algorithm, automation scoring concrete formulas, frontend JSON contracts with TypeScript schemas, test fixture strategy with synthetic data, pipeline runner CLI interface, deployment pipeline with Vite/GH-Pages config, lazy loading strategy, performance budget*
