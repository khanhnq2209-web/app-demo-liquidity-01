"""AR concentration heatmap."""
from __future__ import annotations

import pandas as pd


def ar_heatmap(df: pd.DataFrame, top_k: int = 5) -> dict:
    """df columns: entity_name, client_group_name, external_ar_eom."""
    totals = df.groupby("client_group_name")["external_ar_eom"].sum().sort_values(ascending=False)
    top = list(totals.head(top_k).index)
    df = df.assign(cg=df["client_group_name"].where(df["client_group_name"].isin(top), "Others"))
    pivot = df.pivot_table(index="entity_name", columns="cg",
                           values="external_ar_eom", aggfunc="sum", fill_value=0)
    rows = pivot.index.tolist()
    cols = pivot.columns.tolist()
    data = []
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            data.append({"value": [j, i, float(pivot.iloc[i, j])], "name": f"{rows[i]}||{cols[j]}"})
    max_val = float(pivot.values.max()) if pivot.size else 1.0
    return {
        "tooltip": {"position": "top"},
        "grid": {"height": "70%", "top": "10%", "left": 120, "right": 80},
        "xAxis": {"type": "category", "data": cols, "splitArea": {"show": True}},
        "yAxis": {"type": "category", "data": rows, "splitArea": {"show": True}},
        "visualMap": {"min": 0, "max": max_val, "calculable": True,
                       "orient": "horizontal", "left": "center", "bottom": 0},
        "series": [{
            "name": "AR",
            "type": "heatmap",
            "data": data,
            "label": {"show": False},
            "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"}},
        }],
    }


def cash_heatmap(df: pd.DataFrame, name_map: dict[str, str]) -> dict:
    """1D Heatmap for cash by entity."""
    if df.empty: return {}
    df_sorted = df.sort_values("cash_eom", ascending=False)
    entities = [(name_map.get(e, e).split(" · ")[0] if len(name_map.get(e, e)) > 15 else name_map.get(e, e)) for e in df_sorted["entity_id"]]
    vals = df_sorted["cash_eom"].tolist()
    
    data = []
    for i, val in enumerate(vals):
        data.append({"value": [i, 0, float(val)], "name": entities[i]})
        
    max_val = float(max(vals)) if vals else 1.0
    return {
        "tooltip": {"position": "top", "formatter": "{b}<br/>Cash: {c}"},
        "grid": {"height": "50%", "top": "10%", "left": 60, "right": 20},
        "xAxis": {"type": "category", "data": entities, "splitArea": {"show": True}, "axisLabel": {"rotate": 30, "interval": 0, "fontSize": 10}},
        "yAxis": {"type": "category", "data": ["Tiền mặt"], "splitArea": {"show": True}},
        "visualMap": {"min": 0, "max": max_val, "calculable": True, "orient": "horizontal", "left": "center", "bottom": 0},
        "series": [{
            "name": "Cash",
            "type": "heatmap",
            "data": data,
            "label": {"show": False},
            "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"}},
        }],
    }
