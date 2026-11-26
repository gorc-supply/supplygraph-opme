from __future__ import annotations

import fmt
import streamlit as st
import yaml
from common import ROOT, country_name, header, integer, lang, pct, q, table, tm

from supplygraph.gds.scoring import COMPONENTS, score

header("ranking")

LABELS = {
    "pt": {"revenue_at_risk": "Receita em risco", "betweenness": "Betweenness (gargalo)", "pagerank": "PageRank",
           "geo_risk": "Risco geográfico", "financial_risk": "Risco financeiro", "single_source": "Fonte única"},
    "en": {"revenue_at_risk": "Revenue at risk", "betweenness": "Betweenness (chokepoint)", "pagerank": "PageRank",
           "geo_risk": "Geo risk", "financial_risk": "Financial risk", "single_source": "Single source"},
}[lang()]

defaults = yaml.safe_load((ROOT / "config" / "scoring.yaml").read_text(encoding="utf-8"))["weights"]
df = q("""MATCH (s:Supplier)-[:LOCATED_IN]->(c:Country)
          RETURN s.id AS supplier_id, s.name AS name, s.tier AS tier, s.country_iso2 AS iso2, c.name AS country_en,
                 coalesce(s.revenue_at_risk, 0.0) AS revenue_at_risk, coalesce(s.betweenness, 0.0) AS betweenness,
                 coalesce(s.pagerank, 0.0) AS pagerank, c.geo_risk_score AS geo_risk,
                 s.financial_risk AS financial_risk,
                 CASE WHEN coalesce(s.is_single_source, false) THEN 1.0 ELSE 0.0 END AS single_source""")

with st.sidebar:
    st.markdown(f"**{tm('weights')}**")
    if st.button(tm("reset")):
        for k in COMPONENTS:
            st.session_state[f"w_{k}"] = round(defaults[k] * 100)
    w = {k: st.slider(fmt.esc(LABELS[k]), 0, 100, int(st.session_state.get(f"w_{k}", round(defaults[k] * 100))), 5,
                      format="%d%%", key=f"w_{k}") / 100 for k in COMPONENTS}
total = sum(w.values()) or 1.0
w = {k: v / total for k, v in w.items()}  # normalise so the index stays on 0-100

df["index"] = score(df, w)
df["rank"] = df["index"].rank(ascending=False, method="min").astype(int)
df["rank_default"] = score(df, defaults).rank(ascending=False, method="min").astype(int)
df["rank_change"] = df["rank_default"] - df["rank"]
df["country"] = [country_name(i, n) for i, n in zip(df.iso2, df.country_en, strict=True)]
df = df.sort_values("index", ascending=False)
top10_t23 = int((df.head(10).tier >= 2).sum())

c = st.columns(2)
c[0].metric(tm("top1"), df.iloc[0].supplier_id, border=True)
c[1].metric(tm("t23_top10"), f"{integer(top10_t23)} / 10", border=True)
st.caption(fmt.esc(tm("weights_now").format(w=" · ".join(f"{LABELS[k]} {pct(100 * v)}" for k, v in w.items()))))

yes, no = ("Sim", "Não") if lang() == "pt" else ("Yes", "No")
view = df[["rank", "rank_change", "supplier_id", "name", "tier", "country", "index", "revenue_at_risk", "betweenness",
           "pagerank", "geo_risk", "financial_risk", "single_source"]].copy()
view["single_source"] = view["single_source"].map(lambda v: yes if v == 1.0 else no)
view["rank_change"] = view["rank_change"].map(lambda v: "0" if v == 0 else f"{'+' if v > 0 else '−'}{abs(int(v))}")
table(view, money_cols=["revenue_at_risk"], int_cols=["rank", "tier", "betweenness"],
      dec_cols={"index": 1, "pagerank": 2, "geo_risk": 2, "financial_risk": 2}, height=560,
      column_config={"rank_change": st.column_config.Column(tm("rank_change")),
                     "index": st.column_config.Column(tm("index"))})
st.caption(tm("index_note"))
