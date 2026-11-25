from __future__ import annotations

import streamlit as st
from common import REPO_URL, header, lang

header("about")

if lang() == "pt":
    st.markdown(f"""
**SupplyGraph OPME** é um gêmeo digital, em grafo (Neo4j), de uma rede de suprimentos multi-tier de implantes
ortopédicos e cardiovasculares: matérias-primas, fornecedores tier-1/2/3, plantas, portos, CDs no Brasil, hospitais e
lotes rastreáveis de ponta a ponta.

**Tese:** risco de supply chain é um problema de *relacionamentos*, não de linhas de tabela.

#### O que é sintético
- Toda a rede (fornecedores, BOM, preços, demanda, estoques, lotes, riscos) é **gerada com semente fixa**.
  Nomes como "Synth Forge Works 007" e "Synthetic Hospital 0001" são fictícios.
- `geo_risk_score` é um *proxy* sintético (distância ao Brasil + ruído), **não** é avaliação geopolítica.
- Valores em R$ são sintéticos e não descrevem o mercado brasileiro de OPME.

#### O que é real (dados abertos)
- **Códigos NCM** dos implantes validados na tabela oficial do Siscomex (9021.10, 9021.31, 9021.39, 9021.90).
- **Peso dos países de origem** de plantas e fornecedores tier-1 calibrado com as importações brasileiras de
  NCM 9021 (2024) por país - UN Comtrade (reporter Brasil), usado porque a API do ComexStat estava indisponível.
- **Municípios, população (Censo 2022) e centroides** do IBGE para posicionar CDs e hospitais.

#### Limitações
- Modelo de TTS × TTR simplificado: perda proporcional ao *share*, sem realocação de capacidade.
- Rede sintética: os números ilustram o método, não o mercado.
- A demo pública (AuraDB Free) não roda GDS: centralidades e comunidades foram calculadas localmente e gravadas.

Código, documentação e benchmark: [{REPO_URL}]({REPO_URL})
""")
else:
    st.markdown(f"""
**SupplyGraph OPME** is a graph (Neo4j) digital twin of a multi-tier supply network for orthopedic and
cardiovascular implants: raw materials, tier-1/2/3 suppliers, plants, ports, Brazilian DCs, hospitals and lots
traceable end to end.

**Thesis:** supply-chain risk is a *relationship* problem, not a table-row problem.

#### What is synthetic
- The whole network (suppliers, BOM, prices, demand, inventory, lots, risk scores) is **generated with a fixed seed**.
  Names such as "Synth Forge Works 007" and "Synthetic Hospital 0001" are fictitious.
- `geo_risk_score` is a synthetic proxy (distance to Brazil + noise), **not** a geopolitical assessment.
- R$ values are synthetic and do not describe the Brazilian implant market.

#### What is real (open data)
- Implant **NCM codes** validated against the official Siscomex table (9021.10, 9021.31, 9021.39, 9021.90).
- **Country-of-origin weights** for plants and tier-1 suppliers calibrated with Brazil's 2024 imports of NCM 9021
  by origin - UN Comtrade (reporter Brazil), used because the ComexStat API was unavailable.
- IBGE **municipalities, population (2022 census) and centroids** to place DCs and hospitals.

#### Limitations
- Simplified TTS x TTR model: loss proportional to share, no capacity re-allocation.
- Synthetic network: the numbers illustrate the method, not the market.
- The public demo (AuraDB Free) runs no GDS: centralities and communities are computed locally and stored.

Code, docs and benchmark: [{REPO_URL}]({REPO_URL})
""")
