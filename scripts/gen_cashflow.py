"""Regenerate fact_cash_flow.csv with full coverage of all filter dimensions."""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path

RNG = np.random.default_rng(42)
DATA_DIR = Path(__file__).parent.parent / "data"

# ── Load reference data ───────────────────────────────────────────────────────
ent = pd.read_csv(DATA_DIR / "dim_entity.csv", encoding="utf-8-sig")
companies = ent[ent["entity_type"] == "COMPANY"]["entity_id"].tolist()
all_internal = ent["entity_id"].tolist()

# ── Time periods (48 months) ──────────────────────────────────────────────────
periods = pd.date_range("2022-04-30", periods=48, freq="ME").strftime("%Y-%m-%d").tolist()

# ── Client group → counterparty_type mapping ──────────────────────────────────
# For BÊN NGOÀI rows: from_entity_id = CG, to_entity_id = company
CG_TYPE = {
    "CG01": "EVN",           # Utilities dominant customer
    "CG02": "Khách hàng",    # Industrial customer
    "CG03": "Nhà đầu tư",    # Real-estate / equity partner
    "CG04": "Nhà thầu",      # Construction contractor
    "CG05": "Nhà cung cấp",  # Steel/materials supplier
    "CG06": "Nhà cung cấp",  # Energy/petro supplier
    "CG07": "Khách hàng",    # Retail end-user
    "CG08": "Ngân hàng",     # Other → reused as bank proxy
}

# Government tax entity (we'll use CG08 but override ctype to Cơ quan nhà nước)
GOV_CG = "CG08"

# ── Line-item rules ───────────────────────────────────────────────────────────
# Each rule: (scopes, ext_cg_pool, ctype_int, direction, stability_bias, scale_B)
#   scopes: list of applicable scopes
#   ext_cg_pool: which CGs can appear as counterparty (BÊN NGOÀI)
#   ctype_int: counterparty_type label for NỘI BỘ rows
#   direction: 'in' | 'out' | 'mixed'
#   stability_bias: float 0-1, P(ỔN ĐỊNH)
#   scale_B: (min, max) in billions VND

