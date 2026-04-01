# ERP Process Intelligence Platform

> **Procure-to-Pay Mining, Compliance & Automation Intelligence**  
> Built on 251,734 real enterprise purchase-order cases · 1,595,923 events · BPI Challenge 2019

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![Polars](https://img.shields.io/badge/Polars-1.0%2B-orange)](https://pola.rs)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.0%2B-green)](https://lightgbm.readthedocs.io)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript)](https://typescriptlang.org)
[![ECharts](https://img.shields.io/badge/ECharts-5-aa344d)](https://echarts.apache.org)
[![Tests](https://img.shields.io/badge/Tests-55%20passing-brightgreen)](tests/)
[![Ruff](https://img.shields.io/badge/Lint-Ruff-000000)](https://docs.astral.sh/ruff/)

---

## What This Is

This platform transforms a raw ERP event log into a full-stack process intelligence product — the kind of deliverable a consulting firm like LIDER IT would build before recommending process improvements, RPA rollouts, or ERP reconfigurations to a client.

**It answers six enterprise questions:**

1. **How does the process actually flow?** Variant mining across 12,660 unique P2P paths
2. **Where are we non-compliant?** 9 automated compliance rules (3-way matching, approval sequences, invoice timing)
3. **Where does time accumulate?** Bottleneck detection across 175 transitions — 71% exceed 7-day P90 wait
4. **Which steps should we automate?** Composite RPA scoring across 6 dimensions for all 42 activities
5. **Which cases will breach SLA?** LightGBM classifier with AUC-ROC = 0.917
6. **How do subsidiaries compare?** Multi-dimensional radar benchmarking across 4 companies and 1,975 vendors

---

## Key Findings

| Finding | Value |
|---------|-------|
| Overall compliance rate | **92.3%** (target: >85% ✅) |
| Rework rate | **8.9%** of cases repeat at least one activity |
| Happy path adherence | **24.9%** — process is highly fragmented (12,660 variants) |
| Bottlenecked transitions | **71%** of common transitions exceed 7-day P90 wait |
| Top automation candidate | Create Purchase Order Item — est. **4,844 h/month** savings |
| SLA risk model | AUC-ROC **0.917**, PR-AUC **0.802**, F1 **0.712** |
| Touchless processing | **0.0%** — every case requires human involvement |
| CR-005 anomaly | 21.2% of cases don't start with "Create Purchase Order Item" — requisition-initiated or SRM-originated flows |

---

## Architecture

```
BPI Challenge 2019 XES (728 MB)
         │
         ▼
┌─────────────────┐
│  BRONZE LAYER   │  Raw parquet extraction via pm4py
│  bronze_events  │  1,595,923 events
│  bronze_cases   │  251,734 cases
└────────┬────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│              SILVER LAYER                  │
│  silver_events    · Resource classification │
│  silver_cases     · Flow type (4 types)    │
│  silver_resources · Temporal enrichment    │
│  silver_activities· Variant ID computation │
└────────┬───────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│               GOLD LAYER (12 tables)       │
│  fact_event_log        dim_activity        │
│  fact_case_summary     dim_company         │
│  fact_variant_stats    dim_vendor          │
│  fact_compliance_checks dim_resource       │
│  fact_bottleneck_analysis dim_calendar     │
│  fact_automation_opportunities             │
│  fact_sla_risk                             │
└────────┬───────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│        FRONTEND (React + ECharts)          │
│  9 JSON files · 8-page enterprise dashboard│
│  Sankey · Gauge · Radar · Scatter · Bar    │
└────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Data Processing | **Polars** | Fast columnar DataFrames for 1.6M events |
| Analytical SQL | **DuckDB** | Complex aggregations over parquet |
| Process Mining | **pm4py** | XES parsing (IEEE standard) |
| Data Validation | **Pandera** | Schema contracts between layers |
| ML Model | **LightGBM** | SLA risk classification |
| Testing | **pytest** | 55 unit tests |
| Linting | **Ruff** | Strict Python linting, line length 100 |
| Frontend | **React 18 + TypeScript** | Type-safe component architecture |
| Styling | **Tailwind CSS** | Dark enterprise design system |
| Charts | **ECharts 5** | Sankey, gauge, radar, scatter, bar, line |
| Build | **Vite 5** | Fast bundling with code splitting |
| CI | **GitHub Actions** | Lint + test + build on push |

---

## Dashboard Pages

| Page | Visualizations |
|------|---------------|
| **Executive Overview** | 6 KPI cards, monthly trend, flow-type donut |
| **Process Map** | Sankey of 42 activities, selectable by flow type, bottlenecks highlighted red |
| **Compliance Center** | Gauge (92.3%), per-rule pass rates with severity badges, top-violating vendors |
| **Bottleneck Explorer** | Horizontal P90-wait bar chart, full transitions table |
| **Automation Candidates** | Bubble chart (volume × score × hours saved), ranked scoring table |
| **Case Drilldown** | Filter by flow type / company / SLA risk / rework, case detail panel |
| **Subsidiary Benchmark** | Radar overlay across 4 companies × 5 dimensions |
| **SLA Risk Model** | AUC-ROC 0.917, feature importance, top 100 at-risk cases |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- BPI Challenge 2019 XES file at `data/raw/BPI_Challenge_2019.xes`
  - Download: https://data.4tu.nl/datasets/769f25d0-e167-4a35-bbb6-7c96a8872593

### Backend Pipeline

```bash
# Install Python dependencies
pip install -e ".[dev]"

# Run pipeline phases in order
python scripts/run_pipeline.py --phase ingest
python scripts/run_pipeline.py --phase silver
python scripts/run_pipeline.py --phase gold
python scripts/run_pipeline.py --phase predict
python scripts/export_for_frontend.py

# Run tests
python -m pytest tests/ -m "not integration"

# Lint
python -m ruff check src/ tests/ scripts/
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # dev server → http://localhost:5173/erp-process-intelligence/
npm run build    # production build → dist/
```

See [docs/runbook.md](docs/runbook.md) for the full step-by-step guide.

---

## Project Structure

```
erp-process-intelligence/
├── src/
│   ├── config.py                    # All constants and paths
│   ├── ingestion/                   # XES → Bronze
│   ├── transformation/              # Bronze → Silver
│   ├── analytics/
│   │   ├── process_discovery.py     # Variants, happy path, rework
│   │   ├── conformance.py           # 9 compliance rules
│   │   ├── throughput.py            # Bottleneck detection
│   │   ├── resource_analysis.py     # Handoffs, workload
│   │   ├── automation_scoring.py    # 6-dimension RPA scoring
│   │   └── predictive.py           # LightGBM SLA risk model
│   ├── gold/                        # Fact + dimension table builders
│   └── pipeline/                    # Orchestration and CLI
├── scripts/
│   ├── run_pipeline.py              # Main pipeline CLI
│   └── export_for_frontend.py      # Gold → JSON exports
├── frontend/
│   ├── src/
│   │   ├── pages/                   # 8 application pages
│   │   ├── components/             # Layout + shared components
│   │   ├── hooks/useData.ts        # Generic JSON fetch hook
│   │   └── types/index.ts          # TypeScript interfaces
│   └── public/data/                # Pre-computed JSON (9 files)
├── tests/                           # 55 unit tests
├── docs/                            # Architecture, KPIs, modeling notes
└── data/
    ├── bronze/                      # Gitignored
    ├── silver/                      # Gitignored
    └── gold/                        # Gitignored
```

---

## Compliance Rules

| Rule | Description | Scope | Pass Rate |
|------|-------------|-------|-----------|
| CR-001 | GR before invoice clearance | 3-way after GR | 95.8% |
| CR-002 | GR required before payment | 3-way before GR | 99.7% |
| CR-003 | No invoice on consignment | Consignment | 100.0% |
| CR-005 | Create PO Item is first event | All cases | 78.8% |
| CR-006 | Invoice received before clearance | Cases with clearance | 99.8% |
| CR-007 | Single vendor per document | All cases | 100.0% |
| CR-008 | Duration within P95 for flow type | All cases | 95.0% |
| CR-009 | No excessive rework (≤2 repeats) | All cases | 96.7% |
| CR-010 | Proper closure (terminal activity) | All cases | 78.5% |

*CR-004 (GR↔Invoice value matching) skipped: `event_value` is cumulative net worth, not per-transaction amount. Pairing is intractable without additional ERP data.*

---

## Limitations

See [docs/limitations.md](docs/limitations.md). Key points:
- Dataset is anonymized — entity IDs cannot be decoded to real names
- Automation scores are pattern-based, not validated in production
- SLA thresholds are statistical (P75), not contractual
- Single calendar year (2018) limits temporal generalization of the ML model
- Frontend serves pre-computed JSON — not a live ERP connection

---

## Author

**Héctor Ferrándiz Sanchis**  
Data Science · Universidad Europea de Valencia  
LinkedIn: [linkedin.com/in/hectordata](https://linkedin.com/in/hectordata)

---

*Dataset: BPI Challenge 2019 · Eindhoven University of Technology · 4TU.Centre for Research Data*
