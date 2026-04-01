# Data Dictionary — ERP Process Intelligence Platform

**Dataset:** BPI Challenge 2019 — Procure-to-Pay Event Log
**Source:** XES file inspected and parsed during Phase 1 (2026-03-31)
**All attribute names below are verified from actual XES file content.**

---

## Bronze Layer

### bronze_events.parquet
One row per event (1,595,923 rows).

| Column | Type | pm4py Source Column | Description |
|--------|------|---------------------|-------------|
| `case_id` | String | `case:concept:name` | Unique case identifier. Format: `{PurchasingDocument}_{Item}` e.g. `2000000000_00001` |
| `activity` | String | `concept:name` | Activity name. 42 unique values. See Activity Reference below. |
| `timestamp` | Datetime(UTC) | `time:timestamp` | Event timestamp in UTC. Range: 2018-01-01 to 2019-12-31 (86 anomalous events in 1948 kept) |
| `resource` | String | `org:resource` | Resource identifier. Patterns: `batch_XX` (batch), `user_XXX` (human), `NONE` (vendor) |
| `user` | String | `User` | Duplicate of org:resource in this dataset. Kept for raw fidelity. |
| `event_value` | Float64 | `Cumulative net worth (EUR)` | Anonymized monetary value of the PO line item at event time. Linearly translated from EUR (preserves 0). |

**Notes:**
- `resource = "NONE"`: 399,090 events (25.0%). Occurs on vendor-initiated activities ("Vendor creates invoice", "Vendor creates debit memo").
- `event_value = 0`: Occurs on terminal activities (closures, deletions).
- No null values in any column.

---

### bronze_cases.parquet
One row per case/trace (251,734 rows).

| Column | Type | pm4py Source Column | Description |
|--------|------|---------------------|-------------|
| `case_id` | String | `case:concept:name` | Unique case identifier. Same format as events. |
| `purchasing_document` | String | `case:Purchasing Document` | SAP purchasing document number (anonymized). |
| `item` | String | `case:Item` | Line item number within the document (e.g. `00001`, `00002`). |
| `item_type` | String | `case:Item Type` | Item classification. Values: `Standard`, `Service`, `Limit`, `Blanket PO`, `Subcontracting`, `Third-party`. |
| `gr_based_iv` | Boolean | `case:GR-Based Inv. Verif.` | True = invoice verification is GR-based. Key flag for flow type classification. |
| `goods_receipt` | Boolean | `case:Goods Receipt` | True = goods receipt is required for this item. |
| `source_system` | String | `case:Source` | Source ERP system identifier (anonymized, e.g. `sourceSystemID_0000`). |
| `doc_category_name` | String | `case:Purch. Doc. Category name` | Document category. Values: `Purchase order`, `Outline agreement`, `Purchase requisition`. |
| `company` | String | `case:Company` | Subsidiary company identifier (anonymized, e.g. `companyID_0000`). |
| `spend_classification` | String | `case:Spend classification text` | Spend classification. Values: `NPR` (non-production), `PR` (production). |
| `spend_area` | String | `case:Spend area text` | Spend area (e.g. `Raw Materials`, `Marketing`, `CAPEX & SOCS`). |
| `sub_spend_area` | String | `case:Sub spend area text` | Sub-area within spend area (e.g. `Facility Management`, `Chemicals`). |
| `vendor` | String | `case:Vendor` | Vendor identifier (anonymized, e.g. `vendorID_0000`). |
| `vendor_name` | String | `case:Name` | Vendor display name (anonymized, e.g. `vendor_0000`). |
| `document_type` | String | `case:Document Type` | SAP document type (e.g. `EC Purchase order`, `FO`). |
| `item_category` | String | `case:Item Category` | P2P flow type. One of four values — see Flow Types below. |

**Notes:**
- `doc_category_name` in XES is `Purch. Doc. Category name` (not `Doc. Category name` as assumed pre-inspection).
- No null values in any column.

---

## Flow Type Classification

The `item_category` column determines the P2P process flow:

| item_category value | flow_type (silver) | Cases | % | Description |
|---------------------|-------------------|-------|---|-------------|
| `3-way match, invoice before GR` | `3way_invoice_before_gr` | 221,010 | 87.8% | Invoice arrives before goods; blocked until GR received |
| `3-way match, invoice after GR` | `3way_invoice_after_gr` | 15,182 | 6.0% | Standard: GR must precede invoice |
| `Consignment` | `consignment` | 14,498 | 5.8% | No PO-level invoices; GR-only tracking |
| `2-way match` | `2way` | 1,044 | 0.4% | No GR required; invoice matched against PO value |

> **Surprise:** The dominant flow (87.8%) is `3-way match, invoice before GR`, not the "standard" after-GR variant. This means most invoices arrive before goods are received and must be blocked pending GR.

---

## Activity Reference (all 42 activities)

Ordered by frequency. Stage assignments are provisional pending Phase 3 mapping validation.

