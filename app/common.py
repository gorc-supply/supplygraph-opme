"""Shared helpers for the Streamlit app: connection, cached parameterised queries, i18n, palette."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supplygraph.config import Neo4jSettings  # noqa: E402
from supplygraph.db import get_driver, run_df  # noqa: E402

REPO_URL = "https://github.com/gorc-supply/supplygraph-opme"
BLUE, ORANGE, GRAY = "#257de0", "#f47230", "#9c9c9c"
CATEGORICAL = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17", "#6a4ce2", "#ec4647"]

T = {
    "pt": {
        "app_title": "SupplyGraph OPME",
        "tagline": "Gêmeo digital em grafo de uma cadeia multi-tier de implantes (dados sintéticos)",
        "lang": "Idioma",
        "overview": "Visão geral", "explorer": "Explorador de rede", "simulator": "Simulador de disrupção",
        "recall": "Recall de lote", "ranking": "Ranking de criticidade", "about": "Sobre / metodologia",
        "conn_error": "Não consegui conectar ao banco. Se esta é a demo pública, a instância AuraDB Free pode estar "
                      "pausada por inatividade - tente novamente em alguns minutos.",
        "synthetic_note": "Rede sintética (semente fixa) calibrada com dados abertos reais. Valores em R$ são "
                          "sintéticos e não representam o mercado.",
        "nodes": "Nós", "rels": "Relacionamentos", "suppliers": "Fornecedores", "revenue_month": "Receita/mês (R$)",
        "single_source_rev": "Receita com item de fonte única", "false_dual": "Itens 'falso dual-source'",
        "erp_view": "Visão ERP (tier-1 + planta)", "graph_view": "Visão grafo (todos os tiers)",
        "geo_title": "Receita que depende 100% de um país",
        "tier": "Tier", "country": "País", "category": "Categoria de produto", "max_finished": "Máx. de implantes",
        "kind": "Tipo de disrupção", "supplier": "Fornecedor", "port": "Porto / aeroporto", "ttr": "Dias de interrupção (TTR)",
        "run": "Simular", "rev_risk": "Receita em risco", "hosp": "Hospitais afetados", "first_day": "1ª ruptura (dia)",
        "skus_out": "SKUs com ruptura", "timeline": "Linha do tempo do impacto", "tts_chart": "TTS × TTR por SKU × CD",
        "subs": "Substituição (9G)", "lot": "Lote", "trace": "Rastrear", "forward": "Para frente (onde foi parar)",
        "backward": "Para trás (de onde veio)", "units_stock": "Unidades em estoque a bloquear",
        "units_deliv": "Unidades entregues", "weights": "Pesos do índice", "reset": "Restaurar pesos padrão",
        "index": "Índice de criticidade", "no_impact": "Nenhuma ruptura neste cenário (TTS ≥ TTR em todos os CDs).",
    },
    "en": {
        "app_title": "SupplyGraph OPME",
        "tagline": "Graph digital twin of a multi-tier implant supply chain (synthetic data)",
        "lang": "Language",
        "overview": "Overview", "explorer": "Network explorer", "simulator": "Disruption simulator",
        "recall": "Lot recall", "ranking": "Criticality ranking", "about": "About / methodology",
        "conn_error": "Could not connect to the database. If this is the public demo, the AuraDB Free instance may be "
                      "paused for inactivity - please try again in a few minutes.",
        "synthetic_note": "Synthetic network (fixed seed) calibrated with real open data. R$ values are synthetic and "
                          "do not describe the market.",
        "nodes": "Nodes", "rels": "Relationships", "suppliers": "Suppliers", "revenue_month": "Revenue/month (R$)",
        "single_source_rev": "Revenue with a single-source item", "false_dual": "'False dual-source' items",
        "erp_view": "ERP view (tier-1 + plant)", "graph_view": "Graph view (all tiers)",
        "geo_title": "Revenue that depends 100% on one country",
        "tier": "Tier", "country": "Country", "category": "Product category", "max_finished": "Max implants",
        "kind": "Disruption type", "supplier": "Supplier", "port": "Port / airport", "ttr": "Outage days (TTR)",
        "run": "Simulate", "rev_risk": "Revenue at risk", "hosp": "Hospitals affected", "first_day": "First stock-out (day)",
        "skus_out": "SKUs stocking out", "timeline": "Impact timeline", "tts_chart": "TTS x TTR per SKU x DC",
        "subs": "Substitution (9G)", "lot": "Lot", "trace": "Trace", "forward": "Forward (where it went)",
        "backward": "Backward (where it came from)", "units_stock": "Units in stock to quarantine",
        "units_deliv": "Units delivered", "weights": "Index weights", "reset": "Reset default weights",
        "index": "Criticality index", "no_impact": "No stock-out in this scenario (TTS >= TTR at every DC).",
    },
}


def lang() -> str:
    return st.session_state.get("lang", "pt")


def t(key: str) -> str:
    return T[lang()].get(key, key)


def _settings() -> Neo4jSettings:
    try:
        sec = st.secrets["neo4j"]
        return Neo4jSettings(uri=sec["uri"], user=sec.get("user", "neo4j"), password=sec["password"],
                             database=sec.get("database", "neo4j"))
    except Exception:  # noqa: BLE001 - no secrets.toml locally -> fall back to .env
        from supplygraph.config import neo4j_settings

        return neo4j_settings()


@st.cache_resource(show_spinner=False)
def driver():
    s = _settings()
    os.environ.setdefault("NEO4J_DATABASE", s.database)
    d = get_driver(s)
    d.verify_connectivity()
    return d


def safe_driver():
    try:
        return driver()
    except Exception:  # noqa: BLE001
        st.error(t("conn_error"))
        st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def q(query: str, params: dict | None = None) -> pd.DataFrame:
    """Cached, parameterised read query with a 30 s timeout. Never format values into `query`."""
    return run_df(safe_driver(), query, params or {}, timeout=30)


def money(v: float) -> str:
    if v is None or pd.isna(v):
        return "-"
    if abs(v) >= 1e6:
        return f"R$ {v / 1e6:,.1f} M"
    if abs(v) >= 1e3:
        return f"R$ {v / 1e3:,.0f} k"
    return f"R$ {v:,.0f}"


def header(key: str) -> None:
    st.title(t(key))
    st.caption(t("synthetic_note"))
