"""Synthetic dataset generator for the GELEX demo.

Produces all CSVs listed in requirement_technical_01.md plus a cash-flow
line-item dimension sourced from the user-provided classification sheet.
Deterministic via fixed seed.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# ---------------------------------------------------------------------------
# 1. Dimensions
# ---------------------------------------------------------------------------

ENTITIES = [
    # (id,            name,                                                          type,         parent,      sub,    industry,             supply_chain_node)
    ("GELEX",         "Công ty cổ phần Tập đoàn Gelex",                             "HOLDING",    None,        None,   "Holding",            "Holding"),
    # ── Sub-holding GEE (Thiết bị điện) ──────────────────────────────────────────
    ("GEE",           "Công ty Cổ phần Thiết bị điện Gelex",                        "SUBHOLDING", "GELEX",     "GEE",  "Electric equipment", "Holding"),
    ("CADIVI",        "Công ty Cổ phần Dây Cáp Điện Việt Nam",                      "COMPANY",    "GEE",       "GEE",  "Cables",             "Manufacturing"),
    ("CMB",           "Công ty TNHH MTV Cadivi Miền Bắc",                           "COMPANY",    "CADIVI",    "GEE",  "Cables",             "Manufacturing"),
    ("THI",           "Công ty Cổ phần Thiết bị Điện",                              "COMPANY",    "GEE",       "GEE",  "Electric equipment", "Distribution"),
    ("MEE",           "Công ty Cổ phần Sản xuất Thiết bị điện Đông Anh",            "COMPANY",    "GEE",       "GEE",  "Electric equipment", "Manufacturing"),
    ("HEM",           "Công ty Cổ phần Chế tạo Điện Cơ Hà Nội",                    "COMPANY",    "GEE",       "GEE",  "Motors",             "Manufacturing"),
    ("EMIC",          "Công ty Cổ phần Thiết bị đo điện EMIC",                      "COMPANY",    "GEE",       "GEE",  "Metering",           "Manufacturing"),
    ("CFT",           "Công ty Dây đồng Việt Nam - CFT",                            "COMPANY",    "GEE",       "GEE",  "Cables",             "Raw Material"),
    ("Phatdien",      "Công ty TNHH Một thành viên Phát điện Gelex",                "COMPANY",    "GEE",       "GEE",  "Power generation",   "Operation"),
    ("GETC",          "Công ty Cổ phần Mua bán điện GELEX",                         "COMPANY",    "GEE",       "GEE",  "Power generation",   "Distribution"),
    # ── Directly under GELEX (no subholding) ─────────────────────────────────────
    ("GELEXTECH",     "Công ty TNHH GELEX Technology",                              "COMPANY",    "GELEX",     None,   "Technology",         "Assembly/EPC"),
    ("GELEXINVEST",   "Công ty TNHH Đầu tư GELEX",                                 "COMPANY",    "GELEX",     None,   "Investment",         "Holding"),
    # ── Sub-holding GEL (Hạ tầng) ────────────────────────────────────────────────
    ("GEL",           "Công ty cổ phần Hạ tầng Gelex",                              "SUBHOLDING", "GELEX",     "GEL",  "Infrastructure",     "Holding"),
    ("VGC",           "Tổng Công ty Viglacera – CTCP và các công ty con",           "COMPANY",    "GEL",       "GEL",  "Building materials", "Manufacturing"),
    ("Viwasupco",     "Công ty Cổ phần Đầu tư Nước sạch Sông Đà",                  "COMPANY",    "VGC",       "GEL",  "Water utility",      "Operation"),
    ("PXL",           "Công ty Cổ phần Đầu tư và phát triển KCN Dầu khí Long Sơn", "COMPANY",    "GEL",       "GEL",  "Industrial zone",    "Operation"),
    ("FIH",           "Công ty TNHH FIH và các công ty con",                        "COMPANY",    "GEL",       "GEL",  "Mixed",              "Assembly/EPC"),
    ("TITANHP",       "Công ty Cổ phần Titan Hải Phòng",                            "COMPANY",    "GEL",       "GEL",  "Logistics",          "Distribution"),
    ("WADACO",        "Công ty Cổ phần Nước sạch Tây Hà Nội",                       "COMPANY",    "GEL",       "GEL",  "Water utility",      "Operation"),
    ("TitanCorp",     "Công ty TNHH Titan Corporation",                             "COMPANY",    "TITANHP",   "GEL",  "Logistics",          "Retail/End-User"),
    ("BSG1",          "Công ty TNHH Hạ tầng Gelex Bắc Sài Gòn 1",                  "COMPANY",    "GEL",       "GEL",  "Infrastructure",     "Operation"),
    ("BSG2",          "Công ty TNHH Hạ tầng Gelex Bắc Sài Gòn 2",                  "COMPANY",    "GEL",       "GEL",  "Infrastructure",     "Operation"),
    ("TTP",           "Công ty TNHH Hạ tầng Gelex Tây Thành Phố",                  "COMPANY",    "GEL",       "GEL",  "Infrastructure",     "Operation"),
]

CLIENT_GROUPS = [
    ("CG01", "EVN",               "Utilities",       0, 0.32),
    ("CG02", "Samsung Vina",      "Industrial",      0, 0.18),
    ("CG03", "Vingroup",          "Real estate",     0, 0.14),
    ("CG04", "Coteccons",         "Construction",    0, 0.10),
    ("CG05", "Hòa Phát",          "Industrial",      0, 0.08),
    ("CG06", "PetroVietnam",      "Energy",          0, 0.07),
    ("CG07", "End-user retail",   "Retail",          0, 0.06),
    ("CG08", "Other",             "Mixed",           1, 0.05),
]

CASHFLOW_ITEMS = [
    # (category, line_item, typical_sign)
    ("OPERATING", "Dự thu",                                                 +1),
    ("OPERATING", "Lợi nhuận thuần trước thuế",                              +1),
    ("OPERATING", "Khấu hao TSCĐ",                                           +1),
    ("OPERATING", "Dự phòng",                                                +1),
    ("OPERATING", "Lãi/lỗ do đánh giá lại các khoản mục tiền tệ có gốc ngoại tệ", -1),
    ("OPERATING", "Lãi/lỗ từ hoạt động đầu tư",                              +1),
    ("OPERATING", "Chi phí lãi vay",                                         -1),
    ("OPERATING", "Tăng/giảm các khoản phải thu",                            -1),
    ("OPERATING", "Tăng/giảm hàng tồn kho",                                  -1),
    ("OPERATING", "Tăng/giảm các khoản phải trả",                            +1),
    ("OPERATING", "Tăng/giảm chi phí trả trước",                             -1),
    ("OPERATING", "Tăng/giảm TSCĐ khác",                                     -1),
    ("OPERATING", "Lãi vay đã trả",                                          -1),
    ("OPERATING", "Thuế TNDN đã trả",                                        -1),
    ("OPERATING", "Tiền thu từ hoạt động kinh doanh khác",                    +1),
    ("OPERATING", "Tiền chi khác cho hoạt động kinh doanh",                   -1),
    ("INVESTING", "Tiền chi mua sắm, xây dựng tài sản cố định",               -1),
    ("INVESTING", "Tiền thu từ thanh lý, nhượng bán tài sản cố định",         +1),
    ("INVESTING", "Tiền chi cho vay, mua công cụ nợ",                         -1),
    ("INVESTING", "Tiền thu hồi cho vay, mua công cụ nợ",                     +1),
    ("INVESTING", "Tiền chi góp vốn vào đơn vị khác",                         -1),
    ("INVESTING", "Tiền thu hồi góp vốn vào đơn vị khác",                     +1),
    ("INVESTING", "Tiền thu lãi cho vay, cổ tức, lợi nhuận được chia",        +1),
    ("FINANCING", "Tiền thu từ phát hành cổ phiếu, nhận vốn góp",             +1),
    ("FINANCING", "Tiền chi trả vốn góp, mua lại cổ phiếu",                   -1),
    ("FINANCING", "Tiền thu từ đi vay",                                       +1),
    ("FINANCING", "Tiền trả nợ vay",                                          -1),
    ("FINANCING", "Tiền trả nợ thuê TC",                                      -1),
    ("FINANCING", "Tiền trả cổ tức",                                          -1),
]


def _month_ends(n_months: int, end: pd.Timestamp) -> list[pd.Timestamp]:
    return list(pd.date_range(end=end, periods=n_months, freq="ME"))


def _make_periods(end: pd.Timestamp, n_months: int) -> pd.DataFrame:
    dates = _month_ends(n_months, end)
    df = pd.DataFrame({"period_end": dates})
    df["year"] = df["period_end"].dt.year
    df["month"] = df["period_end"].dt.month
    df["year_month"] = df["period_end"].dt.strftime("%Y-%m")
    df["quarter"] = df["period_end"].dt.to_period("Q").astype(str)  # 2024Q1
    df["is_quarter_end"] = df["month"].isin([3, 6, 9, 12]).astype(int)
    return df


def _entity_frame() -> pd.DataFrame:
    rows = list(ENTITIES)
    return pd.DataFrame(
        rows,
        columns=[
            "entity_id", "entity_name", "entity_type",
            "parent_entity_id", "subholding_code", "industry", "supply_chain_node",
        ],
    ).assign(currency_code="VND")


def _client_group_frame() -> pd.DataFrame:
    df = pd.DataFrame(
        CLIENT_GROUPS,
        columns=["client_group_id", "client_group_name", "industry_group", "is_other", "weight"],
    )
    return df


def _ownership(rng: np.random.Generator, entities: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, e in entities.iterrows():
        if e.parent_entity_id is None:
            continue
        pct = float(np.round(rng.uniform(65, 100), 2))
        rows.append((e.parent_entity_id, e.entity_id, pct, None, None))
    # Inject cross-holding: CADIVI owns 15% of MEE (supply chain integration)
    rows.append(("CADIVI", "MEE", 15.0, None, None))
    return pd.DataFrame(
        rows,
        columns=["parent_entity_id", "child_entity_id", "ownership_pct", "effective_from", "effective_to"],
    )


def _companies(entities: pd.DataFrame) -> pd.DataFrame:
    return entities[entities.entity_type == "COMPANY"].copy()


def _cash(rng: np.random.Generator, periods: pd.DataFrame, companies: pd.DataFrame) -> pd.DataFrame:
    records = []
    # per-company base cash (log-normal, in billion VND units)
    bases = {e: float(rng.lognormal(mean=3.2, sigma=0.7)) for e in companies.entity_id}
    # Declining-trend seed entities
    declining = set(rng.choice(list(bases.keys()), size=3, replace=False))
    # Seasonal factor per month
    season = {m: 1 + 0.08 * np.sin((m - 3) / 12 * 2 * np.pi) for m in range(1, 13)}

    for eid, base in bases.items():
        for i, row in periods.iterrows():
            trend = 1.0
            if eid in declining:
                # steady decline over last 6 months
                last_6 = len(periods) - 6
                if i >= last_6:
                    trend = 1.0 - (i - last_6 + 1) * 0.06
            noise = rng.normal(1.0, 0.04)
            amount = base * season[row.month] * trend * noise
            records.append((row.period_end, eid, max(amount * 1e9, 1e6)))
    return pd.DataFrame(records, columns=["period_end", "entity_id", "cash_eom"])


def _external_ar(rng: np.random.Generator, periods: pd.DataFrame,
                 companies: pd.DataFrame, client_groups: pd.DataFrame) -> pd.DataFrame:
    records = []
    weights = dict(zip(client_groups.client_group_id, client_groups.weight))
    company_scale = {e: float(rng.lognormal(mean=2.5, sigma=0.6)) for e in companies.entity_id}
    for eid, scale in company_scale.items():
        for _, row in periods.iterrows():
            total = scale * 1e9 * rng.normal(1.0, 0.05)
            for cg, w in weights.items():
                amt = total * w * rng.normal(1.0, 0.1)
                records.append((row.period_end, eid, cg, max(amt, 0)))
    return pd.DataFrame(records, columns=["period_end", "entity_id", "client_group_id", "external_ar_eom"])


def _ic_arap(rng: np.random.Generator, periods: pd.DataFrame, companies: pd.DataFrame) -> pd.DataFrame:
    # Build ~80 active pairs, skewed amounts
    ids = companies.entity_id.tolist()
    pairs = set()
    while len(pairs) < 80:
        a, b = rng.choice(ids, 2, replace=False)
        if a != b:
            pairs.add((str(a), str(b)))
    pair_scale = {p: float(rng.pareto(1.2) + 0.5) for p in pairs}
    records = []
    for (a, b), s in pair_scale.items():
        ic_type = rng.choice(["IC_AR", "IC_AP"], p=[0.55, 0.45])
        for _, row in periods.iterrows():
            amt = s * 1e9 * rng.normal(1.0, 0.08)
            records.append((row.period_end, a, b, ic_type, max(amt, 0)))
    return pd.DataFrame(records, columns=["period_end", "from_entity_id", "to_entity_id", "ic_type", "amount_eom"])


def _ic_loans(rng: np.random.Generator, periods: pd.DataFrame, companies: pd.DataFrame) -> pd.DataFrame:
    ids = companies.entity_id.tolist()
    pairs = set()
    while len(pairs) < 25:
        lender, borrower = rng.choice(ids, 2, replace=False)
        if lender != borrower:
            pairs.add((str(lender), str(borrower)))
    pair_scale = {p: float(rng.pareto(1.1) + 1.0) for p in pairs}
    records = []
    for (l, b), s in pair_scale.items():
        for _, row in periods.iterrows():
            amt = s * 1e9 * rng.normal(1.0, 0.05)
            records.append((row.period_end, l, b, max(amt, 0)))
    return pd.DataFrame(records, columns=["period_end", "lender_entity_id", "borrower_entity_id", "outstanding_eom"])


def _credit(rng: np.random.Generator, periods: pd.DataFrame, companies: pd.DataFrame) -> pd.DataFrame:
    records = []
    limits = {e: float(rng.uniform(50, 500)) * 1e9 for e in companies.entity_id}
    high_util = set(rng.choice(list(limits.keys()), size=2, replace=False))
    entity_rates = {e: float(rng.uniform(0.065, 0.105)) for e in companies.entity_id}  # 6.5% - 10.5%
    for eid, limit in limits.items():
        base_util = rng.uniform(0.9, 0.95) if eid in high_util else rng.uniform(0.3, 0.75)
        for _, row in periods.iterrows():
            used = limit * np.clip(base_util + rng.normal(0, 0.03), 0, 0.99)
            records.append((row.period_end, eid, limit, used, entity_rates[eid]))
    return pd.DataFrame(records, columns=["period_end", "entity_id", "credit_limit", "credit_utilized", "interest_rate"])


def _cash_plan(rng: np.random.Generator, hist_cash: pd.DataFrame,
               companies: pd.DataFrame, n_forward: int = 12,
               start: str = "2026-04-30") -> pd.DataFrame:
    """Generate 12-month forward cash plan per entity based on trend extrapolation."""
    records = []
    plan_dates = list(pd.date_range(start=start, periods=n_forward, freq="ME"))
    for eid in companies["entity_id"]:
        hist = hist_cash[hist_cash["entity_id"] == eid].sort_values("period_end")
        if hist.empty:
            continue
        # trend from last 6 months
        last6 = hist["cash_eom"].tail(6).values
        trend = float(np.polyfit(range(len(last6)), last6, 1)[0]) if len(last6) >= 2 else 0.0
        last_val = float(hist["cash_eom"].iloc[-1])
        for i, dt in enumerate(plan_dates):
            proj_cash = max(last_val + trend * (i + 1) * rng.normal(1.0, 0.04), 0)
            planned_capex = float(rng.uniform(0.02, 0.15) * last_val)  # 2-15% of base
            planned_opex_cf = float(rng.uniform(0.05, 0.20) * last_val)
            planned_debt_repayment = float(rng.uniform(0.01, 0.08) * last_val)
            records.append((dt, eid, proj_cash, planned_capex, planned_opex_cf, planned_debt_repayment))
    return pd.DataFrame(records, columns=[
        "period_end", "entity_id", "projected_cash_eom",
        "planned_capex", "planned_opex_cf", "planned_debt_repayment",
    ])


def _cashflow_items_dim() -> pd.DataFrame:
    return pd.DataFrame(CASHFLOW_ITEMS, columns=["activity_category", "line_item", "typical_sign"])


def _cash_flow(rng: np.random.Generator, periods: pd.DataFrame,
               companies: pd.DataFrame, client_groups: pd.DataFrame) -> pd.DataFrame:
    items = CASHFLOW_ITEMS
    records = []
    ent_ids = companies.entity_id.tolist()
    cg_ids = client_groups.client_group_id.tolist()
    cg_weights = dict(zip(client_groups.client_group_id, client_groups.weight))

    # pre-assign a counterparty pattern per (entity, line_item)
    rolling_mean: dict[tuple, list[float]] = {}

    for eid in ent_ids:
        entity_scale = float(rng.lognormal(2.0, 0.5)) * 1e9
        for cat, item, sign in items:
            internal = cat == "FINANCING" and "vay" in item.lower() and rng.random() < 0.4 \
                or cat == "INVESTING" and "góp vốn" in item.lower() and rng.random() < 0.5
            for _, row in periods.iterrows():
                amt = sign * entity_scale * rng.uniform(0.02, 0.2) * rng.normal(1.0, 0.15)
                if internal:
                    scope = "NỘI BỘ"
                    cpty_type = "Internal"
                    partner = rng.choice([x for x in ent_ids if x != eid])
                    from_id, to_id = (partner, eid) if amt > 0 else (eid, partner)
                else:
                    scope = "BÊN NGOÀI"
                    cg = rng.choice(cg_ids, p=[cg_weights[c] for c in cg_ids])
                    cg_name = client_groups.loc[client_groups.client_group_id == cg, "client_group_name"].iloc[0]
                    cpty_type = "EVN" if cg_name == "EVN" else (
                        "End-user" if cg_name == "End-user" else "Customer"
                    )
                    from_id, to_id = (cg, eid) if amt > 0 else (eid, cg)

                # stability flag: ±10% band vs 3-month rolling mean
                key = (eid, item)
                hist = rolling_mean.setdefault(key, [])
                hist.append(amt)
                if len(hist) > 3:
                    hist.pop(0)
                mean = np.mean(hist)
                stable = abs(amt - mean) <= 0.1 * abs(mean) if mean else True
                stability = "ỔN ĐỊNH" if stable else "KHÔNG ỔN ĐỊNH"

                records.append((
                    row.period_end, cat, item, stability, scope, cpty_type,
                    from_id, to_id, amt,
                ))

    return pd.DataFrame(records, columns=[
        "period_end", "activity_category", "line_item", "stability", "scope",
        "counterparty_type", "from_entity_id", "to_entity_id", "flow_amount",
    ])


def generate(out_dir: Path = DATA_DIR, n_months: int = 48, end: str = "2026-03-31") -> None:
    rng = np.random.default_rng(SEED)
    out_dir.mkdir(parents=True, exist_ok=True)
    periods = _make_periods(pd.Timestamp(end), n_months)
    entities = _entity_frame()
    client_groups = _client_group_frame().drop(columns=["weight"])
    client_groups_full = _client_group_frame()
    companies = _companies(entities)

    ownership = _ownership(rng, entities)
    cash = _cash(rng, periods, companies)
    ar = _external_ar(rng, periods, companies, client_groups_full)
    ic_arap = _ic_arap(rng, periods, companies)
    ic_loan = _ic_loans(rng, periods, companies)
    credit = _credit(rng, periods, companies)
    cashflow = _cash_flow(rng, periods, companies, client_groups_full)
    cf_items = _cashflow_items_dim()
    cash_plan = _cash_plan(rng, cash, companies)

    enc = "utf-8-sig"
    saves = {
        "dim_entity.csv": entities,
        "dim_period.csv": periods,
        "dim_client_group.csv": client_groups,
        "rel_ownership.csv": ownership,
        "fact_cash_balance.csv": cash,
        "fact_external_ar_by_client_group.csv": ar,
        "fact_ic_arap.csv": ic_arap,
        "fact_ic_loan.csv": ic_loan,
        "fact_credit_summary.csv": credit,
        "fact_cash_flow.csv": cashflow,
        "dim_cashflow_item.csv": cf_items,
        "fact_cash_plan.csv": cash_plan,
    }
    for fname, df in saves.items():
        try:
            df.to_csv(out_dir / fname, index=False, encoding=enc)
            print(f"  OK  {fname} ({len(df):,} rows)")
        except PermissionError:
            print(f"  SKIP {fname} — file is open/locked, close it in the IDE and re-run")


if __name__ == "__main__":
    generate()
