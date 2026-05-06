---
concluida_em: 2026-05-06
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-U-01
  title: "Sidebar canônica: 8 clusters scroll, brand glyph, sem widgets antigos"
  prioridade: P0
  estimativa: 1 dia
  onda: U
  mockup_fonte: novo-mockup/mockups/00-shell-navegacao.html (bloco sidebar)
  depende_de: []
  bloqueia: [UX-U-04, UX-T-01..UX-T-29]
  touches:
    - path: src/dashboard/componentes/shell.py
      reason: "renderizar_sidebar() já existe e está OK estruturalmente. Garantir wrapper aside.sidebar com overflow-y:auto e height/max-height adequados."
    - path: src/dashboard/tema_css.py
      reason: "Ajustar regra .sidebar com overflow-y:auto, height:100vh, max-height:100vh. Adicionar regras para forçar Streamlit data-testid stSidebar a respeitar scroll interno."
    - path: src/dashboard/app.py
      reason: "linha 206-364 _sidebar() está injetando widgets antigos (logo escudo, caption Dados de, selectbox Granularidade/Mês/Pessoa/Forma de pagamento, text_input Busca Global) DEPOIS do shell HTML novo. Esta sprint NÃO remove esses widgets ainda (FIX-U-04 fará). Esta sprint apenas garante que o shell HTML renderiza corretamente com scroll. Os widgets continuam aparecendo abaixo, mas a U-04 elimina."
    - path: tests/test_sidebar_canonica.py
      reason: "NOVO -- testes playwright validando 8 clusters totalmente visíveis ao rolar dentro da sidebar; brand glyph SVG presente; busca placeholder com kbd /; badges no INBOX."
  forbidden:
    - "Mexer nos widgets Streamlit que aparecem abaixo do shell (selectbox/text_input). FIX-U-04 cuida disso."
    - "Mudar layout dos itens (sidebar-item, sidebar-cluster-header já estão canônicos pelo mockup)."
    - "Quebrar deep-link (?cluster=X&tab=Y) -- todos os hrefs já estão corretos."
  hipotese:
    - "Hoje a sidebar tem altura efetiva limitada e cluster Sistema/Bem-estar/Metas/Análise não aparecem em viewport 1440x900. Causa: container Streamlit data-testid stSidebar tem height fixa sem scroll interno OR shell HTML novo + widgets antigos somam mais altura que o container suporta."
  tests:
    - cmd: ".venv/bin/pytest tests/test_sidebar_canonica.py -v"
      esperado: "5+ PASSED (8 clusters visíveis, brand glyph, busca placeholder, badges, scroll funcional)"
    - cmd: "make smoke"
      esperado: "10/10"
    - cmd: ".venv/bin/pytest tests/ -q --tb=no"
      esperado: "baseline mantida"
  acceptance_criteria:
    - "Em viewport 1440x900, ao rolar dentro do data-testid stSidebar, todos os 8 clusters (Inbox, Home, Finanças, Documentos, Análise, Metas, Bem-estar, Sistema) ficam acessíveis."
    - "Brand topo da sidebar é SVG glyph ouroboros (componentes/glyphs.py:'ouroboros'), não letra 'O'."
    - "Busca placeholder na sidebar tem ícone search à esquerda + texto 'Buscar fornecedor, sha8, ou valor' + kbd '/' à direita."
    - "Cluster Inbox tem badge numérico (.count) com quantidade de arquivos pendentes."
    - "Cada cluster header é mono UPPERCASE 11px ls 0.10em color text-muted (canônico components.css:.sidebar-cluster-header)."
    - "Cada sidebar-item (aba dentro de cluster) é Inter sans 13px color text-secondary, com border-left 2px transparent (active = accent-purple + gradient bg)."
    - "Sidebar tem overflow-y: auto -- ao rolar, conteúdo da página NÃO se mexe."
    - "Validação humana: dono inspeciona ao vivo http://localhost:8765/ e confirma que os 8 clusters estão acessíveis sem que widgets antigos atrapalhem (mesmo que ainda existam abaixo até FIX-U-04)."
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.headless=true --server.port=8765 > /tmp/streamlit_u01.log 2>&1 &
    sleep 8
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
        page.goto('http://127.0.0.1:8765/'); page.wait_for_timeout(5000)
        info = page.evaluate('''() => {
            const sb = document.querySelector('[data-testid=\"stSidebar\"]');
            const cls_headers = sb?.querySelectorAll('.sidebar-cluster-header');
            const overflow = sb ? getComputedStyle(sb).overflowY : null;
            const brand_svg = !!sb?.querySelector('.sidebar-brand svg');
            const kbd_busca = !!sb?.querySelector('.sidebar-search kbd');
            return {
                cluster_headers: cls_headers?.length || 0,
                cluster_names: Array.from(cls_headers || []).map(h => h.textContent.trim()),
                overflow_y: overflow,
                brand_svg,
                kbd_busca,
                sb_height: sb?.scrollHeight,
                sb_visible_height: sb?.clientHeight
            };
        }''')
        print(info)
        # contratos
        assert info['cluster_headers'] == 8, f'esperado 8 cluster headers, achou {info[\"cluster_headers\"]}'
        assert info['overflow_y'] in ('auto', 'scroll'), f'sidebar deve ter scroll interno; tem {info[\"overflow_y\"]}'
        assert info['brand_svg'], 'brand deve ser SVG (FIX-07 portou o glyph)'
        assert info['kbd_busca'], 'busca deve ter kbd /'
        print('OK contratos U-01')
        page.screenshot(path='docs/auditorias/redesign-2026-05-06/U-01_dashboard_sidebar.png', clip={'x':0,'y':0,'width':260,'height':900})
        b.close()
    "
    # comparar com mockup
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
        page.goto('http://127.0.0.1:8766/mockups/00-shell-navegacao.html'); page.wait_for_timeout(800)
        page.screenshot(path='docs/auditorias/redesign-2026-05-06/U-01_mockup_sidebar.png', clip={'x':0,'y':0,'width':260,'height':900})
        b.close()
    "
    # PNG comparativo: docs/auditorias/redesign-2026-05-06/U-01_dashboard_sidebar.png vs U-01_mockup_sidebar.png
