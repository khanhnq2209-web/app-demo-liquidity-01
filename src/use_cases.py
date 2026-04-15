"""Use-case reference extracted from doc/overview.md (business questions & KPIs).

Each entry is paired with a chart block so viewers see which business question
it answers.
"""
from __future__ import annotations

USE_CASES: dict[str, dict[str, str]] = {
    # --- Overview page ---
    "kpi_cards": {
        "title": "Bảng điều khiển Tích hợp",
        "questions": "Q4–Q7, Q11, Q14",
        "desc": "Tóm tắt nhanh về thanh khoản (tiền mặt), dư nợ (AR), vay nội bộ, và hạn mức tín dụng.",
    },
    "ranking": {
        "title": "Xếp hạng Tiền mặt + Phải Thu + Nội bộ",
        "questions": "Q4, Q8, Q13",
        "desc": "Đơn vị nào cầm nhiều tiền nhất, dư nợ lớn nhất, và tỷ trọng nội bộ cao nhất. Click để xem chi tiết.",
    },
    "cash_treemap": {
        "title": "Phân bổ Tiền mặt (Q4–Q5)",
        "questions": "Q4, Q5",
        "desc": "Tiền mặt đang nằm ở đâu trong tập đoàn? Phân bổ đồng đều hay tập trung cục bộ?",
    },
    "ar_stacked_bar": {
        "title": "Mức độ Tập trung AR theo Nhóm KH (Q9–Q10)",
        "questions": "Q9, Q10",
        "desc": "Tập đoàn có phụ thuộc vào 1 nhóm khách hàng không (VD: EVN)? Rủi ro lây nhiễm chéo?",
    },
    "cash_ar_trend": {
        "title": "Xu hướng Tiền mặt & Phải thu (Q6, Q7)",
        "questions": "Q6, Q7",
        "desc": "Chuỗi thời gian 12 tháng giúp phát hiện cạn kiệt thanh khoản sớm hoặc dư nợ tăng bất thường.",
    },
    # --- Relationships page ---
    "ownership_tree": {
        "title": "Cấu trúc Sở hữu (Q1)",
        "questions": "Q1",
        "desc": "Ai sở hữu ai? Các đơn vị được tổ chức như thế nào dưới Khối A (Hạ tầng) và Khối B (Điện lực)?",
    },
    "ownership_network": {
        "title": "Mạng lưới Sở hữu + Nội bộ (Q2–Q3, Q13)",
        "questions": "Q2, Q3, Q13",
        "desc": "Phát hiện sở hữu chéo phức tạp (Q2), nhận diện đơn vị trung tâm (Q3), và các kênh giao dịch nội khối lớn nhất (Q13).",
    },
    # --- Exposure AR page ---
    "ar_heatmap": {
        "title": "Biểu đồ Nhiệt Phân công nợ AR (Q8–Q10)",
        "questions": "Q8, Q9, Q10",
        "desc": "Hàng = công ty, Cột = nhóm khách hàng. Nhận diện các đơn vị có khoản phải thu lớn nhất tập trung vào cùng một nhóm KH.",
    },
    "ar_entity_breakdown": {
        "title": "Chi tiết AR theo Đơn vị (Q8)",
        "questions": "Q8",
        "desc": "Chi tiết các khoản Phải thu của một đơn vị cụ thể nhằm đánh giá rủi ro thu hồi chuyên sâu.",
    },
    # --- Intercompany ---
    "ic_kpis": {
        "title": "Vị thế Giao dịch Nội bộ (Q11, Q12)",
        "questions": "Q11, Q12",
        "desc": "Quy mô Cho vay/Đi vay ròng. Xác định các Đơn vị cấp vốn cốt lõi.",
    },
    "ic_sankey": {
        "title": "Dòng chảy Nội bộ — Sankey (Q12–Q13)",
        "questions": "Q12, Q13",
        "desc": "Hướng dòng tiền từ Chủ nợ sang Con nợ. Độ dày = Quy mô.",
    },
    "ic_network_view": {
        "title": "Cấu trúc Mạng lưới Nội bộ — Network (Q13)",
        "questions": "Q13",
        "desc": "Bản đồ mạng lưới đồ thị trực quan hóa rủi ro chéo nội khối.",
    },
    "ic_supply_chain": {
        "title": "Góc nhìn Chuỗi Giá trị (Q11–Q13)",
        "questions": "Q11, Q12, Q13",
        "desc": "Ánh xạ giao dịch nội bộ theo từng mắt xích chuỗi giá trị.",
    },
    "ic_pair_table": {
        "title": "Top Các Cặp Giao dịch Nội bộ (Q13)",
        "questions": "Q13",
        "desc": "Kiểm tra dư nợ song phương rủi ro nhất hệ thống.",
    },
    # --- Credit ---
    "credit_table": {
        "title": "Bảng Sử dụng Hạn mức Tín dụng (Q14–Q15)",
        "questions": "Q14, Q15",
        "desc": "Đơn vị nào đang chạm ngưỡng hạn mức (>85%)? Hạn mức tín dụng nhóm có được phân bổ hiệu quả không?",
    },
    "credit_bar": {
        "title": "Mức độ Sử dụng theo Đơn vị (Q14)",
        "questions": "Q14",
        "desc": "Biểu đồ cột thể hiện tỷ lệ sử dụng. Cột đo cảnh báo các đơn vị vượt ngưỡng 85% — áp lực huy động vốn cục bộ.",
    },
    # --- Cash Flow page ---
    "cf_waterfall": {
        "title": "Thác Dòng tiền (Q5–Q7)",
        "questions": "Q5, Q6, Q7",
        "desc": "MỞ ĐẦU → KD → ĐẦU TƯ → TÀI CHÍNH → KẾT THÚC. Tiền mặt được tạo ra và tiêu thụ như thế nào.",
    },
    "cf_stability": {
        "title": "Dòng tiền Ổn định vs Biến động (Q7)",
        "questions": "Q7",
        "desc": "Tách biệt giữa Dòng tiền ỔN ĐỊNH (biên độ ±10%) so với BẤT ỔN. Mức độ bất ổn cao = Khó dự báo thanh khoản.",
    },
    "cf_scope": {
        "title": "Dòng tiền Ngoài vs Nội bộ (Q11–Q13)",
        "questions": "Q11, Q12, Q13",
        "desc": "BÊN NGOÀI = Đối tác thứ 3; NỘI BỘ = Trong tập đoàn. Phản ánh quy mô dịch chuyển vốn thực giữ lại.",
    },
    "cf_lines": {
        "title": "Khoản mục Thu/Chi lớn nhất (Q5–Q6)",
        "questions": "Q5, Q6",
        "desc": "Những tác nhân chính chi phối thay đổi tiền mặt lớn nhất trong kỳ.",
    },
    "cf_counterparty": {
        "title": "Dòng tiền theo Đối tác (Q9–Q10)",
        "questions": "Q9, Q10",
        "desc": "EVN / Khách hàng / Đại lý / Nội bộ — Đo lường mức độ phụ thuộc dòng tiền thu được từ 1 đối tác trọng điểm.",
    },
    # --- Alerts / data quality ---
    "alerts_banner": {
        "title": "Tín hiệu Cảnh báo Trọng yếu",
        "questions": "Q6, Q9, Q11, Q14",
        "desc": "Cảnh báo tiền mặt giảm 3 kỳ, KH Top 1 >30%, Tín dụng >85%, và Đột biến GD nội bộ.",
    },
}
