# Group Relationship & Liquidity Intelligence Platform (Demo)
## Detailed Requirement Specification (MVP - Streamlit)

---

## 1. Purpose

This application provides a **group-level visibility platform** for a holding company to:

- Understand **ownership structure**
- Monitor **cash distribution (liquidity)**
- Analyze **external Accounts Receivable (AR) concentration**
- Track **intercompany exposures (AR/AP + loans)**
- Enable **drill-down from Holding → Sub-holding → Company**

This is a **monitoring and insight tool (Stage 1–2)**, NOT a full optimization or forecasting system.

---

## 2. Key Design Principles

- Monthly data input (CSV-based)
- Quarterly view derived dynamically
- Entity-centric (all data tied to entity_id)
- Pair-level relationships (for intercompany)
- Simple but scalable data model
- Focus on **clarity over complexity**

---

## 3. Time Handling

### 3.1 Input Data
- All data is **monthly snapshot (EOM)**

### 3.2 Quarterly View Logic
- **Stock data** (cash, AR, IC balances, loans, credit):
  - Use **quarter-end snapshot only**
- **Flow data** (transactions):
  - Aggregate using **SUM over months**

---

## 4. Data Model

### 4.1 Entity Dimension

#### File: `dim_entity.csv`

| Column | Type | Description |
|------|------|------------|
| entity_id | string | Unique ID |
| entity_name | string | Display name |
| entity_type | enum | HOLDING / SUBHOLDING / COMPANY |
| parent_entity_id | string | Parent in hierarchy |
| subholding_code | enum | A / B |
| industry | string | Optional |
| currency_code | string | Default currency |

---

### 4.2 Period Dimension

#### File: `dim_period.csv`

| Column | Description |
|------|------------|
| period_end | YYYY-MM-DD |
| year | YYYY |
| month | MM |
| year_month | YYYY-MM |
| quarter | YYYYQX |
| is_quarter_end | 0 or 1 |

---

### 4.3 Client Group Dimension

#### File: `dim_client_group.csv`

| Column | Description |
|------|------------|
| client_group_id | Unique ID |
| client_group_name | e.g., EVN |
| industry_group | Optional |
| is_other | 0/1 |

---

## 5. Relationship Data

### 5.1 Ownership

#### File: `rel_ownership.csv`

| Column | Description |
|------|------------|
| parent_entity_id | Parent |
| child_entity_id | Child |
| ownership_pct | 0–100 |
| effective_from | optional |
| effective_to | optional |

---

## 6. Fact Tables (Monthly Snapshot)

---

### 6.1 Cash

#### File: `fact_cash_balance.csv`

| Column | Description |
|------|------------|
| period_end | Date |
| entity_id | Entity |
| cash_eom | Cash balance |

---

### 6.2 External AR

#### File: `fact_external_ar_by_client_group.csv`

| Column | Description |
|------|------------|
| period_end | Date |
| entity_id | Entity |
| client_group_id | Client group |
| external_ar_eom | Amount |

---

### 6.3 Intercompany AR/AP

#### File: `fact_ic_arap.csv`

| Column | Description |
|------|------------|
| period_end | Date |
| from_entity_id | From |
| to_entity_id | To |
| ic_type | IC_AR / IC_AP |
| amount_eom | Amount |

---

### 6.4 Intercompany Loans

#### File: `fact_ic_loan.csv`

| Column | Description |
|------|------------|
| period_end | Date |
| lender_entity_id | Lender |
| borrower_entity_id | Borrower |
| outstanding_eom | Amount |

---

### 6.5 Credit Summary (Optional)

#### File: `fact_credit_summary.csv`

| Column | Description |
|------|------------|
| period_end | Date |
| entity_id | Entity |
| credit_limit | Limit |
| credit_utilized | Used |

---

### 6.6 Cash Flow (Optional)

#### File: `fact_cash_flow.csv`

