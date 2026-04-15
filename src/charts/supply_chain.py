"""yFiles-styled Supply Chain Box Layout using Graphviz."""
from __future__ import annotations

import pandas as pd
import graphviz


def supply_chain_graph(
    comp_df: pd.DataFrame, 
    ic_arap: pd.DataFrame, 
    ic_loan: pd.DataFrame, 
    name_map: dict[str, str],
    top_edges: int = 15
) -> graphviz.Digraph:
    """
    Groups entities by `supply_chain_node` into Graphviz clusters (Boxes).
    Decorates each entity node with an HTML table showing AP, AR, Debt (Internal).
    """
    dot = graphviz.Digraph(engine="dot")
    dot.attr(rankdir="LR", ranksep="1.0", nodesep="0.3", splines="ortho", concentrate="true")
    dot.attr("node", shape="none", margin="0", fontname="Helvetica")
    dot.attr("edge", color="#64748b", penwidth="1.8", arrowhead="vee", arrowsize="0.8")

    # Aggregate AR, AP, Loan per entity
    ar_agg = ic_arap[ic_arap["ic_type"] == "IC_AR"].groupby("to_entity_id")["amount_eom"].sum()
    ap_agg = ic_arap[ic_arap["ic_type"] == "IC_AP"].groupby("from_entity_id")["amount_eom"].sum()
    
    comp_df = comp_df.copy()
    comp_df["subholding_code"] = comp_df["subholding_code"].fillna("Trực Thuộc Tập Đoàn")
    
    # Create clusters for each sub-holding
    nodes_by_chain = comp_df.groupby("subholding_code")
    
    for str_node, group in nodes_by_chain:
        # Create subgraph box
        cluster_name = f"cluster_{str_node.replace('/', '_').replace(' ', '_')}"
        with dot.subgraph(name=cluster_name) as c:
            c.attr(style="rounded,filled", fillcolor="#f8fafc", color="#cbd5e1", penwidth="2")
            c.attr(label=str_node.upper(), fontname="Helvetica-Bold", fontsize="14", fontcolor="#334155")
            
            for _, r in group.iterrows():
                eid = r["entity_id"]
                ename = name_map.get(eid, eid)
                # Cap extremely long names for Graphviz rendering
                if len(ename) > 25:
                    ename = ename[:22] + "..."
                    
                ar_val = ar_agg.get(eid, 0) / 1e9
                ap_val = ap_agg.get(eid, 0) / 1e9
                
                # Format internal debt properly
                # For a node, how much did it borrow?
                l_agg = ic_loan[ic_loan["borrower_entity_id"] == eid]["outstanding_eom"].sum() / 1e9
                
                node_html = f'''<
                <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" COLOR="#cbd5e1" BGCOLOR="#ffffff">
                  <TR><TD COLSPAN="2" BGCOLOR="#334155" ALIGN="CENTER"><B><FONT COLOR="#ffffff">{ename}</FONT></B></TD></TR>
                  <TR><TD ALIGN="LEFT"><FONT COLOR="#64748b"><B>Phải thu Nội bộ</B></FONT></TD><TD ALIGN="RIGHT" BGCOLOR="#f0fdf4"><FONT COLOR="#16a34a"><B>{ar_val:,.1f}</B> B</FONT></TD></TR>
                  <TR><TD ALIGN="LEFT"><FONT COLOR="#64748b"><B>Phải trả Nội bộ</B></FONT></TD><TD ALIGN="RIGHT" BGCOLOR="#fef2f2"><FONT COLOR="#dc2626"><B>{ap_val:,.1f}</B> B</FONT></TD></TR>
                  <TR><TD ALIGN="LEFT"><FONT COLOR="#64748b"><B>Dư nợ Vay</B></FONT></TD><TD ALIGN="RIGHT" BGCOLOR="#fffbeb"><FONT COLOR="#d97706"><B>{l_agg:,.1f}</B> B</FONT></TD></TR>
                </TABLE>>'''
                
                c.node(eid, label=node_html)

    # Add logical edges based on standard material flow between nodes simply to show connection
    # Not plotting every single IC edge to avoid spaghetti, plot top ~15 logical flows
    agg_edges = ic_arap.groupby(["from_entity_id", "to_entity_id"])["amount_eom"].sum().nlargest(top_edges)
    for (src, tgt), amount in agg_edges.items():
        if src in comp_df["entity_id"].values and tgt in comp_df["entity_id"].values:
            dot.edge(src, tgt, label=f" {amount/1e9:.1f}B ", fontcolor="#0f172a", fontsize="11", style="bold")

    return dot

