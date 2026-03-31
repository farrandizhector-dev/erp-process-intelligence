# Decision Log — ERP Process Intelligence Platform

> Each entry: what was decided, why, and any alternatives considered.

---

## DL-001: Use pm4py for XES parsing, not custom XML parser

**Decision:** Use pm4py to parse the BPI Challenge 2019 XES file.

**Rationale:** pm4py implements the IEEE-XES standard natively and handles memory for large files. Writing a custom SAX parser for a 728 MB file would add significant complexity and maintenance burden. pm4py is the industry-standard tool for process mining in Python — using it signals competence to the target audience (process mining / BPM practitioners).

**Alternatives considered:**
- Custom `xml.etree.ElementTree` SAX parser: more control, but more code and same result
- lxml: faster XML parsing but no XES-specific semantics

---

## DL-002: Use Polars instead of pandas for data processing

**Decision:** All DataFrame operations use Polars, not pandas.

**Rationale:** Polars is 5–10× faster than pandas for column operations, uses significantly less memory via lazy evaluation, and has a cleaner API for the kinds of transformations needed (window functions, list operations, expression-based). At 1.6M events, pandas would work but Polars is visibly faster and shows more modern Python data tooling.

**Alternatives considered:**
- pandas: familiar but slower; excluded by CLAUDE.md instruction
- DuckDB SQL only: fine for aggregations but awkward for row-level transformations

---

## DL-003: Use DuckDB for complex aggregations over parquet

**Decision:** Use DuckDB SQL for complex GROUP BY / window queries over parquet files, supplementing Polars.

**Rationale:** DuckDB's SQL interface is more readable for multi-table joins and window functions like percentile calculations. It also has excellent parquet pushdown optimization. Polars and DuckDB complement each other well.

**Alternatives considered:**
- Pure Polars: possible but verbose for multi-table joins
- Spark: overkill for this data scale

---

## DL-004: Medallion architecture (Bronze → Silver → Gold)

**Decision:** Use a 3-layer medallion architecture with strict layer separation.

**Rationale:** Clear data lineage, easy debugging (inspect any layer independently), standard in modern data engineering practice. Demonstrates the kind of architectural thinking a consulting firm expects from a data engineer.

**Alternatives considered:**
- Direct XES → analytics: faster to build but hard to debug and maintain
- 2-layer (raw + analytics): simpler but loses the intermediate clean layer

---

## DL-005: No partitioning for parquet files

**Decision:** All gold parquet tables are single files (no partitioning by date/flow_type/etc.).

**Rationale:** The largest table (fact_event_log) has ~1.6M rows and fits comfortably in memory with Polars. Dashboard queries always scan full tables anyway (no selective filters at the file layer). Partitioning adds complexity and I/O overhead at this scale.

**Conditions for revisiting:** If dataset were 10× larger or if dashboard queries were highly selective on a single dimension, partitioning `fact_event_log` by `flow_type` would make sense.

---

## DL-006: Rule-based automation scoring (not ML)

**Decision:** Automation opportunity scoring uses a deterministic composite formula, not a trained model.

**Rationale:** There is no ground-truth label for "this activity was successfully automated." A rule-based composite (volume, batch gap, input uniformity, timing regularity, error rate, wait reduction) is transparent, explainable, and defensible to a stakeholder audience. It also avoids circularity — using batch_ratio as a label would conflate the target with features.

**Alternatives considered:**
- Clustering: unsupervised grouping of activities by feature similarity; less interpretable
- Expert-labeled ML: would require manual labeling effort that doesn't exist

---

## DL-007: LightGBM for SLA risk prediction

**Decision:** Use LightGBM for the predictive layer if built.

**Rationale:** LightGBM handles categorical features natively (flow_type, company, vendor), is fast to train, and produces good feature importances. The dataset size (~251K cases) is well-suited for gradient boosting. Logistic regression is the fallback if LightGBM overcomplicates interpretation.

**Alternatives considered:**
- Random Forest: similar quality, less efficient
- Neural networks: unjustified complexity for tabular data at this scale

---

## DL-008: Static JSON files for frontend (no API)

**Decision:** Frontend consumes pre-computed static JSON files from `frontend/public/data/`.

**Rationale:** Eliminates backend infrastructure entirely. Dataset is historical and batch-processed — no real-time requirements. Static files are served via GitHub Pages with gzip compression at effectively zero cost. Total payload < 10 MB.

**Alternatives considered:**
- FastAPI backend: adds deployment complexity for no real-time benefit
- SQLite in-browser (sql.js): interesting but adds 500KB+ bundle weight

---

## DL-009: React 18 + TypeScript + ECharts for frontend

**Decision:** Frontend uses React 18 with TypeScript and ECharts via echarts-for-react.

**Rationale:** React + TypeScript is the industry-standard frontend stack. TypeScript catches type errors in data contracts between JSON and components. ECharts provides Sankey diagrams, heatmaps, gauges, radar charts, and bubble charts — all required for this project — in a single library.

**Alternatives considered:**
- D3.js: too low-level; would take 3× longer to build the same charts
- Recharts: limited chart types (no Sankey, no heatmap)
- Observable Plot: excellent but less enterprise-looking
- Plotly: possible but larger bundle size

---

## DL-010: Temporal train/test split for predictive model

**Decision:** Split cases by timestamp (earlier cases = train, later cases = test) rather than random split.

**Rationale:** Random splitting creates data leakage — a model trained on future cases predicting past cases is not realistic. Temporal split mimics real deployment where the model is trained on historical data and predicts on new incoming cases.

**Tradeoff:** Temporal split means the test set may have different case characteristics if the process changed over time. This limitation is documented in `docs/limitations.md`.

---

## DL-011: Synthetic test fixtures (no dependency on XES file)

**Decision:** All unit tests use synthetic DataFrame fixtures defined in `tests/conftest.py`. No test depends on the 728MB XES file.

**Rationale:** Tests must be fast, reproducible, and runnable in CI without downloading the large dataset. The XES file is in `.gitignore`. Integration tests that verify end-to-end behavior are marked separately and skipped in CI if data is absent.

---
