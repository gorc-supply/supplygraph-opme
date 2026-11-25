"""Graph Data Science (local Neo4j + GDS plugin) via the official `graphdatascience` client.

Every projection is named, documented (why these nodes / weights) and ALWAYS dropped at the end.
Results are written back as node properties / relationships (`.write`) because AuraDB Free
has no in-database GDS plugin: the public demo reads the pre-computed values.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
from graphdatascience import GraphDataScience
from rich.console import Console

from supplygraph.analytics.report import OUT, _save, save_metrics
from supplygraph.config import neo4j_settings
from supplygraph.db import driver_ctx, run

console = Console()
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)  # graphdatascience uses id() internally

# 1) Material-flow network, UNDIRECTED. Betweenness: how many shortest paths between any two
#    actors of the chain cross a node -> chokepoints. Undirected on purpose: in a directed flow
#    graph a tier-3 source has zero betweenness by definition (no path goes *through* a source),
#    yet a sole tier-3 source is the archetypal chokepoint.
FLOW_PROJECTION = "sg_flow"
# 2) Dependency network, DIRECTED dependent -> provider, weighted by money / share:
#    Hospital -CONSUMES(revenue)-> Item -BOM-> child Item -SUPPLIES(share)-> Supplier
#    -BUYS_FROM(share)-> sub-tier Supplier; Item -MANUFACTURES(share)-> Plant.
#    PageRank then flows "importance" from revenue down to whoever everything depends on.
DEP_PROJECTION = "sg_dependency"
# 3) Sourcing network (Supplier, Item; SUPPLIES, COMPONENT_OF, BUYS_FROM) UNDIRECTED for
#    community detection: do natural sourcing clusters match purchasing categories?
SOURCING_PROJECTION = "sg_sourcing"
# 4) Supplier -> Item bipartite for Node Similarity (Jaccard of the item portfolios).
PORTFOLIO_PROJECTION = "sg_portfolio"
# 5) Logistics network (Plant, Port, DC, Hospital) DIRECTED with lead time and cost for
#    Dijkstra / Yen; an undirected copy for WCC and bridges (single corridors).
LOGISTICS_PROJECTION = "sg_logistics"
LOGISTICS_UNDIRECTED = "sg_logistics_u"


def gds_client() -> GraphDataScience:
    s = neo4j_settings()
    return GraphDataScience(
        s.uri, auth=(s.user, s.password), database=s.database, arrow=False, show_progress=False
    )


def _drop_all(gds: GraphDataScience) -> None:
    for name in (
        FLOW_PROJECTION,
        DEP_PROJECTION,
        SOURCING_PROJECTION,
        PORTFOLIO_PROJECTION,
        LOGISTICS_PROJECTION,
        LOGISTICS_UNDIRECTED,
        "sg_logistics_no_port",
    ):
        gds.graph.drop(name, fail_if_missing=False)


def _g(res):
    """graph.project.* returns (graph, result) in the 2.x client."""
    return res[0] if isinstance(res, tuple) else getattr(res, "graph", res)


def project_all(gds: GraphDataScience) -> dict:
    flow_rels = ["SUPPLIES", "BUYS_FROM", "COMPONENT_OF", "MANUFACTURES", "SHIPS_TO", "STOCKS", "SERVES"]
    g_flow = _g(
        gds.graph.project.native(
            FLOW_PROJECTION,
            ["Supplier", "Item", "Plant", "Port", "DC", "Hospital"],
            {t: {"orientation": "UNDIRECTED"} for t in flow_rels},
        )
    )
    g_dep = _g(
        gds.graph.project.cypher(
            """
        CALL () {
          MATCH (h:Hospital)-[c:CONSUMES]->(f:Item) RETURN h AS s, f AS t, c.revenue_month AS w
          UNION ALL
          MATCH (c:Item)-[:COMPONENT_OF]->(p:Item) RETURN p AS s, c AS t, 1.0 AS w
          UNION ALL
          MATCH (sp:Supplier)-[r:SUPPLIES]->(i:Item) RETURN i AS s, sp AS t, r.share_pct AS w
          UNION ALL
          MATCH (b:Supplier)-[r:BUYS_FROM]->(u:Supplier) RETURN b AS s, u AS t, r.share_pct AS w
          UNION ALL
          MATCH (pl:Plant)-[m:MANUFACTURES]->(f:Item) RETURN f AS s, pl AS t, m.share_pct AS w
        }
        RETURN gds.graph.project($name, s, t,
          {sourceNodeLabels: labels(s), targetNodeLabels: labels(t), relationshipProperties: {weight: w}})
        """,
            name=DEP_PROJECTION,
        )
    )
    g_src = _g(
        gds.graph.project.native(
            SOURCING_PROJECTION,
            ["Supplier", "Item"],
            {t: {"orientation": "UNDIRECTED"} for t in ("SUPPLIES", "COMPONENT_OF", "BUYS_FROM")},
        )
    )
    g_port = _g(
        gds.graph.project.native(
            PORTFOLIO_PROJECTION, ["Supplier", "Item"], {"SUPPLIES": {"orientation": "NATURAL"}}
        )
    )
    logi_rels = {
        "SHIPS_TO": {
            "properties": {
                "lead_time_days": {"property": "lead_time_days"},
                "cost_per_unit": {"property": "cost_per_unit"},
            }
        },
        "SERVES": {
            "properties": {
                "lead_time_days": {"property": "lead_time_days"},
                "cost_per_unit": {"property": "cost_per_unit"},
            }
        },
    }
    g_log = _g(gds.graph.project.native(LOGISTICS_PROJECTION, ["Plant", "Port", "DC", "Hospital"], logi_rels))
    g_logu = _g(
        gds.graph.project.native(
            LOGISTICS_UNDIRECTED,
            ["Plant", "Port", "DC", "Hospital"],
            {"SHIPS_TO": {"orientation": "UNDIRECTED"}, "SERVES": {"orientation": "UNDIRECTED"}},
        )
    )
    return {
        "flow": g_flow,
        "dep": g_dep,
        "sourcing": g_src,
        "portfolio": g_port,
        "logistics": g_log,
        "logistics_u": g_logu,
    }


def _purity(df: pd.DataFrame, cluster: str, label: str) -> float:
    """Share of nodes whose cluster's majority label equals their own label."""
    if df.empty:
        return 0.0
    maj = df.groupby(cluster)[label].agg(lambda s: s.value_counts().iloc[0]).sum()
    return float(maj / len(df))


