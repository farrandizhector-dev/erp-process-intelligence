# Bronze Layer Profiling Report

**Dataset:** BPI Challenge 2019 — Procure-to-Pay Event Log
**Generated:** 2026-03-31

---

## Summary

| Metric | Value |
|--------|-------|
| Total events | 1,595,923 |
| Total cases | 251,734 |
| Unique activities | 42 |
| Events file size | 8.3 MB |
| Cases file size | 1.3 MB |

## Timestamp Range

| Metric | Value |
|--------|-------|
| Earliest timestamp (raw) | 1948-01-26 22:59:00+00:00 |
| Latest timestamp (raw) | 2020-04-09 21:59:00+00:00 |
| Earliest timestamp (≥2015) | 2015-03-08 22:59:00+00:00 |
| Latest timestamp (≥2015) | 2020-04-09 21:59:00+00:00 |
| Events with anomalous timestamps (<2015) | 86 |

> **Note:** 86 events have timestamps in 1948, all attributed to 'Vendor creates invoice'
> or 'Vendor creates debit memo'. These are likely ERP placeholder dates and will be
> handled in the silver layer (kept but flagged as anomalous).

## bronze_events Schema

| Column | Type | Null count | Null % |
|--------|------|-----------|--------|
| case_id | String | 0 | 0.00% |
| activity | String | 0 | 0.00% |
| timestamp | Datetime(time_unit='ns', time_zone='UTC') | 0 | 0.00% |
| resource | String | 0 | 0.00% |
| user | String | 0 | 0.00% |
| event_value | Float64 | 0 | 0.00% |

## bronze_cases Schema

| Column | Type | Null count | Null % |
|--------|------|-----------|--------|
| case_id | String | 0 | 0.00% |
| purchasing_document | String | 0 | 0.00% |
| item | String | 0 | 0.00% |
| item_type | String | 0 | 0.00% |
| gr_based_iv | Boolean | 0 | 0.00% |
| goods_receipt | Boolean | 0 | 0.00% |
| source_system | String | 0 | 0.00% |
| doc_category_name | String | 0 | 0.00% |
| company | String | 0 | 0.00% |
| spend_classification | String | 0 | 0.00% |
| spend_area | String | 0 | 0.00% |
| sub_spend_area | String | 0 | 0.00% |
| vendor | String | 0 | 0.00% |
| vendor_name | String | 0 | 0.00% |
| document_type | String | 0 | 0.00% |
| item_category | String | 0 | 0.00% |

## Activity Frequencies (all 42 activities)

| Rank | Activity | Count | % of events |
|------|----------|-------|-------------|
| 1 | Record Goods Receipt | 314,097 | 19.68% |
| 2 | Create Purchase Order Item | 251,734 | 15.77% |
| 3 | Record Invoice Receipt | 228,760 | 14.33% |
| 4 | Vendor creates invoice | 219,919 | 13.78% |
| 5 | Clear Invoice | 194,393 | 12.18% |
| 6 | Record Service Entry Sheet | 164,975 | 10.34% |
| 7 | Remove Payment Block | 57,136 | 3.58% |
| 8 | Create Purchase Requisition Item | 46,592 | 2.92% |
| 9 | Receive Order Confirmation | 32,065 | 2.01% |
| 10 | Change Quantity | 21,449 | 1.34% |
| 11 | Change Price | 12,423 | 0.78% |
| 12 | Delete Purchase Order Item | 8,875 | 0.56% |
| 13 | Change Approval for Purchase Order | 7,541 | 0.47% |
| 14 | Cancel Invoice Receipt | 7,096 | 0.44% |
| 15 | Vendor creates debit memo | 6,255 | 0.39% |
| 16 | Change Delivery Indicator | 3,289 | 0.21% |
| 17 | Cancel Goods Receipt | 3,096 | 0.19% |
| 18 | SRM: In Transfer to Execution Syst. | 1,765 | 0.11% |
| 19 | SRM: Complete | 1,628 | 0.10% |
| 20 | SRM: Created | 1,628 | 0.10% |
| 21 | SRM: Document Completed | 1,628 | 0.10% |
| 22 | SRM: Ordered | 1,628 | 0.10% |
| 23 | SRM: Awaiting Approval | 1,628 | 0.10% |
| 24 | Release Purchase Order | 1,610 | 0.10% |
| 25 | SRM: Change was Transmitted | 1,440 | 0.09% |
| 26 | Reactivate Purchase Order Item | 543 | 0.03% |
| 27 | Block Purchase Order Item | 514 | 0.03% |
| 28 | Cancel Subsequent Invoice | 491 | 0.03% |
| 29 | Release Purchase Requisition | 467 | 0.03% |
| 30 | Change Storage Location | 415 | 0.03% |
| 31 | Update Order Confirmation | 244 | 0.02% |
| 32 | SRM: Deleted | 188 | 0.01% |
| 33 | Record Subsequent Invoice | 167 | 0.01% |
| 34 | Set Payment Block | 124 | 0.01% |
| 35 | SRM: Transfer Failed (E.Sys.) | 45 | 0.00% |
| 36 | Change Currency | 35 | 0.00% |
| 37 | Change Final Invoice Indicator | 11 | 0.00% |
| 38 | SRM: Transaction Completed | 8 | 0.00% |
| 39 | Change payment term | 7 | 0.00% |
| 40 | SRM: Held | 6 | 0.00% |
| 41 | SRM: Incomplete | 6 | 0.00% |
| 42 | Change Rejection Indicator | 2 | 0.00% |

