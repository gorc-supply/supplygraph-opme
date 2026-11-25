# Rascunhos de posts para o LinkedIn

Tom: direto, primeira pessoa, sem jargão desnecessário. Os números vêm de uma rede **sintética** e isso está dito
em cada post; não apresente como dado de mercado.

---

## Post 1 - "Visão ERP × visão grafo"

**Visual:** `docs/img/geo_erp_vs_graph.png` (barras laranja = ERP, azul = grafo).

Passei anos olhando fornecedor pelo ERP. Pedido de compra, fornecedor tier-1, país do tier-1. Fim.

Montei um gêmeo digital em grafo de uma cadeia de implantes ortopédicos e cardíacos (rede sintética, calibrada com
importações reais do Brasil e dados do IBGE) e fiz uma pergunta simples: quanto da receita **não existe** sem um
determinado país?

Olhando só o que o comprador vê (tier-1 e planta), a China aparece em 0,4% da receita.
Seguindo a rede até a matéria-prima, o número vai para 43,6%.

Não é que o ERP esteja errado. Ele simplesmente não enxerga o fornecedor do meu fornecedor. A dependência estava lá
o tempo todo, dois ou três níveis abaixo.

Em SQL essa pergunta é um CTE recursivo que dá trabalho para escrever e mais ainda para revisar. Em grafo é um
padrão de caminho.

Código aberto, com os dados sintéticos e as âncoras reais documentadas: [link do repo]

#SupplyChain #Neo4j #OPME #GestãoDeRiscos

---

## Post 2 - "O falso dual-source"

**Visual:** print do Explorador de rede no app, com dois fornecedores tier-1 ligados ao mesmo tier-2 em destaque.

Todo mundo que já trabalhou com compras conhece o alívio de ver "2 fornecedores homologados" no cadastro do item.

Testei isso num gêmeo digital de uma cadeia de implantes (rede sintética, 244 fornecedores em 3 tiers).

Dos 224 componentes com dois ou mais fornecedores diretos, 66 (29%) não têm alternativa nenhuma de verdade: todos
os fornecedores tier-1 compram uma peça crítica, 100%, do mesmo fornecedor tier-2 ou tier-3. Esses 66 itens
entram em produtos que somam 53% da receita.

O cadastro mostra dois fornecedores. A rede mostra um só.

A consulta que encontra isso segue a cadeia de compras do fornecedor do fornecedor, nível a nível, respeitando a
estrutura do produto. É o tipo de pergunta que um banco de grafos responde em segundos e que numa planilha
ninguém faz.

Repo com código, dados e metodologia: [link do repo]

#Suprimentos #Neo4j #SupplyChainRisk

---

## Post 3 - "Recall em milissegundos"

**Visual:** página "Recall de lote" do app (mapa com os hospitais atingidos + tabela de lotes).

Rastreabilidade de implante não é opcional. Quando um lote de matéria-prima é reprovado, a pergunta é imediata:
quais implantes saíram dele, em que hospital estão e quanto ainda dá para segurar no estoque?

No meu projeto de gêmeo digital (dados sintéticos), um único lote de titânio reprovado leva a:
- 105 lotes de implante derivados dele,
- 5.881 unidades já entregues a 180 hospitais em 26 estados,
- 684 unidades ainda em estoque para bloquear.

A consulta que monta essa genealogia completa, da barra de titânio até o hospital, roda em menos de 20 milissegundos.

Com a genealogia modelada como grafo, o rastreio para frente e para trás é uma consulta só, não um mutirão de
planilhas.

Repo: [link do repo]

#OPME #Rastreabilidade #Neo4j #Qualidade
