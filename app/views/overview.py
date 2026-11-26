from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from common import (
    BLUE,
    ORANGE,
    country_name,
    header,
    integer,
    money,
    pct,
    plotly_locale,
    q,
    t,
    table,
    tm,
)

from supplygraph.db import read_cypher

header("overview")

counts = q("""MATCH (n) WITH count(n) AS nodes
              CALL () { MATCH ()-[r]->() RETURN count(r) AS rels }
              RETURN nodes, rels""").iloc[0]
tiers = q("MATCH (s:Supplier) RETURN s.tier AS tier, count(*) AS n ORDER BY tier").set_index("tier")["n"]
rev = q("MATCH (f:Item {type:'FINISHED'}) RETURN sum(f.revenue_month) AS r").iloc[0]["r"]
single_rev = q("""MATCH (i:Item) WHERE COUNT { (:Supplier)-[:SUPPLIES]->(i) } = 1
                  MATCH (i)-[:COMPONENT_OF]->{1,12}(f:Item {type:'FINISHED'})
                  WITH DISTINCT f RETURN sum(f.revenue_month) AS r""").iloc[0]["r"]
false_dual = q(read_cypher("analytics/B1_hidden_convergence.cypher"), {"strict": True})
multi = q("""MATCH (i:Item {type:'COMPONENT', level: 1}) WHERE COUNT { (:Supplier)-[:SUPPLIES]->(i) } >= 2
             RETURN count(i) AS n""").iloc[0]["n"]
nfd = false_dual.item_sku.nunique() if not false_dual.empty else 0

# Row 1 - the network. Row 2 - the business. Short values so no card is truncated.
r1 = st.columns(5)
r1[0].metric(tm("nodes"), integer(counts.nodes), border=True)
r1[1].metric(tm("rels"), integer(counts.rels), border=True)
for i, tier in enumerate((1, 2, 3)):
    r1[2 + i].metric(tm(f"sup_t{tier}"), integer(tiers.get(tier, 0)), border=True)
r2 = st.columns(3)
r2[0].metric(tm("revenue_month"), money(rev), border=True)
r2[1].metric(tm("single_source_rev"), pct(100 * (single_rev or 0) / rev), help=tm("help_single"), border=True)
r2[2].metric(tm("false_dual"), f"{integer(nfd)} / {integer(multi)} ({pct(100 * nfd / max(multi, 1))})",
             help=tm("help_false_dual"), border=True)

st.subheader(tm("geo_title"))
st.caption(tm("geo_sub"))
geo = q(read_cypher("analytics/C2_geo_hard_dependency.cypher")).head(10)
geo["country"] = [country_name(i, n) for i, n in zip(geo.iso2, geo.country, strict=True)]
g = geo.iloc[::-1]
fig = go.Figure()
for colname, name, color in (("graph_pct", t("graph_view"), BLUE), ("erp_pct", t("erp_view"), ORANGE)):
    fig.add_bar(y=g.country, x=g[colname], orientation="h", name=name, marker_color=color,
                text=[pct(v, 1 if 0 < v < 1 else 0) for v in g[colname]], textposition="outside", cliponaxis=False,
                hovertemplate="%{y}: %{x:.1f}%<extra>" + name + "</extra>")
fig.update_layout(barmode="group", height=500, margin=dict(l=10, r=40, t=40, b=10), xaxis_title=t("geo_axis"),
                  showlegend=True, legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", traceorder="reversed"),
                  plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(range=[0, 105], ticksuffix="%"))
plotly_locale(fig)
st.plotly_chart(fig, width="stretch")
with st.expander(tm("data")):
    table(geo[["country", "erp_pct", "graph_pct"]], pct_cols={"erp_pct": 1, "graph_pct": 1})

st.subheader(tm("false_dual_title"))
if not false_dual.empty:
    view = (false_dual.groupby(["item_sku", "item_name", "category", "revenue_exposed"], as_index=False)
            .agg(direct_suppliers=("direct_suppliers", lambda s: ", ".join(s.iloc[0])),
                 hidden=("hidden_supplier", lambda s: ", ".join(s))))
    table(view.sort_values("revenue_exposed", ascending=False).head(25), money_cols=["revenue_exposed"])
