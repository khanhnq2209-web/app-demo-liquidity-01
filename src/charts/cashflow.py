"""Cash-flow visualizations (waterfall, stability mix, scope mix, line items)."""
from __future__ import annotations

import pandas as pd
from streamlit_echarts import JsCode

_CAT_ORDER = ["OPERATING", "INVESTING", "FINANCING"]
_CAT_COLOR = {"OPERATING": "#34a853", "INVESTING": "#fbbc04", "FINANCING": "#1a73e8"}

_TOOLBOX = {
    "show": True, "right": "2%", "top": "1%",
    "feature": {"restore": {"title": "Reset"}, "saveAsImage": {"title": "Save"}},
}
_DZ_X = [{"type": "inside"}, {"type": "slider", "height": 16, "bottom": 4}]
_DZ_Y = [{"type": "inside"}, {"type": "slider", "yAxisIndex": 0, "right": 4, "width": 16}]

_FMT_AXIS = JsCode("function(v){return (v/1e9).toFixed(0)+' B';}")
_TT_AXIS = {"trigger": "axis", "formatter": JsCode("function(params){var s=params[0].axisValue+'<br/>';params.forEach(function(p){s+=p.marker+(p.seriesName||'')+': '+(p.value/1e9).toFixed(2)+' Tỷ VND<br/>';});return s;}")}
_TT_AXIS_SHADOW = {**_TT_AXIS, "axisPointer": {"type": "shadow"}}
_TT_SINGLE = {"trigger": "axis", "formatter": JsCode("function(params){return params[0].axisValue+'<br/>'+params[0].marker+(params[0].value/1e9).toFixed(2)+' Tỷ VND';}")}


def waterfall(cf: pd.DataFrame, opening: float, closing: float) -> dict:
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
        "tooltip": _TT_AXIS_SHADOW,
        "toolbox": _TOOLBOX,
        "dataZoom": _DZ_X,
        "grid": {"top": 40, "bottom": 55, "left": 80, "right": 20},
        "xAxis": {"type": "category", "data": labels, "axisLabel": {"rotate": 20}},
        "yAxis": {"type": "value", "axisLabel": {"formatter": _FMT_AXIS}},
        "series": [
            {"name": "aux", "type": "bar", "stack": "wf",
              "itemStyle": {"color": "transparent"},
              "emphasis": {"itemStyle": {"color": "transparent"}},
              "data": aux},
            {"name": "Δ", "type": "bar", "stack": "wf", "data": delta_series},
        ],
    }


def category_bar(cf: pd.DataFrame) -> dict:
    by_cat = cf.groupby("activity_category")["flow_amount"].sum().reindex(_CAT_ORDER).fillna(0)
    return {
        "tooltip": _TT_AXIS,
        "toolbox": _TOOLBOX,
        "dataZoom": _DZ_X,
        "grid": {"top": 30, "bottom": 50, "left": 80, "right": 20},
        "xAxis": {"type": "category", "data": by_cat.index.tolist()},
        "yAxis": {"type": "value", "axisLabel": {"formatter": _FMT_AXIS}},
        "series": [{
            "name": "Net flow",
            "type": "bar",
            "data": [{"value": float(v), "itemStyle": {"color": _CAT_COLOR.get(c, "#1a73e8")}}
                      for c, v in by_cat.items()],
        }],
    }


def stability_pie(cf: pd.DataFrame) -> dict:
    df = cf.assign(abs_amt=cf["flow_amount"].abs())
    by = df.groupby("stability")["abs_amt"].sum()
    data = [{"name": k, "value": float(v),
              "itemStyle": {"color": "#34a853" if k == "ỔN ĐỊNH" else "#ea4335"}}
             for k, v in by.items()]
    return {
        "tooltip": {"trigger": "item", "formatter": JsCode("function(p){return p.name+'<br/>'+(p.value/1e9).toFixed(2)+' Tỷ VND ('+p.percent+'%)';}")},
        "legend": {"top": 0},
        "series": [{"type": "pie", "radius": ["45%", "70%"],
                     "label": {"formatter": "{b}\n{d}%"}, "data": data}],
    }


def scope_pie(cf: pd.DataFrame) -> dict:
    df = cf.assign(abs_amt=cf["flow_amount"].abs())
    by = df.groupby("scope")["abs_amt"].sum()
    data = [{"name": k, "value": float(v),
              "itemStyle": {"color": "#1a73e8" if k == "BÊN NGOÀI" else "#fbbc04"}}
             for k, v in by.items()]
    return {
        "tooltip": {"trigger": "item", "formatter": JsCode("function(p){return p.name+'<br/>'+(p.value/1e9).toFixed(2)+' Tỷ VND ('+p.percent+'%)';}")},
        "legend": {"top": 0},
        "series": [{"type": "pie", "radius": ["45%", "70%"],
                     "label": {"formatter": "{b}\n{d}%"}, "data": data}],
    }


def counterparty_bar(cf: pd.DataFrame) -> dict:
    df = cf.assign(abs_amt=cf["flow_amount"].abs())
    by = df.groupby("counterparty_type")["abs_amt"].sum().sort_values(ascending=True)
    return {
        "tooltip": _TT_SINGLE,
        "toolbox": _TOOLBOX,
        "dataZoom": _DZ_Y,
        "grid": {"top": 20, "bottom": 30, "left": 110, "right": 50},
        "xAxis": {"type": "value", "axisLabel": {"formatter": _FMT_AXIS}},
        "yAxis": {"type": "category", "data": by.index.tolist()},
        "series": [{"name": "Volume", "type": "bar",
                     "itemStyle": {"color": "#1a73e8"},
                     "data": [float(v) for v in by.values]}],
    }


def top_lines_bar(cf: pd.DataFrame, top_k: int = 10) -> dict:
    by = cf.groupby("line_item")["flow_amount"].sum()
    by = by.reindex(by.abs().sort_values(ascending=False).head(top_k).index).iloc[::-1]
    return {
        "tooltip": _TT_SINGLE,
        "toolbox": _TOOLBOX,
        "dataZoom": _DZ_Y,
        "grid": {"top": 20, "bottom": 30, "left": 260, "right": 60},
        "xAxis": {"type": "value", "axisLabel": {"formatter": _FMT_AXIS}},
        "yAxis": {"type": "category", "data": by.index.tolist()},
        "series": [{
            "name": "Net flow",
            "type": "bar",
            "data": [{"value": float(v), "itemStyle": {"color": "#34a853" if v >= 0 else "#ea4335"}}
                      for v in by.values],
        }],
    }