| Column | Description |
|------|------------|
| period_end | Date |
| from_node_type | ENTITY / CLIENT_GROUP |
| from_node_id | Source |
| to_node_type | ENTITY / CLIENT_GROUP |
| to_node_id | Destination |
| flow_amount | Amount |

---

## 7. KPI Definitions

### 7.1 Liquidity

- Cash (EOM)
- MoM Change:
  ΔCash = Cash_t - Cash_t-1
- Cash Share:
  Cash / Total Group Cash

---

### 7.2 External AR

- Total External AR
- Top 1 Share
- Top 5 Share
- HHI:

HHI = SUM(s_i^2)

---

### 7.3 Intercompany

- IC AR Total
- IC AP Total
- Net IC:

Net IC = IC_AR - IC_AP

- IC Loans Total

---

### 7.4 Credit

- Utilization %:

Utilization = Used / Limit

- Headroom:

Headroom = Limit - Used

---

## 8. UI Architecture

### Sidebar Controls

- Period selector (Month / Quarter)
- Level selector:
  - Holding
  - Sub-holding
  - Company
- Filters:
  - Sub-holding (A/B)
  - Company
  - Client group

---

## 9. Pages

---

### 9.1 Overview Page

#### KPI Cards
- Cash
- External AR
- IC AR
- IC Loans
- Top 1 Share
- HHI
- Credit Utilization

#### Table
- Company ranking
- Columns:
  - Cash
  - AR
  - Top client share
  - IC exposure
  - Flags

#### Charts
- Cash distribution:
  - Bar OR Treemap
- AR concentration:
  - Heatmap OR Stacked Bar
- Trend:
  - Cash + AR (12 months)

---

### 9.2 Relationships Page

#### Views
- Ownership Tree (default)
- Network Graph (toggle)

#### Options
- Show IC AR/AP links
- Show IC Loan links
- Top N edges filter

---

### 9.3 Exposure Page (AR)

#### Main
- Heatmap:
  - Rows: Companies
  - Columns: Client Groups
  - Values: AR

#### Logic
- Show Top 5 client groups
- Aggregate rest into "Others"

#### KPIs
- Top 1 Share
- Top 5 Share
- HHI

---

### 9.4 Intercompany Page

#### Summary
- IC AR
- IC AP
- IC Loans

#### Table
- Pair-level exposure
- Columns:
  - From
  - To
  - Type
  - Amount

#### Charts
- Sankey (default)
- Network (toggle)

---

### 9.5 Credit Page (Optional)

- Table:
  - Limit
  - Used
  - Headroom
  - Utilization %

- Flag:
  - Utilization > 85%

---

## 10. Drill-down Behavior

- Holding → Sub-holding → Company
- Clicking entity filters entire dashboard
- Company page shows:
  - KPIs
  - Top clients
  - Top IC counterparties
  - Mini network graph

---

## 11. Alerts

- Cash declining 3 months
- High concentration (Top1 > threshold)
- High utilization (>85%)
- IC exposure spike

---

## 12. Data Validation Rules

- Entity must exist in dim_entity
- No self IC transactions
- Ownership between 0–100%
- AR >= 0
- Missing data flagged

---

## 13. Visualization Options (A/B Testing)

| Area | Option A | Option B |
|------|--------|--------|
| Ownership | Tree | Network |
| Flow | Sankey | Network |
| Liquidity | Quadrant | Heatmap |
| Concentration | Heatmap | Stacked Bar |

---

## 14. Technical Stack

- Streamlit (UI)
- Pandas (data processing)
- Plotly (charts)
- NetworkX / PyVis (graphs)

---

## 15. Success Criteria

The system should allow users to:

- Identify cash distribution
- Detect AR concentration risk
- Understand intercompany exposures
- Navigate group structure
- Drill down to company level

Time to insight: **< 5 minutes**

---

## 16. Future Enhancements

- Cash pooling simulation
- Netting engine
- Forecasting
- Optimization recommendations

---