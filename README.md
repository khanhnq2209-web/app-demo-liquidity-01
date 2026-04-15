# GELEX — Group Relationship & Liquidity Intelligence (Demo)

Interactive Streamlit demo covering ownership structure, liquidity, external AR concentration, and intercompany exposure for the GELEX group.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.mock_data.generate        # produces CSVs in data/
streamlit run Home.py
```

## Structure

- `Home.py` — landing + sidebar global filters + alerts + data-quality panel
- `pages/1_Overview.py` — KPI cards, company ranking (aggrid), cash treemap, AR stacked bar, trend
- `pages/2_Relationships.py` — ownership tree / IC network with networkx analytics
- `pages/3_Exposure_AR.py` — AR heatmap (entities × client groups), Top1 / Top5 / HHI
- `pages/4_Intercompany.py` — **Sankey / Network / yFiles Supply-Chain** (A/B switcher) + pair table
- `pages/5_Credit.py` — utilization table + bar with >85% highlighted

## Tech

Streamlit · pandas · streamlit-echarts · pyecharts · streamlit-aggrid · networkx · yfiles-jupyter-graphs (with SVG fallback).

## Data model

See `requirement_technical_01.md`. CSV schemas are produced by `src/mock_data/generate.py`.
Cash-flow classification (OPERATING / INVESTING / FINANCING, stable/volatile, internal/external) is in `dim_cashflow_item.csv` + `fact_cash_flow.csv`.

## Cross-filter

All pages read from `st.session_state`. Selecting a sub-holding / entity / client group in the sidebar scopes every page. Selecting a row in the Overview ranking table also sets the global selection.
