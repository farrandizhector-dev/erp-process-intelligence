# ERP Process Intelligence Platform

> **Procure-to-Pay Mining, Compliance & Automation Intelligence**

![Status](https://img.shields.io/badge/status-under%20construction-yellow)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Overview

An end-to-end Procure-to-Pay (P2P) process intelligence platform built on top of a real enterprise event log — **251,734 purchase order cases** and **1,595,923 events** from a multinational company's ERP system.

This platform transforms raw ERP event data into actionable business intelligence:

- **Process Discovery** — Reconstruct how the P2P process actually flows vs. how it should
- **Compliance Analysis** — Check 10 rule-based conformance rules (3-way matching, GR sequencing, value matching)
- **Bottleneck Detection** — Identify where time accumulates across 42 activities
- **Automation Scoring** — Rank manual activities by RPA potential using a composite scoring model
- **SLA Risk Prediction** — Classify cases at risk of breaching expected throughput times
- **Executive BI Dashboard** — 7-page React application for non-technical stakeholders

> Built as a portfolio project demonstrating enterprise data architecture, process mining, and consulting-grade analytics delivery.

---

## Architecture

```
XES Event Log (728 MB)
        │
        ▼
  [Bronze Layer]  ← Raw parquet extraction (pm4py)
        │
        ▼
  [Silver Layer]  ← Cleaned, normalized, enriched (Polars)
        │
        ▼
  [Gold Layer]    ← Analytical facts & dimensions (DuckDB + Polars)
        │
        ▼
  [JSON Export]   ← Frontend-ready static files
        │
        ▼
[React Dashboard] ← ECharts, TypeScript, Tailwind
```

**Stack:** Polars · DuckDB · pm4py · Pandera · scikit-learn · LightGBM · React 18 · TypeScript · ECharts · Vite · Tailwind CSS

---

## Dataset

**Source:** BPI Challenge 2019 — Real purchase order event log from a multinational coatings company (Netherlands).

| Metric | Value |
|--------|-------|
| Purchase Documents | 76,349 |
| Line Items (Cases) | 251,734 |
| Events | 1,595,923 |
| Activities | 42 |
| Users | 627 |
| Time Range | 2018–2019 |

4 process flow types: 3-way match (invoice after GR), 3-way match (invoice before GR), 2-way match, Consignment.

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install -e ".[dev]"

# 2. Place XES file
# Copy BPI_Challenge_2019.xes to data/raw/

# 3. Run full pipeline
python scripts/run_pipeline.py --all

# 4. Start frontend
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
erp-process-intelligence/
├── src/
│   ├── config.py              # Paths & constants
│   ├── ingestion/             # XES → Bronze parquet
│   ├── transformation/        # Bronze → Silver
│   ├── analytics/             # Process mining algorithms
│   ├── gold/                  # Gold layer marts
│   ├── quality/               # Pandera schemas & checks
│   └── pipeline/              # Orchestration
├── tests/                     # pytest tests
├── scripts/                   # CLI entry points
├── frontend/                  # React dashboard
├── docs/                      # Architecture, decisions, KPIs
├── data/
│   ├── raw/                   # Original XES (gitignored)
│   ├── bronze/                # Parsed parquet
│   ├── silver/                # Cleaned parquet
│   └── gold/                  # Analytical marts
└── outputs/                   # Reports & screenshots
```

---

## Key Findings

> *To be filled after data analysis is complete.*

---

## Author

**Héctor Ferrándiz Sanchis** — Data Science, Universidad Europea de Valencia

[LinkedIn](https://linkedin.com/in/hectordata)

---

## License

MIT
