"""Month ↔ Quarter reducer.

Stock = quarter-end snapshot; Flow = SUM over months in the quarter.
"""
from __future__ import annotations

import pandas as pd


STOCK_COLS = {"cash_eom", "external_ar_eom", "amount_eom", "outstanding_eom",
              "credit_limit", "credit_utilized"}
FLOW_COLS = {"flow_amount"}


def period_label(ts: pd.Timestamp, granularity: str) -> str:
    if granularity == "quarter":
        return f"{ts.year}Q{(ts.month - 1) // 3 + 1}"
    return ts.strftime("%Y-%m")


def reduce_period(df: pd.DataFrame, value_col: str, granularity: str,
                  group_cols: list[str] | None = None) -> pd.DataFrame:
    """Reduce a monthly fact frame to the chosen granularity.

    - month: passthrough
    - quarter + stock: keep only Dec/Mar/Jun/Sep rows (quarter-end)
    - quarter + flow:  SUM across months within each quarter
    """
    if granularity == "month":
        return df

    mode = "stock" if value_col in STOCK_COLS else ("flow" if value_col in FLOW_COLS else "stock")

    if mode == "stock":
        out = df[df["period_end"].dt.month.isin([3, 6, 9, 12])].copy()
        return out

    # flow
    if group_cols is None:
        group_cols = [c for c in df.columns if c not in ("period_end", value_col)]
    q = df["period_end"].dt.to_period("Q").dt.to_timestamp("Q")
    tmp = df.assign(period_end=q)
    return tmp.groupby(group_cols + ["period_end"], as_index=False)[value_col].sum()


def list_periods(dim_period: pd.DataFrame, granularity: str) -> list[pd.Timestamp]:
    if granularity == "month":
        return sorted(dim_period["period_end"].unique())
    return sorted(dim_period.loc[dim_period["is_quarter_end"] == 1, "period_end"].unique())