def _nmi(a: pd.Series, b: pd.Series) -> float:
    import numpy as np

    ct = pd.crosstab(a, b).to_numpy().astype(float)
    n = ct.sum()
    pij = ct / n
    pi, pj = pij.sum(1, keepdims=True), pij.sum(0, keepdims=True)
    nz = pij > 0
    mi = float((pij[nz] * np.log(pij[nz] / (pi @ pj)[nz])).sum())
    hi = float(-(pi[pi > 0] * np.log(pi[pi > 0])).sum())
    hj = float(-(pj[pj > 0] * np.log(pj[pj > 0])).sum())
    return mi / ((hi + hj) / 2) if hi + hj > 0 else 0.0


def run_gds() -> dict:
    gds = gds_client()
    m: dict = {"gds_version": str(gds.server_version())}
    t0 = time.perf_counter()
    _drop_all(gds)
    try:
        G = project_all(gds)
        m["projections"] = {
            k: {"nodes": int(g.node_count()), "relationships": int(g.relationship_count())}
            for k, g in G.items()
        }

        # Betweenness: chokepoints of the material flow (exact - the projection is small)
        r = gds.betweenness.write(G["flow"], write_property="betweenness")
        m["betweenness"] = {"compute_ms": int(r.compute_millis), "nodes": int(r.node_properties_written)}
        # PageRank on the revenue-weighted dependency graph
        r = gds.page_rank.write(
            G["dep"],
            write_property="pagerank",
            relationship_weight_property="weight",
            damping_factor=0.85,
            max_iterations=50,
        )
        m["pagerank"] = {"iterations": int(r.ran_iterations), "converged": bool(r.did_converge)}
        # WCC on the whole flow network and on the logistics layer
        r = gds.wcc.write(G["flow"], write_property="component_id")
        m["wcc_flow_components"] = int(r.component_count)
        r = gds.wcc.write(G["logistics_u"], write_property="logistics_component")
        m["wcc_logistics_components"] = int(r.component_count)
        # Leiden communities on the sourcing network
        r = gds.leiden.write(G["sourcing"], write_property="community_id", random_seed=42, concurrency=1)
        m["leiden"] = {"communities": int(r.community_count), "modularity": float(r.modularity)}
        # Node Similarity: suppliers with overlapping portfolios -> alternative sourcing candidates
        run(gds_driver(), "MATCH ()-[r:SIMILAR_PORTFOLIO]->() DELETE r", write=True)
        r = gds.node_similarity.write(
            G["portfolio"],
            write_relationship_type="SIMILAR_PORTFOLIO",
            write_property="jaccard",
            top_k=3,
            similarity_cutoff=0.1,
        )
        m["node_similarity"] = {
            "relationships": int(r.relationships_written),
            "nodes_compared": int(r.nodes_compared),
        }
        # FastRP embeddings + kNN: structurally similar suppliers (beyond shared items)
        gds.fast_rp.mutate(
            G["sourcing"],
            mutate_property="emb",
            embedding_dimension=64,
            random_seed=42,
            iteration_weights=[0.0, 1.0, 1.0, 0.5],
        )
        knn = gds.knn.stream(
            G["sourcing"],
            node_labels=["Supplier"],
            node_properties=["emb"],
            top_k=3,
            random_seed=42,
            concurrency=1,
            sample_rate=1.0,
            delta_threshold=0.0,
        )
        ids = gds.util.as_nodes(knn["node1"].tolist())
        ids2 = gds.util.as_nodes(knn["node2"].tolist())
        knn_df = pd.DataFrame(
            {
                "supplier": [n["id"] for n in ids],
                "similar_supplier": [n["id"] for n in ids2],
                "similarity": knn["similarity"].round(4),
            }
        )
        _save(knn_df, "GDS_fastrp_knn_suppliers")
        # Bridges and articulation points on the logistics network = single corridors
        br = gds.bridges.stream(G["logistics_u"])
        a = gds.util.as_nodes(br["from"].tolist())
        b = gds.util.as_nodes(br["to"].tolist())
        bridges = pd.DataFrame(
            {
                "from": [x.get("code") or x.get("id") for x in a],
                "to": [x.get("code") or x.get("id") for x in b],
            }
        )
        bridges = bridges[~bridges["to"].str.startswith("H-") & ~bridges["from"].str.startswith("H-")]
        _save(bridges, "GDS_logistics_bridges_non_hospital")
        ap = gds.articulation_points.stream(G["logistics_u"])
        apn = gds.util.as_nodes(ap["nodeId"].tolist())
        aps = sorted({x.get("code") or x.get("id") for x in apn})
        m["logistics_single_points"] = {
            "bridges_excluding_last_mile": bridges.to_dict("records"),
            "articulation_points": aps,
        }

        # Dijkstra / Yen on the logistics layer (section 9F), cross-checked with the Cypher version
        m["routes_gds"] = _routes(gds, G["logistics"])
    finally:
        _drop_all(gds)  # never leave projections behind (memory)
    m["runtime_s"] = round(time.perf_counter() - t0, 1)

    # --- read results back, interpret
    with driver_ctx() as d:
        top_btw = run(
            d,
            """MATCH (n) WHERE n.betweenness IS NOT NULL AND (n:Supplier OR n:Item OR n:DC OR n:Port)
                            RETURN coalesce(n.id, n.sku, n.code) AS id, labels(n)[0] AS label, n.name AS name,
                                   round(n.betweenness) AS betweenness ORDER BY betweenness DESC LIMIT 15""",
        )
        top_pr_sup = run(
            d,
            """MATCH (s:Supplier) RETURN s.id AS id, s.tier AS tier, s.country_iso2 AS country,
                                   round(s.pagerank, 4) AS pagerank ORDER BY s.pagerank DESC LIMIT 15""",
        )
        comm = pd.DataFrame(
            run(
                d,
                """MATCH (i:Item) WHERE i.type <> 'RAW'
                                      RETURN i.sku AS sku, i.category AS category, i.family AS family,
                                             i.community_id AS community""",
            )
        )
        single_corr = run(
            d,
            """MATCH (h:Hospital) WHERE COUNT { (:DC)-[:SERVES]->(h) } = 1
                                MATCH (dc:DC)-[:SERVES]->(h)
                                WHERE COUNT { (:DC)-[:SHIPS_TO]->(dc) } + COUNT { (:Port)-[:SHIPS_TO]->(dc) } <= 1
                                RETURN dc.id AS dc, count(h) AS hospitals ORDER BY hospitals DESC""",
        )
        sim = run(
            d,
            """MATCH (a:Supplier)-[r:SIMILAR_PORTFOLIO]->(b:Supplier)
                        RETURN a.id AS supplier, b.id AS alternative, round(r.jaccard, 3) AS jaccard,
                               a.tier AS tier, b.country_iso2 AS alt_country ORDER BY jaccard DESC LIMIT 30""",
        )
    _save(pd.DataFrame(top_btw), "GDS_betweenness_top")
    _save(pd.DataFrame(top_pr_sup), "GDS_pagerank_suppliers_top")
    _save(pd.DataFrame(sim), "GDS_node_similarity_top")
    _save(pd.DataFrame(single_corr), "GDS_single_corridor_dcs")
    cat_col = comm["category"].where(~comm["category"].str.endswith("COMMON"), comm["family"])
    m["communities_vs_categories"] = {
        "items": len(comm),
        "communities": int(comm["community"].nunique()),
        "purity_vs_category": round(_purity(comm.assign(cat=cat_col), "community", "cat"), 3),
        "purity_vs_family": round(_purity(comm, "community", "family"), 3),
        "nmi_vs_category": round(_nmi(comm["community"], cat_col), 3),
    }
    ct = pd.crosstab(comm["community"], cat_col)
    ct.to_csv(OUT / "GDS_communities_x_category.csv")
    m["top_betweenness"] = top_btw[:10]
    m["top_pagerank_suppliers"] = top_pr_sup[:10]
    m["single_corridor_dcs"] = single_corr
    save_metrics({"GDS": m})
    console.print(
        f"GDS {m['gds_version']}: done in {m['runtime_s']}s | Leiden {m['leiden']['communities']} communities "
        f"(purity vs category {m['communities_vs_categories']['purity_vs_category']})"
    )
    return m


