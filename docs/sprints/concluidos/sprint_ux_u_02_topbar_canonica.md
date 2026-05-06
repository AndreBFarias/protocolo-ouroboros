---
concluida_em: 2026-05-06
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-U-02
  title: "Topbar canônica: breadcrumb clicável + slot topbar-actions por página"
  prioridade: P0
  estimativa: 0.5 dia
  onda: U
  mockup_fonte: novo-mockup/mockups/00-shell-navegacao.html (bloco topbar) + 02-extrato.html (botões Importar OFX, Exportar) + 09-revisor.html (Próxima divergência, Aprovar)
  depende_de: []
  bloqueia: [UX-U-03, UX-T-01..UX-T-29]
  touches:
    - path: src/dashboard/componentes/shell.py
      reason: "linhas 245-300+ renderizar_topbar() já existe, mas o slot topbar-actions atualmente só aceita lista pre-definida via parametro 'acoes'. Refatorar para aceitar HTML arbitrário (string) que cada página injeta via componente helper."
    - path: src/dashboard/componentes/topbar_actions.py
      reason: "NOVO -- helper renderizar_acao_botao(label, href=None, primary=False, glyph=None, kbd=None) e renderizar_grupo_acoes([...]). Cada página da Onda T usa este helper."
    - path: src/dashboard/app.py
      reason: "linha ~445 _renderizar_topbar_para(cluster, aba_ativa) chamada antes do dispatcher. Hoje passa só cluster+aba. Adicionar 3o argumento opcional: acoes_html (string emitida pela página corrente). Como o dispatcher é chamado depois, e só a página sabe quais ações ela tem, a topbar precisa ser renderizada via st.empty() placeholder + st.session_state, ou cada página renderizar topbar dela mesma. Decisão: cada página recebe slot via st.session_state['topbar_acoes_html'] que é resetado em cada main() run."
    - path: tests/test_topbar_canonica.py
      reason: "NOVO -- testes: breadcrumb com seg.current ANTES do mockup; slot topbar-actions vazio por padrão na Home; slot preenchido em Extrato com 2 botões Importar OFX + Exportar."
  forbidden:
    - "Reescrever a função renderizar_topbar do zero -- ela já está canônica para o breadcrumb. Apenas adicionar o slot."
    - "Forçar páginas a passar acoes_html (deve ser opcional). Páginas sem botões topbar mantém slot vazio."
  hipotese:
    - "Hoje renderizar_topbar() emite breadcrumb + topbar-actions com 0 botões. Páginas como Extrato/Revisor/Categorias do mockup tem botões topbar específicos que não existem no dashboard."
  tests:
    - cmd: ".venv/bin/pytest tests/test_topbar_canonica.py -v"
      esperado: "5+ PASSED"
    - cmd: "make smoke"
      esperado: "10/10"
  acceptance_criteria:
    - "Topbar dashboard renderiza .topbar-actions DIV vazia em todas páginas por default."
    - "Helper componentes/topbar_actions.py exporta renderizar_grupo_acoes(acoes: list[dict]) -> str que cada página chama em seu renderizar() para injetar via st.session_state['topbar_acoes_html']."
    - "main() em app.py reseta st.session_state['topbar_acoes_html'] = '' no início de cada run, antes de chamar a página."
    - "renderizar_topbar lê st.session_state.get('topbar_acoes_html', '') e injeta entre breadcrumb e fim do topbar."
    - "Breadcrumb segue clicável (UX-RD-FIX-05 já fez); validação humana confirma."
    - "Validação humana: dono abre página Extrato e vê botões 'Importar OFX' + 'Exportar' (mockup canônico). Em Visão Geral vê 'Atualizar' + 'Ir para Validação'. Em Revisor vê 'Próxima divergência' + 'Aprovar e seguir'."
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.headless=true --server.port=8765 &
    sleep 8
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
        page.goto('http://127.0.0.1:8765/?cluster=Finan%C3%A7as&tab=Extrato'); page.wait_for_timeout(5000)
        # validar que .topbar-actions existe e tem 2 botoes (no Extrato)
        info = page.evaluate('''() => {
            const slot = document.querySelector('.topbar-actions');
            return {
                tem_slot: !!slot,
                n_botoes: slot?.querySelectorAll('a.btn, button.btn').length || 0,
                labels: Array.from(slot?.querySelectorAll('a.btn, button.btn') || []).map(b => b.textContent.trim())
            };
        }''')
        print(info)
        # Esperado em Extrato (mockup 02): 2 botões Importar OFX + Exportar
        # MAS esta sprint só cria a infraestrutura; preencher os botões fica para T-02 (Extrato)
        # então em U-02 testamos só que SLOT EXISTE
        assert info['tem_slot'], 'topbar-actions slot ausente'
        b.close()
    "
