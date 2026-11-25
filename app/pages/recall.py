from __future__ import annotations

import time

import pandas as pd
import streamlit as st
from common import header, q, safe_driver, t

from supplygraph.analytics import queries as A

header("recall")

default = q("""MATCH (src:Lot)-[:OF_ITEM]->(:Item {sku: 'RM-TI64'})
               WITH src, COUNT { (l:Lot)-[:DERIVED_FROM]->(src) } AS n WHERE n > 0
               RETURN src.lot_id AS id ORDER BY n DESC, id LIMIT 1""")
c1, c2 = st.columns([3, 1])
lot = c1.text_input(t("lot"), value=default.id.iloc[0] if not default.empty else "",
                    help="Ex.: RM-TI64-L0001 (titânio / titanium), CP-L1-0015-L0010, FG-HIP-0001-L0005")
c2.write("")
c2.button(t("trace"), type="primary")

if lot:
    exists = q("MATCH (l:Lot {lot_id: $id})-[:OF_ITEM]->(i:Item) RETURN i.sku AS sku, i.name AS name, l.status AS s",
               {"id": lot})
    if exists.empty:
        st.warning("Lote não encontrado / lot not found")
        st.stop()
    st.caption(f"{exists.sku.iloc[0]} - {exists.name.iloc[0]} - status: {exists.s.iloc[0]}")
    d = safe_driver()
    t0 = time.perf_counter()
    fwd = A.recall_forward(d, lot)
    t_fwd = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    back = A.recall_backward(d, lot)
    t_back = (time.perf_counter() - t0) * 1000
    s = A.recall_summary(fwd)
    k = st.columns(5)
    k[0].metric("Lotes derivados / derived lots", s["derived_lots"])
    k[1].metric("Lotes de implante / implant lots", s["finished_lots"])
    k[2].metric(t("hosp"), f"{s['hospitals']} ({s['ufs']} UF)")
    k[3].metric(t("units_stock"), s["units_in_stock_to_quarantine"])
    k[4].metric("Tempo / time", f"{t_fwd:.0f} + {t_back:.0f} ms")

    st.subheader(t("forward"))
    if not fwd.empty:
        deliveries = pd.DataFrame([{"lot_id": r.lot_id, **x} for r in fwd.itertuples() for x in r.deliveries])
        if not deliveries.empty:
            pts = q("UNWIND $ids AS id MATCH (h:Hospital {id: id}) RETURN h.lat AS lat, h.lon AS lon",
                    {"ids": sorted(deliveries.hospital_id.unique().tolist())})
            st.map(pts, size=2500, color="#ec4647")
        st.dataframe(fwd.drop(columns=["deliveries"]), hide_index=True, use_container_width=True)
        if not deliveries.empty:
            with st.expander("Entregas / deliveries"):
                st.dataframe(deliveries, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum lote derivado / no derived lots (lote de implante acabado?)")
    st.subheader(t("backward"))
    st.dataframe(back, hide_index=True, use_container_width=True)
