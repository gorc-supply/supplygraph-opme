from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from common import (
    CATEGORICAL,
    GRAY,
    category_name,
    country_name,
    header,
    integer,
    lang,
    q,
    t,
    tm,
    value_label,
)
from neo4j_viz import Node, Relationship, VisualizationGraph

header("explorer")

cats = q("MATCH (i:Item {type:'FINISHED'}) RETURN DISTINCT i.category AS c ORDER BY c").c.tolist()
countries = q("""MATCH (s:Supplier)-[:LOCATED_IN]->(c:Country)
                 RETURN DISTINCT c.iso2 AS iso2, c.name AS name ORDER BY iso2""")
cname = dict(zip(countries.iso2, countries.name, strict=True))
f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
cat = f1.selectbox(tm("category"), cats, index=cats.index("SPINE") if "SPINE" in cats else 0, format_func=category_name)
tiers = f2.multiselect(tm("tier"), [1, 2, 3], default=[1, 2, 3])
country = f3.selectbox(tm("country"), [None] + sorted(cname, key=lambda c: country_name(c, cname[c])),
                       format_func=lambda c: t("all") if c is None else f"{country_name(c, cname[c])} ({c})")
n_fin = f4.number_input(tm("max_finished"), 1, 30, 6)

params = {"cat": cat, "n": int(n_fin), "tiers": tiers, "country": country}
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


# Communities get colours in a fixed order (sorted ids), so two communities never share a colour.
communities = sorted({int(c) for c in list(items.community) + list(sups.community) if c >= 0})
palette = {c: CATEGORICAL[i % len(CATEGORICAL)] for i, c in enumerate(communities)}


def color(comm: int) -> str:
    return palette.get(int(comm), GRAY)


K = {"pt": ("nome", "tipo", "tier", "país", "comunidade"), "en": ("name", "type", "tier", "country", "community")}[lang()]
nodes = [Node(id=r.id, caption=r.id, size=size(r.betweenness), color=color(r.community),
              properties={K[0]: r.name, K[1]: value_label(r.type), K[4]: int(r.community)}) for r in items.itertuples()]
nodes += [Node(id=r.id, caption=f"{r.id} ({r.country})", size=size(r.betweenness), color=color(r.community),
               properties={K[0]: r.name, K[2]: int(r.tier), K[3]: country_name(r.country, cname.get(r.country)),
                           K[4]: int(r.community)})
          for r in sups.itertuples()]
rels = [Relationship(source=r.source, target=r.target, caption=r.type) for r in edges.itertuples()]
vg = VisualizationGraph(nodes=nodes, relationships=rels)
# The force layout keeps expanding after the first automatic fit, which left the graph cut off in a corner.
# Re-run the component's own "Zoom to fit" a few times while the layout settles (static script, no data).
REFIT = """<script>
[1500, 4000, 8000].forEach(function (ms) {
  setTimeout(function () {
    var b = document.querySelector('[aria-label="Zoom to fit"], [title="Zoom to fit"]');
    if (b) { b.click(); }
  }, ms);
});
</script>"""
components.html(vg.render(height="640px", theme="light").data + REFIT, height=660)

# Legend: one swatch per community present, named after the product categories it contains.
comm_cats = q("""MATCH (i:Item) WHERE i.community_id IS NOT NULL AND i.type <> 'RAW'
                   RETURN i.community_id AS c, collect(DISTINCT i.category) AS cats""").set_index("c")["cats"]
legend = []
for c in communities:
    cats_in = sorted({category_name(x) for x in comm_cats.get(c, [])})
    label = f"{t('community')} {c}" + (f": {', '.join(cats_in)}" if cats_in else "")
    legend.append(f'<span style="display:inline-flex;align-items:center;margin-right:16px">'
                  f'<span style="width:12px;height:12px;border-radius:3px;background:{palette[c]};margin-right:6px"></span>'
                  f"{label}</span>")
if legend:
    st.html('<div style="font-size:0.9rem;line-height:1.8">' + "".join(legend) + "</div>")
st.caption(tm("explorer_note").format(n=integer(len(nodes)), r=integer(len(rels))))
