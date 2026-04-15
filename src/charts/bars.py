"""Bar / Treemap / Trend line option builders."""
from __future__ import annotations

import pandas as pd

_TOOLBOX = {
    "show": True, "right": "2%", "top": "1%",
    "feature": {"restore": {"title": "Reset"}, "saveAsImage": {"title": "Save"}},
}
_DATAZOOM = [{"type": "inside"}, {"type": "slider", "height": 16, "bottom": 4}]
_DATAZOOM_Y = [{"type": "inside"}, {"type": "slider", "yAxisIndex": 0, "right": 4, "width": 16}]

# Axis tooltip: divides each series value by 1e9 → Tỷ VND
_TT_AXIS = {"trigger": "axis", "formatter": "function(params){var s=params[0].axisValue+'<br/>';params.forEach(function(p){s+=p.marker+p.seriesName+': '+(p.value/1e9).toFixed(2)+' Tỷ VND<br/>';});return s;}"}
_TT_AXIS_SHADOW = {**_TT_AXIS, "axisPointer": {"type": "shadow"}}


def cash_treemap(df: pd.DataFrame, name_map: dict[str, str]) -> dict:
    data = [
        {"name": name_map.get(r.entity_id, r.entity_id), "value": float(r.cash_eom)}
        for r in df.itertuples()
    ]
    return {
        "tooltip": {"formatter": "function(p){return p.name+'<br/>'+(p.value/1e9).toFixed(2)+' Tỷ VND';}"},
        "toolbox": _TOOLBOX,
        "series": [{
            "type": "treemap",
            "roam": True,
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
        "tooltip": _TT_AXIS,
        "toolbox": _TOOLBOX,
        "dataZoom": _DATAZOOM,
        "grid": {"top": 30, "bottom": 70, "left": 60, "right": 20},
        "xAxis": {"type": "category", "data": entities, "axisLabel": {"rotate": 30, "interval": 0, "fontSize": 10}},
        "yAxis": {"type": "value", "axisLabel": {"formatter": "function(v){return (v/1e9).toFixed(0)+' B';}"}},
        "series": [{"type": "bar", "name": "Cash", "data": values}]
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
        "tooltip": _TT_AXIS_SHADOW,
        "legend": {"top": 0},
        "toolbox": _TOOLBOX,
        "dataZoom": _DATAZOOM,
        "grid": {"top": 40, "bottom": 70, "left": 60, "right": 20},
        "xAxis": {"type": "category", "data": entities, "axisLabel": {"rotate": 30}},
        "yAxis": {"type": "value", "axisLabel": {"formatter": "function(v){return (v/1e9).toFixed(0)+' B';}"}},
        "series": series,
    }


def cash_ar_trend(cash_ts: pd.DataFrame, ar_ts: pd.DataFrame) -> dict:
    dates = sorted(set(cash_ts["period_end"]).union(ar_ts["period_end"]))
    labels = [pd.Timestamp(d).strftime("%Y-%m") for d in dates]
    cash_map = dict(zip(cash_ts["period_end"], cash_ts["cash_eom"]))
    ar_map = dict(zip(ar_ts["period_end"], ar_ts["external_ar_eom"]))
    return {
        "tooltip": _TT_AXIS,
        "legend": {"data": ["Cash", "AR"], "top": 0},
        "toolbox": _TOOLBOX,
        "dataZoom": _DATAZOOM,
        "grid": {"top": 40, "bottom": 50, "left": 70, "right": 70},
        "xAxis": {"type": "category", "data": labels},
        "yAxis": [
            {"type": "value", "name": "Cash (Tỷ)", "axisLabel": {"formatter": "function(v){return (v/1e9).toFixed(0);}"}},
            {"type": "value", "name": "AR (Tỷ)",   "axisLabel": {"formatter": "function(v){return (v/1e9).toFixed(0);}"}},
        ],
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
        "tooltip": {"trigger": "axis", "formatter": "function(params){return params[0].axisValue+'<br/>'+params[0].marker+'Utilization: '+(params[0].value*100).toFixed(1)+'%';}"},
        "toolbox": _TOOLBOX,
        "dataZoom": _DATAZOOM,
        "grid": {"top": 30, "bottom": 70, "left": 60, "right": 20},
        "xAxis": {"type": "category", "data": df["entity_name"].tolist(),
                   "axisLabel": {"rotate": 30}},
        "yAxis": {"type": "value", "max": 1, "axisLabel": {"formatter": "function(v){return (v*100).toFixed(0)+'%';}"}},
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
