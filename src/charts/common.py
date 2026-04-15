"""Common helpers for ECharts rendering."""
from __future__ import annotations

from streamlit_echarts import st_echarts

EVENTS = {"click": "function(p){return {name: p.name, data: p.data};}"}


def render(option: dict, height: str = "420px", key: str | None = None,
           events: dict | None = None):
    return st_echarts(
        options=option,
        events=events or EVENTS,
        height=height,
        key=key,
    )