RULES = {
    # ── OPERATING ──────────────────────────────────────────────────────────────
    "Dự thu": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG01", "CG02", "CG07", "CG08"], ctype_int=None,
        direction="in", stab=0.70, scale=(5, 80),
    ),
    "Lợi nhuận thuần trước thuế": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG01", "CG02", "CG07"], ctype_int=None,
        direction="in", stab=0.60, scale=(2, 40),
    ),
    "Khấu hao TSCĐ": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG05", "CG06"], ctype_int=None,
        direction="in", stab=0.85, scale=(1, 20),
    ),
    "Dự phòng": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG01", "CG07", "CG08"], ctype_int=None,
        direction="out", stab=0.30, scale=(0.5, 10),
    ),
    "Lãi/lỗ do đánh giá lại các khoản mục tiền tệ có gốc ngoại tệ": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG08"], ctype_int=None,
        direction="mixed", stab=0.20, scale=(0.1, 5),
    ),
    "Lãi/lỗ từ hoạt động đầu tư": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG03", "CG08"], ctype_int=None,
        direction="mixed", stab=0.25, scale=(0.5, 15),
    ),
    "Chi phí lãi vay": dict(
        act="OPERATING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="out", stab=0.80, scale=(0.5, 12),
    ),
    "Tăng/giảm các khoản phải thu": dict(
        act="OPERATING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG01", "CG02", "CG07", "CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="mixed", stab=0.40, scale=(1, 50),
    ),
    "Tăng/giảm hàng tồn kho": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG05", "CG06"], ctype_int=None,
        direction="mixed", stab=0.35, scale=(1, 30),
    ),
    "Tăng/giảm các khoản phải trả": dict(
        act="OPERATING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG04", "CG05", "CG06"], ctype_int="Nội bộ Tập đoàn",
        direction="mixed", stab=0.45, scale=(1, 35),
    ),
    "Tăng/giảm chi phí trả trước": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG04", "CG05"], ctype_int=None,
        direction="mixed", stab=0.40, scale=(0.5, 10),
    ),
    "Tăng/giảm TSCĐ khác": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG04", "CG05"], ctype_int=None,
        direction="mixed", stab=0.30, scale=(0.5, 8),
    ),
    "Lãi vay đã trả": dict(
        act="OPERATING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="out", stab=0.80, scale=(0.3, 8),
    ),
    "Thuế TNDN đã trả": dict(
        act="OPERATING", scopes=["BÊN NGOÀI"],
        ext_cg=[GOV_CG], ctype_int=None,
        direction="out", stab=0.70, scale=(0.5, 15),
        ctype_override="Cơ quan nhà nước",
    ),
    "Tiền thu từ hoạt động kinh doanh khác": dict(
        act="OPERATING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG07", "CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="in", stab=0.30, scale=(0.5, 20),
    ),
    "Tiền chi khác cho hoạt động kinh doanh": dict(
        act="OPERATING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG05", "CG06", "CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="out", stab=0.35, scale=(0.5, 15),
    ),

    # ── INVESTING ──────────────────────────────────────────────────────────────
    "Tiền chi mua sắm, xây dựng tài sản cố định": dict(
        act="INVESTING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG04", "CG05"], ctype_int=None,
        direction="out", stab=0.20, scale=(5, 200),
    ),
    "Tiền thu từ thanh lý, nhượng bán tài sản cố định": dict(
        act="INVESTING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG03", "CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="in", stab=0.10, scale=(1, 50),
    ),
    "Tiền chi cho vay, mua công cụ nợ": dict(
        act="INVESTING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="out", stab=0.25, scale=(5, 100),
    ),
    "Tiền thu hồi cho vay, mua công cụ nợ": dict(
        act="INVESTING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="in", stab=0.25, scale=(5, 100),
    ),
    "Tiền chi góp vốn vào đơn vị khác": dict(
        act="INVESTING", scopes=["NỘI BỘ", "BÊN NGOÀI"],
        ext_cg=["CG03"], ctype_int="Nội bộ Tập đoàn",
        direction="out", stab=0.15, scale=(10, 150),
    ),
    "Tiền thu hồi góp vốn vào đơn vị khác": dict(
        act="INVESTING", scopes=["NỘI BỘ", "BÊN NGOÀI"],
        ext_cg=["CG03"], ctype_int="Nội bộ Tập đoàn",
        direction="in", stab=0.15, scale=(10, 150),
    ),
    "Tiền thu lãi cho vay, cổ tức, lợi nhuận được chia": dict(
        act="INVESTING", scopes=["NỘI BỘ", "BÊN NGOÀI"],
        ext_cg=["CG03", "CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="in", stab=0.50, scale=(1, 30),
    ),

    # ── FINANCING ──────────────────────────────────────────────────────────────
    "Tiền thu từ phát hành cổ phiếu, nhận vốn góp": dict(
        act="FINANCING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG03"], ctype_int="Nội bộ Tập đoàn",
        direction="in", stab=0.10, scale=(20, 300),
    ),
    "Tiền chi trả vốn góp, mua lại cổ phiếu": dict(
        act="FINANCING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG03"], ctype_int="Nội bộ Tập đoàn",
        direction="out", stab=0.10, scale=(10, 200),
    ),
    "Tiền thu từ đi vay": dict(
        act="FINANCING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="in", stab=0.50, scale=(10, 200),
        ctype_override_ext="Ngân hàng",
    ),
    "Tiền trả nợ vay": dict(
        act="FINANCING", scopes=["BÊN NGOÀI", "NỘI BỘ"],
        ext_cg=["CG08"], ctype_int="Nội bộ Tập đoàn",
        direction="out", stab=0.55, scale=(10, 200),
        ctype_override_ext="Ngân hàng",
    ),
    "Tiền trả nợ thuê TC": dict(
        act="FINANCING", scopes=["BÊN NGOÀI"],
        ext_cg=["CG08"], ctype_int=None,
        direction="out", stab=0.75, scale=(1, 30),
        ctype_override="Ngân hàng",
    ),
    # ← user note: cổ tức chỉ NỘI BỘ
    "Tiền trả cổ tức": dict(
        act="FINANCING", scopes=["NỘI BỘ"],
        ext_cg=[], ctype_int="Nội bộ Tập đoàn",
        direction="out", stab=0.30, scale=(5, 80),
    ),
}


