"""Storyboard of the 90-second demo (follows docs/portfolio/video-script-90s.md).

Each scene has narration sentences as (speech, subtitle): `speech` is what the voice says (numbers spelled
out so the TTS reads them naturally), `subtitle` is the short on-screen text. Numbers match the README:
China 0.4% -> 43.6%, 29% false dual-source, S-T3-003 out for 180 days -> 35 days of cover, 164 implants,
1,400 hospitals, R$ 242.2 M; recall of RM-TI64-L0043 -> 105 implant lots, 180 hospitals, 684 units.
"""

from __future__ import annotations

DEMO_URL = "https://supplygraph-opme.streamlit.app"
APP_URL = DEMO_URL + "/~/+/"  # the app itself, without the Streamlit Cloud frame (no badges / avatar)
REPO_URL = "github.com/gorc-supply/supplygraph-opme"
VOICES = {"pt": "pt-BR-AntonioNeural", "en": "en-US-AndrewNeural"}
RATES = {"pt": "+10%", "en": "+4%"}  # speaking rate (keeps the cut within 80-95 s)
RECALL_LOT = "RM-TI64-L0043"  # the lot used in the README / analysis
INTRO_S, OUTRO_S = 3.0, 4.0

SCENES = ["overview", "explorer", "simulator", "recall", "ranking"]

NARRATION = {
    "pt": {
        "overview": [
            ("No ERP, eu só enxergo o fornecedor direto.", "No ERP, só aparece o fornecedor direto"),
            (
                "Este gráfico mostra a receita que depende cem por cento de um país.",
                "Receita que depende 100% de um país",
            ),
            (
                "Na visão do ERP, a China pesa zero vírgula quatro por cento.",
                "Visão ERP: China = 0,4% da receita",
            ),
            (
                "Seguindo a rede até a matéria-prima, são quarenta e três vírgula seis por cento.",
                "Visão grafo, todos os tiers: 43,6%",
            ),
            (
                "E vinte e nove por cento dos itens com dois fornecedores dependem de um único fornecedor oculto.",
                "29% dos itens “dual-source” dependem de um só fornecedor oculto",
            ),
        ],
        "explorer": [
            (
                "No explorador, cada cor é uma comunidade encontrada pelo algoritmo Leiden.",
                "Cada cor = uma comunidade (Leiden, GDS)",
            ),
            (
                "E o tamanho do nó mostra o quanto ele é um gargalo da rede.",
                "Tamanho do nó = gargalo (betweenness)",
            ),
        ],
        "simulator": [
            (
                "Agora, o fornecedor de titânio do tier três para por cento e oitenta dias.",
                "S-T3-003 (titânio, tier 3) para por 180 dias",
            ),
            ("Estoque e pipeline seguram só trinta e cinco dias.", "Estoque + pipeline seguram só 35 dias"),
            (
                "Cento e sessenta e quatro implantes entram em ruptura, nos mil e quatrocentos hospitais.",
                "164 implantes em ruptura · 1.400 hospitais",
            ),
            (
                "São duzentos e quarenta e dois milhões de reais em risco.",
                "R$ 242,2 mi em risco (dados sintéticos)",
            ),
        ],
        "recall": [
            ("Um lote de titânio foi reprovado.", "Um lote de titânio foi reprovado"),
            (
                "Em menos de um segundo, o grafo rastreia cento e cinco lotes de implante e cento e oitenta hospitais.",
                "Em < 1 s: 105 lotes de implante · 180 hospitais",
            ),
            (
                "E seiscentas e oitenta e quatro unidades ainda podem ser bloqueadas no estoque.",
                "684 unidades ainda bloqueáveis no estoque",
            ),
        ],
        "ranking": [
            (
                "O índice de criticidade combina receita em risco, centralidade e risco geográfico.",
                "Índice = receita em risco + centralidade + risco geográfico",
            ),
            (
                "Mesmo mudando os pesos, os dez mais críticos são fornecedores que o ERP não mostra.",
                "Top 10: só tier 2 e 3, invisíveis no ERP",
            ),
        ],
        "outro": [("Código, dados e metodologia no GitHub.", None)],
    },
    "en": {
        "overview": [
            ("In the ERP, I only see the direct supplier.", "The ERP only shows the direct supplier"),
            (
                "This chart shows the revenue that depends one hundred percent on one country.",
                "Revenue that depends 100% on one country",
            ),
            ("In the ERP view, China is zero point four percent.", "ERP view: China = 0.4% of revenue"),
            (
                "Following the network down to raw material, it is forty-three point six percent.",
                "Graph view, all tiers: 43.6%",
            ),
            (
                "And twenty-nine percent of the items with two suppliers depend on one hidden supplier.",
                "29% of “dual-source” items depend on one hidden supplier",
            ),
        ],
        "explorer": [
            (
                "In the explorer, each color is a community found by the Leiden algorithm.",
                "Each color = a community (Leiden, GDS)",
            ),
            ("And node size shows how much of a chokepoint it is.", "Node size = chokepoint (betweenness)"),
        ],
        "simulator": [
            (
                "Now the tier-three titanium supplier stops for one hundred and eighty days.",
                "S-T3-003 (titanium, tier 3) stops for 180 days",
            ),
            ("Stock and pipeline last only thirty-five days.", "Stock + pipeline last only 35 days"),
            (
                "One hundred sixty-four implants stock out, across all one thousand four hundred hospitals.",
                "164 implants stock out · 1,400 hospitals",
            ),
            (
                "Two hundred forty-two million reais of revenue are at risk.",
                "R$ 242.2 M at risk (synthetic data)",
            ),
        ],
        "recall": [
            ("A titanium lot failed inspection.", "A titanium lot failed inspection"),
            (
                "In under a second, the graph traces one hundred and five implant lots and one hundred eighty hospitals.",
                "In < 1 s: 105 implant lots · 180 hospitals",
            ),
            (
                "And six hundred eighty-four units can still be stopped in stock.",
                "684 units can still be quarantined",
            ),
        ],
        "ranking": [
            (
                "The criticality index combines revenue at risk, centrality and country risk.",
                "Index = revenue at risk + centrality + geo risk",
            ),
            (
                "Change the weights, and the top ten are still suppliers the ERP never shows.",
                "Top 10: only tier 2 and 3, invisible to the ERP",
            ),
        ],
        "outro": [("Code, data and method on GitHub.", None)],
    },
}

UI = {  # visible texts used to locate elements (they differ by language)
    "pt": {
        "lang": "pt",
        "trace": "Rastrear",
        "rev_slider": "Receita em risco",
        "lot": "Lote",
        "t23": "Tier 2/3 no top 10",
        "false_dual": "Itens falso dual-source",
    },
    "en": {
        "lang": "en",
        "trace": "Trace",
        "rev_slider": "Revenue at risk",
        "lot": "Lot",
        "t23": "Tier 2/3 in the top 10",
        "false_dual": "False dual-source items",
    },
}

TITLE = {
    "pt": ("SupplyGraph OPME", "Risco multi-tier em grafo · Neo4j", "Gabriel Cunha"),
    "en": ("SupplyGraph OPME", "Multi-tier supply risk as a graph · Neo4j", "Gabriel Cunha"),
}
OUTRO = {"pt": ("Teste a demo", "Código e metodologia"), "en": ("Try the demo", "Code and method")}