| Rank | Activity | Count | % | Provisional Stage |
|------|----------|-------|---|------------------|
| 1 | Record Goods Receipt | 314,097 | 19.7% | S4 |
| 2 | Create Purchase Order Item | 251,734 | 15.8% | S1 |
| 3 | Record Invoice Receipt | 228,760 | 14.3% | S5 |
| 4 | Vendor creates invoice | 219,919 | 13.8% | S3 |
| 5 | Clear Invoice | 194,393 | 12.2% | S7 |
| 6 | Record Service Entry Sheet | 164,975 | 10.3% | S4 |
| 7 | Remove Payment Block | 57,136 | 3.6% | S6 |
| 8 | Create Purchase Requisition Item | 46,592 | 2.9% | S1 |
| 9 | Receive Order Confirmation | 32,065 | 2.0% | S3 |
| 10 | Change Quantity | 21,449 | 1.3% | S8 |
| 11 | Change Price | 12,423 | 0.8% | S8 |
| 12 | Delete Purchase Order Item | 8,875 | 0.6% | S8 |
| 13 | Change Approval for Purchase Order | 7,541 | 0.5% | S2 |
| 14 | Cancel Invoice Receipt | 7,096 | 0.4% | S8 |
| 15 | Vendor creates debit memo | 6,255 | 0.4% | S3 |
| 16 | Change Delivery Indicator | 3,289 | 0.2% | S8 |
| 17 | Cancel Goods Receipt | 3,096 | 0.2% | S8 |
| 18 | SRM: In Transfer to Execution Syst. | 1,765 | 0.1% | S1 |
| 19 | SRM: Complete | 1,628 | 0.1% | S1 |
| 20 | SRM: Awaiting Approval | 1,628 | 0.1% | S2 |
| 21 | SRM: Ordered | 1,628 | 0.1% | S1 |
| 22 | SRM: Document Completed | 1,628 | 0.1% | S1 |
| 23 | SRM: Created | 1,628 | 0.1% | S1 |
| 24 | Release Purchase Order | 1,610 | 0.1% | S2 |
| 25 | SRM: Change was Transmitted | 1,440 | 0.1% | S1 |
| 26 | Reactivate Purchase Order Item | 543 | 0.0% | S8 |
| 27 | Block Purchase Order Item | 514 | 0.0% | S8 |
| 28 | Cancel Subsequent Invoice | 491 | 0.0% | S8 |
| 29 | Release Purchase Requisition | 467 | 0.0% | S2 |
| 30 | Change Storage Location | 415 | 0.0% | S8 |
| 31 | Update Order Confirmation | 244 | 0.0% | S3 |
| 32 | SRM: Deleted | 188 | 0.0% | S8 |
| 33 | Record Subsequent Invoice | 167 | 0.0% | S5 |
| 34 | Set Payment Block | 124 | 0.0% | S6 |
| 35 | SRM: Transfer Failed (E.Sys.) | 45 | 0.0% | S1 |
| 36 | Change Currency | 35 | 0.0% | S8 |
| 37 | Change Final Invoice Indicator | 11 | 0.0% | S8 |
| 38 | SRM: Transaction Completed | 8 | 0.0% | S9 |
| 39 | Change payment term | 7 | 0.0% | S8 |
| 40 | SRM: Incomplete | 6 | 0.0% | S1 |
| 41 | SRM: Held | 6 | 0.0% | S1 |
| 42 | Change Rejection Indicator | 2 | 0.0% | S8 |

**SRM activities** (ranks 18-25, 32, 35, 38, 40-41): SRM = Supplier Relationship Management system. These activities are from a secondary system and only appear for a small subset of cases (~1,628 cases have SRM events).

---

## Resource Classification

Resources are classified in the silver layer based on naming patterns confirmed from XES.

| Pattern | resource_type | Example | Count | % of events |
|---------|--------------|---------|-------|-------------|
| `batch_XX` | `"batch"` | `batch_00`, `batch_06` | ~254,000 | ~15.9% |
| `user_XXX` | `"human"` | `user_002`, `user_029` | ~942,000 | ~59.0% |
| `"NONE"` | `"unknown"` | `NONE` | 399,090 | 25.0% |

- **14 batch users** identified: `batch_00` through `batch_13`
- **~600+ human users** identified
- `NONE` resources are vendor-initiated actions (not ERP users)

---

## Data Quality Notes

1. **Timestamp anomalies:** 86 events have timestamps of `1948-01-26 22:59:00 UTC`. All are `Vendor creates invoice` (68) or `Vendor creates debit memo` (18). This is a known ERP data quality issue (placeholder date). Kept in bronze, flagged in silver.

2. **Event values:** All non-null (0.0 to 28,994,530 EUR). Zero values are valid (e.g. delete/close events). No negative values except for cancellation events.

3. **No `eventID` attribute:** The XES global event scope defines no eventID. pm4py doesn't expose one either. Removed from schema (was TBD in Phase 0 design).

4. **No `lifecycle:transition` attribute:** Not present in this dataset. Removed from schema.

5. **`user` column = `org:resource`:** The `User` XES attribute is identical to `org:resource` in all rows. Kept in bronze for raw fidelity; can be dropped in silver.

---

## Silver Layer Schema (Reference)

> Full silver layer built in Phase 2. This section previews the enrichment plan.

### silver_events.parquet (1,595,923 rows + enrichment columns)
All bronze_events columns plus:
- `resource_type` — "batch" / "human" / "unknown"
- `timestamp_utc` — timestamp normalized to UTC (already UTC from pm4py)
- `date`, `hour`, `day_of_week`, `is_weekend`, `is_business_hours`
- `event_order` — sequential position within case (1-indexed)
- `time_since_prev_event` — duration since previous event in same case

### silver_cases.parquet (251,734 rows + enrichment columns)
All bronze_cases columns plus:
- `flow_type` — mapped from item_category
- `case_start`, `case_end`, `case_duration_days`
- `event_count`, `activity_count`, `resource_count`
- `has_batch_activity`, `variant_id`