```

---

# Sprint UX-U-01 — Sidebar canônica

**Status:** BACKLOG — Onda U (estruturante).

## 1. Contexto

A sidebar atual tem dois shells concorrentes:

- **Shell HTML novo** (renderizar_sidebar em componentes/shell.py): 8 clusters listados como links, brand glyph SVG ouroboros, busca placeholder com kbd `/`, badges. Funcionalmente correto, mas o container Streamlit data-testid="stSidebar" não está com scroll interno, então os clusters do final (Sistema, Bem-estar) ficam cortados em viewports menores.
- **Widgets antigos** (em app.py:243-364): logo escudo PNG, caption "Dados de DD/MM — HH:MM", text_input "Busca Global", selectbox "Granularidade", "Mês", "Pessoa", "Forma de pagamento". Estes vão SAIR na FIX-U-04, mas hoje somam ~600px de altura na sidebar, empurrando os clusters do final fora do viewport.

Esta sprint **não remove** os widgets antigos (FIX-U-04 cuida). Esta sprint **garante que o shell HTML novo renderiza com scroll interno**, de modo que ao rolar dentro da sidebar (não a página inteira) os 8 clusters fiquem todos acessíveis. Quando a U-04 remover os widgets antigos, a sidebar fica limpa; até lá, o scroll evita o pior do desconforto visual.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1. confirma que data-testid stSidebar não tem overflow-y:auto hoje
nohup .venv/bin/streamlit run src/dashboard/app.py --server.headless=true --server.port=8765 > /tmp/u01_before.log 2>&1 &
sleep 8
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
    page.goto('http://127.0.0.1:8765/'); page.wait_for_timeout(5000)
    info = page.evaluate('''() => {
        const sb = document.querySelector('[data-testid=\"stSidebar\"]');
        const aside = sb?.querySelector('aside.sidebar.ouroboros-sidebar-redesign');
        return {
            sb_overflow: sb ? getComputedStyle(sb).overflowY : null,
            aside_overflow: aside ? getComputedStyle(aside).overflowY : null,
            sb_height: sb?.clientHeight,
            sb_scroll_height: sb?.scrollHeight,
            cluster_count: sb?.querySelectorAll('.sidebar-cluster-header').length,
            cluster_names: Array.from(sb?.querySelectorAll('.sidebar-cluster-header') || []).map(c => c.textContent.trim())
        };
    }''')
    print(info)
"
pkill -f 'streamlit.*8765'

# 2. confirma que mockup tem 8 clusters (referência canônica)
grep -cE 'class=.sidebar-cluster.' novo-mockup/mockups/00-shell-navegacao.html
# Esperado: 8 (Inbox, Home, Finanças, Documentos, Análise, Metas, Bem-estar, Sistema)
```

