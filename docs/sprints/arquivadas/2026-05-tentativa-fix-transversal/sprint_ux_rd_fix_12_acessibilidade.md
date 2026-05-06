---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-12
  title: "Acessibilidade: skip links + role=tablist + aria-current + foco visível"
  prioridade: P1
  estimativa: 4h
  onda: C5
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §8.5 (UX patterns parcial em ARIA, skip links ausentes)"
  depende_de: []
  bloqueia: []
  touches:
    - path: pyproject.toml
      reason: "ADICIONAR axe-playwright-python como dep opcional [test]. Confirmação: hoje pyproject.toml NÃO tem essa dependência (validado 2026-05-05)."
    - path: src/dashboard/componentes/shell.py
      reason: "adicionar <a href='#main-root' class='skip-link sr-only-focusable'>Pular para conteúdo principal</a> no topo da renderizar_sidebar; aria-current='page' no .sidebar-item.active; role='tablist' nas tabs (já presente em st.tabs nativo, mas garantir custom)"
    - path: src/dashboard/tema_css.py
      reason: "estilos .skip-link (sr-only por default; visible on focus) + .sr-only-focusable; foco visível em links e botões"
    - path: tests/test_acessibilidade.py
      reason: "NOVO -- 8 testes axe-core via playwright: 0 violações WCAG 2.1 AA em 4 telas-amostra; skip-link presente; aria-current em sidebar"
  forbidden:
    - "Adicionar role conflitante (ex.: role=button em <a>)"
    - "Esconder visualmente o skip-link de leitores de tela quando focado"
  hipotese:
    - "Auditoria mostrou aria-label em 4 pontos do shell.py mas faltam: skip links, aria-current, role=tablist explícito em tabs custom. Streamlit st.tabs já renderiza role=tablist; foco visível tem :focus-visible com box-shadow duplo (já em tokens)."
  tests:
    - cmd: ".venv/bin/pytest tests/test_acessibilidade.py -v"
      esperado: "8/8 PASSED"
    - cmd: ".venv/bin/python -m pip show axe-playwright-python"
      esperado: "package instalado"
  acceptance_criteria:
    - "DOM da home tem `<a class='skip-link' href='#main-root'>Pular para conteúdo principal</a>` como primeiro filho do <body>"
    - "Skip-link é invisible por default mas visível ao focar (Tab pelo teclado)"
    - "Sidebar item ativo tem aria-current='page'"
    - "Streamlit tabs (role=tablist) intactos -- não quebrar"
    - "Em 4 telas-amostra (Visão Geral, Revisor, Inbox, Bem-estar/Hoje), axe-core retorna 0 violations de severidade 'critical' ou 'serious'"
    - "Foco com Tab navega ordem: skip-link -> sidebar -> busca -> topbar -> main"
    - ":focus-visible mostra anel duplo accent-purple em links e botões interativos"
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8532 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        page.goto('http://127.0.0.1:8532/?cluster=Home&tab=Vis%C3%A3o%20Geral')
        page.wait_for_timeout(4000)
        # 1. skip link existe
        info = page.evaluate('''() => {
            const skip = document.querySelector('.skip-link, a[href=\"#main-root\"]');
            const aria_current = document.querySelectorAll('[aria-current=\"page\"]').length;
            const tablists = document.querySelectorAll('[role=\"tablist\"]').length;
            return { skip_existe: !!skip, skip_text: skip?.textContent.trim(), aria_current_count: aria_current, tablists };
        }''')
        print('a11y:', info)
        assert info['skip_existe'], 'skip-link ausente'
        assert info['aria_current_count'] >= 1, 'aria-current ausente'
        assert info['tablists'] >= 1, 'role=tablist ausente'
        # 2. tab pelo teclado: primeiro foco vai ao skip-link
        page.keyboard.press('Tab')
        focado = page.evaluate('document.activeElement?.className || document.activeElement?.tagName')
        print(f'primeiro foco: {focado}')   # esperado: contém skip-link ou A
        b.close()
    "
```

---

# Sprint UX-RD-FIX-12 — Acessibilidade WCAG 2.1 AA

**Status:** BACKLOG — Onda C5 (acabamento).

## 1. Contexto

Auditoria 2026-05-05 §8.5 indicou que o dashboard tem ARIA parcial (4 pontos com `aria-label` em `shell.py`), mas faltam:

- **Skip link** ("Pular para conteúdo principal") -- requisito WCAG 2.4.1 Bypass Blocks.
- **aria-current="page"** no sidebar item da página atual -- WCAG 1.3.1 Info and Relationships.
- **role="tablist"** explícito (Streamlit st.tabs já provê, mas custom HTML pode quebrar).
- **Foco visível** consistente -- WCAG 2.4.7 Focus Visible.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) baseline -- skip link ausente
grep -nE 'skip-link|sr-only|#main-root' src/dashboard/ -r

# 2) baseline -- aria-current ausente
grep -nE 'aria-current' src/dashboard/ -r

# 3) instalar axe-playwright e ADICIONAR ao pyproject.toml [test]
.venv/bin/pip show axe-playwright-python || .venv/bin/pip install axe-playwright-python
# Editar pyproject.toml seção [project.optional-dependencies] adicionando bloco:
#     test = [
#         "pytest>=7",
#         "axe-playwright-python>=0.1",
#     ]
# (verificar primeiro se a seção [test] já existe; merge se sim)
```

