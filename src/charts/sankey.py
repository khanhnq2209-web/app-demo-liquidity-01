"""Intercompany Sankey — cycle-safe aggregation."""
from __future__ import annotations

from collections import defaultdict

import networkx as nx
import pandas as pd


_COLOR = {"IC_AR": "#4c8bf5", "IC_AP": "#f59e4c", "IC_LOAN": "#16a34a"}


def _dedupe_and_break_cycles(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate by (from, to), drop self-loops, break cycles by keeping the
    larger-weight edge in any bidirectional pair. Sankey can't render cycles."""
    if df.empty:
        return df
    agg = (df.groupby(["from_entity_id", "to_entity_id"], as_index=False)
             ["amount_eom"].sum())
    agg = agg[agg["from_entity_id"] != agg["to_entity_id"]]
    if agg.empty:
        return agg

    # Break any reverse duplicates
    pair_map = {(r.from_entity_id, r.to_entity_id): float(r.amount_eom) for r in agg.itertuples()}
    keep = set()
    for (a, b), w in pair_map.items():
        if (b, a) in pair_map and (b, a) not in keep and (a, b) not in keep:
            if w >= pair_map[(b, a)]:
                keep.add((a, b))
            else:
                keep.add((b, a))
        elif (b, a) not in pair_map:
            keep.add((a, b))
    agg = agg[agg.apply(lambda r: (r.from_entity_id, r.to_entity_id) in keep, axis=1)]

    # Break remaining cycles by repeatedly removing the smallest edge on a cycle
    g = nx.DiGraph()
    for r in agg.itertuples():
        g.add_edge(r.from_entity_id, r.to_entity_id, weight=float(r.amount_eom))
    try:
        while True:
            cycle = nx.find_cycle(g, orientation="original")
            weakest = min(cycle, key=lambda e: g[e[0]][e[1]]["weight"])
            g.remove_edge(weakest[0], weakest[1])
    except nx.NetworkXNoCycle:
        pass

    keep_pairs = set((u, v) for u, v in g.edges())
    return agg[agg.apply(lambda r: (r.from_entity_id, r.to_entity_id) in keep_pairs, axis=1)]


def ic_sankey(df: pd.DataFrame, name_map: dict[str, str],
              ic_type_col: str = "ic_type") -> dict:
    """df columns: from_entity_id, to_entity_id, ic_type, amount_eom."""
    if df.empty:
        return {"title": {"text": "No IC flows for this selection", "left": "center", "top": "center"}}

    # Pick dominant ic_type per pair for coloring before aggregation
    dominant = (df.groupby(["from_entity_id", "to_entity_id", ic_type_col])["amount_eom"]
                 .sum().reset_index()
                 .sort_values("amount_eom", ascending=False)
                 .drop_duplicates(["from_entity_id", "to_entity_id"])
                 .set_index(["from_entity_id", "to_entity_id"])[ic_type_col].to_dict())

    agg = _dedupe_and_break_cycles(df[["from_entity_id", "to_entity_id", "amount_eom"]])
    if agg.empty:
        return {"title": {"text": "No IC flows for this selection", "left": "center", "top": "center"}}

    nodes = sorted(set(agg["from_entity_id"]).union(agg["to_entity_id"]))
    data_nodes = [{"name": name_map.get(n, n)} for n in nodes]
    data_links = []
    for r in agg.itertuples():
        typ = dominant.get((r.from_entity_id, r.to_entity_id), "IC_AR")
        data_links.append({
            "source": name_map.get(r.from_entity_id, r.from_entity_id),
            "target": name_map.get(r.to_entity_id, r.to_entity_id),
            "value": float(r.amount_eom),
            "lineStyle": {"color": "source", "opacity": 0.45, "curveness": 0.5},
        })

    return {
        "tooltip": {"trigger": "item", "triggerOn": "mousemove"},
        "series": [{
            "type": "sankey",
            "data": data_nodes,
            "links": data_links,
            "emphasis": {"focus": "adjacency"},
            "nodeAlign": "justify",
            "layoutIterations": 32,
            "label": {"fontSize": 11, "color": "#202124", "fontWeight": "bold"},
            "edgeLabel": {
                "show": True, 
                "formatter": "▶", 
                "fontSize": 12, 
                "color": "#1e293b",
                "opacity": 0.8
            },
            "itemStyle": {"borderWidth": 1, "borderColor": "#334155"},
            "left": "4%", "right": "8%", "top": "3%", "bottom": "3%",
        }],
    }
