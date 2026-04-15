"""Overview page — KPI cards, ranking, cash distribution, AR concentration, trend."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from src.charts.bars import ar_stacked_bar, cash_ar_trend, cash_treemap, cash_bar
from src.charts.scatter import risk_bubble_chart
from src.charts.common import render
from src.filters import filter_by_entities, in_scope
from src.kpis import (cash_decline_flag, hhi, high_util_flag, ic_loans_total,
                       ic_totals, top_n_share, utilization)
from src.state import ensure_state, render_sidebar
from src.ui import (card, client_group_filter, inject_css,
                     period_range_filter, subholding_filter)

st.set_page_config(page_title="Báo cáo Lãnh đạo", layout="wide")
inject_css()

dfs = ensure_state()
render_sidebar(dfs)

st.markdown("## Báo cáo Lãnh đạo (Executive Summary)")
st.info("📊 **Lưu ý:** Toàn bộ số liệu trong ứng dụng này chỉ mang tính **minh họa (demo)**, được tạo ngẫu nhiên bằng dữ liệu giả lập. Không phản ánh số liệu tài chính thực tế của bất kỳ tổ chức nào.")

ss = st.session_state
ent = dfs["dim_entity"]
name_map = dict(zip(ent["entity_id"], ent["entity_name"]))
period = ss["period_end"]
scope = in_scope(ent)

cash_p = filter_by_entities(dfs["fact_cash_balance"], "entity_id", scope)
cash_p = cash_p[cash_p["period_end"] == period]
ar_p = filter_by_entities(dfs["fact_external_ar"], "entity_id", scope)
ar_p = ar_p[ar_p["period_end"] == period]
ic_p = dfs["fact_ic_arap"][dfs["fact_ic_arap"]["period_end"] == period]
ic_p = ic_p[ic_p["from_entity_id"].isin(scope) | ic_p["to_entity_id"].isin(scope)]
loan_p = dfs["fact_ic_loan"][dfs["fact_ic_loan"]["period_end"] == period]
loan_p = loan_p[loan_p["lender_entity_id"].isin(scope) | loan_p["borrower_entity_id"].isin(scope)]
credit_p = filter_by_entities(dfs["fact_credit"], "entity_id", scope)
credit_p = credit_p[credit_p["period_end"] == period]

# ---------- KPI cards ----------
with card("kpi_cards"):
    ic_kpi = ic_totals(ic_p)
    util_df = utilization(credit_p)
    overall_util = (util_df["credit_utilized"].sum() / util_df["credit_limit"].sum()) if util_df["credit_limit"].sum() else 0

    # prior-period MoM deltas
    periods_sorted = sorted(dfs["fact_cash_balance"]["period_end"].unique())
    idx = periods_sorted.index(period) if period in periods_sorted else -1
    prev_period = periods_sorted[idx - 1] if idx > 0 else None

    def _delta(cur_val: float, prev_val: float) -> str | None:
        if prev_val in (None, 0) or prev_val == 0:
            return None
        return f"{(cur_val - prev_val)/prev_val*100:+.1f}%"

    cash_cur = float(cash_p["cash_eom"].sum())
    ar_cur   = float(ar_p["external_ar_eom"].sum())
    cash_prev = float(filter_by_entities(dfs["fact_cash_balance"], "entity_id", scope)
                       .query("period_end == @prev_period")["cash_eom"].sum()) if prev_period is not None else 0
    ar_prev = float(filter_by_entities(dfs["fact_external_ar"], "entity_id", scope)
                     .query("period_end == @prev_period")["external_ar_eom"].sum()) if prev_period is not None else 0

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Tiền mặt",        f"{cash_cur/1e9:,.1f} B", _delta(cash_cur, cash_prev))
    c2.metric("AR Khách ngoài", f"{ar_cur/1e9:,.1f} B",   _delta(ar_cur, ar_prev))
    c3.metric("Phải thu Nội bộ", f"{ic_kpi['ic_ar']/1e9:,.1f} B")
    c4.metric("Dư nợ Vay Nội bộ",f"{ic_loans_total(loan_p)/1e9:,.1f} B")
    c5.metric("Tỷ trọng KH Top 1", f"{top_n_share(ar_p, 1):.1%}")
    c6.metric("HHI (Độ tập trung)", f"{hhi(ar_p):.3f}")
    c7.metric("Room Tín dụng TT", f"{overall_util:.1%}")

with card("ai_report"):
    st.markdown("#### Trợ lý Phân tích AI (Báo cáo Lãnh đạo)")
    trend_dir = "tăng" if cash_cur >= cash_prev else "giảm"
    trend_val = _delta(cash_cur, cash_prev) or "0%"
    ar_dir = "tăng" if ar_cur >= ar_prev else "giảm"
    ar_val = _delta(ar_cur, ar_prev) or "0%"
    st.info(f"**Báo cáo Nhanh ({period})**: Quỹ tiền mặt dự trữ chiến lược của Tập đoàn {trend_dir} khoảng {trend_val} so với kỳ trước. Tổng dư nợ phải thu khách hàng bên ngoài {ar_dir} khoảng {ar_val}, chủ yếu bị chi phối bởi tỷ trọng khách hàng Top 1 ở mức {top_n_share(ar_p, 1):.1%} trên tổng dư nợ. Tốc độ chu chuyển vốn vay nội bộ giữa các đơn vị duy trì ổn định ở mức {ic_loans_total(loan_p)/1e9:.1f}B. \n\n**Khuyến nghị**: Chưa phát hiện rủi ro hệ thống nội bộ nghiêm trọng. Đề nghị các Khối tiếp tục theo dõi sát sức khỏe tài chính của nhóm KH Top 1 để tránh rủi ro mất khả năng thanh toán cục bộ.")

# ---------- Ranking table ----------
with card("ranking"):
    f1, f2 = st.columns([1, 3])
    with f1:
        min_flags = st.selectbox("Hiển thị", ["Tất cả", "Chỉ các đơn vị có rủi ro"], key="ov_flag_only")
    with f2:
        sub_pick = subholding_filter("ov_rank_sub")

    company_ids = [c for c in ent[ent["entity_type"] == "COMPANY"]["entity_id"] if c in scope]
    if sub_pick:
        company_ids = [c for c in company_ids
                        if ent.loc[ent["entity_id"] == c, "subholding_code"].iloc[0] in sub_pick]

    decline_flags = cash_decline_flag(filter_by_entities(dfs["fact_cash_balance"], "entity_id", scope))
    util_flags = high_util_flag(filter_by_entities(dfs["fact_credit"], "entity_id", scope))

    rows = []
    for eid in company_ids:
        c = cash_p.loc[cash_p["entity_id"] == eid, "cash_eom"].sum()
        a = ar_p.loc[ar_p["entity_id"] == eid, "external_ar_eom"].sum()
        ic = ic_p.loc[(ic_p["from_entity_id"] == eid) | (ic_p["to_entity_id"] == eid), "amount_eom"].sum()
        e_ar = ar_p[ar_p["entity_id"] == eid]
        top1 = top_n_share(e_ar, 1) if not e_ar.empty else 0
        flags = []
        if eid in decline_flags: flags.append("CẢNH BÁO Tiền mặt↓")
        if eid in util_flags:    flags.append("H.MỨC>85%")
        if top1 > 0.40:          flags.append("KH.TOP1>40%")
        rows.append({"entity_id": eid, "entity_name": name_map.get(eid, eid),
                     "cash": c, "ar": a, "ic_exposure": ic,
                     "top1_share": top1, "flags": " ".join(flags)})
    rank_df = pd.DataFrame(rows).sort_values("cash", ascending=False)
    if min_flags == "Chỉ các đơn vị có rủi ro":
        rank_df = rank_df[rank_df["flags"] != ""]

    gb = GridOptionsBuilder.from_dataframe(rank_df)
    gb.configure_selection("single", use_checkbox=False)
    gb.configure_column("cash",        type=["numericColumn"], valueFormatter="(x/1e9).toFixed(2) + ' B'")
    gb.configure_column("ar",          type=["numericColumn"], valueFormatter="(x/1e9).toFixed(2) + ' B'")
    gb.configure_column("ic_exposure", type=["numericColumn"], valueFormatter="(x/1e9).toFixed(2) + ' B'")
    gb.configure_column("top1_share",  type=["numericColumn"], valueFormatter="(x*100).toFixed(1) + '%'")
    grid = AgGrid(rank_df, gridOptions=gb.build(),
                   update_mode=GridUpdateMode.SELECTION_CHANGED,
                   fit_columns_on_grid_load=True, height=330, theme="streamlit")
    sel = grid.get("selected_rows")
    if sel is not None and len(sel):
        row = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
        if row["entity_id"] != ss.get("selected_entity"):
            ss["selected_entity"] = row["entity_id"]
            st.rerun()

# ---------- Charts ----------
col_a, col_b = st.columns(2)
with col_a:
    with card("cash_chart"):
        st.markdown("#### Phân bổ Nguồn tiền (Liquidity Distribution)")
        mode_a = st.segmented_control("Chế độ xem (A/B Test)", ["Cột (Bar)", "Khối (Treemap)"], default="Cột (Bar)", key="ov_cash_ab", label_visibility="collapsed")
        
        sub_pick = subholding_filter("ov_tree_sub")
        tm = cash_p.merge(ent[["entity_id", "entity_name", "subholding_code"]], on="entity_id")
        if sub_pick:
            tm = tm[tm["subholding_code"].isin(sub_pick)]
            
        if mode_a == "Khối (Treemap)":
            clicked_cash = render(cash_treemap(tm, name_map), key="cash_treemap", height="360px")
        else:
            clicked_cash = render(cash_bar(tm, name_map), key="cash_bar", height="360px")
            
        if clicked_cash and isinstance(clicked_cash, dict) and "name" in clicked_cash:
            eid = clicked_cash["name"].split(" · ")[0]
            if eid != ss.get("selected_entity") and eid in ent["entity_id"].values:
                ss["selected_entity"] = eid
                st.rerun()

with col_b:
    with card("risk_position"):
        st.markdown("#### Bản đồ Rủi ro Tổng hợp (Risk Position)")
        mode_b = st.segmented_control("Chế độ xem A/B", ["Bubble Graph", "Quadrant Risk"], default="Bubble Graph", key="ov_risk_ab", label_visibility="collapsed")
        
        # Prepare Data: X: cash, Y: AR, Size: IC Exposure
        comp_df = ent[ent["entity_type"] == "COMPANY"].copy()
        c_series = cash_p.groupby("entity_id")["cash_eom"].sum()
        a_series = ar_p.groupby("entity_id")["external_ar_eom"].sum()
        
        # Calculate gross IC exposure (sum of AR and AP involving the entity)
        ic_exp1 = ic_p.groupby("from_entity_id")["amount_eom"].sum()
        ic_exp2 = ic_p.groupby("to_entity_id")["amount_eom"].sum()
        ic_tot = ic_exp1.add(ic_exp2, fill_value=0)
        
        comp_df["cash"] = comp_df["entity_id"].map(c_series).fillna(0)
        comp_df["ar"] = comp_df["entity_id"].map(a_series).fillna(0)
        comp_df["ic_exposure"] = comp_df["entity_id"].map(ic_tot).fillna(0)
        
        comp_df = comp_df[comp_df["entity_id"].isin(scope)]
        if sub_pick:
            comp_df = comp_df[comp_df["subholding_code"].isin(sub_pick)]
            
        is_quadrant = mode_b == "Quadrant Risk"
        clicked_bubble = render(risk_bubble_chart(comp_df, use_quadrant=is_quadrant), key="risk_scatter", height="360px")
        
        if clicked_bubble and isinstance(clicked_bubble, dict) and "name" in clicked_bubble:
            eid = clicked_bubble["name"].split(" · ")[0]
            if eid != ss.get("selected_entity") and eid in ent["entity_id"].values:
                ss["selected_entity"] = eid
                st.rerun()

with card("cash_ar_trend"):
    start, end = period_range_filter(dfs["dim_period"], key="ov_trend_range",
                                       default_months=12, granularity=ss["granularity"])
    cash_full = filter_by_entities(dfs["fact_cash_balance"], "entity_id", scope)
    ar_full = filter_by_entities(dfs["fact_external_ar"], "entity_id", scope)
    mask_c = (cash_full["period_end"] >= start) & (cash_full["period_end"] <= end)
    mask_a = (ar_full["period_end"] >= start) & (ar_full["period_end"] <= end)
    cash_ts = cash_full[mask_c].groupby("period_end")["cash_eom"].sum().reset_index()
    ar_ts = ar_full[mask_a].groupby("period_end")["external_ar_eom"].sum().reset_index()
    render(cash_ar_trend(cash_ts, ar_ts), key="trend", height="320px")

# ---------- Company detail drill-down ----------
if ss.get("selected_entity"):
    eid = ss["selected_entity"]
    e_row = ent[ent["entity_id"] == eid]
    if not e_row.empty and e_row["entity_type"].iloc[0] == "COMPANY":
        st.markdown('<div class="section-head">Chi tiết Đơn vị — '
                     f'{e_row["entity_name"].iloc[0]} ({eid})</div>',
                     unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        cg_names = dict(zip(dfs["dim_client_group"]["client_group_id"],
                             dfs["dim_client_group"]["client_group_name"]))
        with d1:
            st.markdown("**Top Nhóm Khách hàng (AR lớn nhất)**")
            e_ar = ar_p[ar_p["entity_id"] == eid]
            top_cg = (e_ar.groupby("client_group_id")["external_ar_eom"].sum()
                      .sort_values(ascending=False).head(5))
            st.dataframe(pd.DataFrame({"Khách hàng": [cg_names.get(i, i) for i in top_cg.index],
                                        "Phải thu (Tỷ)": [v/1e9 for v in top_cg.values]}),
                          hide_index=True, use_container_width=True)
        with d2:
            st.markdown("**Top Đối tác Nội bộ (Giao dịch lớn nhất)**")
            ic_e = ic_p[(ic_p["from_entity_id"] == eid) | (ic_p["to_entity_id"] == eid)].copy()
            ic_e["partner"] = ic_e.apply(
                lambda r: r["to_entity_id"] if r["from_entity_id"] == eid else r["from_entity_id"],
                axis=1)
            top_p = (ic_e.groupby("partner")["amount_eom"].sum()
                     .sort_values(ascending=False).head(5))
            st.dataframe(pd.DataFrame({"Đối tác nội bộ": [name_map.get(i, i) for i in top_p.index],
                                        "Giao dịch dư nợ (Tỷ)": [v/1e9 for v in top_p.values]}),
                          hide_index=True, use_container_width=True)
