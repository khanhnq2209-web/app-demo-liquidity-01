"""Simulation & optimization helpers for AR and cash stress testing."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ar_optimization_sim(
    df_ar: pd.DataFrame,           # fact_external_ar filtered to current period
    df_credit: pd.DataFrame,       # fact_credit filtered to current period
    target_top1_share: float,      # e.g., 0.20 = 20%
    dim_cg: pd.DataFrame,          # dim_client_group
) -> dict:
    """
    Compute what each entity needs to do to reduce Top-1 AR concentration
    to the target_top1_share level.

    Returns a dict with:
      - 'summary': pd.DataFrame per entity with columns:
            entity_id, entity_name, current_top1_share, current_top1_ar,
            top1_client_name, required_collection_B, required_diversification_B, status
      - 'hhi_before': float
      - 'hhi_after': float (estimated)
      - 'group_top1_before': float
      - 'group_top1_after': float
    """
    if df_ar.empty:
        return {"summary": pd.DataFrame(), "hhi_before": 0, "hhi_after": 0,
                "group_top1_before": 0, "group_top1_after": 0}

    # --- Group-level HHI ---
    totals = df_ar.groupby("client_group_id")["external_ar_eom"].sum()
    total_ar = totals.sum()
    shares = (totals / total_ar) if total_ar > 0 else totals
    hhi_before = float((shares ** 2).sum())
    top1_share_before = float(shares.max()) if len(shares) else 0.0
    top1_cg_id = shares.idxmax() if len(shares) else None

    rows = []
    for eid, sub in df_ar.groupby("entity_id"):
        ent_total = sub["external_ar_eom"].sum()
        if ent_total == 0:
            continue
        ent_shares = sub.groupby("client_group_id")["external_ar_eom"].sum()
        top1_id = ent_shares.idxmax()
        top1_ar = float(ent_shares[top1_id])
        cur_share = top1_ar / ent_total

        top1_name = dim_cg.loc[dim_cg["client_group_id"] == top1_id,
                                "client_group_name"].values
        top1_name = top1_name[0] if len(top1_name) else top1_id

        if cur_share > target_top1_share:
            # Option A: collect early → reduce top1 AR
            target_top1_ar = target_top1_share * ent_total
            required_collection = max(top1_ar - target_top1_ar, 0)
            # Option B: grow other revenues so top1 becomes smaller fraction
            # new_total such that top1_ar / new_total = target → new_total = top1_ar / target
            new_total_needed = top1_ar / target_top1_share
            required_diversification = max(new_total_needed - ent_total, 0)
            status = "🔴 Needs Action"
        else:
            required_collection = 0
            required_diversification = 0
            status = "🟢 Within Target"

        # Credit headroom released if collection accelerated
        cred = df_credit[df_credit["entity_id"] == eid]
        headroom_now = 0.0
        if not cred.empty:
            headroom_now = float(cred["credit_limit"].iloc[0] - cred["credit_utilized"].iloc[0])
        headroom_released = min(required_collection * 0.3, headroom_now)  # rough proxy

        rows.append({
            "entity_id": eid,
            "current_top1_share": round(cur_share, 4),
            "current_top1_ar_B": round(top1_ar / 1e9, 2),
            "top1_client": top1_name,
            "required_collection_B": round(required_collection / 1e9, 2),
            "required_diversification_B": round(required_diversification / 1e9, 2),
            "credit_headroom_released_B": round(headroom_released / 1e9, 2),
            "status": status,
        })

    summary_df = pd.DataFrame(rows).sort_values("current_top1_share", ascending=False)

    # Estimate group-level HHI after — assume top1 client share drops proportionally
    scale = min(target_top1_share / top1_share_before, 1.0) if top1_share_before > 0 else 1.0
    adj_shares = shares.copy()
    if top1_cg_id and top1_cg_id in adj_shares.index:
        adj_shares[top1_cg_id] *= scale
        adj_shares = adj_shares / adj_shares.sum()
    hhi_after = float((adj_shares ** 2).sum())

    return {
        "summary": summary_df,
        "hhi_before": round(hhi_before, 4),
        "hhi_after": round(hhi_after, 4),
        "group_top1_before": round(top1_share_before, 4),
        "group_top1_after": round(min(target_top1_share, top1_share_before), 4),
    }


def cash_stress_test(
    df_cash: pd.DataFrame,      # fact_cash_balance — all periods
    df_ar: pd.DataFrame,        # fact_external_ar — current period
    df_ic_loan: pd.DataFrame,   # fact_ic_loan — current period
    dim_entity: pd.DataFrame,
    dim_cg: pd.DataFrame,
    scenario: str,              # 'evn_delay_60d' | 'ic_loan_recall_top3' | 'capex_spike'
) -> pd.DataFrame:
    """
    Returns a DataFrame showing delta cash impact per entity for the chosen scenario.
    Columns: entity_id, entity_name, current_cash_B, delta_B, landing_cash_B, rag
    """
    # Use last available period for cash baseline
    latest = df_cash["period_end"].max()
    base = df_cash[df_cash["period_end"] == latest].copy()
    name_map = dict(zip(dim_entity["entity_id"], dim_entity["entity_name"]))

    deltas: dict[str, float] = {}

    if scenario == "evn_delay_60d":
        # EVN delays full payment by 60 days → cash impact proportional to EVN AR / 365 * 60
        evn_row = dim_cg[dim_cg["client_group_name"] == "EVN"]
        if not evn_row.empty:
            evn_id = evn_row["client_group_id"].iloc[0]
            evn_ar = df_ar[df_ar["client_group_id"] == evn_id]
            for _, row in evn_ar.iterrows():
                daily = row["external_ar_eom"] / 365
                deltas[row["entity_id"]] = deltas.get(row["entity_id"], 0) - daily * 60

    elif scenario == "ic_loan_recall_top3":
        # Top 3 IC borrowers must repay immediately
        if not df_ic_loan.empty:
            top3 = df_ic_loan.nlargest(3, "outstanding_eom")
            for _, row in top3.iterrows():
                # borrower loses cash
                deltas[row["borrower_entity_id"]] = deltas.get(row["borrower_entity_id"], 0) - row["outstanding_eom"]
                # lender gains cash
                deltas[row["lender_entity_id"]] = deltas.get(row["lender_entity_id"], 0) + row["outstanding_eom"]

    elif scenario == "capex_spike":
        # Unexpected 20% capex spike across all entities
        for _, row in base.iterrows():
            deltas[row["entity_id"]] = deltas.get(row["entity_id"], 0) - row["cash_eom"] * 0.20

    rows = []
    for _, row in base.iterrows():
        eid = row["entity_id"]
        cur_cash = float(row["cash_eom"])
        delta = deltas.get(eid, 0.0)
        landing = cur_cash + delta
        rag = "🟢" if landing > cur_cash * 0.5 else ("🟡" if landing > 0 else "🔴")
        rows.append({
            "entity_id": eid,
            "entity_name": name_map.get(eid, eid),
            "current_cash_B": round(cur_cash / 1e9, 2),
            "delta_B": round(delta / 1e9, 2),
            "landing_cash_B": round(landing / 1e9, 2),
            "rag": rag,
        })

    return pd.DataFrame(rows).sort_values("delta_B")
