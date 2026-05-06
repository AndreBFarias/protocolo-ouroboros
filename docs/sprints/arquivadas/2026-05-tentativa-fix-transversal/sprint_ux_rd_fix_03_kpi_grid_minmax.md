---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-03
  title: "Reduzir minmax do .kpi-grid de 220px para 180px (mockup canônico)"
  prioridade: P1
  estimativa: 30min
  onda: C1
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §8.2 (única DIVERGENCE em 39 classes auditadas)"
  depende_de: []
  bloqueia: []
  touches:
    - path: src/dashboard/tema_css.py
      reason: "linha 1158: 'minmax(220px, 1fr)' -> 'minmax(180px, 1fr)' alinhado com novo-mockup/_shared/components.css:241"
    - path: tests/test_tema_css.py
      reason: "NOVO ou aditivo: testar que tema_css.py contém literal 'minmax(180px, 1fr)' e não 'minmax(220px, 1fr)'"
  forbidden:
    - "Mudar outras propriedades do .kpi-grid (gap, display, width)"
    - "Trocar a unidade de minmax (manter px)"
  hipotese:
    - "tema_css.py:1158 usa minmax(220px, 1fr); mockup pede minmax(180px, 1fr); diff visual: KPI cards 40px mais largos no dashboard"
  tests:
    - cmd: "grep -n 'minmax(180px, 1fr)' src/dashboard/tema_css.py"
      esperado: "linha 1158 mostra 'minmax(180px, 1fr)'"
    - cmd: "grep -c 'minmax(220px, 1fr)' src/dashboard/tema_css.py"
      esperado: "0"
    - cmd: ".venv/bin/pytest tests/test_tema_css.py -v -k minmax"
      esperado: "PASSED"
  acceptance_criteria:
    - "tema_css.py contém exatamente 1 ocorrência de 'minmax(180px, 1fr)' associada ao .kpi-grid"
    - "Zero ocorrência de 'minmax(220px, 1fr)' em src/dashboard/tema_css.py"
    - "Em viewport 1440x900, .kpi-grid renderiza 4 cards quando há 4 KPIs (mockup); 6 cards quando há 6 (mockup tela 13)"
  proof_of_work_esperado: |
    grep -n 'minmax(180px\|minmax(220px' src/dashboard/tema_css.py
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8521 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
        page.goto('http://127.0.0.1:8521/?cluster=Documentos&tab=Revisor')
        page.wait_for_timeout(4000)
        info = page.evaluate('''() => {
            const grid = document.querySelector('.kpi-grid');
            if (!grid) return null;
            return {
                grid_template_columns: getComputedStyle(grid).gridTemplateColumns,
                width: Math.round(grid.getBoundingClientRect().width),
                children_count: grid.children.length,
                child_widths: Array.from(grid.children).map(c => Math.round(c.getBoundingClientRect().width))
            };
        }''')
        print('kpi-grid:', info)
        b.close()
    "
```

---

# Sprint UX-RD-FIX-03 — KPI grid minmax 220→180

**Status:** BACKLOG — Onda C1 (higiene crítica).

## 1. Contexto

Auditoria de componentes (agente 8a) identificou **única divergência** em 39 classes do mockup mapeadas para `tema_css.py`: a regra `.kpi-grid` em `tema_css.py:1156-1161`:

```css
/* Dashboard atual */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: ...;
    width: 100%;
}
```

Mockup canônico em `novo-mockup/_shared/components.css:241`:

```css
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--sp-3); }
```

Diferença: dashboard usa **220px** mínimo, mockup usa **180px**. Resultado: KPI cards renderizam 40px mais largos -- e em viewports apertados o número de cards por linha cai (4 cards no mockup, 3 no dashboard).

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) confirma estado atual
grep -n 'minmax(220px\|minmax(180px' src/dashboard/tema_css.py
# esperado: linha 1158 com '220px'; zero ocorrência de '180px'

# 2) confirma mockup
grep -n 'minmax(180px\|minmax(220px' novo-mockup/_shared/components.css
# esperado: linha 241 com '180px'; zero '220px'
```

## 3. Tarefas

1. Rodar hipótese (§2).
2. `Edit` em `src/dashboard/tema_css.py` linha 1158: trocar `minmax(220px, 1fr)` por `minmax(180px, 1fr)`. Usar contexto suficiente para unicidade.
3. Confirmar com novo grep que só há `minmax(180px, 1fr)` no arquivo.
4. Atualizar `tests/test_tema_css.py` (criar se ausente) com 2 asserts:
   ```python
   def test_kpi_grid_usa_minmax_180px():
       css = abrir_tema_css()
       assert 'minmax(180px, 1fr)' in css
       assert 'minmax(220px, 1fr)' not in css
   ```
5. Rodar gauntlet (§7).
6. Capturar PNG comparativo (mockup vs dashboard) no proof-of-work.

## 4. Anti-débito

Se aparecer outra ocorrência de `minmax(.*px, 1fr)` em outro arquivo CSS do dashboard divergindo do mockup: registrar em sprint **UX-RD-FIX-03.B** como achado colateral. Não corrigir aqui.

## 5. Validação visual

PNG antes/depois em viewport 1440×900 da tela Revisor (que tem 4 KPIs):

- **Antes (220px)**: cards renderizam ~280px de largura cada, 3 por linha em alguns casos.
- **Depois (180px)**: cards renderizam ~280px (auto-fit dá igual com 4 cards e gap), mas em viewports estreitos (>= 768px) caem para 4 cards por linha como o mockup.

## 6. Gauntlet

```bash
make lint                                                     # exit 0
make smoke                                                    # 10/10
.venv/bin/pytest tests/test_tema_css.py -v -k minmax          # PASSED
.venv/bin/pytest tests/ -q --tb=no                            # baseline >=2520
git diff src/dashboard/tema_css.py                            # 1 linha alterada
```

---

*"A diferença entre o quase certo e o certo é como a entre o vaga-lume e o relâmpago." -- Mark Twain*
