"""Intercompany & Cashflow Sankey — cycle-safe aggregation."""
from __future__ import annotations

import networkx as nx
import pandas as pd


_CAT_COLOR = {
    "IC_AR": "#4c8bf5",
    "IC_AP": "#f59e4c",
    "IC_LOAN": "#16a34a",
    "OPERATING": "#3b82f6",
    "INVESTING": "#f59e0b",
    "FINANCING": "#10b981",
}


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

    # Net out bidirectional pairs: keep net direction, net value
    pair_map: dict[tuple, float] = {}
    for r in agg.itertuples():
        a, b, w = r.from_entity_id, r.to_entity_id, float(r.amount_eom)
        if (b, a) in pair_map:
            # Reverse already seen — net them
            reverse_w = pair_map.pop((b, a))
            net = w - reverse_w
            if net > 0:
                pair_map[(a, b)] = net
            elif net < 0:
                pair_map[(b, a)] = -net
            # net == 0 → both cancel out, drop
        else:
            pair_map[(a, b)] = w

    if not pair_map:
        return pd.DataFrame(columns=agg.columns)

    agg = pd.DataFrame(
        [{"from_entity_id": a, "to_entity_id": b, "amount_eom": w}
         for (a, b), w in pair_map.items()]
    )

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
            "lineStyle": {"color": _CAT_COLOR.get(typ, "#64748b"), "opacity": 0.45, "curveness": 0.5},
        })

    return {
        "tooltip": {"trigger": "item", "triggerOn": "mousemove",
                    "formatter": "function(p){var v=(p.value/1e9).toFixed(2)+' Tỷ VND';if(p.dataType==='edge'){return p.data.source+' → '+p.data.target+'<br/>'+v;}return p.name+'<br/>'+v;}"},
        "toolbox": {
            "show": True,
            "right": "2%",
            "top": "1%",
            "feature": {
                "restore": {"show": True, "title": "Reset zoom"},
                "saveAsImage": {"show": True, "title": "Save image"},
            },
        },
        "series": [{
            "type": "sankey",
            "data": data_nodes,
            "links": data_links,
            "emphasis": {"focus": "adjacency"},
            "nodeAlign": "justify",
            "layoutIterations": 32,
            "roam": True,
            "label": {"fontSize": 11, "color": "#202124", "fontWeight": "bold"},
            "edgeLabel": {
                "show": True,
                "formatter": "▶",
                "fontSize": 12,
                "color": "#1e293b",
                "opacity": 0.8
            },
            "itemStyle": {"borderWidth": 1, "borderColor": "#334155"},
            "left": "4%", "right": "8%", "top": "6%", "bottom": "3%",
        }],
    }


def cf_sankey(df: pd.DataFrame, name_map: dict[str, str],
              top_n: int = 30) -> dict:
    """Cashflow-specific Sankey that correctly shows all money flows.

    Key differences from ic_sankey:
    - Aggregates ALL rows by (from_entity_id, to_entity_id, activity_category) FIRST
      before selecting top-N pairs — avoids chopping off multi-period data.
    - Selects top-N entity PAIRS by total absolute flow (not raw rows).
    - Uses net-flow cycle resolution to preserve maximum visible flow.

    df must have columns: from_entity_id, to_entity_id, ic_type (=activity_category),
    amount_eom (already abs-valued by caller).
    """
    if df.empty:
        return {"title": {"text": "Không có dữ liệu dòng tiền", "left": "center", "top": "center"}}

    # ── Step 1: Aggregate ALL data first across all rows ──────────────────────
    # This ensures multi-period data is fully summed before top-N selection
    ic_type_col = "ic_type"
    agg_full = (
        df.groupby(["from_entity_id", "to_entity_id", ic_type_col], as_index=False)["amount_eom"]
        .sum()
    )
    agg_full = agg_full[agg_full["from_entity_id"] != agg_full["to_entity_id"]]
    agg_full = agg_full[agg_full["amount_eom"] > 0]

    if agg_full.empty:
        return {"title": {"text": "Không có dữ liệu dòng tiền", "left": "center", "top": "center"}}

    # ── Step 2: Pick top-N entity pairs by total flow ─────────────────────────
    pair_totals = (
        agg_full.groupby(["from_entity_id", "to_entity_id"])["amount_eom"]
        .sum()
        .reset_index()
        .nlargest(top_n, "amount_eom")
    )
    top_pairs = set(zip(pair_totals["from_entity_id"], pair_totals["to_entity_id"]))
    agg_top = agg_full[
        agg_full.apply(lambda r: (r.from_entity_id, r.to_entity_id) in top_pairs, axis=1)
    ].copy()

    # ── Step 3: Dominant activity category per pair (for color) ──────────────
    dominant = (
        agg_top.sort_values("amount_eom", ascending=False)
        .drop_duplicates(["from_entity_id", "to_entity_id"])
        .set_index(["from_entity_id", "to_entity_id"])[ic_type_col]
        .to_dict()
    )

    # ── Step 4: Aggregate to single value per pair for Sankey links ───────────
    agg_pairs = (
        agg_top.groupby(["from_entity_id", "to_entity_id"], as_index=False)["amount_eom"]
        .sum()
    )

    # ── Step 5: Break cycles using net-flow approach ──────────────────────────
    cycle_safe = _dedupe_and_break_cycles(agg_pairs)
    if cycle_safe.empty:
        return {"title": {"text": "Không có dữ liệu dòng tiền", "left": "center", "top": "center"}}

    # ── Step 6: Build ECharts spec ────────────────────────────────────────────
    nodes = sorted(set(cycle_safe["from_entity_id"]).union(cycle_safe["to_entity_id"]))
    data_nodes = [{"name": name_map.get(n, n)} for n in nodes]
    data_links = []
    for r in cycle_safe.itertuples():
        typ = dominant.get((r.from_entity_id, r.to_entity_id), "OPERATING")
        color = _CAT_COLOR.get(typ, "#64748b")
        val_bil = round(float(r.amount_eom) / 1e9, 2)
        data_links.append({
            "source": name_map.get(r.from_entity_id, r.from_entity_id),
            "target": name_map.get(r.to_entity_id, r.to_entity_id),
            "value": float(r.amount_eom),
            "lineStyle": {"color": color, "opacity": 0.5, "curveness": 0.5},
        })

    return {
        "tooltip": {
            "trigger": "item", "triggerOn": "mousemove",
            "formatter": "function(p){var v=(p.value/1e9).toFixed(2)+' Tỷ VND';if(p.dataType==='edge'){return p.data.source+' → '+p.data.target+'<br/>'+v;}return p.name+'<br/>'+v;}",
        },
        "toolbox": {
            "show": True,
            "right": "2%",
            "top": "1%",
            "feature": {
                "restore": {"show": True, "title": "Reset zoom"},
                "saveAsImage": {"show": True, "title": "Save image"},
            },
        },
        "color": list(_CAT_COLOR.values()),
        "series": [{
            "type": "sankey",
            "data": data_nodes,
            "links": data_links,
            "emphasis": {"focus": "adjacency"},
            "nodeAlign": "justify",
            "layoutIterations": 64,
            "roam": True,
            "label": {"fontSize": 11, "color": "#1e293b", "fontWeight": "bold"},
            "edgeLabel": {
                "show": True,
                "formatter": "▶",
                "fontSize": 11,
                "color": "#334155",
                "opacity": 0.7,
            },
            "itemStyle": {"borderWidth": 1, "borderColor": "#475569"},
            "left": "4%", "right": "10%", "top": "6%", "bottom": "3%",
        }],
    }
