---
concluida_em: 2026-05-06
---

## SPEC

```yaml
sprint:
  id: UX-Q-03
  title: "Fechamento documental + tag final + ressalvas"
  prioridade: P0
  estimativa: 0.25 dia
  onda: Q
  depende_de: [UX-Q-01, UX-Q-02]
  touches:
    - path: docs/sprints/REDESIGN_INDEX.md — marca redesign concluído.
    - path: docs/SPRINTS_INDEX.md — espelha.
    - path: contexto/ESTADO_ATUAL.md — sessão 2026-05-06 fechada.
    - path: docs/auditorias/redesign-2026-05-06/RESSALVAS_ONDA_T.md (novo).
  acceptance_criteria:
    - "REDESIGN_INDEX.md marca redesign Onda U+T+Q concluído."
    - "ESTADO_ATUAL.md atualizado."
    - "Ressalvas (sprints-filhas) catalogadas."
```

# Sprint UX-Q-03 — Fechamento

Concluída 2026-05-06. Redesign V1 (Onda U + T + Q) entregue:

- **Onda U** (4 sprints): shell canônico — sidebar shell-only,
  topbar slot dinâmico, page-header canônico, filtros expander.
- **Onda U follow-up** (11 fixes): tipografia + dimensões idênticas
  ao mockup (Material Symbols, sidebar 240px, topbar 56px,
  page-title 40px, sprint-tag 11px, etc.).
- **Onda T** (29 sprints): topbar-actions canônicas em todas as
  páginas; T-01 (Visão Geral) com KPIs agentic-first + bloco OS 5
  CLUSTERS + ATIVIDADE RECENTE + SPRINT ATUAL; T-02 (Extrato) com 4
  KPIs Saldo/Entrada/Saída/Investido; tabs duplicadas eliminadas
  no cluster Home.
- **Onda Q** (3 sprints): auditoria visual + regressão + fechamento.

Ressalvas (sprints-filhas backlog):
- DEEPLINK-FIX-01: `?cluster=X&tab=Y` desalinhado em alguns clusters.
- DEPRECATED-HOME-SUBVIEWS: arquivar home_dinheiro/docs/analise/metas.
- T-02.B: right-cards Saldo 90d / Breakdown / Origens.
- TABS-CLUSTER-CLEANUP: eliminar st.tabs em Finanças/Documentos/Análise.

*"O fim é também o começo." — princípio do ouroboros*
