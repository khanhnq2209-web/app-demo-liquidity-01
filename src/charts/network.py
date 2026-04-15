"""Ownership tree + IC network graphs (ECharts) with multiple layouts."""
from __future__ import annotations

import pandas as pd


def ownership_tree(dim_entity: pd.DataFrame, rel: pd.DataFrame, root: str = "GELEX") -> dict:
    children = rel.groupby("parent_entity_id")
    name = dict(zip(dim_entity["entity_id"], dim_entity["entity_name"]))

    def build(eid: str) -> dict:
        node = {"name": f"{eid} · {name.get(eid, eid)}"}
        if eid in children.groups:
            node["children"] = []
            for _, r in children.get_group(eid).iterrows():
                child = build(r.child_entity_id)
                child["value"] = float(r.ownership_pct)
                node["children"].append(child)
        return node

    return {
        "tooltip": {"trigger": "item", "formatter": "{b}<br/>Ownership: {c}%"},
        "toolbox": {
            "show": True, "right": "2%", "top": "1%",
            "feature": {"restore": {"title": "Reset"}, "saveAsImage": {"title": "Save"}},
        },
        "series": [{
            "type": "tree",
            "data": [build(root)],
            "top": "5%", "bottom": "5%", "left": "12%", "right": "18%",
            "symbolSize": 12,
            "orient": "LR",
            "roam": True,
            "itemStyle": {"color": "#1a73e8"},
            "lineStyle": {"color": "#9aa0a6", "width": 1.2, "curveness": 0.4},
            "label": {"position": "left", "verticalAlign": "middle",
                       "align": "right", "fontSize": 12, "color": "#202124"},
            "leaves": {"label": {"position": "right", "align": "left", "color": "#202124"}},
            "expandAndCollapse": True,
            "initialTreeDepth": 3,
            "animationDuration": 400,
        }],
    }


# ---------------------------------------------------------------------------
# IC network
# ---------------------------------------------------------------------------

_CATEGORIES = [
    {"name": "Holding",     "itemStyle": {"color": "#c5221f"}},
    {"name": "GEE",         "itemStyle": {"color": "#1a73e8"}},
    {"name": "GEL",         "itemStyle": {"color": "#188038"}},
    {"name": "Trực thuộc",  "itemStyle": {"color": "#e8710a"}},
]


def _category_index(e_row) -> int:
    if e_row.entity_type == "HOLDING":
        return 0
    if e_row.subholding_code == "GEE":
        return 1
    if e_row.subholding_code == "GEL":
        return 2
    return 3


def ic_network(ic_arap: pd.DataFrame, ic_loan: pd.DataFrame,
               dim_entity: pd.DataFrame, show_ar: bool, show_loan: bool,
               top_n: int = 20, layout: str = "circular") -> dict:
    """layout: 'circular' | 'force' | 'none' (use provided node positions)."""
    entity_by_id = {e.entity_id: e for e in dim_entity.itertuples()}
    name = {eid: f"{eid} · {e.entity_name}" for eid, e in entity_by_id.items()}

    edges: list[dict] = []
    if show_ar and not ic_arap.empty:
        top = (ic_arap.groupby(["from_entity_id", "to_entity_id", "ic_type"], as_index=False)
                       ["amount_eom"].sum()
                       .nlargest(top_n, "amount_eom"))
        for r in top.itertuples():
            edges.append({
                "source": name.get(r.from_entity_id, r.from_entity_id),
                "target": name.get(r.to_entity_id, r.to_entity_id),
                "value": float(r.amount_eom),
                "lineStyle": {"color": "#1a73e8" if r.ic_type == "IC_AR" else "#f59e4c",
                               "width": 1.6, "opacity": 0.75, "curveness": 0.15},
            })
    if show_loan and not ic_loan.empty:
        top = (ic_loan.groupby(["lender_entity_id", "borrower_entity_id"], as_index=False)
                       ["outstanding_eom"].sum()
                       .nlargest(top_n, "outstanding_eom"))
        for r in top.itertuples():
            edges.append({
                "source": name.get(r.lender_entity_id, r.lender_entity_id),
                "target": name.get(r.borrower_entity_id, r.borrower_entity_id),
                "value": float(r.outstanding_eom),
                "lineStyle": {"color": "#188038", "width": 2.2, "opacity": 0.8,
                               "type": "dashed", "curveness": 0.15},
            })

    node_names = sorted(set(e["source"] for e in edges) | set(e["target"] for e in edges))
    # compute node sizes proportional to total incident value
    incident = {n: 0.0 for n in node_names}
    for e in edges:
        incident[e["source"]] += e["value"]
        incident[e["target"]] += e["value"]
    max_inc = max(incident.values()) if incident else 1

    nodes = []
    for n in node_names:
        eid = n.split(" · ")[0]
        cat = _category_index(entity_by_id[eid]) if eid in entity_by_id else 3
        size = 16 + 40 * (incident[n] / max_inc if max_inc else 0)
        nodes.append({
            "name": n,
            "symbolSize": size,
            "category": cat,
            "label": {"show": True, "fontSize": 11, "color": "#202124"},
        })

    common = {
        "roam": True,
        "draggable": True,
        "label": {"show": True, "fontSize": 11, "color": "#202124", "position": "right"},
        "edgeSymbol": ["none", "arrow"],
        "edgeSymbolSize": 6,
        "data": nodes,
        "links": edges,
        "categories": _CATEGORIES,
        "emphasis": {"focus": "adjacency", "lineStyle": {"width": 3}},
    }

    if layout == "force":
        series = {**common, "type": "graph", "layout": "force",
                   "force": {"repulsion": 450, "edgeLength": [80, 200], "gravity": 0.08,
                              "layoutAnimation": True}}
    elif layout == "circular":
        series = {**common, "type": "graph", "layout": "circular",
                   "circular": {"rotateLabel": True}}
    else:
        series = {**common, "type": "graph", "layout": "none"}

    return {
        "tooltip": {"formatter": "function(p){if(p.dataType==='edge'){return p.data.source+' → '+p.data.target+'<br/>'+(p.data.value/1e9).toFixed(2)+' Tỷ VND';}return p.name;}"},
        "legend": [{"data": [c["name"] for c in _CATEGORIES], "top": 4,
                     "textStyle": {"color": "#5f6368"}}],
        "series": [series],
    }

