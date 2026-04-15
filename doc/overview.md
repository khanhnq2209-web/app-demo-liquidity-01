# Group Relationship & Liquidity Intelligence Platform  
## Business Questions & KPI Framework

---

## 1. Purpose

This document defines the **key business questions** and **performance indicators (KPIs)** that the platform must answer.

The objective is to enable management to:
- Understand **group structure and dependencies**
- Monitor **liquidity (cash) distribution**
- Assess **receivables concentration risk**
- Identify **intercompany exposure and funding patterns**

The focus is on **visibility and insight**, not optimization at this stage.

---

## 2. Analytical Framework

The platform is structured around four key lenses:

1. **Ownership & Structure**
2. **Liquidity (Cash)**
3. **External Exposure (Accounts Receivable)**
4. **Intercompany Exposure (AR/AP & Loans)**

Each lens answers a set of business-critical questions.

---

## 3. Ownership & Structure

### Key Business Questions

**Q1. What is the ownership structure of the group?**  
- Who owns whom?
- How are entities organized under Sub-holding A and B?

**Q2. Where are structural complexities or cross-holdings?**  
- Are there circular or non-standard ownership relationships?

**Q3. Which entities are structurally central or influential?**  
- Which companies sit at key positions in the group?

---

### KPIs

- **Ownership % (Direct)**
- **Effective Ownership %** (if applicable)
- **Number of entities per sub-holding**
- **Ownership depth** (levels from holding to entity)
- **Structure complexity indicators**
  - Number of ownership links
  - Presence of cross-holdings

---

## 4. Liquidity (Cash)

### Key Business Questions

**Q4. Where is cash located across the group?**  
- Which sub-holding or companies hold the most cash?

**Q5. Is liquidity evenly distributed or concentrated?**  
- Are there pockets of excess vs shortage?

**Q6. Which entities may face liquidity stress?**  
- Are there companies with consistently low or declining cash?

---

### KPIs

- **Cash Balance (End of Period)**
- **Cash Share of Group**
  
  Cash Share = Entity Cash / Total Group Cash

- **Month-over-Month Change in Cash**
  
  ΔCash = Cash(t) – Cash(t-1)

- **Cash Trend (last 3–12 months)**

---

### Monitoring Signals

- Continuous decline in cash over multiple periods
- High concentration of cash in a few entities

---

## 5. External Exposure (Accounts Receivable)

### Key Business Questions

**Q7. How much external receivables does the group have?**  
- What is the total AR exposure?

**Q8. Which entities carry the largest receivables?**  
- Where is collection risk concentrated?

**Q9. How dependent is the group on key client groups (e.g., EVN)?**  
- Are revenues/receivables overly concentrated?

**Q10. Do multiple companies share the same concentration risk?**  
- Is there group-level exposure to the same client/industry?

---

### KPIs

#### Size & Distribution
- **Total External AR**
- **AR by Company / Sub-holding**

#### Concentration Metrics
- **Top 1 Client Group Share**
  
  Top1 Share = Largest Client AR / Total AR

- **Top 5 Client Groups Share**
  
  Top5 Share = Sum of Top 5 AR / Total AR

- **HHI (Concentration Index)**
  
  HHI = Σ (Client Share²)

#### Group Risk Indicators
- **Number of companies exposed to same key client group**
- **AR concentration by industry**

---

### Monitoring Signals

- High Top 1 or Top 5 concentration
- Increasing dependence on a single client group
- Multiple entities exposed to same risk cluster

---

## 6. Intercompany Exposure

### Key Business Questions

**Q11. How large are intercompany receivables and payables?**  
- What is the level of internal dependency?

**Q12. Which companies are net lenders or borrowers within the group?**  
- Who funds whom?

**Q13. Where are the largest intercompany exposure channels?**  
- Which entity pairs have the highest balances?

---

### KPIs

#### Intercompany AR/AP
- **Total Intercompany Receivables (IC AR)**
- **Total Intercompany Payables (IC AP)**

- **Net Intercompany Position**
  
  Net IC = IC AR – IC AP

#### Intercompany Loans
- **Total IC Loans Outstanding**
- **IC Loans by lender / borrower**

#### Pair-Level Exposure
- **Top intercompany pairs (by amount)**

---

### Monitoring Signals

- Rapid increase in intercompany balances
- High dependency on a small number of counterparties
- Large bilateral exposures

---

## 7. Credit & Funding (Supporting Lens)

### Key Business Questions

**Q14. Which entities are approaching credit limits?**  
- Where is financing pressure building?

**Q15. Is credit capacity efficiently distributed across the group?**

---

### KPIs

- **Credit Limit**
- **Utilized Amount**
- **Headroom**
  
  Headroom = Limit – Utilized

- **Utilization Ratio**
  
  Utilization = Utilized / Limit

---

### Monitoring Signals

- Utilization above threshold (e.g., 85%)
- Low remaining headroom

---

## 8. Integrated Management View

At group or sub-holding level, management should quickly see:

- **Liquidity position (cash)**
- **Exposure level (AR)**
- **Concentration risk (Top clients / HHI)**
- **Internal dependency (IC balances and loans)**

---

## 9. Decision Support Use Cases

The platform should enable:

### 9.1 Liquidity Awareness
- Identify surplus vs constrained entities
- Highlight imbalance in cash distribution

### 9.2 Risk Monitoring
- Detect concentration to key clients
- Identify clustering of exposure across companies

### 9.3 Internal Dependency Insight
- Understand internal funding structure
- Identify major intercompany exposure chains

---

## 10. Limitations (Current Scope)

This framework does NOT yet address:
- Forecasting or forward-looking liquidity
- Optimization (cash pooling, netting)
- Project-level or contract-level risk
- Off-balance sheet exposures

---

## 11. Future Evolution

This KPI framework can be extended to support:

- Liquidity optimization strategies
- Intercompany netting
- Cash pooling simulation
- Early warning alert systems
- Capital allocation decisions

---