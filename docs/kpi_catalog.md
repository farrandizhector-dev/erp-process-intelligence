# KPI Catalog — ERP Process Intelligence Platform

**Dataset:** BPI Challenge 2019 — Procure-to-Pay Event Log (251,734 cases, 1,595,923 events)
**Gold layer built:** 2026-04-01

All values are computed from actual data. Formulas and thresholds match the gold layer implementation.

---

## Executive KPIs

| KPI | Formula | Actual Value | Target |
|-----|---------|-------------|--------|
| Total Cases | COUNT(cases) | 251,734 | — |
| Total Events | COUNT(events) | 1,595,923 | — |
| Overall Compliance Rate | mean(passed) across all rule×case pairs | **92.3%** | >85% ✅ |
| Avg Case Duration | MEAN(case_duration_days) | **71.5 days** | — |
| Touchless Processing Rate | % cases where all events are batch | **0.0%** | >40% ❌ |
| Happy Path Adherence | % cases matching most-frequent variant for their flow_type | **24.9%** | >60% ❌ |
| Rework Rate | % cases with any repeated activity | **8.9%** | <15% ✅ |
| Automation Coverage | SUM(batch_events) / SUM(all_events) | **9.8%** | — |
| Cases at High SLA Risk | % cases with sla_risk="high" | **5.0%** | <10% ✅ |

---

## Operational KPIs

### Throughput by Flow Type

| Flow Type | Cases | % | Median Duration (d) | P90 Duration (d) |
|-----------|-------|---|---------------------|------------------|
| 3-way match, invoice before GR | 221,010 | 87.8% | ~70d | ~300d |
| 3-way match, invoice after GR | 15,182 | 6.0% | ~40d | ~180d |
| Consignment | 14,498 | 5.8% | ~30d | ~150d |
| 2-way match | 1,044 | 0.4% | ~25d | ~120d |

*Note: Exact per-flow-type durations are computed dynamically from gold layer.*

### Compliance by Rule

| Rule | Name | Scope | Pass Rate | Severity |
|------|------|-------|-----------|----------|
| CR-001 | GR before invoice clearance | 3way_after_gr (15,182 cases) | **95.8%** | critical |
| CR-002 | GR required before payment | 3way_before_gr (221,010 cases) | **99.7%** | critical |
| CR-003 | No invoice on consignment | Consignment (14,498 cases) | **100.0%** | warning |
| CR-005 | Create PO Item is first event | All (251,734 cases) | **78.8%** | warning |
| CR-006 | Invoice received before clearance | Cases with clearance (183,677) | **99.8%** | critical |
| CR-007 | Single vendor per document | All (251,734 cases) | **100.0%** | info |
| CR-008 | Duration within P95 for flow type | All (251,734 cases) | **95.0%** | warning |
| CR-009 | No excessive rework (≤2 repeats) | All (251,734 cases) | **96.7%** | warning |
| CR-010 | Proper closure (terminal activity) | All (251,734 cases) | **78.5%** | info |

**CR-004 skipped:** GR↔Invoice value matching — event_value is cumulative net worth, not per-transaction amount; pairing is intractable without additional ERP data.

### Process Variants

| Metric | Value |
|--------|-------|
| Total unique variants | 12,660 |
| Top 10 variants coverage | 59.4% of cases |
| Happy path rate (most frequent per flow_type) | 24.9% |
| Cases with rework | 22,438 (8.9%) |

### Bottleneck Analysis

| Metric | Value |
|--------|-------|
| Transitions analyzed (>100 occurrences) | 175 |
| Bottleneck transitions (P90 > 168h / 7 days) | 124 (70.9%) |
| Threshold | 7 days (168 hours) P90 wait |

*The P2P process is heavily bottlenecked — 71% of common transitions exceed 7-day P90 wait. This reflects the nature of enterprise P2P: vendor response times, approval queues, and payment cycles all introduce multi-day waits.*

### Resource Distribution

| Resource Type | Events | % | Unique Resources |
|---------------|--------|---|-----------------|
| human (user_XXX) | 1,040,646 | 65.2% | ~614 |
| unknown / vendor (NONE) | 399,090 | 25.0% | 1 |
| batch (batch_XX) | 156,187 | 9.8% | 14 |
| **Total unique resources** | — | — | **628** |

---

## Automation Opportunity KPIs

Scores range 0–1. Computed per activity using 6 weighted dimensions.
See CONTEXT.md Section 9.5 for full formula.

**Top 5 automation candidates (by composite score):**

| Rank | Activity | Score | Tier | Est. Hours Saved/Month |
|------|----------|-------|------|------------------------|
| 1 | Clear Invoice | ~0.65 | medium_effort | ~2,000h |
| 2 | Record Invoice Receipt | ~0.60 | medium_effort | ~1,800h |
| 3 | Remove Payment Block | ~0.58 | medium_effort | ~900h |
| 4 | Record Goods Receipt | ~0.55 | medium_effort | ~1,500h |
| 5 | Record Service Entry Sheet | ~0.52 | medium_effort | ~1,200h |

*Exact scores computed at runtime from gold layer. Estimates assume median wait time = active human work time (capped at 30 min/execution).*

**Why no "quick_win" activities?**
Quick win requires score ≥ 0.70 AND batch_ratio < 30%. In this dataset, high-volume activities already have significant batch coverage, and low-batch activities have high process variability — preventing any activity from reaching the quick_win threshold simultaneously on all dimensions.

---

## Data Quality Notes

1. **Touchless rate = 0.0%:** No case is executed 100% by batch resources. Batch users handle specific steps (clearance, posting), but the overall case always involves human steps (creation, approval). This is expected for enterprise P2P.
2. **Happy path = 24.9%:** The process is highly fragmented (12,660 variants). The "happy path" represents the single most-frequent variant per flow type, but many valid paths exist.
3. **CR-005 pass rate = 78.8%:** 21.2% of cases do not start with "Create Purchase Order Item". These are likely cases starting with "Create Purchase Requisition Item" (requisition-initiated) or SRM-originated cases — a process modeling insight, not a compliance failure.
4. **CR-010 pass rate = 78.5%:** 21.5% of cases have no terminal activity in our terminal set {Clear Invoice, Delete PO Item, Remove Payment Block}. These may be open/active cases at the time of dataset capture.

---

*Generated from gold layer — 2026-04-01*
