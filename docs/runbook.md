# Runbook — ERP Process Intelligence Platform

Step-by-step guide to reproduce the full pipeline from raw data to running dashboard.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | 3.12.x confirmed working |
| Node.js | 20+ | For frontend build |
| npm | 10+ | Comes with Node.js |
| Git | Any | For cloning |
| RAM | 4 GB+ | pm4py parses 728 MB XES into memory |
| Disk | 2 GB+ | Raw XES + parquet outputs |

### Get the Dataset

Download the BPI Challenge 2019 XES file (~728 MB) from:
> https://data.4tu.nl/datasets/769f25d0-e167-4a35-bbb6-7c96a8872593

Place it at:
```
data/raw/BPI_Challenge_2019.xes
```

---

## 1. Clone and Install

```bash
git clone <repo-url>
cd erp-process-intelligence

# Install Python dependencies (editable mode)
pip install -e ".[dev]"
```

This installs: polars, duckdb, pm4py, pandera, lightgbm, scikit-learn, pytest, ruff, and all other dependencies declared in `pyproject.toml`.

---

## 2. Run the Backend Pipeline

Each phase reads from the previous phase's output. Run them in order.

### Phase 1 — Ingestion (Bronze Layer)
```bash
python scripts/run_pipeline.py --phase ingest --log-level INFO
```
- Parses the 728 MB XES file with pm4py (~55 seconds)
- Writes `data/bronze/bronze_events.parquet` (1,595,923 rows)
- Writes `data/bronze/bronze_cases.parquet` (251,734 rows)

### Phase 2 — Silver Layer
```bash
python scripts/run_pipeline.py --phase silver --log-level INFO
```
- Resource classification (batch/human/unknown)
- Flow type assignment (4 types based on case flags)
- Temporal enrichment, variant ID computation
- Writes 4 silver parquet files (~4 seconds)

### Phase 3+4 — Gold Layer
```bash
python scripts/run_pipeline.py --phase gold --log-level INFO
```
- Process discovery, compliance checks, bottleneck analysis
- Automation scoring, resource dimension, fact tables
- Writes 12 gold parquet files (~4 seconds)

### Phase 5 — Predictive Model
```bash
python scripts/run_pipeline.py --phase predict --log-level INFO
```
- Trains LightGBM SLA risk classifier
- Writes `data/gold/fact_sla_risk.parquet` and `models/sla_risk_lgbm.pkl`
- ~2 seconds

### Export JSON for Frontend
```bash
python scripts/export_for_frontend.py
```
- Reads gold layer, aggregates, writes 9 JSON files to `frontend/public/data/`
- ~1 second, ~0.5 MB total

### Run All Phases at Once (after first ingest)
```bash
python scripts/run_pipeline.py --phase silver && \
python scripts/run_pipeline.py --phase gold && \
python scripts/run_pipeline.py --phase predict && \
python scripts/export_for_frontend.py
```

---

## 3. Run the Frontend

```bash
cd frontend
npm install          # first time only
npm run dev          # dev server with hot reload
```

Open: http://localhost:5173/erp-process-intelligence/

### Production Build
```bash
cd frontend
npm run build        # outputs to frontend/dist/
npm run preview      # preview production build locally
```

---

## 4. Run Tests

```bash
# Unit tests only (no data files required)
python -m pytest tests/ -m "not integration" -v

# All tests including integration (requires silver/gold parquet files)
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -m "not integration" --cov=src --cov-report=term-missing
```

**Current status:** 55 unit tests pass, 7 integration tests require parquet files.

---

## 5. Linting

```bash
# Check
python -m ruff check src/ tests/ scripts/

# Auto-fix safe issues (import sort, unused imports)
python -m ruff check src/ tests/ scripts/ --fix
```

---

## 6. Pipeline Options

```
python scripts/run_pipeline.py --help

Options:
  --phase PHASE       ingest | silver | gold | predict | export
  --all               Run all phases in sequence
  --dry-run           Validate inputs without executing
  --skip-validation   Skip Pandera schema checks (faster for dev)
  --log-level LEVEL   DEBUG | INFO | WARNING | ERROR (default: INFO)
  --log-file FILE     Write logs to file in addition to stdout
```

---

## 7. Directory Reference

| Path | Contents |
|------|---------|
| `data/raw/` | Source XES file (gitignored) |
| `data/bronze/` | bronze_events.parquet, bronze_cases.parquet (gitignored) |
| `data/silver/` | 4 silver parquet files (gitignored) |
| `data/gold/` | 12 gold parquet files (gitignored) |
| `models/` | sla_risk_lgbm.pkl (gitignored) |
| `frontend/public/data/` | 9 JSON exports (committed — no PII) |
| `frontend/dist/` | Production build output (gitignored) |
| `outputs/` | Profiling report, screenshots |
| `docs/` | Architecture, data dictionary, KPIs, modeling notes, limitations |

---

## 8. Troubleshooting

**`FileNotFoundError: Silver file not found`**  
→ Run `--phase ingest` and `--phase silver` before `--phase gold`.

**`pm4py` parsing is slow**  
→ Expected: ~55 seconds for the 728 MB XES file. Use `--log-level WARNING` to reduce output noise.

**Frontend shows blank page**  
→ Check that `frontend/public/data/executive_kpis.json` exists. Run `python scripts/export_for_frontend.py` first.

**`npm run dev` fails with missing module**  
→ Run `npm install` in the `frontend/` directory.

**`ruff` reports import sort errors**  
→ Run `python -m ruff check src/ --fix` to auto-sort.

**LightGBM `UserWarning` about feature names**  
→ Fixed in current code. If you see it, check `src/analytics/predictive.py` — `predict_proba` must be called with a pandas DataFrame, not a numpy array.

---

*Runbook version: 1.0 · 2026-04-01*
