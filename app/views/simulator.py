from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from common import (
    BLUE,
    GRAY,
    ORANGE,
    country_name,
    header,
    integer,
    money,
    money_plain,
    num,
    plotly_locale,
    q,
    safe_driver,
    t,
    table,
    tm,
    value_label,
)

from supplygraph.analytics import queries as A

header("simulator")

c1, c2, c3 = st.columns([1, 2, 2])
kind = c1.radio(tm("kind"), ["supplier", "country", "port"], format_func=value_label)
if kind == "supplier":
    opts = q("""MATCH (s:Supplier) RETURN s.id AS id, s.tier AS tier, s.country_iso2 AS c,
                coalesce(s.risk_ttr_days, 60) AS ttr, coalesce(s.revenue_at_risk, 0) AS r ORDER BY r DESC""").set_index("id")
    key = c2.selectbox(tm("supplier"), opts.index,
                       format_func=lambda i: f"{i} (T{opts.loc[i, 'tier']}, {country_name(opts.loc[i, 'c'])})")
elif kind == "country":
    opts = q("""MATCH (s:Supplier)-[:LOCATED_IN]->(c:Country)
                RETURN DISTINCT c.iso2 AS iso2, c.name AS name""").set_index("iso2")
    key = c2.selectbox(tm("country"), sorted(opts.index, key=lambda i: country_name(i, opts.loc[i, "name"])),
                       format_func=lambda i: f"{country_name(i, opts.loc[i, 'name'])} ({i})")
else:
    opts = q("""MATCH (p:Port) RETURN p.code AS code, p.name AS name, p.country_iso2 AS c
                ORDER BY p.country_iso2 = 'BR' DESC, code""").set_index("code")
    key = c2.selectbox(tm("port"), opts.index,
                       format_func=lambda c: f"{c} - {opts.loc[c, 'name']} ({country_name(opts.loc[c, 'c'])})")
# default TTR: the supplier's tier time-to-recover (60/120/180 d, config/scoring.yaml); 60 d for countries / ports
default_ttr = int(opts.loc[key, "ttr"]) if kind == "supplier" else 60
ttr = c3.slider(tm("ttr"), 7, 180, default_ttr, step=1, key=f"ttr_{kind}_{key}", help=tm("ttr_help"))


@st.cache_data(ttl=600, show_spinner=True)
def simulate(kind: str, key: str, ttr: int):
    res = A.disruption(safe_driver(), kind, key, ttr)
    subs = A.substitution(safe_driver(), res)
    return res.summary, res.impact, res.timeline, subs


summary, impact, timeline, subs = simulate(kind, key, ttr)
k = st.columns(4)
k[0].metric(tm("rev_risk"), money(summary["revenue_at_risk"]), border=True)
k[1].metric(tm("hosp"), integer(summary["hospitals_affected"]), border=True)
k[2].metric(tm("skus_out"), f"{integer(summary['finished_skus_stockout'])} / {integer(summary['finished_skus_exposed'])}",
            border=True)
k[3].metric(tm("first_day"), "–" if summary["first_stockout_day"] is None else num(summary["first_stockout_day"]),
            border=True)

if impact.empty or summary["revenue_at_risk"] == 0:
    st.success(tm("no_impact"))
if not impact.empty:
    left, right = st.columns(2)
    out = impact[impact.tts_days < ttr]
    ok = impact[impact.tts_days >= ttr]
    fig = go.Figure()
    fig.add_scatter(x=ok.tts_days, y=ok.daily_demand * 30, mode="markers", name=t("survives"),
                    marker=dict(color=GRAY, size=7), text=ok.sku + " @ " + ok.dc,
                    hovertemplate="%{text}<br>TTS %{x:.0f}<extra></extra>")
    fig.add_scatter(x=out.tts_days, y=out.daily_demand * 30, mode="markers", name=t("stockout"),
                    marker=dict(color=ORANGE, size=8), text=out.sku + " @ " + out.dc,
                    customdata=[money_plain(v) for v in out.revenue_at_risk],
                    hovertemplate="%{text}<br>TTS %{x:.0f}<br>%{customdata}<extra></extra>")
    fig.add_vline(x=ttr, line_dash="dash", annotation_text=f"TTR = {integer(ttr)}")
    fig.update_layout(title=t("tts_chart"), height=440, xaxis_title=t("tts_axis"), yaxis_title=t("demand_axis"),
                      margin=dict(l=10, r=10, t=50, b=10), showlegend=True,
                      legend=dict(orientation="h", x=0, y=-0.22))
    plotly_locale(fig)
    left.plotly_chart(fig, width="stretch")
    fig2 = go.Figure(go.Scatter(x=timeline.day, y=timeline.cumulative_revenue_lost, mode="lines",
                                line=dict(color=BLUE, width=2), fill="tozeroy", name=t("lost_axis"),
                                customdata=[money_plain(v) for v in timeline.cumulative_revenue_lost],
                                hovertemplate="%{x}: %{customdata}<extra></extra>"))
    fig2.update_layout(title=t("timeline"), height=440, xaxis_title=t("days_axis"), yaxis_title=t("lost_axis"),
                       margin=dict(l=10, r=10, t=50, b=10), yaxis=dict(tickformat=",.0f", tickprefix="R$ "))
    plotly_locale(fig2)
    right.plotly_chart(fig2, width="stretch")
    hosp = sorted({h for hs in out.hospitals for h in hs})
    if hosp:
        st.markdown(f"**{tm('map_hosp')}**")
        pts = q("UNWIND $ids AS id MATCH (h:Hospital {id: id}) RETURN h.lat AS lat, h.lon AS lon", {"ids": hosp})
        st.map(pts, size=2000, color="#f47230")
    table(out.drop(columns=["hospitals"]).head(200).assign(loss_frac=lambda d: d.loss_frac * 100),
          money_cols=["revenue_at_risk"], pct_cols={"loss_frac": 0},
          dec_cols={"cover_days": 1, "in_transit_days": 1, "tts_days": 1, "stockout_days": 1, "daily_demand": 2,
                    "units_short": 1})
    if not subs.empty:
        st.subheader(tm("subs"))
        summary_subs = subs.groupby("mitigation", as_index=False).agg(
            rows=("sku", "count"), revenue_at_risk=("revenue_at_risk", "sum"),
            revenue_mitigated=("revenue_mitigated", "sum"))
        table(summary_subs, money_cols=["revenue_at_risk", "revenue_mitigated"], int_cols=["rows"],
              translate_cols=["mitigation"])
