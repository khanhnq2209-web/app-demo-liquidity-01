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
st.info("📊 **Lưu ý:** Toàn bộ số liệu trong ứng dụng này chỉ mang tính **minh họa (demo)**, được tạo ngẫu nhiên bằng dữ liệu giả lập. Không phản ánh số liệu tài chính thực tế của bất kỳ tổ chức nào.")

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
    st.markdown("""
**Sơ đồ Cấu trúc Sở hữu Tập đoàn** — biểu diễn quan hệ sở hữu theo cấp bậc (Holding → Sub-holding → Công ty thành viên).
Mỗi node hiển thị mã định danh và tên đơn vị. Kích thước/màu sắc phản ánh loại hình pháp nhân.
Click vào một node để xem hồ sơ chi tiết, danh sách đối tác nội bộ, và mức độ phơi nhiễm giao dịch nội bộ.
""", help="Trả lời: Ai sở hữu ai? Sở hữu chéo ở đâu? Mức độ kiểm soát ra sao?")

    # ── Filters ──
    f1, f2, f3 = st.columns(3)
    with f1:
        pick_etype = st.multiselect(
            "Lọc loại hình đơn vị",
            options=["HOLDING", "SUBHOLDING", "COMPANY"],
            default=["HOLDING", "SUBHOLDING", "COMPANY"],
            key="ow_entity_type"
        )
    with f2:
        all_industries = sorted(ent["industry"].dropna().unique().tolist())
        pick_industry = st.multiselect("Lọc ngành nghề", options=all_industries, key="ow_industry")
    with f3:
        all_scn = sorted(ent["supply_chain_node"].dropna().unique().tolist())
        pick_scn = st.multiselect("Lọc chuỗi cung ứng", options=all_scn, key="ow_scn")

    ent_filtered = ent.copy()
    if pick_etype:
        ent_filtered = ent_filtered[ent_filtered["entity_type"].isin(pick_etype)]
    if pick_industry:
        ent_filtered = ent_filtered[ent_filtered["industry"].isin(pick_industry)]
    if pick_scn:
        ent_filtered = ent_filtered[ent_filtered["supply_chain_node"].isin(pick_scn)]

    clicked = render(ownership_tree(ent_filtered, rel, root="GELEX"), key="ih_tree", height="560px")
    if clicked and isinstance(clicked, dict) and "name" in clicked:
        eid = clicked["name"].split(" · ")[0]
        if eid in ent["entity_id"].values and eid != ss.get("selected_entity"):
            ss["selected_entity"] = eid; st.rerun()

    if ss.get("selected_entity"):
        eid = ss["selected_entity"]
        row = ent[ent["entity_id"] == eid]
        if not row.empty:
            st.markdown(f"#### {row['entity_name'].iloc[0]} ({eid})")
            r1, r2, r3, r4 = st.columns(4)
            r1.markdown(f"**Loại hình:** {row['entity_type'].iloc[0]}")
            r2.markdown(f"**Khối KD:** {row['subholding_code'].iloc[0] or 'Trực thuộc Tập đoàn'}")
            r3.markdown(f"**Ngành nghề:** {row['industry'].iloc[0]}")
            r4.markdown(f"**Chuỗi cung ứng:** {row['supply_chain_node'].iloc[0]}")
            ic_e = ic[(ic["from_entity_id"] == eid) | (ic["to_entity_id"] == eid)]
            if not ic_e.empty:
                ic_e = ic_e.copy()
                ic_e["partner"] = ic_e.apply(
                    lambda r: r["to_entity_id"] if r["from_entity_id"] == eid else r["from_entity_id"], axis=1)
                top3 = ic_e.groupby("partner")["amount_eom"].sum().nlargest(3)
                st.markdown("**Top Đối tác Nội bộ:** " + " · ".join(
                    f"{name_map.get(p, p)} ({v/1e9:.1f}B)" for p, v in top3.items()))

