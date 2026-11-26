# Resume bullets and site card

## Resume - English

- Built a graph digital twin of a multi-tier implant supply chain in Neo4j (Cypher 25, GDS): 60k nodes / 238k
  relationships, deterministic synthetic data calibrated with Brazilian import and IBGE open data.
- Revealed hidden sub-tier risk invisible to the ERP: 29% of "dual-sourced" components converge on a single
  upstream supplier (53% of revenue), and China exposure rises from 0.4% to 43.6% of revenue across all tiers.
- Designed a Time-to-Survive x Time-to-Recover disruption simulator and a weighted supplier criticality index
  (betweenness, PageRank, revenue at risk) robust to weight changes (Spearman >= 0.90).
- Engineered a reproducible pipeline (Typer CLI, idempotent batched loader, 9 graph data-quality tests, GitHub
  Actions CI with Neo4j service container) and a bilingual Streamlit app for AuraDB Free.
- Benchmarked graph vs relational (DuckDB recursive CTEs) on 18 scenarios with identical answers and documented
  where each engine wins; lot recall traced across 4 BOM levels in 19 ms.

## Currículo - Português

- Construí um gêmeo digital em grafo de uma cadeia multi-tier de implantes no Neo4j (Cypher 25, GDS): 60 mil nós e
  238 mil relacionamentos, com dados sintéticos determinísticos calibrados com importações brasileiras e dados do IBGE.
- Revelei riscos de subfornecedores invisíveis ao ERP: 29% dos componentes "dual-source" convergem para um único
  fornecedor a montante (53% da receita) e a exposição à China sobe de 0,4% para 43,6% da receita considerando todos os tiers.
- Desenvolvi um simulador de disrupção Time-to-Survive × Time-to-Recover e um índice de criticidade de fornecedor
  ponderado (betweenness, PageRank, receita em risco), estável a mudanças de peso (Spearman ≥ 0,90).
- Estruturei um pipeline reprodutível (CLI em Typer, carga idempotente em lotes, 9 testes de qualidade do grafo, CI
  no GitHub Actions com Neo4j em container) e uma app Streamlit bilíngue pronta para o AuraDB Free.
- Comparei grafo e relacional (CTE recursiva no DuckDB) em 18 cenários com respostas idênticas e documentei onde cada
  motor vence; rastreio de recall de lote em 4 níveis de BOM em 19 ms.

## Card for gorc-supply.github.io

Same pattern as the other project cards on the site (`<article class="pc">`: media, `h3` + status pill, one
sentence with an `<em>` highlight, three actions, and i18n strings in PT / EN / ES). Status pill: `No ar` (the demo is live).

```html
<article class="pc">
  <div class="m"><video src="video/supplygraph-card.mp4" poster="img/supplygraph-visao-geral-t.webp" muted loop playsinline autoplay preload="metadata" aria-label="Tour pelas páginas do SupplyGraph OPME"></video></div>
  <div class="in">
    <h3 data-i="sgh">supplygraph-opme <span class="pill">No ar</span></h3>
    <p class="d" data-i="sgd">Gêmeo digital em grafo de uma cadeia de implantes que mostra <em>o fornecedor do fornecedor</em> que o ERP não vê.</p>
    <div class="acts" data-i="sga"><button class="b sm g" type="button" data-open="sg">Ver detalhes</button><a class="b sm" href="https://github.com/gorc-supply/supplygraph-opme">Ver código</a><a class="b sm" href="https://supplygraph-opme.streamlit.app">Abrir ↗</a></div>
  </div>
</article>
```

i18n strings:

```js
// pt
sgh:'supplygraph-opme <span class="pill">No ar</span>',
sgd:'Gêmeo digital em grafo de uma cadeia de implantes que mostra <em>o fornecedor do fornecedor</em> que o ERP não vê.',
// en
sgh:'supplygraph-opme <span class="pill">Live</span>',
sgd:'A graph digital twin of an implant supply chain that shows <em>the supplier\'s supplier</em> the ERP cannot see.',
// es
sgh:'supplygraph-opme <span class="pill">En línea</span>',
sgd:'Gemelo digital en grafo de una cadena de implantes que muestra <em>al proveedor del proveedor</em> que el ERP no ve.',
```

Text for the "Ver detalhes" modal (PT):

> Modelei em Neo4j uma rede sintética de implantes ortopédicos e cardiovasculares, com fornecedores em três tiers,
> BOM, plantas, portos, CDs, hospitais e genealogia de lotes, calibrada com importações reais do Brasil e dados do
> IBGE. Na visão do ERP, a China pesa 0,4% da receita; seguindo a rede até a matéria-prima, 43,6%. Dos componentes
> com dois fornecedores, 29% dependem de um único subfornecedor. Tem simulador de disrupção TTS × TTR, recall de
> lote em milissegundos, ranking de criticidade com GDS e um benchmark grafo × SQL em que o DuckDB ganhou em
> velocidade, e eu explico por quê.

The `Abrir ↗` button points to the live demo: https://supplygraph-opme.streamlit.app
