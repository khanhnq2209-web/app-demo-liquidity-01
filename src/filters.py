"""Apply global sidebar/selection filters to fact frames."""
from __future__ import annotations

import pandas as pd
import streamlit as st


def descendant_entities(dim_entity: pd.DataFrame, root_id: str | None) -> set[str]:
    """Return entity_id plus all descendants."""
    if root_id is None:
        return set(dim_entity["entity_id"])
    children = {root_id}
    frontier = [root_id]
    while frontier:
        parent = frontier.pop()
        kids = dim_entity.loc[dim_entity["parent_entity_id"] == parent, "entity_id"].tolist()
        children.update(kids)
        frontier.extend(kids)
    return children


def in_scope(dim_entity: pd.DataFrame) -> set[str]:
    """Which entity_ids are in current scope, given sidebar selection."""
    ss = st.session_state
    subholding = ss.get("selected_subholding")
    entity = ss.get("selected_entity")

    if entity:
        return descendant_entities(dim_entity, entity)
    if subholding:
        # map sub-holding code (A / B) to its entity_id
        row = dim_entity[(dim_entity["entity_type"] == "SUBHOLDING") &
                         (dim_entity["subholding_code"] == subholding)]
        if len(row):
            return descendant_entities(dim_entity, row["entity_id"].iloc[0])
    return set(dim_entity["entity_id"])


def filter_by_entities(df: pd.DataFrame, entity_col: str, ids: set[str]) -> pd.DataFrame:
    return df[df[entity_col].isin(ids)].copy()


def latest_period(dim_period: pd.DataFrame, granularity: str) -> pd.Timestamp:
    if granularity == "quarter":
        rows = dim_period[dim_period["is_quarter_end"] == 1]
    else:
        rows = dim_period
    return rows["period_end"].max()
