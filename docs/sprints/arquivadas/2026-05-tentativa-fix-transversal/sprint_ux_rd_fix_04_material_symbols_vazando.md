---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-04
  title: "Suprimir vazamento 'keyboard_double_arrow_left' como texto bruto em botões"
  prioridade: P0
  estimativa: 2h
  onda: C1
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §7.11 e §8.9 (top problema #4)"
  depende_de: []
  bloqueia: []
  touches:
    - path: src/dashboard/tema_css.py
      reason: "adicionar regra font-family específica para [data-testid='stIconMaterial'] e ícones Streamlit, com !important para vencer a cascata global"
    - path: tests/test_material_symbols.py
      reason: "NOVO -- testa que regra CSS gerada contém font-family Material Symbols Outlined em seletor stIcon"
  forbidden:
    - "Remover suporte a ícones Streamlit (apenas reservar font-family correta para eles)"
    - "Adicionar !important em regras de font-family fora dos seletores específicos de ícone"
  hipotese:
    - "Auditoria mediu 92 botões com texto 'keyboard_double_arrow_left' na Revisor; isso ocorre porque a fonte 'monospace' aplicada em .streamlit/config.toml + var(--ff-mono) sobrescreve a font-family 'Material Symbols Outlined' que Streamlit usa internamente."
  tests:
    - cmd: "grep -nE 'stIconMaterial|material-symbols' src/dashboard/tema_css.py"
      esperado: "regra font-family explícita para Material Symbols Outlined com !important"
    - cmd: ".venv/bin/pytest tests/test_material_symbols.py -v"
      esperado: "PASSED"
  acceptance_criteria:
    - "Ao acessar ?cluster=Documentos&tab=Revisor, ZERO botões com textContent matching '^[a-z_]+$' que contenha 'arrow' ou 'keyboard' ou 'chevron' ou 'expand_more'"
    - "Ícones Streamlit (Material Symbols) renderizam corretamente como glifos visuais (caracteres Unicode privados E000+)"
    - "Sem regressão em outros componentes Streamlit (selectbox, expander, dataframe sort arrows)"
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8522 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
        page.goto('http://127.0.0.1:8522/?cluster=Documentos&tab=Revisor')
        page.wait_for_timeout(5000)
        n_vazados = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('button')).filter(b => {
                const t = (b.textContent || '').trim();
                return /^[a-z_]+$/.test(t) && (t.includes('arrow') || t.includes('keyboard') || t.includes('chevron') || t.includes('expand'));
            }).length;
        }''')
        print(f'BOTOES com texto Material vazado: {n_vazados}')   # esperado: 0
        page.screenshot(path='.playwright-mcp/auditoria/fix-04/revisor_sem_vazamento.png', full_page=True)
        b.close()
    "
```

---

# Sprint UX-RD-FIX-04 — Material Symbols vazando como texto

**Status:** BACKLOG — Onda C1 (higiene crítica).

## 1. Contexto

A auditoria identificou que **92 botões na tela Revisor** expõem o nome do ícone Material Symbols como texto bruto (`"keyboard_double_arrow_left"`, `"keyboard_arrow_down"`, `"expand_more"`).

**Causa-raiz**:

1. `.streamlit/config.toml` declara `font = "monospace"` no `[theme]`. Isso faz Streamlit aplicar `font-family: "Source Code Pro", monospace` em **todos** elementos.
2. `tema_css.py` injeta tokens `--ff-mono: 'JetBrains Mono'` mas só usa em seletores específicos (`.kpi-value`, `.breadcrumb`, etc.), não no body global.
3. **Streamlit usa Material Symbols Outlined como font ligature** para renderizar ícones (`<button data-testid="stIconMaterial">keyboard_double_arrow_left</button>`). Quando a font global é sobrescrita por `monospace`, o ligature não funciona e o nome literal vaza.

**Solução**: regra CSS específica forçando `font-family: 'Material Symbols Outlined' !important` em todos seletores Streamlit que usam ícones por ligature.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) confirma 92+ vazamentos hoje
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8522 --server.headless true &
sleep 6
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context().new_page()
    page.goto('http://127.0.0.1:8522/?cluster=Documentos&tab=Revisor')
    page.wait_for_timeout(5000)
    n = page.evaluate('Array.from(document.querySelectorAll(\"button\")).filter(b => /^[a-z_]+$/.test(b.textContent.trim()) && b.textContent.includes(\"arrow\")).length')
    print(f'baseline botoes com vazamento: {n}')   # esperado: 92
    b.close()
"
pkill -f 'streamlit.*8522'

# 2) confirma config.toml causa
grep '^font' .streamlit/config.toml
# esperado: 'font = "monospace"'

# 3) confirma sem regra Material Symbols
grep -nE 'Material Symbols|stIconMaterial' src/dashboard/tema_css.py
# esperado: zero ocorrências
```

## 3. Tarefas

1. Rodar hipótese (§2). Confirmar 92+ vazamentos.
2. **Não mudar** `.streamlit/config.toml` (responsabilidade de FIX-08).
3. Adicionar em `src/dashboard/tema_css.py` (em `_classes_redesign()` ou seção de overrides Streamlit) uma regra:

   ```python
   /* FIX-04: forçar Material Symbols Outlined em ícones Streamlit
      para evitar vazamento de texto cru ('keyboard_double_arrow_left')
      quando font-family global é sobrescrita por config.toml font="monospace". */
   [data-testid="stIconMaterial"],
   span[class*="material-symbols"],
   .stMaterialIcon {{
       font-family: 'Material Symbols Outlined' !important;
       font-weight: normal !important;
       font-style: normal !important;
       font-size: 24px;
       line-height: 1;
       letter-spacing: normal;
       text-transform: none;
       display: inline-block;
       white-space: nowrap;
       word-wrap: normal;
       direction: ltr;
       -webkit-font-feature-settings: 'liga';
       -webkit-font-smoothing: antialiased;
   }}
   ```
4. Garantir que `Material Symbols Outlined` está importada (Streamlit já carrega via `<link rel="stylesheet">`; se não, adicionar `@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined')` no topo da string CSS).
5. Criar `tests/test_material_symbols.py`:
   ```python
   def test_tema_css_inclui_material_symbols_outlined():
       from src.dashboard.tema_css import css_global
       css = css_global()
       assert "Material Symbols Outlined" in css
       assert "stIconMaterial" in css

   def test_regra_material_tem_important():
       from src.dashboard.tema_css import css_global
       import re
       css = css_global()
       trecho = re.search(r"stIconMaterial[^}]+", css)
       assert trecho and "!important" in trecho.group(0)
   ```
6. Rodar gauntlet (§6) com playwright validando 0 vazamentos.

## 4. Anti-débito

- Se mesmo após adicionar a regra ainda vazar texto: **NÃO** debugar em loop. Inspecionar elemento real no DevTools, identificar o seletor que precisa override (pode ser específico Streamlit), criar **sprint UX-RD-FIX-04.B** com novo seletor.
- Se Streamlit não carregar Material Symbols sozinho: adicionar `@import` em `tema_css.py:_carregar_fontes_externas()`. Mas confirmar primeiro via DevTools.

## 5. Validação visual

PNG antes/depois da tela Revisor mostrando que botões de paginação não exibem mais `keyboard_double_arrow_left`. Os ícones devem aparecer como glifos visuais (setas pequenas).

## 6. Gauntlet

```bash
make lint                                                  # exit 0
make smoke                                                 # 10/10
.venv/bin/pytest tests/test_material_symbols.py -v         # 2/2 PASSED
.venv/bin/pytest tests/ -q --tb=no                         # baseline >=2522
# captura proof-of-work playwright (§0 acceptance)
```

---

*"A forma é o limite -- mas dentro dela cabe o nome certo das coisas." -- adaptado de Wittgenstein*