def gen_rows() -> list[dict]:
    rows = []

    for line_item, rule in RULES.items():
        act = rule["act"]
        scopes = rule["scopes"]
        ext_cg_pool = rule.get("ext_cg", [])
        ctype_int = rule.get("ctype_int", "Nội bộ Tập đoàn")
        direction = rule["direction"]
        stab_p = rule["stab"]
        lo, hi = rule["scale"]
        ctype_override = rule.get("ctype_override")
        ctype_override_ext = rule.get("ctype_override_ext")

        for period in periods:
            for company in companies:
                for scope in scopes:
                    # ── BÊN NGOÀI ──
                    if scope == "BÊN NGOÀI" and ext_cg_pool:
                        cg = RNG.choice(ext_cg_pool)
                        if ctype_override:
                            ctype = ctype_override
                        elif ctype_override_ext:
                            ctype = ctype_override_ext
                        else:
                            ctype = CG_TYPE.get(cg, "Khách hàng")

                        # direction → sign
                        if direction == "in":
                            amount = float(RNG.uniform(lo * 1e9, hi * 1e9))
                            from_e, to_e = cg, company
                        elif direction == "out":
                            amount = -float(RNG.uniform(lo * 1e9, hi * 1e9))
                            from_e, to_e = company, cg
                        else:  # mixed
                            base = float(RNG.uniform(lo * 1e9, hi * 1e9))
                            sign = RNG.choice([-1, 1])
                            amount = sign * base
                            from_e, to_e = (cg, company) if sign > 0 else (company, cg)

                        stability = "ỔN ĐỊNH" if RNG.random() < stab_p else "KHÔNG ỔN ĐỊNH"
                        rows.append(dict(
                            period_end=period, activity_category=act,
                            line_item=line_item, stability=stability, scope=scope,
                            counterparty_type=ctype, from_entity_id=from_e,
                            to_entity_id=to_e, flow_amount=round(amount, 2),
                        ))

                    # ── NỘI BỘ ──
                    elif scope == "NỘI BỘ":
                        others = [e for e in companies if e != company]
                        if not others:
                            continue
                        partner = RNG.choice(others)

                        if direction == "in":
                            amount = float(RNG.uniform(lo * 1e9, hi * 1e9))
                            from_e, to_e = partner, company
                        elif direction == "out":
                            amount = -float(RNG.uniform(lo * 1e9, hi * 1e9))
                            from_e, to_e = company, partner
                        else:
                            base = float(RNG.uniform(lo * 1e9, hi * 1e9))
                            sign = RNG.choice([-1, 1])
                            amount = sign * base
                            from_e, to_e = (partner, company) if sign > 0 else (company, partner)

                        stability = "ỔN ĐỊNH" if RNG.random() < stab_p else "KHÔNG ỔN ĐỊNH"
                        rows.append(dict(
                            period_end=period, activity_category=act,
                            line_item=line_item, stability=stability, scope=scope,
                            counterparty_type=ctype_int, from_entity_id=from_e,
                            to_entity_id=to_e, flow_amount=round(amount, 2),
                        ))
    return rows


if __name__ == "__main__":
    print("Generating rows...")
    rows = gen_rows()
    df = pd.DataFrame(rows)

    out_path = DATA_DIR / "fact_cash_flow.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    import sys, io
    buf = io.StringIO()
    print(f"Total rows: {len(df):,}", file=buf)
    print("activity_category:", df["activity_category"].value_counts().to_dict(), file=buf)
    print("scope:", df["scope"].value_counts().to_dict(), file=buf)
    print("counterparty_type:", df["counterparty_type"].value_counts().to_dict(), file=buf)
    print("stability:", df["stability"].value_counts().to_dict(), file=buf)
    print("line_item count:", df["line_item"].nunique(), file=buf)
    print(f"Saved -> {out_path}", file=buf)
    sys.stdout.buffer.write(buf.getvalue().encode("utf-8"))
