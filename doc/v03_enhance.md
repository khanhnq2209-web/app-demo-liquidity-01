# Group Treasury & Relationship Intelligence Platform  
## FULL IMPLEMENTATION SPEC v3.5 (DEEP + ZERO-GUESS + INTERACTIVE)

---

## 1. SYSTEM OBJECTIVE

Build an interactive Streamlit application that allows users to:

1. Monitor group-level:
   - Cash
   - External AR
   - Intercompany exposure

2. Diagnose:
   - External concentration risk
   - Internal dependency

3. Operate treasury:
   - Liquidity distribution
   - Credit usage
   - Internal funding

4. Project future:
   - 12-month liquidity
   - Funding gaps
   - Scenario simulation

---

## 2. TECH STACK

- Python 3.9+
- Streamlit
- Pandas
- streamlit-echarts (primary visualization)
- NumPy

---

## 3. GLOBAL FILTER MODEL (CRITICAL)

### 3.1 Filter Hierarchy (ALWAYS APPLIED IN ORDER)

1. Period filter  
2. View mode (Monthly / Quarterly)  
3. Entity scope:
   - Holding (ALL)
   - Subholding A
   - Subholding B
   - Specific company  
4. Optional filters:
   - Client group  
   - Intercompany pair  

---

### 3.2 Session State Variables

selected_period  
view_mode  

selected_level  
selected_entity_id  
selected_subholding  

selected_client_group  
selected_pair  

scenario_type  
chart_variant  

---

### 3.3 Filter Application Logic (MANDATORY)

All datasets MUST pass through:

```
def apply_filters(df):
    df = filter_by_period(df)
    df = filter_by_entity_scope(df)

    if selected_client_group:
        df = df[df.client_group_id == selected_client_group]

    if selected_pair:
        df = df[
            (df.from_entity_id == selected_pair[0]) &
            (df.to_entity_id == selected_pair[1])
        ]

    return df
```

---

## 4. DATA PREPARATION RULES

### 4.1 Top 5 Client Logic

```
grouped = df.groupby("client_group_id").sum()

top5 = grouped.sort_values(desc).head(5)
others = grouped.sum() - top5.sum()
```

Output MUST include:
- Top 5
- Others

---

### 4.2 Entity Aggregation

Holding → sum all entities  
Subholding → filter by A/B then sum  
Company → single entity  

---

## 5. KPI ENGINE (EXACT)

### 5.1 Liquidity

```
total_cash = sum(cash_eom)
cash_share = entity_cash / total_cash
mom_change = current_cash - previous_cash
```

---

### 5.2 External AR

```
total_ar = sum(external_ar)

top1_share = max(client_ar) / total_ar
top5_share = sum(top5_clients) / total_ar

hhi = sum((client_ar / total_ar)^2)
```

---

### 5.3 Intercompany

```
ic_ar = sum(IC_AR)
ic_ap = sum(IC_AP)

net_ic = ic_ar - ic_ap

ic_loans = sum(loans)
```

---

## 6. TAB 2: EXECUTIVE SUMMARY

---

### 6.1 KPI Cards

Source: aggregated data at selected level  

---

### 6.2 Liquidity Distribution Chart

Input:
- cash grouped by entity  

Filter:
- respect entity scope  

A/B Test:

A → Bar chart  
- X: entity  
- Y: cash  

B → Treemap  
- hierarchy: holding → subholding → company  
- value: cash  

Interaction:
- click entity → update selected_entity_id  

---

### 6.3 Risk Position Chart

Input per entity:
- X: cash  
- Y: external AR  
- Size: IC exposure  

A/B Test:

A → Quadrant  
- split by median  

B → Bubble  

Interaction:
- click → select entity  

---

## 7. TAB 3: RISK & EXPOSURE

---

### 7.1 External Risk

Input:
- AR grouped by entity + client  

Filter:
- entity scope  
- optional client filter  

A/B Test:

A → Heatmap  
- X: client group  
- Y: entity  
- value: AR  

B → Stacked Bar  
- X: entity  
- stack: client group  

Interaction:
- click cell → set selected_entity_id + selected_client_group  

---

### 7.2 Internal Exposure

Input:
- IC data (from, to, amount)  

Filter:
- entity scope  
- top 20 edges  

A/B Test:

A → Network Graph  
- node size: exposure  
- edge width: amount  

B → Sankey  
- source: from  
- target: to  

Interaction:
- click edge → set selected_pair  

---

## 8. TAB 4: TREASURY & CASH INTELLIGENCE

---

### 8.1 Liquidity

Input:
- cash by entity  

A/B Test:
- Bar  
- Heatmap  

---

### 8.2 Credit

Table:
- entity  
- limit  
- used  
- utilization  

---

### 8.3 FORWARD LIQUIDITY PLAN

---

#### Inputs (UI)

collection_days (30–180)  
operating_ratio (0–20%)  
ic_repayment_rate (0–20%)  

---

#### Calculation Loop

```
for month in range(12):

    ar_collection = ar / collection_days * 30
    
    operating = ar * operating_ratio
    
    cash_next = (
        cash
        + ar_collection
        - operating
    )
    
    store(cash_next)
    
    cash = cash_next
```

---

#### Outputs

- 12-month cash series  
- runway  
- funding gap  

---

#### Chart

A/B Test:

A → Multi-line (top entities)  
B → Aggregated + selected entity  

Interaction:
- select entity → highlight  

---

#### KPI

```
runway = first month cash < 0
funding_gap = min(cash)
```

---

### 8.4 Simulation (Internal Bank)

Inputs:
- lender  
- borrower  
- amount  

Calculation:

```
interest_saved =
(external_rate - internal_rate) * amount
```

---

## 9. INTERACTION RULES

Click entity → filter all  
Click client → filter exposure  
Click IC link → filter pair  

Reset button → clear all  

Selected items must be highlighted  

---

## 10. ECHART CONFIG RULES

Graph:
- type: graph  
- layout: force  
- roam: true  

Sankey:
- curved links  

Heatmap:
- dynamic scale  

---

## 11. PERFORMANCE RULES

- cache all data  
- limit edges ≤ 20  
- limit entities ≤ 15  

---

## 12. SUCCESS CRITERIA

User can:
- detect liquidity imbalance  
- detect concentration risk  
- understand IC exposure  
- see future risk  
- simulate funding  

Time to insight < 5 minutes  

---

## 13. DESIGN PRINCIPLE

Every chart must answer:

So what?