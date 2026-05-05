## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-13
  title: "Análise reescrita: 3 abas (sankey + comparativo + heatmap) com drill-down"
  prioridade: P1
  estimativa: 4h
  onda: 4
  origem: "mockup 12-analise.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/analise_avancada.py
      reason: "REESCRITA -- 3 sub-abas: (a) Sankey de fluxo categorias->classificação->pessoa; (b) Comparativo mensal multi-metric; (c) Heatmap calendário (52 semanas × 7 dias) com cor D7. Drill-down via click."
    - path: tests/test_analise_redesign.py
      reason: "NOVO -- 6 testes: 3 abas renderizam, sankey labels visíveis, heatmap não desaparece valores baixos, click em cell drilldown"
  forbidden:
    - "Tocar src/transform/* (lógica preservada)"
    - "Heatmap fundo Dracula que faz cell desaparecer (UX-RD-12 invariante)"
  hipotese:
    - "analise_avancada.py atual (363L) usa Plotly. Sankey atual corta labels em viewport estreito (UX-03 do plano ativo). Layout custom corrige."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_analise_redesign.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "3 sub-abas dentro da página Análise"
    - "Sankey: labels visíveis em viewport ≥1200px, sem corte"
    - "Comparativo: linhas multi-metric com legend, hover tooltip"
    - "Heatmap calendário: cell visível mesmo para valor baixo (cor D7 com contraste WCAG-AA)"
    - "Click cell drilldown para Extrato filtrado"
    - "Deep-link preservado"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # ?cluster=Análise&tab=Análise -- 3 abas visíveis
    # screenshot
```

---

# Sprint UX-RD-13 — Análise

**Status:** BACKLOG

**Specs absorvidas:** UX-03 (drill-down Sankey + heatmap) — agora coberto.

---

*"Análise sem ação é inércia decorada." — princípio do dashboard útil*