def cashflow_supply_chain(
    cf: pd.DataFrame,
    comp_df: pd.DataFrame,
    cg_df: pd.DataFrame,
    name_map: dict[str, str]
) -> graphviz.Digraph:
    """Graphviz map for Cashflow, grouping External into a Clients Box and Internal into Supply Chain."""
    dot = graphviz.Digraph(engine="dot")
    dot.attr(rankdir="LR", ranksep="1.5", nodesep="0.6")
    dot.attr("node", shape="none", margin="0", fontname="Helvetica")
    dot.attr("edge", color="#94a3b8", uniform="true", penwidth="1.2")

    cf_agg = cf.groupby(["from_entity_id", "to_entity_id", "activity_category"])["flow_amount"].sum()

    comp_df = comp_df.copy()
    comp_df["subholding_code"] = comp_df["subholding_code"].fillna("Trực Thuộc Tập Đoàn")
    nodes_by_chain = comp_df.groupby("subholding_code")
    rendered_nodes = set()
    
    # Internal clusters
    for str_node, group in nodes_by_chain:
        cluster_name = f"cluster_{str_node.replace('/', '_').replace(' ', '_')}"
        with dot.subgraph(name=cluster_name) as c:
            c.attr(style="rounded,filled", fillcolor="#f8fafc", color="#cbd5e1", penwidth="2")
            c.attr(label=str_node.upper(), fontname="Helvetica-Bold", fontsize="14", fontcolor="#334155")
            for _, r in group.iterrows():
                eid = r["entity_id"]
                ename = name_map.get(eid, eid)
                if len(ename) > 25: ename = ename[:22] + "..."
                
                # We don't have AR/AP here, but we can just show the Node name clearly
                node_html = f'''<
                <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" COLOR="#64748b">
                  <TR><TD BGCOLOR="#e2e8f0" ALIGN="CENTER"><B><FONT COLOR="#0f172a">{ename}</FONT></B></TD></TR>
                </TABLE>>'''
                c.node(eid, label=node_html)
                rendered_nodes.add(eid)

    # External Client Group cluster
    with dot.subgraph(name="cluster_EXTERNAL") as ext:
        ext.attr(style="rounded,filled", fillcolor="#fff1f2", color="#fda4af", penwidth="2")
        ext.attr(label="EXTERNAL COUNTERPARTIES", fontname="Helvetica-Bold", fontsize="14", fontcolor="#be123c")
        for eid in cg_df["client_group_id"].unique():
            ename = name_map.get(eid, eid)
            node_html = f'''<
            <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" COLOR="#f43f5e">
              <TR><TD BGCOLOR="#ffe4e6" ALIGN="CENTER"><B><FONT COLOR="#9f1239">{ename}</FONT></B></TD></TR>
            </TABLE>>'''
            ext.node(eid, label=node_html)
            rendered_nodes.add(eid)

    # Draw edges based on top cashflows
    agg_flow = cf.groupby(["from_entity_id", "to_entity_id"])["flow_amount"].sum().reset_index()
    agg_flow["abs_flow"] = agg_flow["flow_amount"].abs()
    top_flows = agg_flow.nlargest(25, "abs_flow")
    
    for _, r in top_flows.iterrows():
        src = r["from_entity_id"]
        tgt = r["to_entity_id"]
        if src in rendered_nodes and tgt in rendered_nodes:
            amount = abs(r["flow_amount"]) / 1e9
            dot.edge(src, tgt, label=f"{amount:.1f}B", fontsize="10", fontcolor="#475569")

    return dot
