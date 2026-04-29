---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: 24f5bf9
---

# Sprint 87.1 — Drill-down em 3 gráficos adicionais (R73-1)

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P2
**Onda**: KAPPA (legado pré-plan)

## Problema

Sprint 73 entregou drill-down apenas no treemap de Categorias. Outros 3 plots (visao_geral, grafo_obsidian, extrato) precisavam do mesmo tratamento para uniformizar UX.

## Hipótese

Aplicar `aplicar_drilldown(fig, campo, tab, key_grafico)` (helper já criado em Sprint 73) em 4 páginas adicionais. `_bar_chart` aceita `drilldown_campo`/`drilldown_tab` opcionais.

## Acceptance criteria

- 4 plots ganham drill-down com breadcrumb funcional.
- `_ranking_com_variacao` permanece tabela HTML (limite Streamlit, R74-2).
- Testes regressivos cobrindo customdata setado.

## Proof-of-work

Commit `24f5bf9`: aplicado em visao_geral, categorias, grafo_obsidian, extrato. R73-1 fechado.