Se `cluster_count != 8` ou `sb_overflow != 'auto'/'scroll'`, hipótese confirmada.

## 3. Tarefas

1. Rodar hipótese ANTES e confirmar.
2. Em `src/dashboard/tema_css.py`, adicionar regra (após o bloco @import) ou ajustar regra existente:

   ```css
   /* UX-U-01: Sidebar canônica com scroll interno e altura cheia */
   [data-testid="stSidebar"] {
       overflow-y: auto !important;
       height: 100vh !important;
       max-height: 100vh !important;
   }
   [data-testid="stSidebar"] aside.sidebar.ouroboros-sidebar-redesign {
       /* O wrapper interno precisa permitir o scroll do parent */
       min-height: auto;
       overflow: visible;
   }
   /* Scrollbar discreta (já existe no mockup tokens.css linhas 134-137) */
   [data-testid="stSidebar"]::-webkit-scrollbar { width: 8px; }
   [data-testid="stSidebar"]::-webkit-scrollbar-track { background: var(--bg-base); }
   [data-testid="stSidebar"]::-webkit-scrollbar-thumb {
       background: var(--border-subtle);
       border-radius: var(--r-sm);
   }
   [data-testid="stSidebar"]::-webkit-scrollbar-thumb:hover {
       background: var(--border-strong);
   }
   ```

