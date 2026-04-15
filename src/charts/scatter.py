"""Scatter charts for Risk Position Analysis."""
from __future__ import annotations

import pandas as pd

_TOOLBOX = {
    "show": True, "right": "2%", "top": "1%",
    "feature": {"restore": {"title": "Reset"}, "saveAsImage": {"title": "Save"}},
}


def risk_bubble_chart(df: pd.DataFrame, use_quadrant: bool = False) -> dict:
    """df needs: entity_name, cash, ar, ic_exposure."""
    if df.empty:
        return {}

    median_cash = float(df["cash"].median()) if not df.empty else 0
    median_ar   = float(df["ar"].median())   if not df.empty else 0
    max_ic = float(df["ic_exposure"].max()) if df["ic_exposure"].max() > 0 else 1

    data = []
    for r in df.itertuples():
        size_ratio = r.ic_exposure / max_ic
        data.append({
            "name": r.entity_name,
            "value": [float(r.cash), float(r.ar), float(r.ic_exposure), r.entity_name],
            "symbolSize": max(10, size_ratio * 50)
        })

    mark_line = {}
    if use_quadrant:
        mark_line = {
            "animation": False,
            "lineStyle": {"type": "solid", "color": "#1a73e8", "width": 1},
            "data": [{"xAxis": median_cash}, {"yAxis": median_ar}],
            "symbol": ["none", "none"]
        }

    return {
        "tooltip": {
            "trigger": "item",
            "formatter": "function(p){return p.name+'<br/>Cash: '+(p.value[0]/1e9).toFixed(2)+' Tỷ VND<br/>AR: '+(p.value[1]/1e9).toFixed(2)+' Tỷ VND<br/>IC Exposure: '+(p.value[2]/1e9).toFixed(2)+' Tỷ VND';}"
        },
        "toolbox": _TOOLBOX,
        "dataZoom": [{"type": "inside"}, {"type": "slider", "height": 16, "bottom": 4}],
        "grid": {"top": 40, "bottom": 50, "left": 80, "right": 30},
        "xAxis": {
            "type": "value", "name": "Cash (Tỷ VND)", "nameLocation": "middle", "nameGap": 30,
            "splitLine": {"show": not use_quadrant},
            "axisLabel": {"formatter": "function(v){return (v/1e9).toFixed(0);}"}
        },
        "yAxis": {
            "type": "value", "name": "External AR (Tỷ VND)",
            "splitLine": {"show": not use_quadrant},
            "axisLabel": {"formatter": "function(v){return (v/1e9).toFixed(0);}"}
        },
        "series": [{
            "type": "scatter", "data": data,
            "itemStyle": {"opacity": 0.7, "color": "#1a73e8"},
            "markLine": mark_line
        }]
    }
