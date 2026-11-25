from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from common import CATEGORICAL, GRAY, header, q, t
from neo4j_viz import Node, Relationship, VisualizationGraph

header("explorer")

cats = q("MATCH (i:Item {type:'FINISHED'}) RETURN DISTINCT i.category AS c ORDER BY c").c.tolist()
countries = q("MATCH (s:Supplier) RETURN DISTINCT s.country_iso2 AS c ORDER BY c").c.tolist()
f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
cat = f1.selectbox(t("category"), cats, index=cats.index("SPINE") if "SPINE" in cats else 0)
tiers = f2.multiselect(t("tier"), [1, 2, 3], default=[1, 2, 3])
country = f3.selectbox(t("country"), ["(all)"] + countries)
n_fin = f4.number_input(t("max_finished"), 1, 30, 6)

params = {"cat": cat, "n": int(n_fin), "tiers": tiers, "country": None if country == "(all)" else country}
items = q("""
    MATCH (f:Item {type:'FINISHED', category: $cat})
    WITH f ORDER BY f.revenue_month DESC LIMIT $n
    OPTIONAL MATCH (x:Item)-[:COMPONENT_OF]->{1,12}(f)
    WITH collect(DISTINCT f) + collect(DISTINCT x) AS all
    UNWIND all AS i
    RETURN DISTINCT i.sku AS id, i.name AS name, i.type AS type, coalesce(i.community_id, -1) AS community,
           coalesce(i.betweenness, 0.0) AS betweenness""", params)
skus = items.id.tolist()
sups = q("""
    UNWIND $skus AS sku
    MATCH (s:Supplier)-[r:SUPPLIES]->(:Item {sku: sku})
    WHERE s.tier IN $tiers AND ($country IS NULL OR s.country_iso2 = $country)
    RETURN DISTINCT s.id AS id, s.name AS name, s.tier AS tier, s.country_iso2 AS country,
           coalesce(s.community_id, -1) AS community, coalesce(s.betweenness, 0.0) AS betweenness""",
          {**params, "skus": skus})
edges = q("""
    UNWIND $skus AS sku
    MATCH (c:Item {sku: sku})-[:COMPONENT_OF]->(p:Item) WHERE p.sku IN $skus
    RETURN c.sku AS source, p.sku AS target, 'COMPONENT_OF' AS type
    UNION
    UNWIND $sids AS sid
    MATCH (s:Supplier {id: sid})-[:SUPPLIES]->(i:Item) WHERE i.sku IN $skus
    RETURN s.id AS source, i.sku AS target, 'SUPPLIES' AS type
    UNION
    UNWIND $sids AS sid
    MATCH (s:Supplier {id: sid})-[:BUYS_FROM]->(u:Supplier) WHERE u.id IN $sids
    RETURN DISTINCT s.id AS source, u.id AS target, 'BUYS_FROM' AS type""", {"skus": skus, "sids": sups.id.tolist()})

if items.empty:
    st.info("-")
    st.stop()
allb = list(items.betweenness) + list(sups.betweenness)
bmax = max(allb) or 1.0


def size(b: float) -> int:
    return int(8 + 30 * (b / bmax) ** 0.5)


def color(comm: int) -> str:
    return GRAY if comm < 0 else CATEGORICAL[comm % len(CATEGORICAL)]


nodes = [Node(id=r.id, caption=r.id, size=size(r.betweenness), color=color(r.community),
              properties={"name": r.name, "type": r.type, "community": int(r.community)}) for r in items.itertuples()]
nodes += [Node(id=r.id, caption=f"{r.id} ({r.country})", size=size(r.betweenness), color=color(r.community),
               properties={"name": r.name, "tier": int(r.tier), "country": r.country, "community": int(r.community)})
          for r in sups.itertuples()]
rels = [Relationship(source=r.source, target=r.target, caption=r.type) for r in edges.itertuples()]
vg = VisualizationGraph(nodes=nodes, relationships=rels)
components.html(vg.render(height="640px", theme="light").data, height=660)
st.caption(("Cor = comunidade (Leiden, GDS) · tamanho = betweenness (GDS) · " if st.session_state.get("lang", "pt") == "pt"
            else "Color = community (Leiden, GDS) · size = betweenness (GDS) · ")
           + f"{len(nodes)} nodes / {len(rels)} relationships")