def cashflow_network(cf_df: pd.DataFrame, dim_entity: pd.DataFrame, name_map: dict[str, str], top_n: int = 20, layout: str = "circular") -> dict:
    """Cashflow-specific interactive network graph."""
    edges: list[dict] = []
    
    # Aggregate abs flow amounts
    cf_df = cf_df.copy()
    cf_df["abs_flow"] = cf_df["flow_amount"].abs()
    
    # Top N pairs by volume
    top = cf_df.groupby(["from_entity_id", "to_entity_id"], as_index=False)["abs_flow"].sum().nlargest(top_n, "abs_flow")
    
    # We want to dominant category per pair
    dom = cf_df.groupby(["from_entity_id", "to_entity_id", "activity_category"])["abs_flow"].sum().reset_index().sort_values("abs_flow", ascending=False).drop_duplicates(["from_entity_id", "to_entity_id"]).set_index(["from_entity_id", "to_entity_id"])["activity_category"].to_dict()
    
    cat_colors = {"OPERATING": "#34a853", "INVESTING": "#fbbc04", "FINANCING": "#1a73e8"}
    
    for r in top.itertuples():
        dom_cat = dom.get((r.from_entity_id, r.to_entity_id), "OPERATING")
        edges.append({
            "source": name_map.get(r.from_entity_id, r.from_entity_id),
            "target": name_map.get(r.to_entity_id, r.to_entity_id),
            "value": float(r.abs_flow),
            "lineStyle": {"color": cat_colors.get(dom_cat, "#888"), "width": 1.6, "opacity": 0.75, "curveness": 0.15},
        })

    node_names = sorted(set(e["source"] for e in edges) | set(e["target"] for e in edges))
    incident = {n: 0.0 for n in node_names}
    for e in edges:
        incident[e["source"]] += e["value"]
        incident[e["target"]] += e["value"]
    max_inc = max(incident.values()) if incident else 1

    entity_by_id = {str(e.entity_id): e for e in dim_entity.itertuples()}
    nodes = []
    for n in node_names:
        # Re-derive eid from names, or we can just iterate using the map
        # If external, it will default to 3
        # Wait, name_map values are like "EVN" not "CG01 · EVN". Sankey uses the full mapped name!
        # So n is the mapped name. We need to check if it matches an entity name.
        cat = 3 # External
        for e_obj in entity_by_id.values():
            if e_obj.entity_name == n:
                cat = _category_index(e_obj)
                break
        
        size = 18 + 45 * (incident[n] / max_inc if max_inc else 0)
        nodes.append({
            "name": n,
            "symbolSize": size,
            "category": cat,
            "label": {"show": True, "fontSize": 11, "color": "#202124"},
        })

    common = {
        "roam": True, "draggable": True,
        "label": {"show": True, "fontSize": 11, "color": "#202124", "position": "right"},
        "edgeSymbol": ["none", "arrow"], "edgeSymbolSize": 7,
        "data": nodes, "links": edges, "categories": _CATEGORIES,
        "emphasis": {"focus": "adjacency", "lineStyle": {"width": 3}},
    }

    series = {**common, "type": "graph", "layout": layout}
    if layout == "force":
        series["force"] = {"repulsion": 500, "edgeLength": [100, 200], "gravity": 0.08, "layoutAnimation": True}
    elif layout == "circular":
        series["circular"] = {"rotateLabel": True}

    return {
        "tooltip": {"formatter": "function(p){if(p.dataType==='edge'){return p.data.source+' → '+p.data.target+'<br/>'+(p.data.value/1e9).toFixed(2)+' Tỷ VND';}return p.name;}"},
        "legend": [{"data": [c["name"] for c in _CATEGORIES], "top": 4, "textStyle": {"color": "#5f6368"}}],
        "series": [series],
    }
