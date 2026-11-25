from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from common import BLUE, GRAY, ORANGE, header, money, q, safe_driver, t

from supplygraph.analytics import queries as A

header("simulator")

c1, c2, c3 = st.columns([1, 2, 2])
kind = c1.radio(t("kind"), ["supplier", "country", "port"],
                format_func=lambda k: {"supplier": t("supplier"), "country": t("country"), "port": t("port")}[k])
if kind == "supplier":
    opts = q("""MATCH (s:Supplier) RETURN s.id AS id, s.tier AS tier, s.country_iso2 AS c,
                coalesce(s.revenue_at_risk, 0) AS r ORDER BY r DESC""")
    key = c2.selectbox(t("supplier"), opts.id, format_func=lambda i: f"{i} (T{opts.set_index('id').loc[i, 'tier']}, "
                                                                     f"{opts.set_index('id').loc[i, 'c']})")
elif kind == "country":
    opts = q("MATCH (s:Supplier) RETURN DISTINCT s.country_iso2 AS c ORDER BY c")
    key = c2.selectbox(t("country"), opts.c)
else:
    opts = q("MATCH (p:Port) RETURN p.code AS code, p.name AS name ORDER BY p.country_iso2 = 'BR' DESC, code")
    key = c2.selectbox(t("port"), opts.code, format_func=lambda c: f"{c} - {opts.set_index('code').loc[c, 'name']}")
ttr = c3.slider(t("ttr"), 7, 180, 60, step=1)


@st.cache_data(ttl=600, show_spinner=True)
def simulate(kind: str, key: str, ttr: int):
    res = A.disruption(safe_driver(), kind, key, ttr)
    subs = A.substitution(safe_driver(), res)
    return res.summary, res.impact, res.timeline, subs


summary, impact, timeline, subs = simulate(kind, key, ttr)
k = st.columns(4)
k[0].metric(t("rev_risk"), money(summary["revenue_at_risk"]))
k[1].metric(t("hosp"), f"{summary['hospitals_affected']:,}")
k[2].metric(t("skus_out"), f"{summary['finished_skus_stockout']} / {summary['finished_skus_exposed']}")
k[3].metric(t("first_day"), "-" if summary["first_stockout_day"] is None else f"{summary['first_stockout_day']:.0f}")

if impact.empty or summary["revenue_at_risk"] == 0:
    st.success(t("no_impact"))
if not impact.empty:
    left, right = st.columns(2)
    out = impact[impact.tts_days < ttr]
    ok = impact[impact.tts_days >= ttr]
    fig = go.Figure()
    fig.add_scatter(x=ok.tts_days, y=ok.daily_demand * 30, mode="markers", name="TTS >= TTR",
                    marker=dict(color=GRAY, size=7), text=ok.sku + " @ " + ok.dc,
                    hovertemplate="%{text}<br>TTS %{x:.0f} d<extra></extra>")
    fig.add_scatter(x=out.tts_days, y=out.daily_demand * 30, mode="markers", name="TTS < TTR",
                    marker=dict(color=ORANGE, size=8), text=out.sku + " @ " + out.dc,
                    customdata=out.revenue_at_risk,
                    hovertemplate="%{text}<br>TTS %{x:.0f} d<br>R$ %{customdata:,.0f}<extra></extra>")
    fig.add_vline(x=ttr, line_dash="dash", annotation_text=f"TTR = {ttr} d")
    fig.update_layout(title=t("tts_chart"), height=420, xaxis_title="TTS (dias/days)", yaxis_title="units / month",
                      margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.2))
    left.plotly_chart(fig, width="stretch")
    fig2 = go.Figure(go.Scatter(x=timeline.day, y=timeline.cumulative_revenue_lost, mode="lines",
                                line=dict(color=BLUE, width=2), fill="tozeroy",
                                hovertemplate="dia/day %{x}: R$ %{y:,.0f}<extra></extra>"))
    fig2.update_layout(title=t("timeline"), height=420, xaxis_title="dias / days", yaxis_title="R$",
                       margin=dict(l=10, r=10, t=50, b=10))
    right.plotly_chart(fig2, width="stretch")
    hosp = sorted({h for hs in out.hospitals for h in hs})
    if hosp:
        pts = q("UNWIND $ids AS id MATCH (h:Hospital {id: id}) RETURN h.lat AS lat, h.lon AS lon", {"ids": hosp})
        st.map(pts, size=2000, color="#f47230")
    st.dataframe(out.drop(columns=["hospitals"]).head(200), hide_index=True, width="stretch",
                 column_config={"revenue_at_risk": st.column_config.NumberColumn(format="R$ %.0f")})
    if not subs.empty:
        st.subheader(t("subs"))
        st.dataframe(subs.groupby("mitigation", as_index=False).agg(rows=("sku", "count"),
                                                                   revenue_at_risk=("revenue_at_risk", "sum"),
                                                                   revenue_mitigated=("revenue_mitigated", "sum")),
                     hide_index=True, column_config={c: st.column_config.NumberColumn(format="R$ %.0f")
                                                     for c in ("revenue_at_risk", "revenue_mitigated")})
