"""Session state + shared sidebar."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_loader import load_all
from src.filters import latest_period

SS_DEFAULTS = {
    "granularity": "month",
    "period_end": None,
    "level": "Holding",
    "selected_subholding": None,
    "selected_entity": None,
    "selected_client_group": None,
    "selected_pair": None,
    "show_ic_ar": True,
    "show_ic_loan": True,
    "top_n_edges": 20,
    "heatmap_top_k_clients": 5,
    "ic_view": "Sankey",
}


def ensure_state() -> dict[str, pd.DataFrame]:
    """Idempotent bootstrap. Returns the loaded data dict."""
    dfs = load_all()
    for k, v in SS_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if st.session_state["period_end"] is None:
        st.session_state["period_end"] = latest_period(dfs["dim_period"], st.session_state["granularity"])
    return dfs


def render_sidebar(dfs: dict[str, pd.DataFrame]) -> None:
    ss = st.session_state
    with st.sidebar:
        st.header("Bộ lọc Hệ thống")

        granularity = st.radio(
            "Độ chi tiết (Granularity)",
            options=["month", "quarter"],
            format_func=lambda x: "Theo Tháng" if x == "month" else "Theo Quý",
            index=0 if ss["granularity"] == "month" else 1,
            horizontal=True,
            key="_granularity",
        )
        if granularity != ss["granularity"]:
            ss["granularity"] = granularity
            ss["period_end"] = latest_period(dfs["dim_period"], granularity)
            st.rerun()

        periods = _available_periods(dfs["dim_period"], ss["granularity"])
        labels = [_fmt_period(p, ss["granularity"]) for p in periods]
        current_idx = periods.index(ss["period_end"]) if ss["period_end"] in periods else len(periods) - 1
        selected_label = st.selectbox("Kỳ báo cáo (Period)", labels, index=current_idx)
        ss["period_end"] = periods[labels.index(selected_label)]

        ss["level"] = st.selectbox(
            "Cấp độ xem (Level)", ["Holding", "Sub-holding", "Company"],
            index=["Holding", "Sub-holding", "Company"].index(ss["level"]),
        )

        sub_opts = ["(tất cả)", "A", "B"]
        cur_sub = ss["selected_subholding"] or "(tất cả)"
        sub = st.selectbox("Khối KD (Sub-holding)", sub_opts, index=sub_opts.index(cur_sub))
        ss["selected_subholding"] = None if sub == "(tất cả)" else sub

        ent_opts = ["(trống)"] + dfs["dim_entity"]["entity_id"].tolist()
        cur_ent = ss["selected_entity"] or "(trống)"
        ent = st.selectbox(
            "Đơn vị (Entity)",
            ent_opts,
            index=ent_opts.index(cur_ent) if cur_ent in ent_opts else 0,
            format_func=lambda x: _entity_label(dfs["dim_entity"], x),
        )
        ss["selected_entity"] = None if ent == "(trống)" else ent

        cg_opts = ["(tất cả)"] + dfs["dim_client_group"]["client_group_id"].tolist()
        cur_cg = ss["selected_client_group"] or "(tất cả)"
        cg = st.selectbox(
            "Nhóm KH (Client Group)",
            cg_opts,
            index=cg_opts.index(cur_cg) if cur_cg in cg_opts else 0,
            format_func=lambda x: _cg_label(dfs["dim_client_group"], x),
        )
        ss["selected_client_group"] = None if cg == "(tất cả)" else cg

        st.divider()
        if st.button("Xóa lựa chọn (Clear)", use_container_width=True):
            ss["selected_entity"] = None
            ss["selected_subholding"] = None
            ss["selected_client_group"] = None
            ss["selected_pair"] = None
            st.rerun()


def _available_periods(dim_period: pd.DataFrame, granularity: str) -> list[pd.Timestamp]:
    if granularity == "quarter":
        return sorted(dim_period.loc[dim_period["is_quarter_end"] == 1, "period_end"].unique().tolist())
    return sorted(dim_period["period_end"].unique().tolist())


def _fmt_period(ts, granularity: str) -> str:
    ts = pd.Timestamp(ts)
    if granularity == "quarter":
        return f"{ts.year}Q{(ts.month - 1) // 3 + 1}"
    return ts.strftime("%Y-%m")


def _entity_label(dim_entity: pd.DataFrame, eid: str) -> str:
    if eid in (None, "(trống)", "(none)"):
        return "(trống)"
    row = dim_entity[dim_entity["entity_id"] == eid]
    if row.empty:
        return eid
    return f"{eid} · {row['entity_name'].iloc[0]}"


def _cg_label(dim_cg: pd.DataFrame, cg_id: str) -> str:
    if cg_id in (None, "(tất cả)", "(all)"):
        return "(tất cả)"
    row = dim_cg[dim_cg["client_group_id"] == cg_id]
    if row.empty:
        return cg_id
    return f"{cg_id} · {row['client_group_name'].iloc[0]}"
