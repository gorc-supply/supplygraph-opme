# Case - SupplyGraph OPME

**Enxergando os fornecedores que o ERP não mostra: um gêmeo digital em grafo de uma cadeia de implantes**

## Problema

Cadeias de OPME são profundas: uma haste femoral depende de uma usinagem, que depende de uma forjaria, que depende
de poucas usinas de titânio grau médico. O sistema de compras só mostra o primeiro elo. Análises de risco feitas
nessa visão deixam de fora justamente os fornecedores que podem parar a operação, e quando um lote de material é
reprovado, rastrear até o paciente leva dias.

## Abordagem

- Construí um **gêmeo digital em grafo** no Neo4j (Community 2026.10, Cypher 25): 244 fornecedores em três tiers,
  869 itens numa BOM multinível, plantas, portos, 14 CDs no Brasil, 1.400 hospitais e 58 mil lotes com genealogia
  completa. **Dados sintéticos (semente fixa) calibrados com dados abertos reais**: importações brasileiras de
  implantes em 2024 por origem, NCMs oficiais e municípios do IBGE.
- Modelei o que falta no ERP: **de qual tier-2 cada tier-1 compra de fato** (`BUYS_FROM`), o que transforma a
  convergência oculta numa consulta.
- Escrevi sete análises de negócio em Cypher comentado, um simulador de disrupção **TTS × TTR** (Simchi-Levi),
  algoritmos de GDS (betweenness, PageRank, Leiden, similaridade, Dijkstra/Yen) e um **índice de criticidade de
  fornecedor** ponderado, com análise de sensibilidade.
- Tratei como produção: gerador determinístico, carga idempotente, 9 verificações de qualidade como testes, CI com
  Neo4j em container de serviço e app Streamlit pronta para o AuraDB Free.
- **Comparei grafo × relacional** (CTE recursiva no DuckDB) nas mesmas três perguntas e publiquei o resultado mesmo
  com o DuckDB vencendo em velocidade.

## Resultados (rede sintética)

1. **China: de 0,4% para 43,6%.** Parte da receita que não existe sem a China, na visão do ERP e na visão do grafo.
2. **29% de falso dual-source.** 66 de 224 componentes com dois ou mais fornecedores convergem 100% para um único
   fornecedor a montante; eles alimentam 53% da receita.
3. **Os 10 maiores riscos são invisíveis ao ERP.** Os 10 fornecedores com maior receita em risco são tier-2/3; o
   primeiro tier-1 aparece em 74º. O pior (produtor de barra de titânio) deixa 35 dias de cobertura para uma
   recuperação de 180 dias.
4. **Recall em 19 ms**: um lote de titânio -> 105 lotes de implante, 180 hospitais em 26 estados, 684 unidades a bloquear.

## Impacto

Para um diretor de suprimentos: a lista ranqueada dos fornecedores que devem entrar no programa de risco (e não os
maiores em gasto), o caso quantificado para estoque estratégico de matéria-prima, os 66 itens que precisam de uma
segunda fonte realmente independente e o perímetro de um recall em milissegundos. Para um avaliador técnico: um
pipeline de grafo reprodutível e testado, e uma medição honesta de quando o grafo é, e quando não é, a ferramenta certa.

Repositório: https://github.com/gorc-supply/supplygraph-opme  
Demo no ar: https://supplygraph-opme.streamlit.app
