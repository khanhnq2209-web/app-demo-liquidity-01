"""Internal Holding Banking Model — Liquidity, Credit Limits, and Optimization."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.charts.common import render
from src.filters import filter_by_entities, in_scope
from src.state import ensure_state, render_sidebar
from src.ui import inject_css

st.set_page_config(page_title="Internal Bank", layout="wide")
inject_css()
dfs = ensure_state()
render_sidebar(dfs)
st.markdown("## Điều hành Nguồn vốn (Group Treasury)")

ss = st.session_state
ent = dfs["dim_entity"]
scope = in_scope(ent)
name_map = dict(zip(ent["entity_id"], ent["entity_name"]))

cash_hist = filter_by_entities(dfs["fact_cash_balance"], "entity_id", scope)
credit_p = filter_by_entities(dfs["fact_credit"], "entity_id", scope)
credit_curr = credit_p[credit_p["period_end"] == ss["period_end"]]

view_mode = st.radio("Cửa sổ Điều hành", 
                     ["Dashboard Thanh khoản", "Hạn mức & Chi phí Vốn", "Bot Tối ưu (Simulation)", "Dự phóng Dòng tiền (Forward Plan)"], 
                     horizontal=True, label_visibility="collapsed")

# ── View 1: Liquidity Dashboard ──────────────────────────────────────────────────
if view_mode == "Dashboard Thanh khoản":
    st.markdown("**Quỹ tiền mặt khả dụng và Sức chịu đựng dự trữ (Runway) của các Đơn vị trực thuộc.**")

    all_periods = sorted(cash_hist["period_end"].unique())
    last_12 = all_periods[-12:] if len(all_periods) >= 12 else all_periods
    hist_12 = cash_hist[cash_hist["period_end"].isin(last_12)]
    period_labels = [pd.Timestamp(p).strftime("%Y-%m") for p in last_12]

    latest_cash = hist_12[hist_12["period_end"] == hist_12["period_end"].max()].copy()
    prev_cash   = hist_12[hist_12["period_end"] == (sorted(hist_12["period_end"].unique())[-2] if len(sorted(hist_12["period_end"].unique())) >= 2 else hist_12["period_end"].max())]
    cur_total = float(latest_cash["cash_eom"].sum())
    prv_total = float(prev_cash["cash_eom"].sum()) or 1

    k1, k2, k3 = st.columns(3)
    k1.metric("Tổng Quỹ tiền mặt (Gộp)", f"{cur_total/1e9:,.1f} B",
              f"{(cur_total-prv_total)/prv_total*100:+.1f}% MoM")
    avg_burn = float((hist_12.groupby("period_end")["cash_eom"].sum().diff().dropna()).mean())
    k2.metric("Burn Rate (Trung bình ròng/tháng)", f"{avg_burn/1e9:+.1f} B",
              help="Dương = Thặng dư. Âm = Tiêu hao tiền mặt.")
    months_runway = int(cur_total / abs(avg_burn)) if avg_burn < 0 else 99
    k3.metric("Sức chịu đựng tiền mặt (Runway Hệ thống)",
              f"{months_runway} tháng" if months_runway < 99 else "An toàn",
              delta_color="inverse" if months_runway < 6 else "normal")

    st.markdown("#### Phân bổ Cục diện Tiền mặt (Liquidity Allocation)")
    liq_mode = st.segmented_control("Chế độ xem A/B", ["A. Cột (Bar)", "B. Mảng màu (Heatmap)"], default="A. Cột (Bar)", key="liq_ab", label_visibility="collapsed")
    from src.charts.bars import cash_bar
    from src.charts.heatmap import cash_heatmap
    
    if liq_mode == "A. Cột (Bar)":
        render(cash_bar(latest_cash, name_map), key="liq_bar", height="350px")
    else:
        render(cash_heatmap(latest_cash, name_map), key="liq_heat", height="350px")

    st.markdown("#### Bảng Đo lường Tốc độ Tiêu hao & Phòng vệ")
    rows = []
    for eid in scope:
        e_hist = hist_12[hist_12["entity_id"] == eid].sort_values("period_end")
        if len(e_hist) < 2: continue
        burns = e_hist["cash_eom"].diff().dropna()
        avg_b = float(burns.mean())
        latest_c = float(e_hist["cash_eom"].iloc[-1])
        runway = int(latest_c / abs(avg_b)) if avg_b < 0 else 99
        rag = "Rủi ro cao" if (avg_b < 0 and runway < 6) else ("Tiêu hao" if avg_b < 0 else "Tạo thặng dư")
        rows.append({"Đơn vị": name_map.get(eid, eid),
                     "Tiền mặt (Tỷ)": round(latest_c/1e9, 2),
                     "Trung bình Δ (Tỷ/tháng)": round(avg_b/1e9, 2),
                     "Runway (Tháng)": runway if runway < 99 else "∞",
                     "Trạng thái": rag})
    if rows:
        df_display = pd.DataFrame(rows).sort_values("Trung bình Δ (Tỷ/tháng)")
        st.dataframe(df_display, hide_index=True, use_container_width=True)

# ── View 2: Credit Limit & Cost of Funds ─────────────────────────────────────────
elif view_mode == "Hạn mức & Chi phí Vốn":
    st.markdown("**Kiểm soát mảng tín dụng ngoài hệ thống (External Bank Limits) và chi phí vốn đắt đỏ.**")
    
    if credit_curr.empty:
         st.warning("Không có dữ liệu hạn mức tín dụng.")
    else:
         total_lim = credit_curr["credit_limit"].sum()
         total_util = credit_curr["credit_utilized"].sum()
         overall_rt = total_util / total_lim if total_lim else 0
         
         c1, c2, c3 = st.columns(3)
         c1.metric("Tổng Hạn mức Tín dụng Group", f"{total_lim/1e9:,.1f} B")
         c2.metric("Đã Dùng (Dư nợ Vay)", f"{total_util/1e9:,.1f} B")
         c3.metric("Tỷ lệ Nắm giữ (Utilization)", f"{overall_rt:.1%}", 
                   delta_color="inverse" if overall_rt > 0.8 else "normal", 
                   help="Cảnh báo > 80% là căng thẳng thanh khoản.")
         
         st.markdown("#### Phân bổ Cấp vốn & Lãi suất ngoài (Cost of Debt)")
         c_df = credit_curr.copy()
         c_df["util_%"] = c_df["credit_utilized"] / c_df["credit_limit"]
         c_df["interest_str"] = c_df["interest_rate"].apply(lambda x: f"{x:.2%}") if "interest_rate" in c_df.columns else "N/A"
         
         plot_df = c_df.sort_values("util_%", ascending=False)
         data_bar = [{"value": float(row["util_%"]), 
                      "itemStyle": {"color": "#dc2626" if row["util_%"] > 0.85 else "#1a73e8"}} 
                     for _, row in plot_df.iterrows()]
         
         option = {
             "tooltip": {"trigger": "axis", "formatter": "{b}: {c}"},
             "grid": {"top": 20, "bottom": 60, "left": 40, "right": 20},
             "xAxis": {"type": "category", "data": [name_map.get(e,e) for e in plot_df["entity_id"]], "axisLabel": {"rotate": 30}},
             "yAxis": {"type": "value", "max": 1, "axisLabel": {"formatter": "{value}"}},
             "series": [{"type": "bar", "data": data_bar}]
         }
         render(option, height="300px", key="ib_credit_bar")
         
         st.dataframe(
             c_df.rename(columns={"entity_id": "Mã ĐV", "credit_limit": "H.Mức", 
                                  "credit_utilized": "Đã dùng", "util_%": "Tỷ lệ", "interest_str": "Lãi suất (%)"})
                 .assign(H_Mức=lambda d: d["H.Mức"]/1e9, Đã_dùng=lambda d: d["Đã dùng"]/1e9, Tên=lambda d: d["Mã ĐV"].map(name_map))
                 [["Tên", "H_Mức", "Đã_dùng", "Tỷ lệ", "Lãi suất (%)"]]
                 .sort_values("Tỷ lệ", ascending=False)
                 .style.format({"H_Mức": "{:.1f} B", "Đã_dùng": "{:.1f} B", "Tỷ lệ": "{:.1%}"}),
             hide_index=True, use_container_width=True
         )

# ── View 3: Optimization Simulator ───────────────────────────────────────────────
elif view_mode == "Bot Tối ưu (Simulation)":
    st.markdown("**Mô phỏng Giao dịch Pooling Vốn: Phạt Đơn vị thừa tiền đi cho vay nội bộ với Đơn vị đang vay kịch trần lãi cao.**")
    
    st.info("Hệ thống quét các đơn vị đang chịu lãi suất vay ngân hàng ngoài (External Debt) > 8% và ghép cặp với đơn vị đang thừa tiền nhàn rỗi trong quỹ để tài trợ chéo (Inter-company loan) với lãi suất nội bộ ưu đãi (e.g. 5.5%).")
    
    if not credit_curr.empty and "interest_rate" in credit_curr.columns:
        latest_cash = cash_hist[cash_hist["period_end"] == cash_hist["period_end"].max()].copy()
        
        INTERNAL_RATE = st.slider("Lãi suất Điều chuyển Nội bộ Target (%)", 4.0, 10.0, 5.5, 0.1) / 100.0
        
        # Borrowers: Have utilized credit and pay higher external interest than internal rate
        borrowers = credit_curr[(credit_curr["interest_rate"] > INTERNAL_RATE) & (credit_curr["credit_utilized"] > 1e9)].copy()
        borrowers["cost_saving_spread"] = borrowers["interest_rate"] - INTERNAL_RATE
        
        # Lenders: Have excess cash (e.g., > 10 B)
        lenders = latest_cash[latest_cash["cash_eom"] > 10e9].copy()
        lenders["excess_cash"] = lenders["cash_eom"] - 10e9  # Keep at least 10B buffer
        
        if borrowers.empty or lenders.empty:
            st.warning("Hiện tại không tìm thấy cơ hội Pool vốn hợp lệ (Thiếu đơn vị vay lãi cao hoặc Đơn vị thừa quỹ).")
        else:
            simul_log = []
            total_savings = 0.0
            
            # Simple matching algorithm (Greedy algorithm maximizing savings spread)
            b_list = borrowers.sort_values("cost_saving_spread", ascending=False).to_dict('records')
            l_list = lenders.sort_values("excess_cash", ascending=False).to_dict('records')
            
            for b in b_list:
                amt_needed = b["credit_utilized"]
                b_eid = b["entity_id"]
                spread = b["cost_saving_spread"]
                ext_rate = b["interest_rate"]
                
                for l in l_list:
                    if l["excess_cash"] <= 0 or amt_needed <= 0 or b_eid == l["entity_id"]:
                        continue
                    
                    l_eid = l["entity_id"]
                    transaction_amt = min(amt_needed, l["excess_cash"])
                    
                    amt_needed -= transaction_amt
                    l["excess_cash"] -= transaction_amt
                    
                    saving = transaction_amt * spread
                    total_savings += saving
                    
                    simul_log.append({
                        "Bên Cho vay (Thừa vốn)": name_map.get(l_eid, l_eid),
                        "Bên Vay (Đảo nợ)": name_map.get(b_eid, b_eid),
                        "Quy mô Bơm vốn (Tỷ)": round(transaction_amt / 1e9, 2),
                        "Lãi cũ NH Ngoài": f"{ext_rate:.1%}",
                        "Tiết kiệm (Spread)": f"{spread:.2%}",
                        "Lợi ích Chi phí 1 Năm (Tỷ VNĐ)": round(saving / 1e9, 2)
                    })
            
            c1, c2 = st.columns(2)
            c1.metric("Tổng Lợi ích Điều chuyển (Tiết kiệm/Năm)", f"{total_savings/1e9:.2f} B")
            c2.metric("Số Giao dịch Pooling Đề xuất", len(simul_log))
            
            if simul_log:
                st.markdown("#### Kế hoạch Giao dịch Tối ưu (Smart Routing)")
                st.dataframe(pd.DataFrame(simul_log), hide_index=True, use_container_width=True)
            else:
                st.info("Không có ghép cặp nào thỏa mãn điều kiện an toàn quỹ.")
    else:
        st.error("Lỗi dữ liệu: Cần trường interest_rate trong fact_credit_summary để kích hoạt Bot.")

# ── View 4: Forward Liquidity Plan (V03) ───────────────────────────────────────
elif view_mode == "Dự phóng Dòng tiền (Forward Plan)":
    st.markdown("**Mô phỏng sức khỏe dòng tiền (12 tháng tới) qua các Giả định Thu hồi nợ và Chi phí Vận hành.**")
    
    comp_df = ent[ent["entity_type"] == "COMPANY"].copy()
    company_ids = [e for e in comp_df["entity_id"].tolist() if e in scope]
    sel_eid = st.selectbox("Chọn Đơn vị", company_ids, format_func=lambda x: f"{x} · {name_map.get(x, x)}", key="ib_fwd_eid")
    
    # Get current Cash and AR for selected entity
    curr_cash_df = cash_hist[cash_hist["period_end"] == cash_hist["period_end"].max()]
    curr_cash = curr_cash_df[curr_cash_df["entity_id"] == sel_eid]["cash_eom"].sum()
    
    ar_df = dfs["fact_external_ar"][dfs["fact_external_ar"]["period_end"] == ss["period_end"]]
    curr_ar = ar_df[ar_df["entity_id"] == sel_eid]["external_ar_eom"].sum()
    
    # UI Inputs
    p1, p2, p3 = st.columns(3)
    coll_days = p1.slider("Vòng quay Phải thu (Collection Days)", 30, 180, 60, 5)
    opex_ratio = p2.slider("Tỷ lệ Chi phí HĐKD trên AR (%)", 0, 50, 10, 1) / 100.0
    ic_repay = p3.slider("Phần trăm Phải trả nội bộ (/tháng)", 0, 20, 5, 1) / 100.0
    
    st.markdown(f"**Khởi điểm:** Tiền mặt hiện tại là `{curr_cash/1e9:,.1f} B`. Nợ Phải thu (AR) là `{curr_ar/1e9:,.1f} B`.")
    
    # Calculation Loop
    cash_val = curr_cash
    ar_val = curr_ar
    proj_vals = []
    gap_detect = 0
    
    for i in range(12):
        ar_collection = (ar_val / coll_days) * 30
        operating = ar_val * opex_ratio
        ic_cash_out = ar_val * ic_repay # Simplified proxy
        
        cash_next = cash_val + ar_collection - operating - ic_cash_out
        proj_vals.append(round(cash_next / 1e9, 2))
        
        if cash_next < 0 and gap_detect == 0:
            gap_detect = i + 1
            
        cash_val = cash_next
        
    k1, k2 = st.columns(2)
    min_cash = min(proj_vals)
    k1.metric("Runway (Sức chịu đựng)", f"{gap_detect} tháng tới cạn tiền" if gap_detect > 0 else "An toàn", delta_color="inverse" if gap_detect > 0 else "normal")
    k2.metric("Lỗ hổng Dòng tiền Sâu nhất (Funding Gap)", f"{min_cash:,.1f} B" if min_cash < 0 else "Không thâm hụt")
    
    st.markdown("#### Cảnh báo Viễn cảnh Dự phóng (Forward Risk Chart)")
    fwd_mode = st.segmented_control("Chế độ xem A/B", ["A. Đường Tổng (Aggregated)", "B. Nhiều đường (Multi-line)"], default="A. Đường Tổng (Aggregated)", key="fwd_ab", label_visibility="collapsed")
    months_label = [f"Tháng {i+1}" for i in range(12)]
    
    if fwd_mode == "A. Đường Tổng (Aggregated)":
        option = {
            "tooltip": {"trigger": "axis", "formatter": "{b}<br/>Dự kiến: {c} B"},
            "xAxis": {"type": "category", "data": months_label},
            "yAxis": {"type": "value", "name": "Cash (B)"},
            "series": [{
                "data": proj_vals,
                "type": "line",
                "smooth": True,
                "areaStyle": {"color": "rgba(220, 38, 38, 0.1)" if min_cash < 0 else "rgba(22, 163, 74, 0.1)"},
                "itemStyle": {"color": "#dc2626" if min_cash < 0 else "#16a34a"},
                "markLine": {"data": [{"yAxis": 0}], "lineStyle": {"color": "#ef4444"}}
            }]
        }
    else:
        # Multi-line simulation logic! We simulate the loop across the top 5 entities.
        # This showcases A/B testing of advanced logic vs aggregated logic.
        top_5_entities = curr_cash_df.nlargest(5, "cash_eom")["entity_id"].tolist()
        series_data = []
        for e in top_5_entities:
            c_val = curr_cash_df[curr_cash_df["entity_id"] == e]["cash_eom"].sum()
            a_val = ar_df[ar_df["entity_id"] == e]["external_ar_eom"].sum()
            e_proj = []
            for i in range(12):
                a_coll = (a_val / coll_days) * 30
                op = a_val * opex_ratio
                icc = a_val * ic_repay
                c_val = c_val + a_coll - op - icc
                e_proj.append(round(c_val / 1e9, 2))
            series_data.append({
                "name": name_map.get(e, e).split(" · ")[0],
                "type": "line",
                "smooth": True,
                "data": e_proj
            })
            
        option = {
            "tooltip": {"trigger": "axis"},
            "legend": {"top": 0},
            "grid": {"top": 40},
            "xAxis": {"type": "category", "data": months_label},
            "yAxis": {"type": "value", "name": "Cash (B)"},
            "series": series_data
        }
        
    render(option, key="fwd_line", height="350px") 

