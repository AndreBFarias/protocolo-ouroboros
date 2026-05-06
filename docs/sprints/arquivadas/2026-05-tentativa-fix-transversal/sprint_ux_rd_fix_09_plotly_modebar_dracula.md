---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-09
  title: "Plotly: suprimir modebar e aplicar template Dracula em todos os charts"
  prioridade: P1
  estimativa: 1 dia (8h)
  onda: C2
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §7.12, §8.4 (modebar visivel + cores fora da paleta)"
  depende_de: []
  bloqueia: []
  touches:
    - path: src/dashboard/tema_plotly.py
      reason: "NOVO -- template Plotly Dracula com paleta canônica (bg, gridline, font, axis, marker color sequence) + helper aplicar_tema(fig) que aplica template + config={'displayModeBar': False}"
    - path: src/dashboard/paginas/projecoes.py
      reason: "se existir, aplicar tema_plotly em todos st.plotly_chart"
    - path: src/dashboard/paginas/analise_avancada.py
      reason: "linha 433-474: Sankey existente. Aplicar tema + suprimir modebar"
    - path: src/dashboard/paginas/metas.py
      reason: "linha 195-494: Pie + Indicator. Aplicar tema + suprimir modebar"
    - path: src/dashboard/paginas/categorias.py
      reason: "treemap. Aplicar tema + suprimir modebar"
    - path: tests/test_tema_plotly.py
      reason: "NOVO -- 6 testes: template tem cores Dracula; aplicar_tema(fig) retorna fig com layout.template alterado; helper st_plotly_chart_dracula passa config={displayModeBar:False}"
  forbidden:
    - "Substituir Plotly por outra biblioteca (manter onde já está)"
    - "Aplicar tema fora dos charts Plotly (não tocar em SVG inline custom)"
  hipotese:
    - "Auditoria detectou 2-8 plotly charts por página com modebar visível e paleta default. Necessário: 1) helper de tema; 2) wrapper st_plotly_chart que aplica template + suprime modebar; 3) refatorar 4 páginas para usar wrapper."
  tests:
    - cmd: ".venv/bin/pytest tests/test_tema_plotly.py -v"
      esperado: "6/6 PASSED"
    - cmd: "grep -rE 'st\\.plotly_chart\\(' src/dashboard/paginas/ | grep -v 'st_plotly_chart_dracula' | grep -v 'use_container_width=True, config'"
      esperado: "ZERO -- nenhuma chamada st.plotly_chart sem o wrapper ou sem config explícito"
  acceptance_criteria:
    - "Todas as chamadas st.plotly_chart no dashboard passam config={'displayModeBar': False} OU usam wrapper st_plotly_chart_dracula"
    - "Todas as figuras Plotly aplicam template Dracula (bg #0e0f15, paper #1a1d28, font Inter, gridcolor #313445, axis lines #4a4f63)"
    - "Color sequence segue paleta Dracula: ['#bd93f9', '#ff79c6', '#50fa7b', '#8be9fd', '#f1fa8c', '#ffb86c', '#ff5555']"
    - "DOM real: zero `.modebar` visível nos 4 telas com Plotly (Análise, Metas, Categorias, Projeções se implementada)"
    - "Sankey de Análise mantém estrutura igual mas com cores Dracula"
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8527 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        for cluster, tab in [('Análise', 'Categorias'), ('Análise', 'Análise'), ('Metas', 'Metas')]:
            import urllib.parse
            page.goto(f'http://127.0.0.1:8527/?cluster={urllib.parse.quote(cluster)}&tab={urllib.parse.quote(tab)}')
            page.wait_for_timeout(5000)
            n_modebar = page.evaluate('document.querySelectorAll(\".modebar:not([style*=\\\"display: none\\\"])\").length')
            print(f'{cluster}/{tab}: modebars visiveis = {n_modebar}')   # esperado 0
            assert n_modebar == 0, f'{cluster}/{tab}: modebar nao foi suprimido'
        print('OK modebar suprimido em 3 telas')
        b.close()
    "
```

---

# Sprint UX-RD-FIX-09 — Plotly modebar + tema Dracula

**Status:** BACKLOG — Onda C2 (reconstrução estética).

## 1. Contexto

Auditoria 2026-05-05 §7.12 e §8.4: dashboard usa Plotly em 4 telas (Análise/Sankey, Metas/Pie+Indicator, Categorias/treemap, Projeções/Scatter). Visual atual diverge do mockup:

1. **Modebar visível** (botões zoom/pan/reset/camera) -- mockup é estático/minimalista, sem modebar.
2. **Paleta default Plotly** -- cores variadas que destoam da paleta Dracula (#bd93f9, #ff79c6, #50fa7b, #8be9fd, #f1fa8c, #ffb86c, #ff5555).
3. **Font sans default** em ticks/labels -- mockup pede Inter.
4. **Background plot/paper** -- não casa com `--bg-base #0e0f15` e `--bg-surface #1a1d28`.

