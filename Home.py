"""Group Relationship & Liquidity Intelligence Platform — Home."""
from __future__ import annotations

import streamlit as st
from src.state import ensure_state, render_sidebar
from src.ui import inject_css

st.set_page_config(page_title="Hệ thống Quản trị Thanh khoản BOM", layout="wide", initial_sidebar_state="expanded")
inject_css()

dfs = ensure_state()
render_sidebar(dfs)

st.markdown("# Nền tảng Trí tuệ Thanh khoản (BOM Liquidity & Risk Platform)")
st.caption("Công cụ Hỗ trợ Ra Quyết định (Decision Support System) cao cấp dành riêng cho Ban Lãnh đạo, CFO và Giám đốc Quản trị Rủi ro (CRO).")

period = st.session_state["period_end"]
st.info(f"**Cập nhật số liệu mới nhất đến Vĩ mô:** `{period.strftime('%Y-%m')}`")

st.divider()

st.markdown("""
## Hướng dẫn Cấu trúc Nền tảng (Navigation Playbook)

Nền tảng được thiết kế theo cấu trúc **4 Màn hình Quản trị Cốt lõi**, mô phỏng chính xác mô hình Ngân hàng Nội bộ (In-House Bank) và Quản trị Rủi ro Tập đoàn:

### 1. Báo cáo Lãnh đạo (Executive Summary)
- Tóm tắt "sức khỏe" nhanh chóng thông qua Trợ lý AI phân tích dòng tiền và các Tín hiệu Cảnh báo Trọng yếu (Cạn kiệt tiền mặt, Lạm dụng hạn mức > 85%, Đột biến giao dịch nội bộ).
- Xác định điểm nghẽn dòng tiền nằm ở đâu với Bảng Xếp hạng rủi ro tổng hợp.

### 2. Quản trị Rủi ro & Phơi nhiễm (Risk & Exposure)
- **Cấu trúc Sở hữu & Phơi nhiễm Nội bộ**: Giám sát dòng vốn luân chuyển (Sankey Flow / Network) và bản đồ Chuỗi Cung ứng (Supply Chain).
- **Rủi ro Đối ngoại**: Bóc tách rủi ro tập trung vào các nhóm Khách hàng lớn (External AR) qua Heatmap và Stacked Bar.

### 3. Điều hành Nguồn vốn (Treasury & Cash Intelligence)
- Cửa sổ Quản trị Nguồn vốn và Thanh khoản Tập đoàn.
- **Tiêu điểm**: Triển khai các chính sách điều tiết vốn nội bộ nhằm tối ưu chi phí sử dụng vốn (Cost of Capital). Mô phỏng dòng tiền thả nổi và dư địa tín dụng hợp lệ cho từng đơn vị phụ thuộc.
""")

st.divider()

st.markdown("### Quy tắc Bộ lọc Ngữ cảnh (Global Context Filters)")
st.markdown("""
Sử dụng Sidebar (Thanh công cụ bên trái) để điều hướng các góc nhìn:
- **Thời gian phân tích**: Dữ liệu có thể tổng hợp theo Tháng hoặc Quý.
- **Phân tách Khối Kinh doanh**: Hệ thống cho phép bóc tách độc lập Khối Hạ tầng (Hatang) và Khối Điện lực (Electric).
""")
