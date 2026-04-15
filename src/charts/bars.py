"""Bar / Treemap / Trend line option builders."""
from __future__ import annotations

import pandas as pd


def cash_treemap(df: pd.DataFrame, name_map: dict[str, str]) -> dict:
    data = [
        {"name": name_map.get(r.entity_id, r.entity_id), "value": float(r.cash_eom)}
        for r in df.itertuples()
    ]
    return {
        "tooltip": {"formatter": "{b}: {c}"},
        "series": [{
            "type": "treemap",
            "roam": False,
            "breadcrumb": {"show": False},
            "label": {"show": True, "formatter": "{b}"},
            "data": data,
        }],
    }


def cash_bar(df: pd.DataFrame, name_map: dict[str, str]) -> dict:
    df_sorted = df.sort_values("cash_eom", ascending=False)
    entities = [(name_map.get(e, e).split(" · ")[0] if len(name_map.get(e, e)) > 15 else name_map.get(e, e)) for e in df_sorted["entity_id"]]
    values = [{"value": float(v), "itemStyle": {"color": "#1a73e8"}} for v in df_sorted["cash_eom"]]
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"top": 20, "bottom": 60, "left": 60, "right": 20},
        "xAxis": {"type": "category", "data": entities, "axisLabel": {"rotate": 30, "interval": 0, "fontSize": 10}},
        "yAxis": {"type": "value", "axisLabel": {"formatter": "{value}"}},
        "series": [{"type": "bar", "data": values}]
    }


def ar_stacked_bar(df: pd.DataFrame, top_k: int = 5) -> dict:
    """df: long-form (entity_name, client_group_name, external_ar_eom)."""
    totals = df.groupby("client_group_name")["external_ar_eom"].sum().sort_values(ascending=False)
    top = list(totals.head(top_k).index)
    df = df.assign(cg=df["client_group_name"].where(df["client_group_name"].isin(top), "Others"))
    pivot = df.pivot_table(index="entity_name", columns="cg",
                           values="external_ar_eom", aggfunc="sum", fill_value=0)
    entities = pivot.index.tolist()
    series = []
    for col in pivot.columns:
        series.append({"name": col, "type": "bar", "stack": "ar",
                        "data": [float(v) for v in pivot[col].values]})
    return {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": 0},
        "grid": {"top": 40, "bottom": 60, "left": 60, "right": 20},
        "xAxis": {"type": "category", "data": entities, "axisLabel": {"rotate": 30}},
        "yAxis": {"type": "value"},
        "series": series,
    }


def cash_ar_trend(cash_ts: pd.DataFrame, ar_ts: pd.DataFrame) -> dict:
    dates = sorted(set(cash_ts["period_end"]).union(ar_ts["period_end"]))
    labels = [pd.Timestamp(d).strftime("%Y-%m") for d in dates]
    cash_map = dict(zip(cash_ts["period_end"], cash_ts["cash_eom"]))
    ar_map = dict(zip(ar_ts["period_end"], ar_ts["external_ar_eom"]))
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"data": ["Cash", "AR"], "top": 0},
        "grid": {"top": 40, "bottom": 30, "left": 60, "right": 60},
        "xAxis": {"type": "category", "data": labels},
        "yAxis": [{"type": "value", "name": "Cash"}, {"type": "value", "name": "AR"}],
        "series": [
            {"name": "Cash", "type": "line", "smooth": True,
              "data": [float(cash_map.get(d, 0)) for d in dates]},
            {"name": "AR", "type": "line", "yAxisIndex": 1, "smooth": True,
              "data": [float(ar_map.get(d, 0)) for d in dates]},
        ],
    }


def utilization_bar(df: pd.DataFrame) -> dict:
    df = df.sort_values("utilization", ascending=False)
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"top": 30, "bottom": 60, "left": 60, "right": 20},
        "xAxis": {"type": "category", "data": df["entity_name"].tolist(),
                   "axisLabel": {"rotate": 30}},
        "yAxis": {"type": "value", "max": 1, "axisLabel": {"formatter": "{value}"}},
        "series": [{
            "name": "Utilization",
            "type": "bar",
            "data": [
                {"value": float(u),
                 "itemStyle": {"color": "#d33" if u > 0.85 else "#4c8bf5"}}
                for u in df["utilization"].values
            ],
        }],
    }
