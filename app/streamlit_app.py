"""SupplyGraph OPME - Streamlit entry point. Run: streamlit run app/streamlit_app.py"""

from __future__ import annotations

import streamlit as st
from common import t

st.set_page_config(page_title="SupplyGraph OPME", page_icon=":material/hub:", layout="wide")

with st.sidebar:
    st.markdown("### SupplyGraph OPME")
    choice = st.radio("Idioma / Language", ["Português", "English"], horizontal=True,
                      index=0 if st.session_state.get("lang", "pt") == "pt" else 1)
    st.session_state["lang"] = "pt" if choice == "Português" else "en"
    st.caption(t("tagline"))

pages = [
    st.Page("pages/overview.py", title=t("overview"), icon=":material/dashboard:", default=True),
    st.Page("pages/explorer.py", title=t("explorer"), icon=":material/hub:"),
    st.Page("pages/simulator.py", title=t("simulator"), icon=":material/warning:"),
    st.Page("pages/recall.py", title=t("recall"), icon=":material/search:"),
    st.Page("pages/ranking.py", title=t("ranking"), icon=":material/leaderboard:"),
    st.Page("pages/about.py", title=t("about"), icon=":material/info:"),
]
st.navigation(pages).run()
