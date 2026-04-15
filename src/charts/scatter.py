"""Scatter charts for Risk Position Analysis."""
from __future__ import annotations

import pandas as pd


def risk_bubble_chart(df: pd.DataFrame, use_quadrant: bool = False) -> dict:
    """
    df needs: entity_name, cash, ar, ic_exposure
    """
    if df.empty:
        return {}

    median_cash = float(df["cash"].median()) if not df.empty else 0
    median_ar = float(df["ar"].median()) if not df.empty else 0

    max_ic = float(df["ic_exposure"].max()) if df["ic_exposure"].max() > 0 else 1
    
    data = []
    for r in df.itertuples():
        size_ratio = r.ic_exposure / max_ic
        data.append({
            "name": r.entity_name,
            "value": [float(r.cash), float(r.ar), float(r.ic_exposure), r.entity_name],
            "symbolSize": max(10, size_ratio * 50)
        })

    grid = {"top": 40, "bottom": 50, "left": 70, "right": 30}
    
    mark_line = {}
    if use_quadrant:
        mark_line = {
            "animation": False,
            "lineStyle": {"type": "solid", "color": "#1a73e8", "width": 1},
            "data": [
                {"xAxis": median_cash},
                {"yAxis": median_ar}
            ],
            "symbol": ["none", "none"]
        }

    return {
        "tooltip": {
            "trigger": "item",
            "formatter": "{b}<br/>Value: {c}"
        },
        "grid": grid,
        "xAxis": {
            "type": "value",
            "name": "Cash",
            "nameLocation": "middle",
            "nameGap": 30,
            "splitLine": {"show": not use_quadrant},
            "axisLabel": {
                "formatter": "{value}"
            }
        },
        "yAxis": {
            "type": "value",
            "name": "External AR",
            "splitLine": {"show": not use_quadrant},
            "axisLabel": {
                "formatter": "{value}"
            }
        },
        "series": [{
            "type": "scatter",
            "data": data,
            "itemStyle": {
                "opacity": 0.7,
                "color": "#1a73e8"
            },
            "markLine": mark_line
        }]
    }
