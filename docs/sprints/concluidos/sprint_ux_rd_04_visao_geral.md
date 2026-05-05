---
concluida_em: 2026-05-04
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-04
  title: "Visão Geral reescrita: hero + KPI grid 4 + cluster cards + timeline"
  prioridade: P0
  estimativa: 3h
  onda: 1
  origem: "mockup novo-mockup/mockups/01-visao-geral.html + _visao-render.js"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/visao_geral.py
      reason: "REESCRITA -- hero (gradient + Ω animado SVG) + KPI grid 4-col (Receita/Despesa/Saldo/Reserva com .kpi e color D7) + dual-row (resumo financeiro + timeline) + cluster-cards 3-col apontando para Inbox/Finanças/Documentos/Análise/Metas/Bem-estar"
    - path: assets/ouroboros.svg
      reason: "NOVO -- glyph Ω animado (rotate infinito, opacity pulse). Reutilizar de _shared/glyphs.js se existir SVG path equivalente"
    - path: tests/test_visao_geral_redesign.py
      reason: "NOVO -- 6 testes: KPI grid renderiza 4 cards, valores reais (Receita/Despesa/Saldo/Reserva), timeline last-5 events, cluster cards links corretos"
  forbidden:
    - "Quebrar carregamento de dados (carregar_dados, filtrar_por_pessoa, filtrar_por_periodo)"
    - "Hardcodar hex -- usar tokens"
    - "Tocar páginas dos outros clusters"
  hipotese:
    - "visao_geral.py atual (298L) usa st.metric e st.columns. Mockup pede HTML custom via st.markdown(unsafe_allow_html=True). Confirmar via grep st.metric."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_visao_geral_redesign.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Hero ocupa topo: 1.6fr texto + 1fr Ω SVG; bg var(--bg-surface); border-radius var(--r-md)"
    - "Marca 'OUROBOROS' (mono, uppercase, tracking 0.12em, color var(--accent-purple))"
    - "Título h1 (mono, 32px, weight 500, letter-spacing -0.02em)"
    - "KPI grid 4 colunas em viewport ≥1200px (responsive auto-fit minmax(180px,1fr) abaixo)"
    - "Cada KPI: label uppercase (.kpi-label), valor mono 32px tabular-nums (.kpi-value), delta colorido (.kpi-delta.up/down/flat)"
    - "Timeline com 5 últimos eventos do dataset (mes_ref + tipo + descrição) -- mono, dashed border-bottom"
    - "Cluster cards: 6 cards 3-col, hover transform translateY(-2px), border-color accent-purple, link href via query_params"
    - "Dados reais: receita/despesa/saldo do período ativo, sem mock"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    # Hipótese
    grep -c "st.metric\|st.columns" src/dashboard/paginas/visao_geral.py

    # AC: KPI grid
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/?cluster=Home -- abrir Visão Geral
    # 1. Hero com Ω à direita girando
    # 2. 4 KPIs em linha (Receita verde / Despesa vermelho / Saldo dinâmico / Reserva R$ 44.019,78)
    # 3. Timeline com 5 entradas
    # 4. 6 cluster cards clicáveis
    # screenshot vs novo-mockup/mockups/01-visao-geral.html
    # docs/auditorias/redesign/UX-RD-04.png
```

---

# Sprint UX-RD-04 — Visão Geral reescrita

**Status:** BACKLOG

Primeira página com conteúdo. Diff visual ≥95% com mockup `01-visao-geral.html`.

**Validação visual do dono:** comparação lado-a-lado mockup × dashboard.

**Specs absorvidas:** nenhuma direta. Sprint UX-123 (Home cross-tabs) já era
parte do shell — preservada.

---

*"Comece pelo todo, depois detalhe." — princípio do design top-down*