def gds_driver():
    from supplygraph.db import get_driver

    return get_driver()


def _routes(gds: GraphDataScience, G) -> dict:
    with driver_ctx() as d:
        pair = run(
            d,
            """MATCH (pl:Plant)-[:SHIPS_TO]->(:Port)-[:SHIPS_TO]->(:Port {code:'GRU'})
                         MATCH (h:Hospital {uf: 'BA'}) RETURN pl.id AS plant, h.id AS hospital
                         ORDER BY plant, hospital LIMIT 1""",
        )[0]
    src = gds.util.find_node_id(["Plant"], {"id": pair["plant"]})
    dst = gds.util.find_node_id(["Hospital"], {"id": pair["hospital"]})
    out = {"pair": pair}
    for w in ("lead_time_days", "cost_per_unit"):
        dj = gds.shortest_path.dijkstra.stream(
            G, source_node=src, target_nodes=dst, relationship_weight_property=w
        )
        yen = gds.shortest_path.yens.stream(
            G, source_node=src, target_node=dst, k=5, relationship_weight_property=w
        )
        rows = []
        for r in yen.itertuples():
            nodes = gds.util.as_nodes(list(r.nodeIds))
            rows.append(
                {
                    "rank": int(r.index) + 1,
                    "total": round(float(r.totalCost), 2),
                    "route": " > ".join(n.get("code") or n.get("id") for n in nodes),
                }
            )
        _save(pd.DataFrame(rows), f"GDS_yen_{w}")
        out[w] = {
            "dijkstra_total": round(float(dj["totalCost"].iloc[0]), 2) if len(dj) else None,
            "yen_top5": rows,
        }
    return out
