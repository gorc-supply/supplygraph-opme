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
| 8 - Publicação | **Parcial** | 12 commits locais, READMEs, CI, export para o Aura e deploy prontos. **O repositório público não foi criado e nada foi enviado ao GitHub**: o modo automático do Claude Code bloqueou o `gh repo create ... --push`. Por isso o CI também nunca rodou. |
| 9 - Divulgação | Concluída (texto) | Case EN/PT, roteiro de 90 s, 3 posts, bullets de currículo e card do site em [docs/portfolio/](docs/portfolio). O vídeo depende de você. |

## 2. Pendências que dependem de você (ordem de prioridade)

1. **Criar o repositório público e enviar o código** (~2 min). No PowerShell, dentro da pasta do projeto:
   ```powershell
   cd C:\Projetos\Neo4J\supplygraph-opme
   git ls-files | Select-String "\.env$"     # deve voltar vazio (o .env está no .gitignore)
   gh repo create gorc-supply/supplygraph-opme --public --source . --remote origin --push
   ```
   Fiz a varredura de segredos antes de cada commit: nenhum `.env`, senha ou URI com credencial está versionado.
   A senha do Neo4j local (`supplygraph-dev`) existe só no seu `.env`.

2. **Conferir o CI** (~10 min). `gh run watch` logo após o push. O workflow nunca rodou, então a primeira execução
   pode precisar de ajuste (o ponto mais provável é o download dos plugins pelo `NEO4J_PLUGINS` no container).
   Se falhar, `gh run view --log-failed` mostra o erro.

3. **AuraDB Free** (~15 min). Crie a instância em <https://console.neo4j.io> (tipo *AuraDB Free*), baixe o arquivo
   de credenciais e preencha `AURA_URI`, `AURA_USER` e `AURA_PASSWORD` no `.env`. Depois, com o Neo4j local no ar:
   ```powershell
   uv run sgraph up --mode portable          # se o Neo4j local não estiver rodando
   uv run sgraph export-aura --dry-run       # já testado: cabe no limite (30,3% / 59,7%)
   uv run sgraph export-aura                 # copia o grafo com as propriedades do GDS (~5-10 min)
   ```

4. **Streamlit Community Cloud** (~10 min). Em <https://share.streamlit.io>: *Create app* -> repositório
   `gorc-supply/supplygraph-opme`, branch `main`, arquivo `app/streamlit_app.py`. Em *Advanced settings -> Secrets*,
   cole o bloco de `.streamlit/secrets.toml.example` com os dados do Aura. Passo a passo em [docs/deploy.md](docs/deploy.md).
   Depois, confira a URL final e troque o link "Live demo" no card do site.

5. **Gravar o vídeo de 90 s** (~1 h com edição). Roteiro em [docs/portfolio/video-script-90s.md](docs/portfolio/video-script-90s.md).
   Para rodar a app localmente: `uv run streamlit run app/streamlit_app.py`.

6. **Publicar no site e no LinkedIn** (~30 min). Card no padrão dos outros projetos e posts em
   [docs/portfolio/](docs/portfolio) (substitua `[link do repo]`). Vale revisar o tom dos posts antes.

7. **Instalar o Docker Desktop** (opcional, ~20 min + reinício). Não é necessário para nada funcionar (a instalação
   portátil cobre tudo), mas é o caminho "oficial" do README. Depois: `uv run sgraph up --mode docker`.

8. **Atualizar a âncora do ComexStat** quando o serviço voltar (~2 min): `uv run sgraph fetch-anchors` e
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
- Visualização com `neo4j-viz` ([ADR-005](docs/decisions/ADR-005-neo4j-viz.md)), a única das três opções com manutenção ativa.

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
- **App:** testada por `AppTest`, não por um navegador; os prints e o GIF para o README ficam para a gravação do vídeo.

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
