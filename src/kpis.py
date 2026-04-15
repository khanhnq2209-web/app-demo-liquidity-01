"""KPI computations operating on filtered DataFrames."""
from __future__ import annotations

import numpy as np
import pandas as pd


def cash_total(df: pd.DataFrame) -> float:
    return float(df["cash_eom"].sum())


def cash_share(df: pd.DataFrame) -> pd.DataFrame:
    total = df["cash_eom"].sum()
    if total == 0:
        return df.assign(share=0.0)
    return df.assign(share=df["cash_eom"] / total)


def mom_change(current: pd.DataFrame, previous: pd.DataFrame, value_col: str,
                key: str = "entity_id") -> pd.DataFrame:
    cur = current.groupby(key)[value_col].sum().rename("current")
    prev = previous.groupby(key)[value_col].sum().rename("previous")
    out = pd.concat([cur, prev], axis=1).fillna(0)
    out["delta"] = out["current"] - out["previous"]
    out["delta_pct"] = np.where(out["previous"] != 0, out["delta"] / out["previous"], np.nan)
    return out.reset_index()


def total_ar(df: pd.DataFrame) -> float:
    return float(df["external_ar_eom"].sum())


def top_n_share(df: pd.DataFrame, n: int = 1,
                group_col: str = "client_group_id",
                value_col: str = "external_ar_eom") -> float:
    grp = df.groupby(group_col)[value_col].sum().sort_values(ascending=False)
    if grp.sum() == 0:
        return 0.0
    return float(grp.head(n).sum() / grp.sum())


def hhi(df: pd.DataFrame, group_col: str = "client_group_id",
        value_col: str = "external_ar_eom") -> float:
    grp = df.groupby(group_col)[value_col].sum()
    total = grp.sum()
    if total == 0:
        return 0.0
    shares = grp / total
    return float((shares ** 2).sum())


def ic_totals(ic_arap: pd.DataFrame) -> dict[str, float]:
    ar = float(ic_arap.loc[ic_arap["ic_type"] == "IC_AR", "amount_eom"].sum())
    ap = float(ic_arap.loc[ic_arap["ic_type"] == "IC_AP", "amount_eom"].sum())
    return {"ic_ar": ar, "ic_ap": ap, "net_ic": ar - ap}


def ic_loans_total(df: pd.DataFrame) -> float:
    return float(df["outstanding_eom"].sum())


def utilization(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["headroom"] = out["credit_limit"] - out["credit_utilized"]
    out["utilization"] = np.where(out["credit_limit"] > 0,
                                   out["credit_utilized"] / out["credit_limit"], 0)
    return out


def cash_decline_flag(cash_df: pd.DataFrame, n_months: int = 3) -> set[str]:
    """Entities whose cash has declined for `n_months` consecutive months ending at max period."""
    flagged = set()
    for eid, sub in cash_df.sort_values("period_end").groupby("entity_id"):
        vals = sub["cash_eom"].tail(n_months + 1).values
        if len(vals) < n_months + 1:
            continue
        diffs = np.diff(vals)
        if np.all(diffs[-n_months:] < 0):
            flagged.add(eid)
    return flagged


def high_util_flag(credit_df: pd.DataFrame, threshold: float = 0.85) -> set[str]:
    latest = credit_df.sort_values("period_end").groupby("entity_id").tail(1)
    util = utilization(latest)
    return set(util.loc[util["utilization"] > threshold, "entity_id"])


def ic_spike_flag(ic_arap: pd.DataFrame, jump_pct: float = 0.30) -> set[tuple[str, str]]:
    """Pairs whose latest-period IC balance jumped > jump_pct vs 3-month avg."""
    if ic_arap.empty:
        return set()
    df = ic_arap.sort_values("period_end")
    flagged = set()
    for (f, t), sub in df.groupby(["from_entity_id", "to_entity_id"]):
        tail = sub.tail(4)
        if len(tail) < 4:
            continue
        cur = float(tail.iloc[-1]["amount_eom"])
        base = float(tail.iloc[:-1]["amount_eom"].mean())
        if base > 0 and (cur - base) / base > jump_pct:
            flagged.add((f, t))
    return flagged


def validate(dfs: dict[str, pd.DataFrame]) -> list[str]:
    issues: list[str] = []
    valid_ids = set(dfs["dim_entity"]["entity_id"])

    for key, col in [("fact_cash_balance", "entity_id"),
                     ("fact_external_ar", "entity_id"),
                     ("fact_credit", "entity_id")]:
        bad = set(dfs[key][col]) - valid_ids
        if bad:
            issues.append(f"{key}: unknown {col}s {sorted(bad)[:3]}")

    bad_ic = dfs["fact_ic_arap"].query("from_entity_id == to_entity_id")
    if len(bad_ic):
        issues.append(f"fact_ic_arap has {len(bad_ic)} self-IC rows")

    bad_loan = dfs["fact_ic_loan"].query("lender_entity_id == borrower_entity_id")
    if len(bad_loan):
        issues.append(f"fact_ic_loan has {len(bad_loan)} self-loan rows")

    ownership = dfs["rel_ownership"]
    if ((ownership["ownership_pct"] < 0) | (ownership["ownership_pct"] > 100)).any():
        issues.append("rel_ownership: ownership_pct outside [0, 100]")

    if (dfs["fact_external_ar"]["external_ar_eom"] < 0).any():
        issues.append("fact_external_ar: negative AR rows")

    return issues
