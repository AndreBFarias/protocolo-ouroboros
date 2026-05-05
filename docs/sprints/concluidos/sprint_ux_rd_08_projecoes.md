---
concluida_em: 2026-05-04
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-08
  title: "Projeções reescritas: 3 cenários 5 anos + marcos sobrepostos"
  prioridade: P1
  estimativa: 2h
  onda: 2
  origem: "mockup 05-projecoes.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/projecoes.py
      reason: "REESCRITA -- gráfico Plotly multi-line: 3 cenários (pessimista=red, realista=cyan, otimista=green) em 60 meses + marcos verticais (reserva 100%, casa, carro). Tema dark coerente com tokens. Cards laterais com KPIs por cenário."
    - path: tests/test_projecoes_redesign.py
      reason: "NOVO -- 4 testes: 3 cenários renderizam, marcos visíveis, KPI cards atualizam, deep-link"
  forbidden:
    - "Tocar src/projections/* (lógica de cálculo preservada)"
    - "Hardcodar cores no Plotly -- importar de CORES"
  hipotese:
    - "projecoes.py atual usa Plotly. Tema dark Plotly não casa 100% com Dracula novo. Aplicar layout custom."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_projecoes_redesign.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Gráfico Plotly com paper_bgcolor=#0e0f15, plot_bgcolor=#1a1d28, font color #f8f8f2"
    - "3 linhas: red/cyan/green com width=2"
    - "Marcos verticais com label rotacionado"
    - "Cards laterais: 'Reserva 100% em XX meses', 'Casa em XX meses', 'Carro em XX meses' por cenário"
    - "Deep-link preservado"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/?cluster=Finanças&tab=Projeções
    # 3 linhas, marcos visíveis, cards atualizam ao trocar cenário
    # screenshot vs 05-projecoes.html
```

---

# Sprint UX-RD-08 — Projeções

**Status:** BACKLOG

Sprint mais leve da Onda 2 — só ajusta tema do Plotly e troca layout para
casar mockup. Lógica de projeção (`src/projections/`) intacta.

---

*"Quem não tem visão de longo prazo, não enxerga curto." — princípio do planejamento*
