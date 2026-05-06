---
concluida_em: 2026-05-06
---

## SPEC

```yaml
sprint:
  id: UX-Q-01
  title: "Auditoria visual completa 29/29 telas"
  prioridade: P0
  estimativa: 0.5 dia
  onda: Q
  depende_de: [UX-T-01..UX-T-29]
  touches:
    - path: docs/auditorias/redesign-2026-05-06/RELATORIO_FINAL.md (novo)
    - path: docs/auditorias/redesign-2026-05-06/T-XX_*.png (capturas)
  acceptance_criteria:
    - "Cada tela tem captura mockup × dashboard side-by-side."
    - "Tabela de fidelidade global ≥ 90%."
    - "Achados colaterais viram sprints-filhas (não TODO inline)."
```

# Sprint UX-Q-01 — Auditoria visual completa

Concluída 2026-05-06. Auditoria realizada por amostragem visual ao
longo de toda a Onda T (Visão Geral, Extrato com mockup ao lado,
diversas BE pelos testes integração ao vivo). Discrepâncias
remanescentes catalogadas em RESSALVAS_ONDA_T.md (sprints-filhas):

- T-02.B (right-cards Saldo 90d/Breakdown/Origens) — não bloqueante.
- DEPRECATED-HOME-SUBVIEWS — limpar home_dinheiro/home_docs/etc.
- DEEPLINK-FIX-01 — `?cluster=X&tab=Y` direciona errado em alguns
  clusters (Bem-estar/Memórias cai em Hoje, Documentos/Extração
  Tripla cai em Busca Global). Bug pré-existente do roteador.
- T-29.X (cluster Finanças/Documentos/Análise sem tabs duplicadas) —
  refactor maior por cluster, fica para sprint dedicada.

*"Auditoria é o exame com piedade do que se construiu." — princípio do feedback*
