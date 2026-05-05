---
concluida_em: 2026-05-04
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-02
  title: "Reescrever tema_css.py sobre _shared/tokens.css + _shared/components.css dos mockups"
  prioridade: P0
  estimativa: 3h
  onda: 0
  origem: "redesign aprovado 2026-05-04 + novo-mockup/_shared/{tokens.css,components.css}"
  bloqueia: [UX-RD-03 e descendentes]
  depende_de: [UX-RD-01]
  touches:
    - path: src/dashboard/tema_css.py
      reason: "css_global() reescrito: :root pega de tokens.css; componentes (.kpi, .pill-d7-*, .pill-humano-*, .table densa, .drawer, .skill-instr, .page-header, .sidebar-cluster, .btn-*, .card.interactive) injetados de components.css; manter seletores [data-testid=stApp*] que ainda fazem sentido"
    - path: assets/fonts/
      reason: "NOVO -- self-host Inter + JetBrains Mono (Variable). Streamlit não tem @font-face nativo; injeção via st.markdown com base64 ou referência a static path"
    - path: tests/test_tema_css_redesign.py
      reason: "NOVO -- 6 testes regressivos: css_global() não vaza hex hardcoded, classes-chave presentes, fontes referenciadas, queries responsivas (max-width 700px) preservadas"
  forbidden:
    - "Tocar tema.py (UX-RD-01 já fechou)"
    - "Tocar app.py ou paginas/*.py"
    - "Hardcodar hex fora de var(--*) ou de CORES injetado"
    - "Usar fontes externas via CDN do Google -- self-host obrigatório (Local First, ADR-07)"
  hipotese:
    - "tema_css.py exporta css_global() como única função pública usada por app.py linha 104. Validar via grep."
    - "569 linhas atuais com seletores [data-testid=...] heavy. Migração preserva seletores Streamlit-críticos (sidebar, stApp, stMain, stButton)."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_tema_css_redesign.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
    - cmd: "grep -E '#[0-9a-fA-F]{6}' src/dashboard/tema_css.py | grep -v 'var(--\\|/\\*' | wc -l"
  acceptance_criteria:
    - "css_global() injeta :root com TODAS as variáveis de novo-mockup/_shared/tokens.css (--bg-base, --bg-surface, --bg-elevated, --bg-inset, --text-primary/secondary/muted/inverse, --accent-purple/pink/cyan/green/yellow/orange/red, --d7-*, --humano-*, --syn-*, --diff-*, --sp-1..16, --r-xs..full, --sidebar-w, --topbar-h, --row-h, --kpi-w/h, --drawer-w, --sh-sm/md/lg/xl/focus, --ff-sans, --ff-mono, --fs-11..40)"
    - "Classes utilitárias presentes: .shell, .sidebar, .sidebar-cluster, .sidebar-item, .topbar, .breadcrumb, .main, .page-header, .page-title, .page-subtitle, .kpi, .kpi-grid, .pill-d7-*, .pill-humano-*, .sprint-tag, .confidence, .table densa, .drawer, .skill-instr, .btn primary/ghost/danger/sm/icon, .card interactive"
    - "Fontes Inter + JetBrains Mono carregadas via @font-face local (assets/fonts/)"
    - "grep '#[0-9a-fA-F]{6}' em tema_css.py retorna apenas hex dentro de comentário ou de var() fallback (≤3 ocorrências)"
    - "Dashboard renderiza com tipografia correta: dados em mono, descrições em sans"
    - "Streamlit nativo (st.button, st.selectbox, st.tabs) ainda funciona visualmente"
    - "pytest baseline mantida"
    - "make smoke 10/10"
  proof_of_work_esperado: |
    # Hipótese: tema_css é importado por app.py
    grep -n "from src.dashboard.tema import.*css_global\|css_global()" src/dashboard/app.py
    # = 53,104 (esperado)

    # AC: zero hex hardcoded fora de fallback
    grep -E '#[0-9a-fA-F]{6}' src/dashboard/tema_css.py | grep -vE 'var\(--|/\*|^\s*#' | wc -l
    # esperado <= 3

    # AC: classes-chave presentes
    for cls in .kpi .pill-d7-graduado .drawer .skill-instr .page-header; do
      grep -c "$cls" src/dashboard/tema_css.py
    done
    # cada >= 1

    # Probe runtime
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/ -- abrir aba "Visão Geral"
    # 1. Tipografia: títulos em Inter, valores em JetBrains Mono
    # 2. Sidebar com bg #1a1d28
    # 3. KPIs com border #313445 (--border-subtle)
    # screenshot lado-a-lado novo-mockup/styleguide.html × dashboard
    # docs/auditorias/redesign/UX-RD-02.png
```

---

# Sprint UX-RD-02 — `tema_css.py` reescrito sobre componentes shared

**Status:** BACKLOG

Migra `tema_css.py` (569 linhas atuais) para um `:root + classes utilitárias`
mapeado 1:1 sobre `novo-mockup/_shared/tokens.css` + `_shared/components.css`.

**Por quê isolada:** CSS global afeta todas as 14 páginas simultaneamente. Se
quebrar, isolamos o estrago aqui — não nas páginas reescritas.

**Tradeoff:** Streamlit não tem `@font-face` nativo. Solução: self-host fontes
Variable (Inter + JetBrains Mono) em `assets/fonts/` e inject via base64 ou
static URL no CSS. Sem CDN externa — Local First (ADR-07).

**Validação visual do dono:** abrir `novo-mockup/styleguide.html` ao lado do
dashboard reformado. Tipografia, espaçamento, pills D7, KPI cards e drawer
devem casar visualmente.

**Specs absorvidas:** UX-01 do plano ativo (callout_html — agora coberto por
.btn-* e .pill-*).

---

*"Forma é nada, função é tudo, mas forma e função juntas elevam a obra." — Frank Lloyd Wright*
