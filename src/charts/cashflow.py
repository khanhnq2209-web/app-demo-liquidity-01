"""Cash-flow visualizations (waterfall, stability mix, scope mix, line items)."""
from __future__ import annotations

import pandas as pd

_CAT_ORDER = ["OPERATING", "INVESTING", "FINANCING"]
_CAT_COLOR = {"OPERATING": "#34a853", "INVESTING": "#fbbc04", "FINANCING": "#1a73e8"}


def waterfall(cf: pd.DataFrame, opening: float, closing: float) -> dict:
    """Opening + activity-category net flow + Closing waterfall."""
    by_cat = cf.groupby("activity_category")["flow_amount"].sum()
    cats = [c for c in _CAT_ORDER if c in by_cat.index]
    values = [float(by_cat[c]) for c in cats]

    labels = ["Opening"] + cats + ["Closing"]
    running = opening
    aux: list[float] = [0]
    deltas: list[float] = [opening]
    for v in values:
        base = running if v >= 0 else running + v
        aux.append(base)
        deltas.append(abs(v))
        running += v
    aux.append(0)
    deltas.append(closing)

    bar_colors = ["#5f6368"] + [_CAT_COLOR.get(c, "#1a73e8") for c in cats] + ["#5f6368"]
    delta_series = [
        {"value": d, "itemStyle": {"color": bar_colors[i]}}
        for i, d in enumerate(deltas)
    ]

    return {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"top": 40, "bottom": 50, "left": 70, "right": 20},
        "xAxis": {"type": "category", "data": labels,
                   "axisLabel": {"rotate": 20}},
        "yAxis": {"type": "value"},
        "series": [
            {"name": "aux", "type": "bar", "stack": "wf",
              "itemStyle": {"color": "transparent"},
              "emphasis": {"itemStyle": {"color": "transparent"}},
              "data": aux},
            {"name": "Δ", "type": "bar", "stack": "wf",
              "data": delta_series},
        ],
    }


def category_bar(cf: pd.DataFrame) -> dict:
    """Net flow per activity category."""
    by_cat = cf.groupby("activity_category")["flow_amount"].sum().reindex(_CAT_ORDER).fillna(0)
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"top": 30, "bottom": 30, "left": 70, "right": 20},
        "xAxis": {"type": "category", "data": by_cat.index.tolist()},
        "yAxis": {"type": "value"},
        "series": [{
            "type": "bar",
            "data": [{"value": float(v),
                       "itemStyle": {"color": _CAT_COLOR.get(c, "#1a73e8")}}
                      for c, v in by_cat.items()],
        }],
    }


def stability_pie(cf: pd.DataFrame) -> dict:
    """ỔN ĐỊNH vs KHÔNG ỔN ĐỊNH (absolute amount)."""
    df = cf.assign(abs_amt=cf["flow_amount"].abs())
    by = df.groupby("stability")["abs_amt"].sum()
    data = [{"name": k, "value": float(v),
              "itemStyle": {"color": "#34a853" if k == "ỔN ĐỊNH" else "#ea4335"}}
             for k, v in by.items()]
    return {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"top": 0},
        "series": [{"type": "pie", "radius": ["45%", "70%"],
                     "label": {"formatter": "{b}\n{d}%"},
                     "data": data}],
    }


def scope_pie(cf: pd.DataFrame) -> dict:
    """BÊN NGOÀI vs NỘI BỘ."""
    df = cf.assign(abs_amt=cf["flow_amount"].abs())
    by = df.groupby("scope")["abs_amt"].sum()
    data = [{"name": k, "value": float(v),
              "itemStyle": {"color": "#1a73e8" if k == "BÊN NGOÀI" else "#fbbc04"}}
             for k, v in by.items()]
    return {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"top": 0},
        "series": [{"type": "pie", "radius": ["45%", "70%"],
                     "label": {"formatter": "{b}\n{d}%"},
                     "data": data}],
    }


def counterparty_bar(cf: pd.DataFrame) -> dict:
    df = cf.assign(abs_amt=cf["flow_amount"].abs())
    by = df.groupby("counterparty_type")["abs_amt"].sum().sort_values(ascending=True)
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"top": 20, "bottom": 30, "left": 110, "right": 30},
        "xAxis": {"type": "value"},
        "yAxis": {"type": "category", "data": by.index.tolist()},
        "series": [{"type": "bar",
                     "itemStyle": {"color": "#1a73e8"},
                     "data": [float(v) for v in by.values]}],
    }


def top_lines_bar(cf: pd.DataFrame, top_k: int = 10) -> dict:
    """Top absolute-value line items for the period."""
    by = cf.groupby("line_item")["flow_amount"].sum()
    by = by.reindex(by.abs().sort_values(ascending=False).head(top_k).index).iloc[::-1]
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"top": 20, "bottom": 30, "left": 260, "right": 40},
        "xAxis": {"type": "value"},
        "yAxis": {"type": "category", "data": by.index.tolist()},
        "series": [{
            "type": "bar",
            "data": [{"value": float(v),
                       "itemStyle": {"color": "#34a853" if v >= 0 else "#ea4335"}}
                      for v in by.values],
        }],
    }
