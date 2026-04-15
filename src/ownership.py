"""Ownership graph analytics via networkx."""
from __future__ import annotations

import networkx as nx
import pandas as pd


def build_graph(rel_ownership: pd.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    for _, r in rel_ownership.iterrows():
        g.add_edge(r.parent_entity_id, r.child_entity_id,
                   weight=float(r.ownership_pct) / 100.0)
    return g


def effective_ownership(g: nx.DiGraph, root: str) -> dict[str, float]:
    """Effective % of ownership from `root` to every reachable descendant.

    Multiplies direct ownership along the path. If multiple paths exist, sums them
    (standard effective-ownership calc).
    """
    eff: dict[str, float] = {root: 1.0}
    for node in nx.topological_sort(g):
        if node not in eff:
            continue
        for child in g.successors(node):
            w = g[node][child]["weight"]
            eff[child] = eff.get(child, 0.0) + eff[node] * w
    return eff


def centrality(g: nx.DiGraph) -> pd.DataFrame:
    betw = nx.betweenness_centrality(g)
    deg = dict(g.degree())
    return pd.DataFrame({
        "entity_id": list(g.nodes()),
        "degree": [deg[n] for n in g.nodes()],
        "betweenness": [betw[n] for n in g.nodes()],
    })


def has_cycles(g: nx.DiGraph) -> list[list[str]]:
    try:
        return list(nx.simple_cycles(g))
    except Exception:
        return []