# ── View 2: IC Flow & Network ─────────────────────────────────────────────────
elif view_mode == "Mạng lưới & Dòng Vốn":
    st.markdown("""
**Phân tích Dòng Vốn & Mạng lưới Giao dịch Nội bộ** — cho thấy tiền và công nợ đang chảy từ đâu đến đâu trong tập đoàn.
Bao gồm: Phải thu nội bộ (IC AR), Phải trả nội bộ (IC AP), và Vay nội bộ (IC Loan).
Sử dụng để phát hiện điểm tập trung rủi ro, đơn vị đang "hút vốn" hay "bơm vốn" trong chuỗi nội bộ.
""")

    # ── COMMON FILTERS ────
    with st.expander("Bộ lọc Dữ liệu (Mở rộng để lọc chi tiết)", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            sub_p = subholding_filter("ih_common_sub")
        with f2:
            top_edges = st.slider("Top-N giao dịch hiển thị", 5, 100, 25, key="ih_common_n")
        with f3:
            show_loan = st.checkbox("Bao gồm Vay nội bộ (IC Loan)", True, key="ih_common_loan")

        f4, f5, f6 = st.columns(3)
        with f4:
            pick_ic_type = st.multiselect(
                "Loại giao dịch IC",
                options=["IC_AR", "IC_AP"],
                default=["IC_AR", "IC_AP"],
                help="IC_AR = Phải thu nội bộ (Bên bán ghi nhận), IC_AP = Phải trả nội bộ (Bên mua ghi nhận)",
                key="ih_ic_type"
            )
        with f5:
            all_industries = sorted(ent["industry"].dropna().unique().tolist())
            pick_industry = st.multiselect("Lọc ngành nghề đơn vị", options=all_industries, key="ih_industry")
        with f6:
            all_scn = sorted(ent["supply_chain_node"].dropna().unique().tolist())
            pick_scn = st.multiselect(
                "Lọc vị trí Chuỗi cung ứng",
                options=all_scn,
                help="Raw Material → Manufacturing → Assembly → Distribution → Retail",
                key="ih_scn"
            )

        f7, f8 = st.columns(2)
        with f7:
            min_amount = st.number_input(
                "Ngưỡng tối thiểu mỗi giao dịch (Tỷ VND)",
                min_value=0.0, value=0.0, step=0.5,
                key="ih_min_amt"
            )
        with f8:
            all_currencies = sorted(ent["currency_code"].dropna().unique().tolist())
            pick_currency = st.multiselect("Đơn vị tiền tệ", options=all_currencies, key="ih_currency")

    # Build entity inclusion set from dimension filters
    ent_mask = pd.Series(True, index=ent.index)
    if pick_industry:
        ent_mask &= ent["industry"].isin(pick_industry)
    if pick_scn:
        ent_mask &= ent["supply_chain_node"].isin(pick_scn)
    if pick_currency:
        ent_mask &= ent["currency_code"].isin(pick_currency)
    filtered_eids = set(ent[ent_mask]["entity_id"].tolist())

    # Pre-filter IC data
    ic_f = ic.copy()
    loan_f = loan.copy()

    if pick_ic_type:
        ic_f = ic_f[ic_f["ic_type"].isin(pick_ic_type)]
    if min_amount > 0:
        ic_f = ic_f[ic_f["amount_eom"] >= min_amount * 1e9]
    if filtered_eids != set(ent["entity_id"].tolist()):
        ic_f = ic_f[ic_f["from_entity_id"].isin(filtered_eids) | ic_f["to_entity_id"].isin(filtered_eids)]
        loan_f = loan_f[loan_f["lender_entity_id"].isin(filtered_eids) | loan_f["borrower_entity_id"].isin(filtered_eids)]
    if sub_p:
        sub_ids = set(ent.loc[ent["subholding_code"].isin(sub_p), "entity_id"])
        ic_f = ic_f[ic_f["from_entity_id"].isin(sub_ids) | ic_f["to_entity_id"].isin(sub_ids)]
        loan_f = loan_f[loan_f["lender_entity_id"].isin(sub_ids) | loan_f["borrower_entity_id"].isin(sub_ids)]

    # Summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng IC AR (Phải thu nội bộ)", f"{ic_f[ic_f['ic_type']=='IC_AR']['amount_eom'].sum()/1e9:,.1f} B")
    m2.metric("Tổng IC AP (Phải trả nội bộ)", f"{ic_f[ic_f['ic_type']=='IC_AP']['amount_eom'].sum()/1e9:,.1f} B")
    m3.metric("Tổng Vay nội bộ (IC Loan)", f"{loan_f['outstanding_eom'].sum()/1e9:,.1f} B")

    c_mode = st.segmented_control(
        "Chế độ xem",
        ["A. Dòng chảy (Sankey)", "B. Tương tác (Network)", "C. Chuỗi Cung ứng Box (yFiles)"],
        default="A. Dòng chảy (Sankey)",
        key="ic_abc_test",
        label_visibility="collapsed"
    )

    if c_mode == "A. Dòng chảy (Sankey)":
        st.markdown("""
> **Sankey Diagram** — mỗi dải băng biểu diễn một luồng giao dịch công nợ nội bộ từ đơn vị **gốc** (trái)
> sang đơn vị **đích** (phải). Độ rộng dải tỷ lệ thuận với **giá trị dư nợ cuối kỳ**.
> Màu sắc phân biệt IC_AR (phải thu), IC_AP (phải trả) và IC_Loan (vay nội bộ).
> Dùng để phát hiện nhanh **luồng vốn lớn nhất** và **đơn vị trung gian phân phối vốn**.
""")
        if show_loan and not loan_f.empty:
            loan_as_arap = loan_f.rename(columns={
                "lender_entity_id": "from_entity_id",
                "borrower_entity_id": "to_entity_id",
                "outstanding_eom": "amount_eom"
            })
            loan_as_arap["ic_type"] = "IC_LOAN"
            combined = pd.concat([ic_f, loan_as_arap], ignore_index=True)
            sankey_df = combined.nlargest(top_edges, "amount_eom")
        else:
            sankey_df = ic_f.nlargest(top_edges, "amount_eom")

        clicked_sk = render(ic_sankey(sankey_df, name_map), key="ih_sankey", height="580px")
        if clicked_sk and isinstance(clicked_sk, dict) and "data" in clicked_sk:
            d = clicked_sk["data"]
            if "source" in d and "target" in d:
                src, tgt = d["source"].split(" · ")[0], d["target"].split(" · ")[0]
                if ss.get("selected_pair") != (src, tgt):
                    ss["selected_pair"] = (src, tgt); st.rerun()

    elif c_mode == "B. Tương tác (Network)":
        st.markdown("""
> **Network Graph** — mỗi node là một pháp nhân, mỗi cạnh (edge) là giao dịch công nợ/vay nội bộ.
> Kích thước node tỷ lệ với **tổng giá trị giao dịch hai chiều**. Màu cạnh phân biệt AR/AP/Loan.
> Layout **Circular** thích hợp để nhìn tổng thể mạng lưới; **Force** (lực đẩy) tách cụm các nhóm ít kết nối.
> Click vào node để xem hồ sơ chi tiết đơn vị đó.
""")
        c1, c2 = st.columns([1, 3])
        with c1:
            layout = st.selectbox("Bố cục (Layout)", ["Circular", "Force"], key="ih_net_layout")
        with c2:
            show_ar = st.checkbox("Hiển thị giá trị AR/AP trên node", True, key="ih_net_ar")

        clicked_net = render(
            ic_network(ic_f, loan_f, ent, show_ar=show_ar, show_loan=show_loan, top_n=top_edges, layout=layout.lower()),
            key="ih_network", height="620px"
        )
        if clicked_net and isinstance(clicked_net, dict) and "name" in clicked_net:
            eid = clicked_net["name"].split(" · ")[0]
            if eid in ent["entity_id"].values and eid != ss.get("selected_entity"):
                ss["selected_entity"] = eid; st.rerun()

    else:
        st.markdown("""
> **Supply Chain Box Layout** — nhóm các pháp nhân theo **vị trí trong chuỗi cung ứng** (Sub-holding cluster).
> Mỗi ô (box) là một Khối kinh doanh; bên trong hiển thị từng công ty với số liệu:
> **Phải thu nội bộ** (IC AR) · **Phải trả nội bộ** (IC AP) · **Dư nợ Vay nội bộ**.
> Các mũi tên giữa node biểu diễn Top luồng giao dịch lớn nhất giữa các đơn vị.
> Dùng để đọc nhanh cấu trúc tài chính nội bộ theo chiều chuỗi cung ứng.
""")
        dot = supply_chain_graph(
            ent, ic_f, loan_f if show_loan else pd.DataFrame(columns=loan.columns),
            name_map, top_edges=top_edges
        )
        st.graphviz_chart(dot, use_container_width=True)

# ── View 3: External AR Risk ───────────────────────────────────────────────────
elif view_mode == "AR Nội bộ & Bên ngoài":
    st.markdown("""
**Cơ cấu Nợ Phải thu Khách hàng Bên ngoài** — phân tích mức độ tập trung rủi ro phải thu theo từng nhóm khách hàng.
Trả lời: *Đơn vị nào đang có dư nợ phải thu lớn nhất? Tập trung vào nhóm KH nào? Nếu KH đó mất khả năng thanh toán thì rủi ro lan rộng đến đâu?*
""")

    ar_p = dfs["fact_external_ar"][dfs["fact_external_ar"]["period_end"] == ss["period_end"]].copy()
    ar_df = ar_p.merge(ent[["entity_id", "entity_name", "subholding_code", "industry", "supply_chain_node"]], on="entity_id").merge(
        dfs["dim_client_group"][["client_group_id", "client_group_name", "industry_group"]], on="client_group_id"
    )

    with st.expander("Bộ lọc AR (Mở rộng để lọc chi tiết)", expanded=True):
        fa1, fa2, fa3 = st.columns(3)
        with fa1:
            cg_pick = st.multiselect("Lọc nhóm Khách hàng", ar_df["client_group_name"].unique(), key="ar_cg")
        with fa2:
            ig_pick = st.multiselect(
                "Lọc ngành KH (Industry Group)",
                options=sorted(ar_df["industry_group"].dropna().unique().tolist()),
                help="Nhóm ngành của khách hàng bên ngoài (VD: Utilities, Industrial, Energy...)",
                key="ar_ig"
            )
        with fa3:
            sub_ar = st.multiselect(
                "Lọc Khối (Sub-holding)",
                options=sorted(ar_df["subholding_code"].dropna().unique().tolist()),
                key="ar_sub"
            )

        fa4, fa5 = st.columns(2)
        with fa4:
            industry_ar = st.multiselect(
                "Lọc ngành nghề đơn vị",
                options=sorted(ar_df["industry"].dropna().unique().tolist()),
                key="ar_entity_ind"
            )
        with fa5:
            top_k = st.slider("Số nhóm KH hiển thị (Top-K)", 3, 15, 5, key="ar_topk")

    if cg_pick:
        ar_df = ar_df[ar_df["client_group_name"].isin(cg_pick)]
    if ig_pick:
        ar_df = ar_df[ar_df["industry_group"].isin(ig_pick)]
    if sub_ar:
        ar_df = ar_df[ar_df["subholding_code"].isin(sub_ar)]
    if industry_ar:
        ar_df = ar_df[ar_df["industry"].isin(industry_ar)]

    am1, am2, am3 = st.columns(3)
    am1.metric("Tổng AR bên ngoài", f"{ar_df['external_ar_eom'].sum()/1e9:,.1f} B")
    top1_cg = ar_df.groupby("client_group_name")["external_ar_eom"].sum().nlargest(1)
    if not top1_cg.empty:
        top1_name = top1_cg.index[0]
        top1_val = top1_cg.iloc[0]
        top1_share = top1_val / ar_df["external_ar_eom"].sum() if ar_df["external_ar_eom"].sum() > 0 else 0
        am2.metric(f"KH lớn nhất: {top1_name}", f"{top1_val/1e9:,.1f} B")
        am3.metric("Tỷ trọng Top 1 KH / Tổng AR", f"{top1_share:.1%}",
                   delta_color="inverse" if top1_share > 0.4 else "normal",
                   help="Ngưỡng cảnh báo: > 40% là tập trung rủi ro cao")

    ar_mode = st.segmented_control(
        "Chế độ xem",
        ["A. Cột Kép (Stacked Bar)", "B. Bản đồ nhiệt (Heatmap)"],
        default="A. Cột Kép (Stacked Bar)",
        key="ar_ab_test",
        label_visibility="collapsed"
    )

    if ar_mode == "A. Cột Kép (Stacked Bar)":
        st.markdown("""
> **Stacked Bar** — mỗi cột là một đơn vị, mỗi màu là một nhóm khách hàng.
> Chiều cao cột = tổng AR; màu sắc phân tầng cho thấy đơn vị nào **phụ thuộc quá nhiều vào một nhóm KH**.
""")
        from src.charts.bars import ar_stacked_bar
        render(ar_stacked_bar(ar_df, top_k=top_k), key="ih_ar_stack", height="450px")
    else:
        st.markdown("""
> **Heatmap** — trục X là đơn vị, trục Y là nhóm KH. Màu sắc ô = giá trị AR.
> Dễ nhìn để phát hiện **ô nóng** (hot spot) — tức cặp đơn vị – khách hàng có dư nợ đặc biệt lớn.
""")
        from src.charts.heatmap import ar_heatmap
        render(ar_heatmap(ar_df, top_k=top_k), key="ih_ar_heat", height="450px")

    # Detail table
    with st.expander("Bảng chi tiết AR theo Đơn vị × Khách hàng"):
        detail_tbl = (
            ar_df.groupby(["entity_name", "client_group_name", "industry_group"])["external_ar_eom"]
            .sum().reset_index()
            .sort_values("external_ar_eom", ascending=False)
            .assign(AR_Ty=lambda d: d["external_ar_eom"] / 1e9)
            .rename(columns={"entity_name": "Đơn vị", "client_group_name": "Nhóm KH",
                             "industry_group": "Ngành KH", "AR_Ty": "AR (Tỷ VND)"})
            [["Đơn vị", "Nhóm KH", "Ngành KH", "AR (Tỷ VND)"]]
        )
        st.dataframe(detail_tbl.style.format({"AR (Tỷ VND)": "{:,.2f}"}),
                     hide_index=True, use_container_width=True, height=280)

# ── View 4: Cashflow (Internal vs External) ────────────────────────────────────
elif view_mode == "Luân chuyển Dòng tiền":
    st.markdown("""
**Theo dõi hướng dòng tiền thực tế** — phân biệt giao dịch **Nội bộ** (giữa các đơn vị trong tập đoàn)
và **Bên ngoài** (thực sự chảy ra/vào hệ thống). Phân loại theo hoạt động: Kinh doanh / Đầu tư / Tài chính.
Dùng để nhận diện nhanh: *Tiền đang đi đâu? Luồng nào lớn nhất? Đơn vị nào đang thực sự tiêu tiền hay thu tiền?*
""")

    cf = dfs["fact_cash_flow"].copy()
    if "data_type" not in cf.columns:
        cf["data_type"] = "ACTUAL"
    available_periods_dt = sorted(cf["period_end"].unique())
    period_strs = [pd.Timestamp(p).strftime("%Y-%m") for p in available_periods_dt]

    with st.expander("Bộ lọc Đa Chiều (Mở rộng để lọc chi tiết)", expanded=True):
        c_time, c_dtype, c_scope, c_cat = st.columns(4)
        c_sub, c_line, c_cpty, c_stab = st.columns(4)
        c_entity, c_ind, c_scn, c_min = st.columns(4)

        with c_time:
            if period_strs:
                dt_range = st.select_slider(
                    "Chu kỳ Thời gian (Từ → Đến)",
                    options=period_strs,
                    value=(period_strs[max(0, len(period_strs) - 12)], period_strs[-1])
                )
            else:
                dt_range = (None, None)

        with c_dtype:
            pick_dtype = st.multiselect("Loại Dữ liệu", ["ACTUAL", "FORECAST"],
                                        default=["ACTUAL", "FORECAST"],
                                        help="ACTUAL: số liệu thực tế. FORECAST: dự báo (6% tăng trưởng/năm).")

        with c_scope:
            pick_scope = st.multiselect("Phạm vi Đối tác", ["NỘI BỘ", "BÊN NGOÀI"],
                                        default=["NỘI BỘ", "BÊN NGOÀI"])
        with c_cat:
            pick_cat = st.multiselect("Hoạt động dòng tiền",
                                      ["OPERATING", "INVESTING", "FINANCING"],
                                      default=["OPERATING", "INVESTING", "FINANCING"])
        with c_sub:
            pick_sub = st.multiselect("Khối (Sub-holding)",
                                      options=sorted(ent["subholding_code"].dropna().unique().tolist()),
                                      default=sorted(ent["subholding_code"].dropna().unique().tolist()))

        avail_lines = cf[cf["activity_category"].isin(pick_cat)]["line_item"].unique() if pick_cat else cf["line_item"].unique()
        with c_line:
            pick_line = st.multiselect("Hạng mục (Chỉ tiêu)", avail_lines)

        avail_cpty = cf[cf["scope"].isin(pick_scope)]["counterparty_type"].unique() if pick_scope else cf["counterparty_type"].unique()
        with c_cpty:
            pick_cpty = st.multiselect("Loại Đối tác", list(avail_cpty))

        with c_stab:
            pick_stab = st.multiselect("Tính Ổn định dòng tiền",
                                       ["ỔN ĐỊNH", "KHÔNG ỔN ĐỊNH"],
                                       help="Dòng tiền ổn định: lặp lại theo chu kỳ. Không ổn định: phát sinh bất thường.")

        with c_entity:
            company_ids = sorted(ent[ent["entity_type"] == "COMPANY"]["entity_id"].tolist())
            pick_entity = st.multiselect(
                "Lọc Đơn vị cụ thể",
                options=company_ids,
                format_func=lambda x: f"{x} · {name_map.get(x, x)}",
                key="cf_entity"
            )

        with c_ind:
            all_industries = sorted(ent["industry"].dropna().unique().tolist())
            pick_cf_ind = st.multiselect("Ngành nghề Đơn vị", options=all_industries, key="cf_industry")

        with c_scn:
            all_scn = sorted(ent["supply_chain_node"].dropna().unique().tolist())
            pick_cf_scn = st.multiselect(
                "Vị trí Chuỗi cung ứng",
                options=all_scn,
                help="Raw Material → Manufacturing → Assembly → Distribution → Retail",
                key="cf_scn"
            )

        with c_min:
            min_flow = st.number_input("Ngưỡng tối thiểu giao dịch (Tỷ VND)", min_value=0.0, value=0.0, step=0.5, key="cf_min_flow")

    # Apply filters
    if dt_range and dt_range[0] and dt_range[1]:
        start_dt = pd.to_datetime(dt_range[0] + "-01") + pd.offsets.MonthEnd(0)
        end_dt = pd.to_datetime(dt_range[1] + "-01") + pd.offsets.MonthEnd(0)
        cf = cf[(pd.to_datetime(cf["period_end"]) >= start_dt) & (pd.to_datetime(cf["period_end"]) <= end_dt)]

    if pick_dtype:
        cf = cf[cf["data_type"].isin(pick_dtype)]
    if pick_scope:
        cf = cf[cf["scope"].isin(pick_scope)]
    if pick_cat:
        cf = cf[cf["activity_category"].isin(pick_cat)]
    if pick_line:
        cf = cf[cf["line_item"].isin(pick_line)]
    if pick_cpty:
        cf = cf[cf["counterparty_type"].isin(pick_cpty)]
    if pick_stab:
        cf = cf[cf["stability"].isin(pick_stab)]
    if min_flow > 0:
        cf = cf[cf["flow_amount"].abs() >= min_flow * 1e9]

    # Entity dimension filters
    ent_cf_mask = pd.Series(True, index=ent.index)
    if pick_cf_ind:
        ent_cf_mask &= ent["industry"].isin(pick_cf_ind)
    if pick_cf_scn:
        ent_cf_mask &= ent["supply_chain_node"].isin(pick_cf_scn)
    filtered_cf_eids = set(ent[ent_cf_mask]["entity_id"].tolist())

    sub_ids = []
    if pick_sub:
        sub_ids = ent[ent["subholding_code"].isin(pick_sub)]["entity_id"].tolist()
    if pick_entity:
        sub_ids = list(set(sub_ids) & set(pick_entity)) if sub_ids else pick_entity

    if sub_ids:
        cf = cf[cf["from_entity_id"].isin(sub_ids) | cf["to_entity_id"].isin(sub_ids)]
    if filtered_cf_eids != set(ent["entity_id"].tolist()):
        cf = cf[cf["from_entity_id"].isin(filtered_cf_eids) | cf["to_entity_id"].isin(filtered_cf_eids)]

    # Summary metrics
    cm1, cm2, cm3 = st.columns(3)
    total_in = cf[cf["flow_amount"] > 0]["flow_amount"].sum()
    total_out = cf[cf["flow_amount"] < 0]["flow_amount"].sum()
    cm1.metric("Tổng Thu (Dòng vào)", f"{total_in/1e9:,.1f} B")
    cm2.metric("Tổng Chi (Dòng ra)", f"{abs(total_out)/1e9:,.1f} B")
    cm3.metric("Ròng (Net Flow)", f"{(total_in + total_out)/1e9:,.1f} B",
               delta_color="normal" if (total_in + total_out) >= 0 else "inverse")

    cf_mode = st.segmented_control(
        "Biểu đồ Trực quan hóa",
        ["A. Dòng chảy Tiền mặt (Sankey)", "B. Tương tác (Network Graph)"],
        default="A. Dòng chảy Tiền mặt (Sankey)",
        key="cf_ab_viz",
        label_visibility="collapsed"
    )

    if cf_mode == "A. Dòng chảy Tiền mặt (Sankey)":
        st.markdown("""
> **Cashflow Sankey** — mỗi dải biểu diễn một luồng tiền thực tế từ đơn vị **gốc** sang đơn vị **đích**.
> Độ rộng dải = giá trị tuyệt đối dòng tiền. Màu phân biệt loại hoạt động (Operating / Investing / Financing).
> Dùng để nhận diện **đơn vị trung chuyển vốn** và **điểm rò rỉ thanh khoản** trong hệ thống.
""")
        from src.charts.sankey import cf_sankey
        sankey_df = cf.rename(columns={"activity_category": "ic_type", "flow_amount": "amount_eom"}).copy()
        sankey_df["amount_eom"] = sankey_df["amount_eom"].abs()
        render(cf_sankey(sankey_df, name_map, top_n=30), key="cf_sankey", height="450px")
    else:
        st.markdown("""
> **Cashflow Network Graph** — node = đơn vị, cạnh = dòng tiền thực tế hai chiều.
> Độ dày cạnh = tổng giá trị tuyệt đối. Hướng mũi tên = hướng dòng tiền ròng.
> Layout Force giúp **tách nhóm đơn vị độc lập** (ít giao dịch với nhau).
""")
        from src.charts.network import cashflow_network
        cl1, cl2 = st.columns([1, 3])
        with cl1:
            layout_cf = st.selectbox("Bố cục thuật toán", ["Circular", "Force"], key="cf_net_layout")
        with cl2:
            top_edges_cf = st.slider("Top-N giao dịch hiển thị", 5, 100, 30, key="cf_net_n")
        render(cashflow_network(cf, ent, name_map, top_n=top_edges_cf, layout=layout_cf.lower()),
               key="cf_network", height="550px")

    st.markdown("#### Bảng Kê Lưu chuyển Tiền tệ")
    st.dataframe(
        cf.sort_values(by="period_end", ascending=False)
          .assign(flow_amount_bil=lambda x: x["flow_amount"] / 1e9)
          .rename(columns={"activity_category": "Phân loại", "line_item": "Hạng mục",
                           "counterparty_type": "Loại Đối tác", "scope": "Phạm vi",
                           "flow_amount_bil": "Giá trị (Tỷ VND)", "period_end": "Tháng",
                           "data_type": "Loại DL"})
          [["Tháng", "Loại DL", "Phạm vi", "Phân loại", "Hạng mục", "Loại Đối tác", "Giá trị (Tỷ VND)"]],
        use_container_width=True, hide_index=True, height=300
    )
