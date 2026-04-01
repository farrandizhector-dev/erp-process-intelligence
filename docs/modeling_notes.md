# Modeling Notes — SLA Risk Prediction

**Dataset:** BPI Challenge 2019 — Procure-to-Pay Event Log
**Phase:** 5 (Predictive Layer)
**Built:** 2026-04-01

---

## 1. Problem Definition

**Objective:** Given a purchase order case at creation time, predict whether it will
exceed the P75 processing time for its flow type (i.e., be classified as "medium" or
"high" SLA risk in the gold layer).

**Target variable:** Binary — `1` if `sla_risk ∈ {medium, high}`, else `0`.

**SLA thresholds (P75 of case_duration_days per flow_type):**

| Flow Type | P75 Threshold (days) | Positive Rate |
|-----------|---------------------|---------------|
| 2-way match | 63.4 | 25% |
| 3-way match, invoice after GR | 96.5 | 25% |
| 3-way match, invoice before GR | 100.2 | 25% |
| Consignment | 29.9 | 25% |

Overall positive rate: **25.0%** across 251,470 cases.

---

## 2. Features Used

All features come from case-level attributes available at order creation (no event-level
data, no duration — zero leakage).

| Feature | Type | Encoding |
|---------|------|----------|
| `flow_type` | Categorical | Label encode (0–3) |
| `company` | Categorical | Label encode (0–3) |
| `vendor` | High-cardinality categorical | Frequency encode (count of cases per vendor in training set; unseen → 1) |
| `item_type` | Categorical | Label encode (0–5) |
| `document_type` | Categorical | Label encode (0–2) |
| `gr_based_iv` | Boolean | Cast to Int32 |
| `goods_receipt` | Boolean | Cast to Int32 |
| `start_month` | Ordinal (1–12) | As-is |
| `start_quarter` | Ordinal (1–4) | As-is |
| `start_dow` | Ordinal (0–6) | As-is |

**Excluded:** `case_duration_days`, `rework_count`, `compliance_score`, `event_count`,
`sla_risk` — all post-creation features that would constitute data leakage.

**Note on `source_system`:** Only 1 unique value in dataset (`sourceSystemID_0000`) —
no predictive signal, excluded.

---

## 3. Train/Test Split Strategy

### Why stratified random instead of temporal

A temporal split (first 80% of cases chronologically) was initially implemented.
However, the dataset covers a single calendar year (Jan–Dec 2018) with minimal 2019
data (202 cases). A temporal 80/20 split puts Q4 2018 cases in the test set.

**Problem:** Cases starting in October–December 2018 have not had time to complete
their full lifecycle within the dataset observation window (dataset ends Dec 2019,
but cases can span 100–300 days). This causes **right-censoring bias**:

| Quarter | Cases | Median Duration (days) | Positive Rate |
|---------|-------|----------------------|---------------|
| Q1 2018 | 67,211 | 76.0 | 32.4% |
| Q2 2018 | 67,731 | 77.2 | 33.5% |
| Q3 2018 | 59,929 | 72.0 | 28.9% |
| Q4 2018 | 56,599 | 33.5 | **1.8%** |

Q4 cases appear to be fast (~33 days median) because they simply haven't
run long enough to breach P75 yet, not because they are genuinely fast.
This makes Q4 the test set equivalent of looking at a sample where "high-risk
cases haven't shown up yet" — train-test positive rates diverge from 31% vs 2%.

**Solution:** Stratified random split (80/20) using `sklearn.StratifiedShuffleSplit`.
Both folds maintain 25.0% positive rate. This is methodologically sound because
the features used are all pre-creation (no future leakage), so the split direction
doesn't affect feature validity.

**Documented limitation:** In a real deployment, a temporal split aligned with a
longer observation window (e.g., using 2016–2018 to train and 2019 to test) would
be ideal. With this single-year dataset it is not feasible without inducing censoring.

---

## 4. Model

**Algorithm:** LightGBM (`LGBMClassifier`)

**Hyperparameters:**
```python
n_estimators=300,
max_depth=5,
learning_rate=0.05,
num_leaves=31,
scale_pos_weight=3.01,   # neg/pos count in training set
random_state=42,
n_jobs=-1,
```

`scale_pos_weight` handles the 25/75 class imbalance explicitly.

---

## 5. Results

**Test set: 50,294 cases (stratified 20%)**

| Metric | Value |
|--------|-------|
| AUC-ROC | **0.917** |
| PR-AUC | **0.802** |
| Precision (threshold=0.5) | 0.617 |
| Recall (threshold=0.5) | 0.842 |
| F1 (threshold=0.5) | 0.712 |

An AUC-ROC of 0.917 indicates the model strongly separates above- from below-P75
cases. PR-AUC of 0.802 on the 25% positive class is excellent.

**Interpretation:** At the 0.5 threshold, ~84% of true above-P75 cases are flagged
(recall), at 62% precision. For a business use case (early warning), high recall is
more valuable than high precision — missing a slow case is worse than a false alarm.

---

## 6. Feature Importance (Gain)

| Rank | Feature | Gain |
|------|---------|------|
| 1 | `vendor_freq` | 4,038 |
| 2 | `start_month` | 2,439 |
| 3 | `start_dow` | 1,413 |
| 4 | `flow_type_enc` | 416 |
| 5 | `item_type_enc` | 394 |
| 6 | `gr_based_iv` | 85 |
| 7 | `document_type_enc` | 80 |
| 8 | `start_quarter` | 3 |
| 9 | `company_enc` | 1 |
| 10 | `goods_receipt` | 0 |

**Key insight:** Vendor identity (frequency as proxy) is the single strongest predictor —
specific vendors consistently produce long-running cases. Month and day-of-week effects
are also substantial (purchasing patterns vary significantly by calendar timing).
Flow type and item type contribute moderate signal. Company and goods_receipt have
negligible individual importance (though company is partially captured by vendor and
flow_type correlation).

---

## 7. Limitations

1. **No event-level features at prediction time.** Real-time SLA prediction would
   benefit from current activity, elapsed time, resource assigned — but those are only
   available after the case starts executing.

2. **Vendor frequency as proxy for vendor identity.** High-cardinality vendor IDs
   (1,975 unique) are encoded by frequency count in training. This is a reasonable
   approximation but loses granularity for mid-frequency vendors.

3. **Single calendar year.** With only 2018 data, the model may overfit to seasonal
   patterns of that year. A multi-year model would generalize better.

4. **Stratified random vs temporal split.** The random split avoids censoring bias
   but violates strict temporal ordering. In deployment, the model would be trained
   on historical cases and scored on new ones — the temporal gap would exist naturally.

5. **Anonymized dataset.** `company`, `vendor`, `item_type` are opaque IDs; their
   practical meaning (which vendor is systematically slow, which item category delays)
   cannot be decoded from this data alone.

6. **P75 threshold is data-driven, not business-defined.** In a real ERP context,
   the SLA threshold would come from contractual terms (e.g., "payment within 45 days").
   P75 is a reasonable statistical proxy but not a business-validated threshold.

---

## 8. Artifacts

| File | Description |
|------|-------------|
| `models/sla_risk_lgbm.pkl` | Pickled dict: model, vendor_freq_map, feature_names, metrics, feature_importance |
| `data/gold/fact_sla_risk.parquet` | 251,470 rows: case_id, flow_type, sla_risk (actual), sla_risk_score, sla_risk_predicted, in_test_set |
| `frontend/public/data/sla_risk.json` | Model metrics + feature importance + top 100 at-risk cases |

---

*Generated: 2026-04-01*
