# Relatório final de pendências

Projeto em `C:\Projetos\Neo4J\supplygraph-opme`. Gerado em 25/11/2026.

## 1. Status por fase

| Fase | Status | Observação |
|---|---|---|
| 0 - Plano | Concluída | Versões conferidas online em 25/11/2026 ([VERSIONS.md](docs/VERSIONS.md)); plano em [PLAN.md](docs/PLAN.md). |
| 1 - Fundação | Concluída | Neo4j Community 2026.10.2 + APOC + GDS 2026.10.2 respondendo, schema aplicado, CLI `sgraph`. Rodou no Neo4j **portátil** porque o Docker Desktop não está instalado; o `docker-compose.yml` existe, mas não foi executado localmente. |
| 2 - Dados | Concluída | Gerador determinístico; âncoras NCM (Siscomex), importações (UN Comtrade, porque o ComexStat estava fora) e IBGE; rede `full` = 60.560 nós (30,3%) / 238.467 relacionamentos (59,6%) do Aura Free. |
| 3 - Carga e qualidade | Concluída | Carga idempotente (15,3 s), `neo4j-admin import` (10,5 s de import, 38,8 s de ponta a ponta), 9/9 verificações passando, relatório em `reports/data_quality.md`. |
| 4 - Análises Cypher | Concluída | 9A-9G com números e recomendações em [docs/analysis.md](docs/analysis.md). |
| 5 - GDS | Concluída | 6 projeções, 9 algoritmos, propriedades gravadas, índice de criticidade com sensibilidade. |
| 6 - Benchmark | Concluída | 18 medições com respostas idênticas; o DuckDB venceu todas e isso está documentado com as razões ([benchmarks.md](docs/benchmarks.md)). |
| 7 - App | Concluída | 6 páginas PT/EN; testadas com `streamlit.testing.AppTest` (12/12 renderizações sem erro). Não abri no navegador nem tirei prints. |
| 8 - Publicação | Concluída | Repositório público com CI verde; grafo no AuraDB Free (contagens idênticas às do local); demo no ar em https://supplygraph-opme.streamlit.app (`?lang=en` para inglês). |
| 9 - Divulgação | Concluída | Case EN/PT, 3 posts, bullets de currículo e card do site em [docs/portfolio/](docs/portfolio). Vídeo de 90 s gerado por script (PT/EN, 16:9 e 4:5, com e sem narração) na [Release v1.0-demo](https://github.com/gorc-supply/supplygraph-opme/releases/tag/v1.0-demo); GIF no topo dos READMEs. |

## 2. Pendências que dependem de você (ordem de prioridade)

1. ~~Repositório público, CI, AuraDB Free e Streamlit Cloud~~ **feitos.** Demo: https://supplygraph-opme.streamlit.app
   Para atualizar a demo depois de mudar o grafo: `uv run sgraph export-aura` (a app lê o Aura) e, se mudar dependências, *Reboot app* no Streamlit Cloud. As dependências da app vêm de `app/requirements.txt`.

2. **Cadastrar os secrets do keepalive do Aura** (~3 min). Em GitHub -> repositório -> *Settings* -> *Secrets and variables* -> *Actions* -> *New repository secret*: `AURA_URI`, `AURA_USER`, `AURA_PASSWORD` e `AURA_DATABASE` (mesmos valores do seu `.env`). Depois teste: `gh workflow run aura-keepalive.yml` e `gh run watch`. O workflow roda a cada 2 dias; se falhar, retome a instância no console do Aura em até 30 dias.

3. ~~Gravar o vídeo de 90 s~~ **feito por script** ([ADR-015](docs/decisions/ADR-015-demo-video-pipeline.md)). Falta só **assistir
   aos vídeos inteiros com som** (~5 min) e, se quiser, trocar a voz sintética pela sua: as frases estão em
   `scripts/video/storyboard.py` e o passo a passo para refazer em [video-script-90s.md](docs/portfolio/video-script-90s.md).
   Vídeos: [PT](https://github.com/gorc-supply/supplygraph-opme/releases/download/v1.0-demo/supplygraph-demo-pt-1080p.mp4) · [PT 4:5](https://github.com/gorc-supply/supplygraph-opme/releases/download/v1.0-demo/supplygraph-demo-pt-4x5.mp4) · [EN](https://github.com/gorc-supply/supplygraph-opme/releases/download/v1.0-demo/supplygraph-demo-en-1080p.mp4).
   Ao publicar no LinkedIn, suba o MP4 (não o link) e anexe o `.srt` como legenda.
   Para rodar a app localmente: `uv run streamlit run app/streamlit_app.py`.

4. ~~Card no site~~ **publicado** em https://gorc-supply.github.io (primeiro card de Projetos, PT/EN/ES). Falta **publicar no LinkedIn** (~20 min): posts em [docs/portfolio/](docs/portfolio), vale revisar o tom; suba o MP4 4:5 com o `.srt`. O botão "Vídeo" do card baixa o MP4 (o GitHub serve assets de Release como download); para tocar no navegador, troque o link por um vídeo no YouTube/LinkedIn quando publicar.

5. **Instalar o Docker Desktop** (opcional, ~20 min + reinício). Não é necessário para nada funcionar (a instalação
   portátil cobre tudo), mas é o caminho "oficial" do README. Depois: `uv run sgraph up --mode docker`.

6. **Atualizar a âncora do ComexStat** quando o serviço voltar (~2 min): `uv run sgraph fetch-anchors` e
   `uv run sgraph all`. Hoje a âncora vem do UN Comtrade (reporter Brasil).

## 3. Decisões que tomei sozinho e vale revisar

- [ADR-003](docs/decisions/ADR-003-buys-from.md): adicionei o relacionamento `BUYS_FROM` (fornecedor -> fornecedor, com o item e o item-destino). Sem ele, o falso dual-source não é detectável.
- [ADR-006](docs/decisions/ADR-006-portable-neo4j.md): Neo4j portátil (JDK + zip em `.runtime/`, 1,5 GB, fora do git) no lugar do Docker.
- [ADR-007](docs/decisions/ADR-007-comtrade-fallback.md): UN Comtrade como âncora no lugar do ComexStat (API com HTTP 503 e certificado TLS expirado no site de download; não desliguei a verificação de certificado).
- [ADR-008](docs/decisions/ADR-008-tts-ttr-model.md): modelo TTS × TTR e **TTR por tier (60/120/180 dias)**. É a premissa que mais muda o ranking de risco.
- [ADR-011](docs/decisions/ADR-011-network-size.md): dimensionei pela restrição de relacionamentos (59,6%); os nós ficam em 30,3%, abaixo da faixa de 40-60% pedida, porque o modelo tem ~3,9 relacionamentos por nó.
- [ADR-012](docs/decisions/ADR-012-geo-metrics.md): duas métricas geográficas; a manchete usa a "dependência total" (100% de um país).
- [ADR-013](docs/decisions/ADR-013-calibration.md): calibrei os parâmetros de sourcing até os resultados ficarem críveis (a primeira versão dava 81% de convergência oculta e um único fornecedor tier-2 com 43% dos componentes).
- Status de lote `expired` adicionado aos três pedidos (released/quarantine/recalled).
- `geo_risk_score` é um proxy sintético (distância ao Brasil + ruído), não uma avaliação geopolítica.
- [ADR-014](docs/decisions/ADR-014-tls-certifi.md): conexão TLS verificada com o repositório do sistema + `certifi`, num helper único (CLI, export e app). Nunca desliga a verificação de certificado.
- Visualização com `neo4j-viz` ([ADR-005](docs/decisions/ADR-005-neo4j-viz.md)), a única das três opções com manutenção ativa.
- [ADR-015](docs/decisions/ADR-015-demo-video-pipeline.md): vídeo gravado da demo publicada (Playwright + screencast do Chromium em 133%), narração edge-tts (`pt-BR-AntonioNeural`, `en-US-AndrewNeural`), legendas numa faixa abaixo da app, MP4 só como assets da Release.

**Onde a documentação oficial contradisse o escopo:** o changelog do Neo4j anuncia o *Aura Graph Analytics*
disponível no AuraDB Free (sessões de GDS fora do banco). O plugin GDS dentro do banco continua fora do Free, então
mantive o desenho original (GDS local, resultados gravados como propriedades). Detalhe em [VERSIONS.md](docs/VERSIONS.md).

## 4. Limitações e riscos conhecidos

- **Tudo de negócio é sintético.** Os números ilustram o método. As manchetes dependem das premissas de
  `config/network.yaml` e `config/scoring.yaml` (sobretudo a concentração de fornecedores e o TTR por tier). Com
  outra semente ou outros pesos, os valores mudam; o método não.
- **Modelo de ruptura simplificado:** perda proporcional ao share, sem realocação de capacidade, sem rampa de
  recuperação e com pipeline estimado pela Lei de Little. Tende a superestimar perdas.
- **Benchmark:** medido de dentro do Python, com o Neo4j via rede (Bolt) e o DuckDB dentro do processo, numa máquina
  só. O DuckDB venceu os 18 casos; o argumento do grafo neste projeto é expressividade e consultas interativas, não
  velocidade em lote.
- **CI e Docker nunca rodaram.** Os testes passaram localmente (29 + 12 de fumaça da app), mas o workflow do GitHub
  Actions e o `docker-compose.yml` só serão validados depois do push.
- **Aura Free:** a instância pausa por inatividade (a app mostra um aviso amigável) e pode ser apagada depois de um
  período longo sem uso; o export precisa ser refeito quando o grafo mudar.
- **Âncora de importações** em granularidade HS6 (UN Comtrade), não NCM de 8 dígitos.
- **App:** testada por `AppTest` e, na gravação do vídeo, percorrida num Chromium real (Playwright) contra a demo publicada, com checagem dos números em cada cena.
- **Vídeo:** voz sintética (edge-tts, cliente não oficial de um serviço gratuito da Microsoft). Na demo hospedada (AuraDB Free, via rede) o recall leva ~0,7-0,9 s; a narração diz "em menos de um segundo" e o README mantém os 19 ms do benchmark local. Se a app mudar, o vídeo precisa ser refeito (4 comandos).

## 5. Os 3 números mais fortes

1. **China: 0,4% -> 43,6% da receita.** Na visão do ERP (planta + fornecedores tier-1), só 0,4% da receita depende
   100% da China. Seguindo a rede até a matéria-prima, 43,6% da receita tem pelo menos um insumo que só fornecedores
   chineses entregam. É o contraste que mostra por que olhar só o tier-1 engana.
2. **29% de falso dual-source, 53% da receita.** Dos 224 componentes com dois ou mais fornecedores diretos, 66
   dependem 100% do mesmo fornecedor tier-2 ou tier-3. No cadastro parecem ter alternativa; na rede, não têm. Esses
   componentes entram em produtos que respondem por 53,3% da receita mensal.
3. **Os 10 maiores riscos são tier-2/3; o primeiro tier-1 é o 74º.** No ranking de receita em risco (TTS × TTR), o
   pior caso é um produtor tier-3 de barra de titânio: parado pelo tempo de requalificação (180 dias), o estoque e o
   pipeline seguram só 35 dias, 164 implantes entram em ruptura, os 1.400 hospitais são atingidos e R$ 242 mi
   (sintéticos) ficam em risco. Nenhum dos 10 aparece num pedido de compra.

Bônus para o post de rastreabilidade: um lote de titânio reprovado é rastreado em 19 ms até 105 lotes de implante,
180 hospitais em 26 estados e 684 unidades ainda bloqueáveis no estoque.
