"""Inter Company — Ownership + IC Flow + IC Network in one page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts.common import render
from src.charts.network import ic_network, ownership_tree
from src.charts.sankey import ic_sankey
from src.charts.supply_chain import supply_chain_graph
from src.filters import in_scope
from src.state import ensure_state, render_sidebar
from src.ui import card, inject_css, subholding_filter

st.set_page_config(page_title="Inter Company", layout="wide")
inject_css()
dfs = ensure_state()
render_sidebar(dfs)
st.markdown("## Giao dịch Nội bộ (Inter Company)")

ss = st.session_state
ent = dfs["dim_entity"]
rel = dfs["rel_ownership"]
scope = in_scope(ent)
name_map = dict(zip(ent["entity_id"], ent["entity_name"]))
cg_df = dfs["dim_client_group"]
name_map.update(dict(zip(cg_df["client_group_id"], cg_df["client_group_name"])))

ic = dfs["fact_ic_arap"][dfs["fact_ic_arap"]["period_end"] == ss["period_end"]]
ic = ic[ic["from_entity_id"].isin(scope) | ic["to_entity_id"].isin(scope)]
loan = dfs["fact_ic_loan"][dfs["fact_ic_loan"]["period_end"] == ss["period_end"]]
loan = loan[loan["lender_entity_id"].isin(scope) | loan["borrower_entity_id"].isin(scope)]

view_mode = st.radio("Phân tích Trực quan", 
                     ["Cấu trúc Sở hữu", "Mạng lưới & Dòng Vốn", "AR Nội bộ & Bên ngoài", "Luân chuyển Dòng tiền"], 
                     horizontal=True, label_visibility="collapsed")

# ── View 1: Ownership Tree ────────────────────────────────────────────────────
if view_mode == "Cấu trúc Sở hữu":
    st.markdown("**Ai sở hữu ai?** Click vào một node để xem chi tiết hồ sơ đơn vị đó.", help="Trả lời: Cấu trúc tập đoàn, sở hữu chéo, và mức độ kiểm soát.")
    clicked = render(ownership_tree(ent, rel, root="001"), key="ih_tree", height="560px")
    if clicked and isinstance(clicked, dict) and "name" in clicked:
        eid = clicked["name"].split(" · ")[0]
        if eid in ent["entity_id"].values and eid != ss.get("selected_entity"):
            ss["selected_entity"] = eid; st.rerun()

    # Contextual panel when entity selected
    if ss.get("selected_entity"):
        eid = ss["selected_entity"]
        row = ent[ent["entity_id"] == eid]
        if not row.empty:
            st.markdown(f"#### {row['entity_name'].iloc[0]} ({eid})")
            r1, r2, r3 = st.columns(3)
            r1.markdown(f"**Loại hình:** {row['entity_type'].iloc[0]}")
            r2.markdown(f"**Khối KD:** {row['subholding_code'].iloc[0] or 'Trực thuộc Tập đoàn'}")
            r3.markdown(f"**Ngành nghề:** {row['industry'].iloc[0]}")
            # IC partners
            ic_e = ic[(ic["from_entity_id"] == eid) | (ic["to_entity_id"] == eid)]
            if not ic_e.empty:
                ic_e = ic_e.copy()
                ic_e["partner"] = ic_e.apply(
                    lambda r: r["to_entity_id"] if r["from_entity_id"] == eid else r["from_entity_id"], axis=1)
                top3 = ic_e.groupby("partner")["amount_eom"].sum().nlargest(3)
                st.markdown("**Top Đối tác Nội bộ:** " + " · ".join(
                    f"{name_map.get(p, p)} ({v/1e9:.1f}B)" for p, v in top3.items()))

# ── View 2: IC Flow & Network A/B/C Test ─────────────────────────────────────────
elif view_mode == "Mạng lưới & Dòng Vốn":
    st.markdown("**Kiểm soát và Điều tiết Dòng Vốn Nội bộ:** Chế độ xem mô phỏng rủi ro ngầm và sự tập trung vốn.")
    
    # ──── COMMON FILTERS ────
    f1, f2, f3 = st.columns([1.2, 1, 1])
    with f1: sub_p = subholding_filter("ih_common_sub")
    with f2: top_edges = st.slider("Số lượng giao dịch (Edges) Top-N", 5, 100, 25, key="ih_common_n")
    with f3: show_loan = st.checkbox("Bao gồm cả Vay nội bộ", True, key="ih_common_loan")
    
    # Pre-filter Data
    ic_f, loan_f = ic.copy(), loan.copy()
    if sub_p:
        sub_ids = set(ent.loc[ent["subholding_code"].isin(sub_p), "entity_id"])
        ic_f = ic_f[ic_f["from_entity_id"].isin(sub_ids) | ic_f["to_entity_id"].isin(sub_ids)]
        loan_f = loan_f[loan_f["lender_entity_id"].isin(sub_ids) | loan_f["borrower_entity_id"].isin(sub_ids)]
        
    c_mode = st.segmented_control("Chế độ xem A/B/C", ["A. Dòng chảy (Sankey)", "B. Tương tác (Network)", "C. Chuỗi Cung ứng Box (yFiles)"], default="A. Dòng chảy (Sankey)", key="ic_abc_test", label_visibility="collapsed")
    
    if c_mode == "A. Dòng chảy (Sankey)":
        if show_loan and not loan_f.empty:
            loan_as_arap = loan_f.rename(columns={"lender_entity_id": "from_entity_id", "borrower_entity_id": "to_entity_id", "outstanding_eom": "amount_eom"})
            loan_as_arap["ic_type"] = "IC_LOAN"
            import pandas as _pd
            combined = _pd.concat([ic_f, loan_as_arap], ignore_index=True)
            sankey_df = combined.nlargest(top_edges, "amount_eom")
        else:
            sankey_df = ic_f.nlargest(top_edges, "amount_eom")
    
        clicked_sk = render(ic_sankey(sankey_df, name_map), key="ih_sankey", height="580px")
        if clicked_sk and isinstance(clicked_sk, dict) and "data" in clicked_sk:
            d = clicked_sk["data"]
            if "source" in d and "target" in d:
                src, tgt = d["source"].split(" · ")[0], d["target"].split(" · ")[0]
                if ss.get("selected_pair") != (src, tgt): ss["selected_pair"] = (src, tgt); st.rerun()

    elif c_mode == "B. Tương tác (Network)":
        c1, c2 = st.columns([1, 3])
        with c1: layout = st.selectbox("Bố cục thuật toán (Layout)", ["Circular", "Force"], key="ih_net_layout")
        with c2: show_ar = st.checkbox("Trực quan luôn cả Phải thu/trả (AR/AP)", True, key="ih_net_ar")
        
        clicked_net = render(ic_network(ic_f, loan_f, ent, show_ar=show_ar, show_loan=show_loan, top_n=top_edges, layout=layout.lower()), key="ih_network", height="620px")
        if clicked_net and isinstance(clicked_net, dict) and "name" in clicked_net:
            eid = clicked_net["name"].split(" · ")[0]
            if eid in ent["entity_id"].values and eid != ss.get("selected_entity"): ss["selected_entity"] = eid; st.rerun()
            
    else:
        st.markdown("**Mô hình Chuỗi Cung ứng Phân mảnh (Sub-holding Cluster Architecture).**")
        dot = supply_chain_graph(ent, ic_f, loan_f if show_loan else pd.DataFrame(columns=loan.columns), name_map, top_edges=top_edges)
        st.graphviz_chart(dot, use_container_width=True)

# ── View 3: External AR Risk A/B Test ─────────────────────────────────────────
elif view_mode == "AR Nội bộ & Bên ngoài":
    st.markdown("**Ai là con nợ lớn nhất? Phụ thuộc bao nhiêu vào khách hàng bên ngoài (VD: EVN)?**")
    
    from src.charts.bars import ar_stacked_bar
    from src.charts.heatmap import ar_heatmap
    
    ar_mode = st.segmented_control("Chế độ xem A/B", ["A. Cột Kép (Stacked Bar)", "B. Bản đồ (Heatmap)"], default="A. Cột Kép (Stacked Bar)", key="ar_ab_test", label_visibility="collapsed")
    
    st.markdown("#### Cơ cấu Nợ Phải Thu theo Khách hàng bên ngoài")
    ar_p = dfs["fact_external_ar"][dfs["fact_external_ar"]["period_end"] == ss["period_end"]].copy()
    ar_df = ar_p.merge(ent[["entity_id", "entity_name"]], on="entity_id").merge(
        dfs["dim_client_group"][["client_group_id", "client_group_name"]], on="client_group_id")
        
    cg_pick = st.multiselect("Lọc nhóm KH", dfs["dim_client_group"]["client_group_name"].unique())
    if cg_pick:
         ar_df = ar_df[ar_df["client_group_name"].isin(cg_pick)]
            
    if ar_mode == "A. Cột Kép (Stacked Bar)":
         render(ar_stacked_bar(ar_df, top_k=5), key="ih_ar_stack", height="450px")
    else:
         render(ar_heatmap(ar_df, top_k=5), key="ih_ar_heat", height="450px")

# ── View 5: Cashflow (Internal vs External Filtering) ──────────────────────────
elif view_mode == "Luân chuyển Dòng tiền":
    st.markdown("**Theo dõi hướng gió: Giao dịch tiền mặt nào mang tính Nội bộ, Tiền mặt nào thực sự chảy ra ngoài?**")
    
    cf = dfs["fact_cash_flow"].copy()
    available_periods_dt = sorted(cf["period_end"].unique())
    period_strs = [pd.Timestamp(p).strftime("%Y-%m") for p in available_periods_dt]
    
    with st.expander("Bộ lọc Đa Chiều (Cashflow Multi-Dimension Controller)", expanded=True):
        c_time, c_scope, c_cat, c_sub = st.columns(4)
        c_line, c_cpty, c_stab, _ = st.columns(4)
        
        with c_time:
             if period_strs:
                  dt_range = st.select_slider("Chu kỳ Thời gian (Từ - Đến)", options=period_strs, value=(period_strs[max(0, len(period_strs)-12)], period_strs[-1]))
             else:
                  dt_range = (None, None)
                  
        with c_scope: pick_scope = st.multiselect("Phạm vi Đối tác", ["NỘI BỘ", "BÊN NGOÀI"], default=["NỘI BỘ", "BÊN NGOÀI"])
        with c_cat: pick_cat = st.multiselect("Hoạt động dòng tiền", ["OPERATING", "INVESTING", "FINANCING"], default=["OPERATING", "INVESTING", "FINANCING"])
        with c_sub: pick_sub = st.multiselect("Lọc Khối (Sub-holding)", ["A", "B"], default=["A", "B"])
        
        # Dependent filters
        avail_lines = cf[cf["activity_category"].isin(pick_cat)]["line_item"].unique() if pick_cat else cf["line_item"].unique()
        with c_line: pick_line = st.multiselect("Hạng mục (Chỉ tiêu)", avail_lines)
        
        avail_cpty = cf[cf["scope"].isin(pick_scope)]["counterparty_type"].unique() if pick_scope else cf["counterparty_type"].unique()
        with c_cpty: pick_cpty = st.multiselect("Loại Đối tác", list(avail_cpty))
        
        with c_stab: pick_stab = st.multiselect("Tính Ổn định", ["ỔN ĐỊNH", "KHÔNG ỔN ĐỊNH"])

    # Apply Filters
    if dt_range and dt_range[0] and dt_range[1]:
        start_dt = pd.to_datetime(dt_range[0] + "-01") + pd.offsets.MonthEnd(0)
        end_dt = pd.to_datetime(dt_range[1] + "-01") + pd.offsets.MonthEnd(0)
        cf = cf[(pd.to_datetime(cf["period_end"]) >= start_dt) & (pd.to_datetime(cf["period_end"]) <= end_dt)]
        
    if pick_scope: cf = cf[cf["scope"].isin(pick_scope)]
    if pick_cat: cf = cf[cf["activity_category"].isin(pick_cat)]
    if pick_line: cf = cf[cf["line_item"].isin(pick_line)]
    if pick_cpty: cf = cf[cf["counterparty_type"].isin(pick_cpty)]
    if pick_stab: cf = cf[cf["stability"].isin(pick_stab)]
    
    sub_ids = []
    if pick_sub:
        sub_ids = ent[ent["subholding_code"].isin(pick_sub)]["entity_id"].tolist()
        cf = cf[cf["from_entity_id"].isin(sub_ids) | cf["to_entity_id"].isin(sub_ids)]
        
    cf_mode = st.segmented_control("Biểu đồ Trực quan hóa A/B", ["A. Dòng chảy Tiền mặt (Sankey)", "B. Tương tác (Network Graph)"], default="A. Dòng chảy Tiền mặt (Sankey)", key="cf_ab_viz", label_visibility="collapsed")
    
    if cf_mode == "A. Dòng chảy Tiền mặt (Sankey)":
         from src.charts.sankey import ic_sankey
         sankey_df = cf.rename(columns={"activity_category": "ic_type", "flow_amount": "amount_eom"}).copy()
         sankey_df["amount_eom"] = sankey_df["amount_eom"].abs()
         render(ic_sankey(sankey_df.nlargest(30, "amount_eom"), name_map), key="cf_sankey", height="450px")
    else:
         from src.charts.network import cashflow_network
         
         cl1, cl2 = st.columns([1, 3])
         with cl1: layout_cf = st.selectbox("Bố cục thuật toán", ["Circular", "Force"], key="cf_net_layout")
         with cl2: top_edges_cf = st.slider("Số lượng giao dịch Top-N hiển thị", 5, 100, 30, key="cf_net_n")
         
         render(cashflow_network(cf, ent, name_map, top_n=top_edges_cf, layout=layout_cf.lower()), key="cf_network", height="550px")
         
    st.markdown("#### Bảng Kê Lưu chuyển Tiền tệ")
    st.dataframe(
        cf.sort_values(by="period_end", ascending=False)
          .assign(flow_amount_bil = lambda x: x["flow_amount"] / 1e9)
          .rename(columns={"activity_category": "Phân loại", "line_item": "Hạng mục",
                           "counterparty_type": "Loại Đối tác", "scope": "Phạm vi",
                           "flow_amount_bil": "Giá trị (Tỷ VND)", "period_end": "Tháng"})
          [["Tháng", "Phạm vi", "Phân loại", "Hạng mục", "Loại Đối tác", "Giá trị (Tỷ VND)"]],
        use_container_width=True, hide_index=True, height=300
    )