## 3. Tarefas

1. Rodar hipótese.
2. Em `src/dashboard/componentes/shell.py`, adicionar no início de `renderizar_sidebar()` (ou no chamador, antes da sidebar):
   ```python
   skip_html = '<a class="skip-link sr-only-focusable" href="#main-root">Pular para conteúdo principal</a>'
   # adicionar como primeiro elemento do main HTML emitido
   ```
3. Em `src/dashboard/app.py`, adicionar âncora `<div id="main-root">` no início do main:
   ```python
   st.markdown('<div id="main-root" tabindex="-1"></div>', unsafe_allow_html=True)
   ```
4. Em `_renderizar_sidebar_clusters_html()` ou similar, marcar item ativo com `aria-current="page"`:
   ```python
   classe = "sidebar-item active" if seg == aba_ativa else "sidebar-item"
   aria = ' aria-current="page"' if seg == aba_ativa else ""
   linha = f'<a class="{classe}"{aria} href="?cluster={cluster}&tab={seg}">{seg}</a>'
   ```
5. Em `src/dashboard/tema_css.py`, adicionar:
   ```css
   /* FIX-12: skip-link + sr-only */
   .sr-only, .sr-only-focusable:not(:focus):not(:focus-within) {
       position: absolute !important;
       width: 1px; height: 1px; padding: 0; margin: -1px;
       overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
   }
   .skip-link:focus {
       position: fixed; top: 8px; left: 8px;
       background: var(--accent-purple); color: var(--text-inverse);
       padding: 8px 16px; border-radius: var(--r-sm);
       z-index: 99999; text-decoration: none;
       font-family: var(--ff-mono); font-size: var(--fs-12);
       text-transform: uppercase;
   }
   ```
6. Garantir `:focus-visible` aplicado:
   ```css
   :focus-visible { outline: none; box-shadow: var(--sh-focus); border-radius: var(--r-sm); }
   /* sh-focus já definido em tokens: 0 0 0 2px var(--bg-base), 0 0 0 4px var(--accent-purple) */
   ```
7. Criar `tests/test_acessibilidade.py`:
   ```python
   import subprocess, time
   import pytest
   from playwright.sync_api import sync_playwright

   STREAMLIT_PORT = 8532

   @pytest.fixture(scope="module")
   def dashboard():
       p = subprocess.Popen([".venv/bin/streamlit","run","src/dashboard/app.py","--server.port",str(STREAMLIT_PORT),"--server.headless","true"])
       time.sleep(7)
       yield f"http://127.0.0.1:{STREAMLIT_PORT}"
       p.terminate(); p.wait()

   def test_skip_link_existe(dashboard):
       with sync_playwright() as p:
           b = p.chromium.launch()
           page = b.new_context().new_page()
           page.goto(dashboard); page.wait_for_timeout(4000)
           assert page.locator('.skip-link, a[href="#main-root"]').count() >= 1
           b.close()

   def test_aria_current_em_sidebar_ativo(dashboard):
       with sync_playwright() as p:
           b = p.chromium.launch()
           page = b.new_context().new_page()
           page.goto(dashboard + "/?cluster=Documentos&tab=Revisor"); page.wait_for_timeout(4000)
           assert page.locator('[aria-current="page"]').count() >= 1
           b.close()

   def test_role_tablist_presente(dashboard):
       with sync_playwright() as p:
           b = p.chromium.launch()
           page = b.new_context().new_page()
           page.goto(dashboard); page.wait_for_timeout(4000)
           assert page.locator('[role="tablist"]').count() >= 1
           b.close()

   # ... + 5 testes axe-core em 4 telas
   ```
8. (Opcional) Rodar `axe-playwright-python` para violations report:
   ```python
   from axe_playwright_python.sync_playwright import Axe
   axe = Axe()
   results = axe.run(page)
   violations = [v for v in results.violations if v["impact"] in ("critical","serious")]
   assert not violations, f"violations WCAG: {violations}"
   ```
9. Rodar gauntlet (§6).

## 4. Anti-débito

- Streamlit pode renderizar elementos com IDs duplicados (vários h1, vários main-root). Garantir que só um `#main-root` exista no DOM.
- Se Streamlit `st.tabs` quebrar com role=tablist conflitante: confiar no que Streamlit emite e não duplicar.

## 5. Validação visual

```bash
# focar via teclado e capturar
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context().new_page()
    page.goto('http://127.0.0.1:8532/'); page.wait_for_timeout(4000)
    page.keyboard.press('Tab')   # foco no skip-link
    page.wait_for_timeout(300)
    page.screenshot(path='.playwright-mcp/auditoria/fix-12/skip_link_visible_on_focus.png', full_page=False)
    b.close()
"
```

## 6. Gauntlet

```bash
make lint                                              # exit 0
make smoke                                             # 10/10
.venv/bin/pytest tests/test_acessibilidade.py -v       # 8/8
.venv/bin/pytest tests/ -q --tb=no                     # baseline >=2520
```

---

*"O acesso é o primeiro direito; sem ele, todos os outros são promessa." -- adaptado de Hannah Arendt*
