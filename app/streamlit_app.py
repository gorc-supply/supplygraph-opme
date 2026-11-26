"""SupplyGraph OPME - Streamlit entry point. Run: streamlit run app/streamlit_app.py"""

from __future__ import annotations

import streamlit as st
from common import t, tm

st.set_page_config(page_title="SupplyGraph OPME", page_icon=":material/hub:", layout="wide")

# First visit: language from the URL (?lang=en / ?lang=pt), so links can be shared in either language.
if "lang" not in st.session_state:
    st.session_state["lang"] = "en" if st.query_params.get("lang") == "en" else "pt"

with st.sidebar:
    st.markdown("### SupplyGraph OPME")
    choice = st.radio("Idioma / Language", ["Português", "English"], horizontal=True,
                      index=0 if st.session_state["lang"] == "pt" else 1)
    st.session_state["lang"] = "pt" if choice == "Português" else "en"
    st.query_params["lang"] = st.session_state["lang"]
    st.caption(tm("tagline"))

pages = [
    st.Page("views/overview.py", title=t("overview"), icon=":material/dashboard:", default=True),
    st.Page("views/explorer.py", title=t("explorer"), icon=":material/hub:"),
    st.Page("views/simulator.py", title=t("simulator"), icon=":material/warning:"),
    st.Page("views/recall.py", title=t("recall"), icon=":material/search:"),
    st.Page("views/ranking.py", title=t("ranking"), icon=":material/leaderboard:"),
    st.Page("views/about.py", title=t("about"), icon=":material/info:"),
]
st.navigation(pages).run()
