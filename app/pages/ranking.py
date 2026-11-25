from __future__ import annotations

import streamlit as st
import yaml
from common import ROOT, header, q, t

from supplygraph.gds.scoring import COMPONENTS, score

header("ranking")

defaults = yaml.safe_load((ROOT / "config" / "scoring.yaml").read_text(encoding="utf-8"))["weights"]
df = q("""MATCH (s:Supplier)-[:LOCATED_IN]->(c:Country)
          RETURN s.id AS supplier_id, s.name AS name, s.tier AS tier, s.country_iso2 AS country,
                 coalesce(s.revenue_at_risk, 0.0) AS revenue_at_risk, coalesce(s.betweenness, 0.0) AS betweenness,
                 coalesce(s.pagerank, 0.0) AS pagerank, c.geo_risk_score AS geo_risk,
                 s.financial_risk AS financial_risk,
                 CASE WHEN coalesce(s.is_single_source, false) THEN 1.0 ELSE 0.0 END AS single_source,
                 s.criticality_index AS stored_index""")

with st.sidebar:
    st.markdown(f"**{t('weights')}**")
    if st.button(t("reset")):
        for k in COMPONENTS:
            st.session_state[f"w_{k}"] = float(defaults[k])
    w = {k: st.slider(k, 0.0, 1.0, float(st.session_state.get(f"w_{k}", defaults[k])), 0.05, key=f"w_{k}")
         for k in COMPONENTS}
total = sum(w.values()) or 1.0
w = {k: v / total for k, v in w.items()}  # normalise so the index stays on 0-100

df["index"] = score(df, w)
df["rank"] = df["index"].rank(ascending=False, method="min").astype(int)
df["rank_default"] = score(df, defaults).rank(ascending=False, method="min").astype(int)
df["rank_change"] = df["rank_default"] - df["rank"]
df = df.sort_values("index", ascending=False)
top10_t23 = int((df.head(10).tier >= 2).sum())
c = st.columns(3)
c[0].metric("Top 1", df.iloc[0].supplier_id)
c[1].metric("Tier-2/3 no top 10 / in top 10", f"{top10_t23} / 10")
c[2].metric("Pesos / weights (normalised)", " · ".join(f"{v:.2f}" for v in w.values()))
st.dataframe(
    df[["rank", "rank_change", "supplier_id", "name", "tier", "country", "index", "revenue_at_risk", "betweenness",
        "pagerank", "geo_risk", "financial_risk", "single_source"]],
    hide_index=True, use_container_width=True, height=560,
    column_config={
        "index": st.column_config.ProgressColumn(t("index"), min_value=0, max_value=100, format="%.1f"),
        "revenue_at_risk": st.column_config.NumberColumn(format="R$ %.0f"),
        "rank_change": st.column_config.NumberColumn("Δ rank", format="%+d"),
    })
st.caption("Índice = 100 × Σ peso × componente normalizado (min-max). Fórmula e pesos em config/scoring.yaml. "
           "/ Index = 100 x sum(weight x min-max normalised component).")
