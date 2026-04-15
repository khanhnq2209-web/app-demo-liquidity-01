"""Reusable UI blocks (Google Material style)."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable

import pandas as pd
import streamlit as st

from src.use_cases import USE_CASES


def inject_css() -> None:
    """Google-material-ish tweaks: soft cards, compact KPI metrics, light chips."""
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            background: #fff;
            border: 1px solid #e8eaed;
            border-radius: 12px;
            padding: 12px 16px;
            box-shadow: 0 1px 2px rgba(60,64,67,0.05);
        }
        div[data-testid="stMetricLabel"] { font-size: 0.78rem; color: #5f6368; }
        div[data-testid="stMetricValue"] { font-size: 1.45rem; color: #202124; }
        .uc-chip {
            display: inline-block;
            background: #e8f0fe;
            color: #1967d2;
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.72rem;
            margin-right: 6px;
            font-weight: 600;
            letter-spacing: 0.2px;
        }
        .uc-desc {
            color: #5f6368;
            font-size: 0.85rem;
            margin-top: 2px;
            margin-bottom: 10px;
            line-height: 1.45;
        }
        .card {
            background: #fff;
            border: 1px solid #e8eaed;
            border-radius: 12px;
            padding: 16px 18px 12px 18px;
            box-shadow: 0 1px 2px rgba(60,64,67,0.05);
            margin-bottom: 14px;
        }
        .card h4 { margin: 0 0 4px 0; color: #202124; font-weight: 600; }
        .filters-row { background: #f8f9fa; border-radius: 8px; padding: 8px 10px; margin-bottom: 8px; }
        .section-head {
            font-size: 1.4rem; font-weight: 600; color: #202124;
            margin: 10px 0 4px 0;
        }
        .badge-q { background:#fce8e6; color:#c5221f; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def card(use_case_key: str):
    """Render a Google-style card with title, use-case chips, description, then body."""
    uc = USE_CASES.get(use_case_key, {})
    title = uc.get("title", use_case_key)
    qs = uc.get("questions", "")
    desc = uc.get("desc", "")
    st.markdown(
        f"""
        <div class="card">
          <h4>{title}</h4>
          <div>
            <span class="uc-chip">Góc nhìn phân tích · {qs}</span>
          </div>
          <div class="uc-desc">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    yield


def period_range_filter(dim_period: pd.DataFrame, key: str,
                        default_months: int = 12,
                        granularity: str = "month") -> tuple[pd.Timestamp, pd.Timestamp]:
    """Compact period-range filter. Returns (start, end) Timestamps."""
    if granularity == "quarter":
        periods = sorted(dim_period.loc[dim_period["is_quarter_end"] == 1, "period_end"].unique())
        fmt = lambda ts: f"{pd.Timestamp(ts).year}Q{(pd.Timestamp(ts).month - 1) // 3 + 1}"
    else:
        periods = sorted(dim_period["period_end"].unique())
        fmt = lambda ts: pd.Timestamp(ts).strftime("%Y-%m")
    labels = [fmt(p) for p in periods]
    default_start_idx = max(0, len(labels) - default_months)
    start_label, end_label = st.select_slider(
        "Khung thời gian (Time range)",
        options=labels,
        value=(labels[default_start_idx], labels[-1]),
        key=key,
    )
    start = pd.Timestamp(periods[labels.index(start_label)])
    end = pd.Timestamp(periods[labels.index(end_label)])
    return start, end


def multi_entity_filter(dim_entity: pd.DataFrame, key: str,
                         label: str = "Đơn vị (Entities)") -> list[str]:
    companies = dim_entity[dim_entity["entity_type"] == "COMPANY"]
    opts = companies["entity_id"].tolist()
    labels = {e.entity_id: f"{e.entity_id} · {e.entity_name}" for e in companies.itertuples()}
    picked = st.multiselect(label, opts, default=[],
                             format_func=lambda x: labels.get(x, x), key=key)
    return picked


def subholding_filter(key: str) -> list[str]:
    return st.multiselect("Khối Kinh doanh (Sub-holding)", ["A", "B"], default=[], key=key)


def client_group_filter(dim_cg: pd.DataFrame, key: str) -> list[str]:
    opts = dim_cg["client_group_id"].tolist()
    labels = {c.client_group_id: c.client_group_name for c in dim_cg.itertuples()}
    return st.multiselect("Nhóm Khách hàng", opts, default=[],
                           format_func=lambda x: labels.get(x, x), key=key)


def ic_type_filter(key: str) -> list[str]:
    return st.multiselect("Loại GD Nội bộ", ["IC_AR", "IC_AP"], default=["IC_AR", "IC_AP"], key=key)
