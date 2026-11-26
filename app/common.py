"""Shared helpers for the Streamlit app: connection, cached parameterised queries, i18n, formatting, palette."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import fmt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from supplygraph.config import Neo4jSettings  # noqa: E402
from supplygraph.db import get_driver, run_df  # noqa: E402

REPO_URL = "https://github.com/gorc-supply/supplygraph-opme"
DEMO_URL = "https://supplygraph-opme.streamlit.app"
BLUE, ORANGE, GRAY = "#257de0", "#f47230", "#9c9c9c"
CATEGORICAL = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17", "#6a4ce2", "#ec4647"]

T = {
    "pt": {
        "tagline": "Gêmeo digital em grafo de uma cadeia multi-tier de implantes (dados sintéticos)",
        "overview": "Visão geral", "explorer": "Explorador de rede", "simulator": "Simulador de disrupção",
        "recall": "Recall de lote", "ranking": "Ranking de criticidade", "about": "Sobre / metodologia",
        "conn_error": "Não consegui conectar ao banco. Se esta é a demo pública, a instância AuraDB Free pode estar "
                      "pausada por inatividade. Tente novamente em alguns minutos.",
        "synthetic_note": "Rede sintética (semente fixa) calibrada com dados abertos reais. Valores em R$ são "
                          "sintéticos e não representam o mercado.",
        # overview
        "nodes": "Nós", "rels": "Relacionamentos", "sup_t1": "Fornecedores tier 1", "sup_t2": "Fornecedores tier 2",
        "sup_t3": "Fornecedores tier 3", "revenue_month": "Receita mensal",
        "single_source_rev": "Receita com item de fonte única", "false_dual": "Itens falso dual-source",
        "help_single": "Parte da receita mensal vinda de implantes cuja lista de materiais (em qualquer nível) tem "
                       "**pelo menos um item com um único fornecedor**.\n\n"
                       "Fórmula: soma da receita mensal dos implantes *f* que contêm, em qualquer nível da BOM, um item "
                       "*x* com exatamente 1 relação `SUPPLIES` ÷ soma da receita mensal de todos os implantes.",
        "help_false_dual": "Componentes de nível 1 que **parecem ter 2 ou mais fornecedores diretos** (tier 1), mas em "
                           "que **todos** compram 100% de uma peça do **mesmo fornecedor a montante** (tier 2 ou 3).\n\n"
                           "Regra: seguir as compras `BUYS_FROM` de cada fornecedor direto respeitando a BOM (cada salto "
                           "compra o item usado no salto anterior), com participação ≥ 99,9% em todos os saltos.\n\n"
                           "Valor = nº desses componentes / nº de componentes de nível 1 com 2 ou mais fornecedores.",
        "geo_title": "Receita que depende 100% de um país",
        "geo_sub": "Cada barra mostra a parte da receita mensal que **não existe sem aquele país**: implantes com pelo "
                   "menos um insumo comprado 100% de fornecedores (ou plantas) dele. As barras não somam 100%: o mesmo "
                   "implante conta em todos os países dos quais depende, e a soma passa de 100%.",
        "erp_view": "Visão ERP: só tier 1 (e planta)", "graph_view": "Visão grafo: rede completa",
        "geo_axis": "% da receita mensal", "data": "Dados",
        "false_dual_title": "Componentes falso dual-source",
        # explorer
        "tier": "Tier", "country": "País", "all": "(todos)", "category": "Categoria de produto",
        "max_finished": "Máx. de implantes",
        "explorer_note": "Cor = comunidade (Leiden, GDS) · tamanho = betweenness (GDS) · {n} nós / {r} relacionamentos",
        # simulator
        "kind": "Tipo de disrupção", "supplier": "Fornecedor", "port": "Porto / aeroporto",
        "ttr": "Dias de interrupção (TTR)", "rev_risk": "Receita em risco", "hosp": "Hospitais afetados",
        "first_day": "1ª ruptura (dia)", "skus_out": "Implantes em ruptura", "timeline": "Linha do tempo do impacto",
        "tts_chart": "TTS × TTR por implante × CD", "tts_axis": "Time-to-Survive (dias)",
        "demand_axis": "Demanda mensal no CD (unidades)", "days_axis": "Dias desde a interrupção",
        "lost_axis": "Receita perdida acumulada (R$)", "survives": "Sobrevive (TTS ≥ TTR)",
        "stockout": "Ruptura (TTS < TTR)", "subs": "Substituição (9G)", "no_impact": "Nenhuma ruptura neste cenário "
                                                                                      "(TTS ≥ TTR em todos os CDs).",
        "map_hosp": "Hospitais afetados (mapa)",
        "ttr_help": "Tempo até o nó interrompido voltar a fornecer. Padrão para fornecedores: o TTR do tier (60/120/180 dias para tier 1/2/3, premissa sintética em config/scoring.yaml); 60 dias para países e portos.",
        "no_upstream": "Lote de matéria-prima: não há lotes a montante.",
        "community": "Comunidade",
        # recall
        "lot": "Lote", "lot_help": "Ex.: RM-TI64-L0043 (titânio), CP-L1-0015-L0010 (componente), FG-HIP-0001-L0005 "
                                  "(implante)", "trace": "Rastrear", "lot_not_found": "Lote não encontrado.",
        "derived": "Lotes derivados", "implant_lots": "Lotes de implante", "hosp_uf": "Hospitais (UFs)",
        "units_stock": "Unidades a bloquear", "query_time": "Tempo da consulta",
        "query_time_help": "Para frente: {f} ms · para trás: {b} ms (medido nesta execução, inclui a ida e volta ao banco; a primeira consulta após o banco ficar ocioso é mais lenta).",
        "forward": "Para frente (onde foi parar)", "backward": "Para trás (de onde veio)",
        "deliveries": "Entregas", "no_derived": "Nenhum lote derivado (é um lote de implante acabado?)",
        # ranking
        "weights": "Pesos do índice", "reset": "Restaurar pesos padrão", "index": "Índice de criticidade",
        "top1": "1º do ranking", "t23_top10": "Tier 2/3 no top 10", "weights_now": "Pesos normalizados: {w}",
        "index_note": "Índice = 100 × Σ (peso × componente normalizado min-max). Pesos padrão em config/scoring.yaml.",
        "rank_change": "Δ posição",
    },
    "en": {
        "tagline": "Graph digital twin of a multi-tier implant supply chain (synthetic data)",
        "overview": "Overview", "explorer": "Network explorer", "simulator": "Disruption simulator",
        "recall": "Lot recall", "ranking": "Criticality ranking", "about": "About / methodology",
        "conn_error": "Could not connect to the database. If this is the public demo, the AuraDB Free instance may be "
                      "paused for inactivity. Please try again in a few minutes.",
        "synthetic_note": "Synthetic network (fixed seed) calibrated with real open data. R$ values are synthetic and "
                          "do not describe the market.",
        "nodes": "Nodes", "rels": "Relationships", "sup_t1": "Tier-1 suppliers", "sup_t2": "Tier-2 suppliers",
        "sup_t3": "Tier-3 suppliers", "revenue_month": "Monthly revenue",
        "single_source_rev": "Revenue with a single-source item", "false_dual": "False dual-source items",
        "help_single": "Share of monthly revenue coming from implants whose bill of materials (at any level) contains "
                       "**at least one item with a single supplier**.\n\n"
                       "Formula: sum of the monthly revenue of implants *f* that contain, at any BOM level, an item *x* "
                       "with exactly 1 `SUPPLIES` relationship ÷ sum of the monthly revenue of all implants.",
        "help_false_dual": "Level-1 components that **look like they have 2 or more direct (tier-1) suppliers**, but "
                           "where **all** of them buy a part 100% from the **same upstream supplier** (tier 2 or 3).\n\n"
                           "Rule: follow each direct supplier's `BUYS_FROM` purchases along the BOM (each hop buys the "
                           "item used in the previous hop), with a share of at least 99.9% on every hop.\n\n"
                           "Value = number of such components / number of level-1 components with 2 or more suppliers.",
        "geo_title": "Revenue that depends 100% on one country",
        "geo_sub": "Each bar is the share of monthly revenue that **cannot be produced without that country**: implants "
                   "with at least one input bought 100% from its suppliers (or plants). Bars do not add up to 100%: the "
                   "same implant counts in every country it depends on, so the total exceeds 100%.",
        "erp_view": "ERP view: tier 1 only (and plant)", "graph_view": "Graph view: full network",
        "geo_axis": "% of monthly revenue", "data": "Data",
        "false_dual_title": "False dual-source components",
        "tier": "Tier", "country": "Country", "all": "(all)", "category": "Product category",
        "max_finished": "Max implants",
        "explorer_note": "Color = community (Leiden, GDS) · size = betweenness (GDS) · {n} nodes / {r} relationships",
        "kind": "Disruption type", "supplier": "Supplier", "port": "Port / airport", "ttr": "Outage days (TTR)",
        "rev_risk": "Revenue at risk", "hosp": "Hospitals affected", "first_day": "First stock-out (day)",
        "skus_out": "Implants stocking out", "timeline": "Impact timeline", "tts_chart": "TTS x TTR per implant x DC",
        "tts_axis": "Time-to-Survive (days)", "demand_axis": "Monthly demand at the DC (units)",
        "days_axis": "Days since the disruption", "lost_axis": "Cumulative revenue lost (R$)",
        "survives": "Survives (TTS ≥ TTR)", "stockout": "Stock-out (TTS < TTR)", "subs": "Substitution (9G)",
        "no_impact": "No stock-out in this scenario (TTS ≥ TTR at every DC).", "map_hosp": "Affected hospitals (map)",
        "ttr_help": "Time until the disrupted node supplies again. Default for suppliers: the tier TTR (60/120/180 days for tier 1/2/3, synthetic assumption in config/scoring.yaml); 60 days for countries and ports.",
        "no_upstream": "Raw-material lot: there are no upstream lots.", "community": "Community",
        "lot": "Lot", "lot_help": "E.g. RM-TI64-L0043 (titanium), CP-L1-0015-L0010 (component), FG-HIP-0001-L0005 "
                                  "(implant)", "trace": "Trace", "lot_not_found": "Lot not found.",
        "derived": "Derived lots", "implant_lots": "Implant lots", "hosp_uf": "Hospitals (states)",
        "units_stock": "Units to quarantine", "query_time": "Query time",
        "query_time_help": "Forward: {f} ms · backward: {b} ms (measured on this run, including the round trip to the database; the first query after the database was idle is slower).",
        "forward": "Forward (where it went)", "backward": "Backward (where it came from)",
        "deliveries": "Deliveries", "no_derived": "No derived lots (is it a finished-implant lot?)",
        "weights": "Index weights", "reset": "Reset default weights", "index": "Criticality index",
        "top1": "Ranked #1", "t23_top10": "Tier 2/3 in the top 10", "weights_now": "Normalised weights: {w}",
        "index_note": "Index = 100 × Σ (weight × min-max normalised component). Default weights in config/scoring.yaml.",
        "rank_change": "Δ rank",
    },
}

# Column headers for tables (shared across pages)
COLS = {
    "pt": {"item_sku": "Componente", "item_name": "Nome", "category": "Categoria", "revenue_exposed": "Receita exposta/mês",
           "direct_suppliers": "Fornecedores diretos", "hidden": "Fornecedor oculto (a montante)",
           "country": "País", "erp_pct": "Visão ERP", "graph_pct": "Visão grafo",
           "sku": "SKU", "name": "Nome", "dc": "CD", "uf": "UF", "loss_frac": "Oferta perdida", "cover_days": "Cobertura (dias)",
           "in_transit_days": "Pipeline + trânsito (dias)", "tts_days": "TTS (dias)", "stockout_days": "Dias em ruptura",
           "daily_demand": "Demanda/dia", "units_short": "Unidades faltantes", "revenue_at_risk": "Receita em risco",
           "mitigation": "Mitigação", "rows": "Casos implante × CD", "revenue_mitigated": "Receita mitigada",
           "lot_id": "Lote", "type": "Tipo", "level": "Nível BOM", "status": "Status", "qty": "Quantidade",
           "delivered": "Entregue", "in_stock": "Em estoque", "depth": "Profundidade", "produced_by": "Produzido por",
           "mfg_date": "Fabricação", "hospital_id": "Hospital (id)", "hospital": "Hospital", "date": "Data",
           "rank": "Posição", "supplier_id": "Fornecedor", "tier": "Tier", "index": "Índice",
           "betweenness": "Betweenness", "pagerank": "PageRank", "geo_risk": "Risco geográfico",
           "financial_risk": "Risco financeiro", "single_source": "Fonte única"},
    "en": {"item_sku": "Component", "item_name": "Name", "category": "Category", "revenue_exposed": "Revenue exposed/month",
           "direct_suppliers": "Direct suppliers", "hidden": "Hidden upstream supplier",
           "country": "Country", "erp_pct": "ERP view", "graph_pct": "Graph view",
           "sku": "SKU", "name": "Name", "dc": "DC", "uf": "State", "loss_frac": "Supply lost", "cover_days": "Cover (days)",
           "in_transit_days": "Pipeline + transit (days)", "tts_days": "TTS (days)", "stockout_days": "Stock-out days",
           "daily_demand": "Demand/day", "units_short": "Units short", "revenue_at_risk": "Revenue at risk",
           "mitigation": "Mitigation", "rows": "Implant × DC cases", "revenue_mitigated": "Revenue mitigated",
           "lot_id": "Lot", "type": "Type", "level": "BOM level", "status": "Status", "qty": "Quantity",
           "delivered": "Delivered", "in_stock": "In stock", "depth": "Depth", "produced_by": "Produced by",
           "mfg_date": "Manufactured", "hospital_id": "Hospital (id)", "hospital": "Hospital", "date": "Date",
           "rank": "Rank", "supplier_id": "Supplier", "tier": "Tier", "index": "Index",
           "betweenness": "Betweenness", "pagerank": "PageRank", "geo_risk": "Geo risk",
           "financial_risk": "Financial risk", "single_source": "Single source"},
}

COUNTRY_PT = {
    "BR": "Brasil", "AR": "Argentina", "US": "Estados Unidos", "MX": "México", "CA": "Canadá", "CR": "Costa Rica",
    "DE": "Alemanha", "IE": "Irlanda", "CH": "Suíça", "FR": "França", "DK": "Dinamarca", "IT": "Itália",
    "GB": "Reino Unido", "ES": "Espanha", "NL": "Países Baixos", "BE": "Bélgica", "SE": "Suécia", "PT": "Portugal",
    "IL": "Israel", "CN": "China", "IN": "Índia", "KR": "Coreia do Sul", "JP": "Japão", "TH": "Tailândia",
    "MY": "Malásia", "SG": "Singapura",
}
CATEGORY = {
    "pt": {"HIP": "Quadril", "KNEE": "Joelho", "SPINE": "Coluna", "TRAUMA": "Trauma", "STENT": "Stents",
           "VALVE": "Válvulas cardíacas", "VASCULAR": "Vascular", "ORTHO-COMMON": "Ortopedia (comum)",
           "CARDIO-COMMON": "Cardio (comum)", "RAW": "Matéria-prima"},
    "en": {"HIP": "Hip", "KNEE": "Knee", "SPINE": "Spine", "TRAUMA": "Trauma", "STENT": "Stents",
           "VALVE": "Heart valves", "VASCULAR": "Vascular", "ORTHO-COMMON": "Orthopedic (shared)",
           "CARDIO-COMMON": "Cardio (shared)", "RAW": "Raw material"},
}
VALUES = {  # categorical values shown in tables
    "pt": {"RAW": "Matéria-prima", "COMPONENT": "Componente", "FINISHED": "Implante", "released": "Liberado",
           "quarantine": "Quarentena", "recalled": "Recolhido", "expired": "Vencido",
           "no substitute": "Sem substituto", "not in time": "Substituto não fica pronto a tempo",
           "partially mitigable": "Parcialmente mitigável", "fully mitigable": "Totalmente mitigável",
           "supplier": "Fornecedor", "country": "País", "port": "Porto / aeroporto"},
    "en": {"RAW": "Raw material", "COMPONENT": "Component", "FINISHED": "Implant", "released": "Released",
           "quarantine": "Quarantine", "recalled": "Recalled", "expired": "Expired",
           "no substitute": "No substitute", "not in time": "Substitute not ready in time",
           "partially mitigable": "Partially mitigable", "fully mitigable": "Fully mitigable",
           "supplier": "Supplier", "country": "Country", "port": "Port / airport"},
}


def lang() -> str:
    return st.session_state.get("lang", "pt")


def t(key: str) -> str:
    """Raw translated text (plain contexts: Plotly, dataframes). Wrap with esc()/tm() for Markdown contexts."""
    return T[lang()].get(key, key)


def tm(key: str) -> str:
    """Translated text escaped for Markdown contexts (metric, caption, help, labels...)."""
    return fmt.esc(t(key))


esc = fmt.esc


def num(v, decimals: int = 0) -> str:
    return fmt.num(v, lang(), decimals)


def integer(v) -> str:
    return fmt.integer(v, lang())


def pct(v, decimals: int = 0) -> str:
    return fmt.pct(v, lang(), decimals)


def money(v) -> str:
    """Compact R$ for Markdown contexts (already escaped)."""
    return fmt.esc(fmt.money(v, lang()))


def money_plain(v) -> str:
    """Compact R$ for plain-text contexts (Plotly, dataframes)."""
    return fmt.money(v, lang())


def country_name(iso2: str, english: str | None = None) -> str:
    return COUNTRY_PT.get(iso2, english or iso2) if lang() == "pt" else (english or iso2)


def category_name(code: str) -> str:
    return CATEGORY[lang()].get(code, code)


def value_label(v) -> str:
    return VALUES[lang()].get(v, v) if isinstance(v, str) else v


def col(name: str) -> str:
    return COLS[lang()].get(name, name)


def table(df: pd.DataFrame, money_cols=(), int_cols=(), dec_cols: dict | None = None, pct_cols: dict | None = None,
          translate_cols=(), **kw) -> None:
    """st.dataframe with language-aware display formats (via pandas Styler: values stay numeric, so sorting
    still works numerically), translated headers and translated categorical values."""
    if df is None or df.empty:
        st.info("–")
        return
    d = df.copy()
    for c in translate_cols:
        if c in d:
            d[c] = d[c].map(value_label)
    if "category" in d:
        d["category"] = d["category"].map(category_name)
    formats = {c: (lambda v: fmt.money_full(v, lang())) for c in money_cols if c in d}
    formats |= {c: (lambda v: fmt.integer(v, lang())) for c in int_cols if c in d}
    formats |= {c: (lambda v, k=k: fmt.num(v, lang(), k)) for c, k in (dec_cols or {}).items() if c in d}
    formats |= {c: (lambda v, k=k: fmt.pct(v, lang(), k)) for c, k in (pct_cols or {}).items() if c in d}
    # Streamlit shows nulls as "None" even with a Styler formatter: pre-format columns that contain nulls
    # (those few lose numeric sorting; every other column keeps numeric values and sorts correctly)
    for c in [c for c in formats if d[c].isna().any()]:
        d[c] = d[c].map(formats.pop(c))
    config = {c: st.column_config.Column(col(c)) for c in d.columns}
    config |= kw.pop("column_config", {})
    st.dataframe(d.style.format(formats, na_rep="–"), hide_index=True, width="stretch", column_config=config, **kw)


def plotly_locale(fig) -> None:
    """Decimal and thousands separators in Plotly (hover / axes) follow the app language."""
    fig.update_layout(separators=",." if lang() == "pt" else ".,")


def _settings() -> Neo4jSettings:
    """Connection settings, in order: st.secrets [neo4j] (Streamlit Cloud or .streamlit/secrets.toml),
    then .env - the local Neo4j by default, or AuraDB when SGRAPH_APP_TARGET=aura."""
    try:
        sec = st.secrets["neo4j"]
        return Neo4jSettings(uri=sec["uri"], user=sec.get("user", "neo4j"), password=sec["password"],
                             database=sec.get("database", "neo4j"))
    except Exception:  # noqa: BLE001 - no secrets.toml locally -> fall back to .env
        from supplygraph.config import neo4j_settings

        return neo4j_settings(os.getenv("SGRAPH_APP_TARGET", "local"))


@st.cache_resource(show_spinner=False)
def driver():
    # same helper as the CLI / export: verified TLS (OS store + certifi) for neo4j+s:// URIs
    d = get_driver(_settings())
    d.verify_connectivity()
    return d


def safe_driver():
    try:
        return driver()
    except Exception:  # noqa: BLE001
        st.error(tm("conn_error"))
        st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def q(query: str, params: dict | None = None) -> pd.DataFrame:
    """Cached, parameterised read query with a 30 s timeout. Never format values into `query`."""
    return run_df(safe_driver(), query, params or {}, timeout=30)


def header(key: str) -> None:
    st.title(tm(key))
    st.caption(tm("synthetic_note"))
