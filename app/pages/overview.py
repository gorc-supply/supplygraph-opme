from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from common import BLUE, ORANGE, header, money, q, t

from supplygraph.db import read_cypher

header("overview")

counts = q("""MATCH (n) WITH count(n) AS nodes
              CALL () { MATCH ()-[r]->() RETURN count(r) AS rels }
              RETURN nodes, rels""").iloc[0]
tiers = q("MATCH (s:Supplier) RETURN s.tier AS tier, count(*) AS n ORDER BY tier")
rev = q("MATCH (f:Item {type:'FINISHED'}) RETURN sum(f.revenue_month) AS r").iloc[0]["r"]
single_rev = q("""MATCH (i:Item) WHERE COUNT { (:Supplier)-[:SUPPLIES]->(i) } = 1
                  MATCH (i)-[:COMPONENT_OF]->{1,12}(f:Item {type:'FINISHED'})
                  WITH DISTINCT f RETURN sum(f.revenue_month) AS r""").iloc[0]["r"]
false_dual = q(read_cypher("analytics/B1_hidden_convergence.cypher"), {"strict": True})
multi = q("""MATCH (i:Item {type:'COMPONENT', level: 1}) WHERE COUNT { (:Supplier)-[:SUPPLIES]->(i) } >= 2
             RETURN count(i) AS n""").iloc[0]["n"]

c = st.columns(5)
c[0].metric(t("nodes"), f"{int(counts.nodes):,}")
c[1].metric(t("rels"), f"{int(counts.rels):,}")
c[2].metric(t("suppliers"), " / ".join(f"T{int(r.tier)}: {int(r.n)}" for r in tiers.itertuples()))
c[3].metric(t("single_source_rev"), f"{100 * (single_rev or 0) / rev:.0f}%")
nfd = false_dual.item_sku.nunique() if not false_dual.empty else 0
c[4].metric(t("false_dual"), f"{nfd} / {multi}", help="Itens com >=2 fornecedores tier-1 que convergem num único "
            "fornecedor tier-2/3 / items with >=2 tier-1 suppliers converging on one tier-2/3 supplier")
st.caption(f"{t('revenue_month')}: {money(rev)}")

st.subheader(t("geo_title"))
geo = q(read_cypher("analytics/C2_geo_hard_dependency.cypher")).head(10).iloc[::-1]
fig = go.Figure()
fig.add_bar(y=geo.country, x=geo.graph_pct, orientation="h", name=t("graph_view"), marker_color=BLUE,
            text=geo.graph_pct.map(lambda v: f"{v:.0f}%"), textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra>" + t("graph_view") + "</extra>")
fig.add_bar(y=geo.country, x=geo.erp_pct, orientation="h", name=t("erp_view"), marker_color=ORANGE,
            text=geo.erp_pct.map(lambda v: f"{v:.0f}%"), textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra>" + t("erp_view") + "</extra>")
fig.update_layout(barmode="group", height=460, margin=dict(l=10, r=30, t=10, b=10), xaxis_title="% R$",
                  legend=dict(orientation="h", y=-0.12), plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)
with st.expander("Dados / data"):
    st.dataframe(geo.iloc[::-1], hide_index=True, use_container_width=True)

st.subheader(t("false_dual"))
if not false_dual.empty:
    view = (false_dual.groupby(["item_sku", "item_name", "category", "revenue_exposed"], as_index=False)
            .agg(direct_suppliers=("direct_suppliers", "first"), hidden=("hidden_supplier", lambda s: ", ".join(s))))
    st.dataframe(view.sort_values("revenue_exposed", ascending=False).head(25), hide_index=True,
                 use_container_width=True,
                 column_config={"revenue_exposed": st.column_config.NumberColumn(format="R$ %.0f")})
