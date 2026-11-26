# Roteiro de vídeo - 90 segundos (gravação de tela do app)

Formato: tela cheia do app em 1920×1080, idioma do app em português, narração em primeira pessoa. Deixe o app já
aberto e "aquecido" (todas as páginas visitadas uma vez, para o cache responder na hora).

| Tempo | Tela | Narração |
|---|---|---|
| 0:00-0:10 | Página **Visão geral**, KPIs no topo | "Este é o SupplyGraph OPME: um gêmeo digital, em grafo, de uma cadeia de implantes ortopédicos e cardíacos. A rede é sintética, calibrada com importações reais do Brasil e dados do IBGE." |
| 0:10-0:25 | Rolar até o gráfico **ERP × grafo** e passar o mouse em China e Alemanha | "No ERP, eu só vejo o fornecedor direto. Aqui, a parte da receita que depende 100% de um país: a China aparece com menos de 1% na visão do ERP e com 44% quando o grafo segue a rede até a matéria-prima." |
| 0:25-0:40 | Tabela **falso dual-source**; depois abrir **Explorador de rede**, categoria SPINE | "Dos componentes que parecem ter dois fornecedores, 29% convergem para um único fornecedor tier-2 ou tier-3. No grafo dá para ver: dois fornecedores diretos, um só ponto de falha." |
| 0:40-1:00 | **Simulador de disrupção**: fornecedor do topo da lista (S-T3-003), TTR 180 dias, mostrar KPIs, gráfico TTS × TTR e linha do tempo | "Se este fornecedor de titânio, lá no tier-3, parar pelo tempo que leva para qualificar outro (180 dias), estoque e pipeline seguram cerca de cinco semanas. Depois disso, cada ponto laranja é um produto em ruptura num CD. Receita em risco, hospitais afetados e o dia em que o impacto chega." |
| 1:00-1:15 | **Recall de lote**: lote de titânio padrão, mostrar o mapa e o tempo da consulta | "Um lote de titânio reprovado: em menos de um segundo na demo hospedada (19 ms no benchmark local) eu tenho todos os lotes de implante derivados, os hospitais que receberam e o que ainda dá para bloquear no estoque." |
| 1:15-1:30 | **Ranking de criticidade**: mexer num peso e mostrar o ranking mudando pouco; terminar na página **Sobre** com o link do repo e mostrar o endereço da demo (supplygraph-opme.streamlit.app) | "O índice de criticidade combina receita em risco, centralidade e risco geográfico. Os dez mais críticos são fornecedores que o ERP nem mostra. Código, dados e metodologia estão no GitHub." |

## Produção automatizada (o vídeo publicado)

O vídeo foi produzido por script, sem gravação manual ([ADR-015](../decisions/ADR-015-demo-video-pipeline.md)).
A narração e as legendas usadas estão em [`scripts/video/storyboard.py`](../../scripts/video/storyboard.py)
(versão enxuta deste roteiro, 80-95 s).

- Vídeos (assets da Release): [PT 16:9](https://github.com/gorc-supply/supplygraph-opme/releases/download/v1.0-demo/supplygraph-demo-pt-1080p.mp4) ·
  [PT sem narração](https://github.com/gorc-supply/supplygraph-opme/releases/download/v1.0-demo/supplygraph-demo-pt-1080p-sem-narracao.mp4) ·
  [PT 4:5 (feed)](https://github.com/gorc-supply/supplygraph-opme/releases/download/v1.0-demo/supplygraph-demo-pt-4x5.mp4) ·
  [EN 16:9](https://github.com/gorc-supply/supplygraph-opme/releases/download/v1.0-demo/supplygraph-demo-en-1080p.mp4) ·
  [EN no narration](https://github.com/gorc-supply/supplygraph-opme/releases/download/v1.0-demo/supplygraph-demo-en-1080p-no-narration.mp4)
- No repositório: GIF [PT](video/supplygraph-demo-pt.gif) e [EN](video/supplygraph-demo-en.gif), [poster](video/poster.png),
  legendas [PT](video/supplygraph-demo-pt.srt) e [EN](video/supplygraph-demo-en.srt).

Para refazer (PowerShell, da raiz do repo; a demo publicada precisa estar no ar):

```powershell
python -m venv .video-build/venv
.video-build/venv/Scripts/python -m pip install -r scripts/video/requirements.txt
.video-build/venv/Scripts/python -m playwright install chromium
foreach ($l in "pt", "en") {
  .video-build/venv/Scripts/python scripts/video/narration.py $l   # edge-tts, 1 MP3 por frase
  .video-build/venv/Scripts/python scripts/video/record.py $l      # grava cada cena da demo publicada
}
.video-build/venv/Scripts/python scripts/video/build.py pt --extras  # PT 16:9, sem narração, GIF, 4:5, poster
.video-build/venv/Scripts/python scripts/video/build.py en                  # EN 16:9, sem narração, GIF
.video-build/venv/Scripts/python scripts/video/verify.py docs/portfolio/video/supplygraph-demo-pt-1080p.mp4
```

`record.py <lang> recall,ranking` regrava só as cenas indicadas. Os MP4 ficam fora do Git (`.gitignore`); suba-os
para a Release com `gh release upload v1.0-demo docs/portfolio/video/*.mp4 --clobber`.