## Resource Distribution

| Resource Type | Events | % |
|---------------|--------|---|
| Batch (batch_XX) | 156,187 | 9.8% |
| Human (user_XXX) | 1,040,646 | 65.2% |
| NONE (vendor) | 399,090 | 25.0% |
| **Total unique resources** | **628** | — |

Top 20 resources by event count:

| Resource | Events | Type |
|----------|--------|------|
| NONE | 399,090 | unknown |
| user_002 | 166,353 | human |
| user_029 | 71,539 | human |
| user_020 | 39,770 | human |
| batch_06 | 38,100 | batch |
| user_013 | 35,069 | human |
| user_001 | 34,563 | human |
| user_012 | 32,707 | human |
| user_019 | 29,764 | human |
| user_235 | 28,336 | human |
| user_015 | 27,941 | human |
| batch_00 | 27,934 | batch |
| batch_02 | 27,933 | batch |
| user_006 | 17,636 | human |
| user_040 | 17,627 | human |
| batch_03 | 17,384 | batch |
| user_057 | 16,089 | human |
| batch_07 | 15,189 | batch |
| user_036 | 14,745 | human |
| user_005 | 14,672 | human |

## Item Category Distribution (cases)

| Item Category | Cases | % |
|---------------|-------|---|
| 3-way match, invoice before GR | 221,010 | 87.8% |
| 3-way match, invoice after GR | 15,182 | 6.0% |
| Consignment | 14,498 | 5.8% |
| 2-way match | 1,044 | 0.4% |

## Case Length Distribution (events per case)

| Metric | Value |
|--------|-------|
| Min | 1 |
| Median | 5.0 |
| Mean | 6.3 |
| P90 | 7 |
| P99 | 24 |
| Max | 990 |

## Event Value (Cumulative net worth EUR) Statistics

| Metric | Value |
|--------|-------|
| Min | 0.00 |
| Max | 28,994,530.00 |
| Mean | 17,888.97 |
| Median | 536.00 |
| % zero | 2.5% |
| % non-zero | 97.5% |
| Null count | 0 |

> **Note:** Values are linearly translated from original EUR amounts (preserves 0 and
> additive properties). Represents cumulative net worth of the purchase order line item
> at the time of the event.

## Company Distribution (top 20)

| Company | Cases | % |
|---------|-------|---|
| companyID_0000 | 250,686 | 99.6% |
| companyID_0003 | 1,044 | 0.4% |
| companyID_0002 | 2 | 0.0% |
| companyID_0001 | 2 | 0.0% |

## Quality Gate Summary

| Gate | Expected | Actual | Pass? |
|------|----------|--------|-------|
| Event count | ~1,595,923 ±1% | 1,595,923 | ✅ |
| Case count | ~251,734 ±1% | 251,734 | ✅ |
| Activity count | ≥42 | 42 | ✅ |
| Null case_id in events | 0 | 0 | ✅ |
| Null activity | 0 | 0 | ✅ |
| Null timestamp | <0.1% | 0 | ✅ |
