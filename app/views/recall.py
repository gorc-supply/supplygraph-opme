from __future__ import annotations

import time

import pandas as pd
import streamlit as st
from common import esc, header, integer, num, q, safe_driver, table, tm, value_label

from supplygraph.analytics import queries as A

header("recall")

default = q("""MATCH (src:Lot)-[:OF_ITEM]->(:Item {sku: 'RM-TI64'})
               WITH src, COUNT { (l:Lot)-[:DERIVED_FROM]->(src) } AS n WHERE n > 0
               RETURN src.lot_id AS id ORDER BY n DESC, id LIMIT 1""")
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
lot = c1.text_input(tm("lot"), value=default.id.iloc[0] if not default.empty else "", help=tm("lot_help"))
c2.button(tm("trace"), type="primary")

if lot:
    exists = q("MATCH (l:Lot {lot_id: $id})-[:OF_ITEM]->(i:Item) RETURN i.sku AS sku, i.name AS name, l.status AS s",
               {"id": lot})
    if exists.empty:
        st.warning(tm("lot_not_found"))
        st.stop()
    st.caption(esc(f"{exists.sku.iloc[0]} · {exists.name.iloc[0]} · {value_label(exists.s.iloc[0])}"))
    d = safe_driver()
    t0 = time.perf_counter()
    fwd = A.recall_forward(d, lot)
    t_fwd = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    back = A.recall_backward(d, lot)
    t_back = (time.perf_counter() - t0) * 1000
    s = A.recall_summary(fwd)
    k = st.columns(5)
    k[0].metric(tm("derived"), integer(s["derived_lots"]), border=True)
    k[1].metric(tm("implant_lots"), integer(s["finished_lots"]), border=True)
    k[2].metric(tm("hosp_uf"), f"{integer(s['hospitals'])} ({integer(s['ufs'])})", border=True)
    k[3].metric(tm("units_stock"), integer(s["units_in_stock_to_quarantine"]), border=True)
    k[4].metric(tm("query_time"), f"{num(t_fwd + t_back)} ms", help=tm("query_time_help").format(
        f=num(t_fwd), b=num(t_back)), border=True)

    st.subheader(tm("forward"))
    if not fwd.empty:
        deliveries = pd.DataFrame([{"lot_id": r.lot_id, **x} for r in fwd.itertuples() for x in r.deliveries])
        if not deliveries.empty:
            pts = q("UNWIND $ids AS id MATCH (h:Hospital {id: id}) RETURN h.lat AS lat, h.lon AS lon",
                    {"ids": sorted(deliveries.hospital_id.unique().tolist())})
            st.map(pts, size=2500, color="#ec4647")
        fwd_view = fwd.drop(columns=["deliveries"]).assign(in_stock=lambda d: pd.to_numeric(d.in_stock, errors="coerce"))
        table(fwd_view, int_cols=["qty", "delivered", "in_stock", "level"],
              translate_cols=["type", "status"])
        if not deliveries.empty:
            with st.expander(tm("deliveries")):
                table(deliveries, int_cols=["qty"])
    else:
        st.info(tm("no_derived"))
    st.subheader(tm("backward"))
    if back.empty:
        st.info(tm("no_upstream"))
    else:
        table(back, int_cols=["depth"], translate_cols=["type", "status"])