```

---

# Sprint UX-U-02 — Topbar canônica com slot de ações

**Status:** BACKLOG — Onda U (estruturante).

## 1. Contexto

O mockup canônico tem topbar com 2 partes:

1. **Breadcrumb** à esquerda: `OUROBOROS / VISÃO GERAL` ou `OUROBOROS / FINANÇAS / EXTRATO` — segmentos clicáveis exceto o último (`.seg.current`). FIX-05 já tornou clicável.
2. **Slot `topbar-actions`** à direita: cada página injeta seus botões secundários:
   - Visão Geral: `↻ Atualizar` + `→ Ir para Validação`
   - Extrato: `↑ Importar OFX` + `↓ Exportar`
   - Revisor: `Próxima divergência` + `Aprovar (rever) e seguir`
   - Catalogação: `Categorizar` + `Recategorizar`
   - Inbox: `Upload` + `Limpar fila`

Hoje o slot existe na função `renderizar_topbar` em `componentes/shell.py:245-300+` mas é alimentado por uma lista pré-definida. Não há mecanismo das páginas injetarem seus próprios botões.

Esta sprint cria a **infraestrutura** (slot + helper + integração com `app.py`). **Cada página da Onda T preenche os botões dela mesma** quando chega a vez.

## 2. Hipótese verificável (Fase ANTES)

```bash
grep -nE 'def renderizar_topbar|topbar-actions|partes_acoes' src/dashboard/componentes/shell.py | head -10
# esperado: renderizar_topbar aceita arg `acoes` mas não tem mecanismo de session_state
```

## 3. Tarefas

1. Rodar hipótese.
2. Criar `src/dashboard/componentes/topbar_actions.py`:

   ```python
   """Helper para páginas injetarem botões na topbar.

   Cada página chama renderizar_grupo_acoes(...) em seu renderizar() e o resultado
   é registrado em st.session_state['topbar_acoes_html']. main() reseta antes de
   cada run e renderizar_topbar lê o valor para injetar no slot .topbar-actions.

   Mockup-fonte: components.css:.topbar-actions + 00-shell-navegacao.html.
   """
   from __future__ import annotations
   import html as _html
   import streamlit as st
   from typing import Iterable, TypedDict

   class Acao(TypedDict, total=False):
       label: str
       href: str
       primary: bool
       glyph: str  # nome do glyph em componentes/glyphs.py
       kbd: str    # tecla atalho (ex.: "/")

   def _renderizar_acao(acao: Acao) -> str:
       """Renderiza UMA ação como HTML link/button da topbar."""
       label = _html.escape(str(acao.get("label", "")))
       href = acao.get("href")
       classe = "btn btn-primary btn-sm" if acao.get("primary") else "btn btn-sm"
       glyph_nome = acao.get("glyph")
       glyph_html = ""
       if glyph_nome:
           from src.dashboard.componentes.glyphs import glyph
           glyph_html = glyph(glyph_nome, tamanho_px=14)
       kbd_html = (
           f'<kbd class="kbd">{_html.escape(acao["kbd"])}</kbd>'
           if acao.get("kbd")
           else ""
       )
       conteudo = f'{glyph_html}<span>{label}</span>{kbd_html}'
       if href:
           href_esc = _html.escape(str(href), quote=True)
           return (
               f'<a class="{classe}" href="{href_esc}" '
               'style="text-decoration:none;display:inline-flex;'
               'align-items:center;gap:6px;">'
               f'{conteudo}</a>'
           )
       return f'<button class="{classe}" type="button">{conteudo}</button>'

   def renderizar_grupo_acoes(acoes: Iterable[Acao]) -> None:
       """Define o HTML das ações da topbar para esta run.

       Deve ser chamado por cada página em seu renderizar() ANTES do
       dispatcher de tabs. main() em app.py reseta o estado antes de cada run.
       """
       html_acoes = "".join(_renderizar_acao(a) for a in acoes)
       st.session_state["topbar_acoes_html"] = html_acoes

   def consumir_acoes_html() -> str:
       """Lê e RESETA o html das ações para o próximo render."""
       html_acoes = st.session_state.get("topbar_acoes_html", "")
       return html_acoes

   # "Aja como o vento e seja como o tempo." -- Sun Tzu (paráfrase)
   ```

3. Em `src/dashboard/componentes/shell.py:renderizar_topbar`, adicionar leitura do slot:

   ```python
   def renderizar_topbar(...):
       # ... código existente do breadcrumb
       
       # UX-U-02: slot topbar-actions alimentado por session_state
       try:
           import streamlit as st
           acoes_html = st.session_state.get("topbar_acoes_html", "")
       except (ImportError, AttributeError):
           acoes_html = ""
       
       return (
           f'<header class="topbar">'
           f'<nav class="breadcrumb" aria-label="Localização">{breadcrumb_html}</nav>'
           f'<div class="topbar-actions">{acoes_html}</div>'
           f'</header>'
       )
   ```

4. Em `src/dashboard/app.py`, no início de `main()` (logo após `_configurar_pagina()`), resetar slot:

   ```python
   def main() -> None:
       _configurar_pagina()
       # UX-U-02: resetar slot topbar-actions antes de cada run
       st.session_state["topbar_acoes_html"] = ""
       # ... resto da main
   ```

5. Criar `tests/test_topbar_canonica.py`:

   ```python
   import subprocess, time, urllib.parse
   import pytest
   from playwright.sync_api import sync_playwright

   PORT = 8771

   @pytest.fixture(scope="module")
   def streamlit_url():
       p = subprocess.Popen([".venv/bin/streamlit","run","src/dashboard/app.py","--server.port",str(PORT),"--server.headless","true"])
       time.sleep(8)
       yield f"http://127.0.0.1:{PORT}"
       p.terminate(); p.wait()

   def test_topbar_tem_slot_actions(streamlit_url):
       with sync_playwright() as p:
           b = p.chromium.launch(); page = b.new_context().new_page()
           page.goto(streamlit_url); page.wait_for_timeout(5000)
           tem = page.evaluate("!!document.querySelector('.topbar .topbar-actions')")
           assert tem, ".topbar-actions slot ausente"
           b.close()

   def test_topbar_breadcrumb_clicavel(streamlit_url):
       with sync_playwright() as p:
           b = p.chromium.launch(); page = b.new_context().new_page()
           page.goto(streamlit_url + "/?cluster=Documentos&tab=Revisor"); page.wait_for_timeout(4500)
           segs = page.evaluate("Array.from(document.querySelectorAll('.breadcrumb .seg')).map(s => ({tag:s.tagName, current:s.classList.contains('current')}))")
           # Primeiros n-1 são <a>, último é <span class=current>
           for s in segs[:-1]:
               assert s["tag"] == "A", f'segmento intermediário deve ser <a>; achei {s}'
           assert segs[-1]["tag"] == "SPAN" and segs[-1]["current"]
           b.close()

   def test_helper_renderizar_grupo_acoes_grava_session_state():
       """Teste unitário do helper sem Streamlit ao vivo."""
       from unittest.mock import MagicMock, patch
       acoes = [
           {"label": "Atualizar", "glyph": "refresh", "kbd": "r"},
           {"label": "Ir para Validação", "primary": True, "href": "?cluster=Documentos&tab=Revisor"},
       ]
       with patch("streamlit.session_state", {}) as ss:
           from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
           renderizar_grupo_acoes(acoes)
           html = ss.get("topbar_acoes_html", "")
           assert "Atualizar" in html
           assert "Ir para Validação" in html
           assert "btn-primary" in html

   def test_main_reseta_slot_em_cada_run():
       """Garante que main() limpa st.session_state['topbar_acoes_html'] = '' no início."""
       import re
       with open("src/dashboard/app.py") as f:
           texto = f.read()
       # busca regex `st.session_state["topbar_acoes_html"] = ""` em main()
       m = re.search(r'def main\(\).*?st\.session_state\[\"topbar_acoes_html\"\] = \"\"', texto, re.DOTALL)
       assert m, "main() não reseta topbar_acoes_html no início; pode causar leak entre runs"
   ```

6. Rodar gauntlet (§7).

## 4. Anti-débito

- Se Streamlit não permitir injeção HTML no topbar via st.session_state (cache de re-renders pode causar piscadas): mover para `st.markdown` direto na main() em lugar fixo do layout.
- **NÃO** colocar lógica de página dentro de `renderizar_topbar`. Topbar é dumb sink que só lê session_state.

## 5. Validação visual humana

```bash
# Dashboard ao vivo + abrir 3 telas e ver topbar:
# - http://127.0.0.1:8765/                                       (Visão Geral, slot vazio até T-01)
# - http://127.0.0.1:8765/?cluster=Finan%C3%A7as&tab=Extrato     (Extrato, slot vazio até T-02)
# - http://127.0.0.1:8765/?cluster=Documentos&tab=Revisor        (Revisor, slot vazio até T-09)
```

Esta sprint **não preenche** os botões. Ela só cria o slot. As Onda T preenchem.

## 6. Gauntlet

```bash
make lint                                                  # exit 0
make smoke                                                 # 10/10
.venv/bin/pytest tests/test_topbar_canonica.py -v          # 4/4
.venv/bin/pytest tests/ -q --tb=no --no-header             # baseline mantida
```

---

*"Aja como o vento e seja como o tempo." -- Sun Tzu (paráfrase)*
