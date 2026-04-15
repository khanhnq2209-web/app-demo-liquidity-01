"""CSV loaders with Streamlit caching."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _read(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `python -m src.mock_data.generate` first."
        )
    return pd.read_csv(path, parse_dates=parse_dates)


@st.cache_data(show_spinner=False)
def load_all() -> dict[str, pd.DataFrame]:
    # Cache busted: 2026-04-15 — entity list updated to real GELEX entities (GEE/GEL structure)
    dfs = {
        "dim_entity":            _read("dim_entity.csv"),
        "dim_period":            _read("dim_period.csv", parse_dates=["period_end"]),
        "dim_client_group":      _read("dim_client_group.csv"),
        "dim_cashflow_item":     _read("dim_cashflow_item.csv"),
        "rel_ownership":         _read("rel_ownership.csv"),
        "fact_cash_balance":     _read("fact_cash_balance.csv", parse_dates=["period_end"]),
        "fact_external_ar":      _read("fact_external_ar_by_client_group.csv", parse_dates=["period_end"]),
        "fact_ic_arap":          _read("fact_ic_arap.csv", parse_dates=["period_end"]),
        "fact_ic_loan":          _read("fact_ic_loan.csv", parse_dates=["period_end"]),
        "fact_credit":           _read("fact_credit_summary.csv", parse_dates=["period_end"]),
        "fact_cash_flow":        _read("fact_cash_flow.csv", parse_dates=["period_end"]),
        "fact_cash_plan":        _read("fact_cash_plan.csv", parse_dates=["period_end"]),
    }
    return dfs