3. Validar via playwright que `getComputedStyle(stSidebar).overflowY === 'auto'`.
4. Capturar PNG da sidebar em viewport 1440x900 antes/depois (clip x=0 y=0 w=260 h=900).
5. Criar `tests/test_sidebar_canonica.py`:

   ```python
   import subprocess, time
   import pytest
   from playwright.sync_api import sync_playwright

   PORT = 8770

   @pytest.fixture(scope="module")
   def streamlit_url():
       p = subprocess.Popen([".venv/bin/streamlit","run","src/dashboard/app.py","--server.port",str(PORT),"--server.headless","true"])
       time.sleep(8)
       yield f"http://127.0.0.1:{PORT}"
       p.terminate(); p.wait()

   def test_sidebar_tem_8_clusters(streamlit_url):
       with sync_playwright() as p:
           b = p.chromium.launch(); page = b.new_context(viewport={"width":1440,"height":900}).new_page()
           page.goto(streamlit_url); page.wait_for_timeout(5000)
           clusters = page.eval_on_selector_all('[data-testid="stSidebar"] .sidebar-cluster-header', "els => els.map(e => e.textContent.trim())")
           esperados = ["Inbox","Home","Finanças","Documentos","Análise","Metas","Bem-estar","Sistema"]
           for esp in esperados:
               assert any(esp.lower() in c.lower() for c in clusters), f'cluster {esp} ausente; achei {clusters}'
           b.close()

   def test_sidebar_tem_scroll_interno(streamlit_url):
       with sync_playwright() as p:
           b = p.chromium.launch(); page = b.new_context(viewport={"width":1440,"height":900}).new_page()
           page.goto(streamlit_url); page.wait_for_timeout(5000)
           overflow = page.evaluate("getComputedStyle(document.querySelector('[data-testid=\"stSidebar\"]')).overflowY")
           assert overflow in ("auto", "scroll"), f'esperado overflow-y auto/scroll, tem {overflow}'
           b.close()

   def test_sidebar_brand_eh_svg_ouroboros(streamlit_url):
       with sync_playwright() as p:
           b = p.chromium.launch(); page = b.new_context().new_page()
           page.goto(streamlit_url); page.wait_for_timeout(5000)
           has_svg = page.evaluate("!!document.querySelector('[data-testid=\"stSidebar\"] .sidebar-brand svg')")
           assert has_svg, "brand glyph SVG ausente; aplicar componentes/glyphs.py:glyph('ouroboros')"
           b.close()

   def test_sidebar_busca_tem_kbd(streamlit_url):
       with sync_playwright() as p:
           b = p.chromium.launch(); page = b.new_context().new_page()
           page.goto(streamlit_url); page.wait_for_timeout(5000)
           kbd_text = page.evaluate("document.querySelector('[data-testid=\"stSidebar\"] .sidebar-search kbd')?.textContent")
           assert kbd_text and kbd_text.strip() == "/", f'kbd da busca deve mostrar /; achei {kbd_text!r}'
           b.close()

   def test_sidebar_inbox_tem_badge(streamlit_url):
       with sync_playwright() as p:
           b = p.chromium.launch(); page = b.new_context().new_page()
           page.goto(streamlit_url); page.wait_for_timeout(5000)
           badge = page.evaluate("document.querySelector('[data-testid=\"stSidebar\"] .sidebar-cluster:first-child .badge')?.textContent")
           # Badge pode ser número ou ... ; só validar que existe
           assert badge is not None, "Inbox cluster deve ter badge .count"
           b.close()
   ```

6. Rodar gauntlet (§7).
7. Capturar PNG side-by-side em `docs/auditorias/redesign-2026-05-06/U-01_*.png`.
8. **Pausar** e pedir validação humana antes de mover spec para `concluidos/`.

## 4. Anti-débito

- Se overflow-y:auto não funcionar (Streamlit pode ter regra mais específica que sobrescreve): aumentar specificidade com seletor mais aninhado ou !important. Limite: 3 iterações; depois disso, criar UX-U-01.B com solução alternativa.
- Se badge do Inbox aparece com `...` em vez de número: backend de contagem não está implementado. Aceitar `...` por agora; criar sprint-filha **UX-U-01.C** para popular contador real.
- **NÃO** mexer nos widgets antigos (selectbox/text_input/logo escudo) -- FIX-U-04 cuida disso.

## 5. Validação visual humana

```bash
# 1. dashboard ao vivo
nohup .venv/bin/streamlit run src/dashboard/app.py --server.headless=true --server.port=8765 &
sleep 8

# 2. mockup ao vivo
nohup python3 -m http.server 8766 --bind 127.0.0.1 --directory novo-mockup &
sleep 2

# 3. dono abre 2 abas no navegador:
#    - http://127.0.0.1:8765/             (dashboard)
#    - http://127.0.0.1:8766/mockups/00-shell-navegacao.html  (mockup)
#    e compara as sidebars lado a lado.
```

Critério visual: ao rolar dentro do dashboard, os 8 clusters aparecem; brand é SVG ouroboros (não letra "O"); busca tem kbd `/`; inbox tem badge.

## 6. Gauntlet

```bash
make lint                                              # exit 0
make smoke                                             # 10/10
.venv/bin/pytest tests/test_sidebar_canonica.py -v     # 5/5
.venv/bin/pytest tests/ -q --no-header --tb=no         # baseline >=2530
```

---

*"Toda casa precisa de uma porta antes das janelas." -- adaptado de Lao-Tsé*