Esta sprint cria template Plotly Dracula reutilizável e aplica em todas as 4 páginas.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) inventário de chamadas st.plotly_chart
grep -rnE 'st\.plotly_chart\(' src/dashboard/ | tee /tmp/plotly_calls.txt
wc -l /tmp/plotly_calls.txt

# 2) confirma modebar visível
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8527 --server.headless true &
sleep 6
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context().new_page()
    page.goto('http://127.0.0.1:8527/?cluster=An%C3%A1lise&tab=An%C3%A1lise')
    page.wait_for_timeout(5000)
    n = page.evaluate('document.querySelectorAll(\".modebar\").length')
    print(f'modebars no DOM: {n}')   # esperado: 1+
    b.close()
"
pkill -f 'streamlit.*8527'
```

## 3. Tarefas

1. Rodar hipótese.
2. Criar `src/dashboard/tema_plotly.py`:

   ```python
   """Template Plotly Dracula espelhando a paleta tokens.css do mockup.
   
   Uso:
       from src.dashboard.tema_plotly import st_plotly_chart_dracula, aplicar_tema
       fig = go.Figure(...)
       st_plotly_chart_dracula(fig)   # aplica tema + suprime modebar
   """
   from __future__ import annotations
   from typing import Final
   import streamlit as st
   import plotly.graph_objects as go

   PALETA_DRACULA: Final[list[str]] = [
       "#bd93f9",  # purple (primary)
       "#ff79c6",  # pink
       "#50fa7b",  # green
       "#8be9fd",  # cyan
       "#f1fa8c",  # yellow
       "#ffb86c",  # orange
       "#ff5555",  # red
   ]

   COR_BG_BASE: Final[str] = "#0e0f15"
   COR_BG_SURFACE: Final[str] = "#1a1d28"
   COR_BORDER_SUBTLE: Final[str] = "#313445"
   COR_BORDER_STRONG: Final[str] = "#4a4f63"
   COR_TEXT_PRIMARY: Final[str] = "#f8f8f2"
   COR_TEXT_MUTED: Final[str] = "#6c6f7d"

   TEMPLATE_DRACULA: Final[dict] = {
       "layout": {
           "paper_bgcolor": COR_BG_BASE,
           "plot_bgcolor": COR_BG_SURFACE,
           "font": {"family": "Inter, sans-serif", "color": COR_TEXT_PRIMARY, "size": 13},
           "title": {"font": {"family": "JetBrains Mono", "size": 14, "color": COR_TEXT_PRIMARY}},
           "colorway": PALETA_DRACULA,
           "xaxis": {
               "gridcolor": COR_BORDER_SUBTLE, "linecolor": COR_BORDER_STRONG,
               "tickfont": {"family": "JetBrains Mono", "size": 11, "color": COR_TEXT_MUTED},
               "zerolinecolor": COR_BORDER_SUBTLE,
           },
           "yaxis": {
               "gridcolor": COR_BORDER_SUBTLE, "linecolor": COR_BORDER_STRONG,
               "tickfont": {"family": "JetBrains Mono", "size": 11, "color": COR_TEXT_MUTED},
               "zerolinecolor": COR_BORDER_SUBTLE,
           },
           "legend": {"font": {"family": "Inter", "size": 12, "color": COR_TEXT_PRIMARY}},
           "hoverlabel": {"font": {"family": "JetBrains Mono", "size": 12}, "bgcolor": COR_BG_SURFACE, "bordercolor": COR_BORDER_STRONG},
           "margin": {"l": 40, "r": 16, "t": 32, "b": 40},
       }
   }

   PLOTLY_CONFIG_NO_MODEBAR: Final[dict] = {
       "displayModeBar": False,
       "displaylogo": False,
       "responsive": True,
   }

   def aplicar_tema(fig: go.Figure) -> go.Figure:
       """Aplica template Dracula in-place e retorna a figura."""
       fig.update_layout(**TEMPLATE_DRACULA["layout"])
       return fig

   def st_plotly_chart_dracula(fig: go.Figure, **kwargs) -> None:
       """Wrapper que aplica template + config sem modebar."""
       fig = aplicar_tema(fig)
       config = {**PLOTLY_CONFIG_NO_MODEBAR, **kwargs.pop("config", {})}
       st.plotly_chart(fig, use_container_width=True, config=config, **kwargs)

   # "<citação filosófica final>"
   ```

3. Refatorar **TODAS** as chamadas `st.plotly_chart` em `src/dashboard/paginas/*.py` para usar `st_plotly_chart_dracula`. Localizar com:
   ```bash
   grep -rnE 'st\.plotly_chart\(' src/dashboard/paginas/
   ```
   Para cada chamada, substituir:
   ```python
   # ANTES
   st.plotly_chart(fig, use_container_width=True)
   # DEPOIS
   from src.dashboard.tema_plotly import st_plotly_chart_dracula
   st_plotly_chart_dracula(fig)
   ```
4. Criar `tests/test_tema_plotly.py`:
   ```python
   def test_paleta_tem_7_cores_dracula():
       from src.dashboard.tema_plotly import PALETA_DRACULA
       assert len(PALETA_DRACULA) == 7
       assert PALETA_DRACULA[0] == "#bd93f9"

   def test_aplicar_tema_define_paper_bgcolor():
       import plotly.graph_objects as go
       from src.dashboard.tema_plotly import aplicar_tema, COR_BG_BASE
       fig = go.Figure()
       fig = aplicar_tema(fig)
       assert fig.layout.paper_bgcolor == COR_BG_BASE

   def test_aplicar_tema_define_colorway():
       import plotly.graph_objects as go
       from src.dashboard.tema_plotly import aplicar_tema, PALETA_DRACULA
       fig = aplicar_tema(go.Figure())
       assert list(fig.layout.colorway) == PALETA_DRACULA

   def test_config_modebar_false():
       from src.dashboard.tema_plotly import PLOTLY_CONFIG_NO_MODEBAR
       assert PLOTLY_CONFIG_NO_MODEBAR["displayModeBar"] is False

   def test_st_plotly_chart_dracula_chama_aplicar_tema(monkeypatch):
       # mock streamlit
       import plotly.graph_objects as go
       from src.dashboard.tema_plotly import st_plotly_chart_dracula
       chamadas = []
       monkeypatch.setattr("streamlit.plotly_chart", lambda fig, **kw: chamadas.append((fig, kw)))
       fig = go.Figure()
       st_plotly_chart_dracula(fig)
       assert chamadas and chamadas[0][1]["config"]["displayModeBar"] is False

   def test_paginas_usam_wrapper_dracula():
       """Garante que nenhum paginas/*.py chama st.plotly_chart sem o wrapper."""
       import re, os
       diretorios = "src/dashboard/paginas"
       infratores = []
       for arq in os.listdir(diretorios):
           if not arq.endswith(".py"): continue
           with open(f"{diretorios}/{arq}") as f: txt = f.read()
           for m in re.finditer(r"st\.plotly_chart\(", txt):
               # contexto antes precisa indicar wrapper
               start = max(0, m.start() - 200)
               trecho = txt[start:m.start()]
               if "st_plotly_chart_dracula" not in trecho:
                   infratores.append(arq)
       assert not infratores, f"st.plotly_chart sem wrapper em: {infratores}"
   ```
5. Rodar gauntlet (§6) com playwright validando 0 modebars.

## 4. Anti-débito

- Não trocar SVG inline custom (extrato, contas, skills, humor, medidas, ciclo, cruzamentos) por Plotly. Mockup pede SVG inline -- preservar.
- Se um `Indicator` (gauge) ficar com cor errada após template (Plotly Indicator não usa colorway): override cor explícita por meta.

## 5. Validação visual

```bash
# Comparar PNGs antes/depois das 4 telas com Plotly
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8527 --server.headless true &
sleep 6
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
import urllib.parse
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
    for cluster, tab in [('Análise','Categorias'), ('Análise','Análise'), ('Metas','Metas')]:
        page.goto(f'http://127.0.0.1:8527/?cluster={urllib.parse.quote(cluster)}&tab={urllib.parse.quote(tab)}')
        page.wait_for_timeout(5000)
        path = f'.playwright-mcp/auditoria/fix-09/{cluster.lower()}_{tab.lower()}_dracula.png'
        page.screenshot(path=path, full_page=True)
        print(f'salvo {path}')
    b.close()
"
```

Comparar com mockup: visual mais limpo, cores Dracula, sem modebar.

## 6. Gauntlet

```bash
make lint                                              # exit 0
make smoke                                             # 10/10
.venv/bin/pytest tests/test_tema_plotly.py -v          # 6/6
.venv/bin/pytest tests/ -q --tb=no                     # baseline >=2520
grep -c 'st_plotly_chart_dracula' src/dashboard/paginas/*.py  # >=4 (1 por página com Plotly)
```

---

*"O que se vê depende do que se mostra; mostre menos para que se veja mais." -- Mies van der Rohe (paráfrase)*
