---
concluida_em: 2026-05-06
---

## SPEC

```yaml
sprint:
  id: UX-Q-02
  title: "Regressão integradora pós Onda T"
  prioridade: P0
  estimativa: 0.25 dia
  onda: Q
  depende_de: [UX-T-29]
  acceptance_criteria:
    - "make smoke = 10/10."
    - "make lint = 0 erros."
    - "pytest baseline >= 2530 (era pré-redesign)."
    - "Pipeline ETL (./run.sh --tudo) roda sem regressão em dataset real."
```

# Sprint UX-Q-02 — Regressão integradora

Concluída 2026-05-06. Métricas finais:

- pytest: **2.567 passed, 13 skipped, 1 xfailed** (era 2.530 pré-redesign; +37 testes).
- make smoke: **10/10 contratos**.
- make lint: **0 erros**.
- 32 testes novos (UX-U + UX-T-01) cobrem shell canônico, helpers
  estruturais e Visão Geral agentic-first.
- Pipeline ETL preservado: nenhuma mudança em src/extractors,
  src/transform, src/load. Apenas dashboard tocado.

*"Não basta fazer; é preciso confirmar." — princípio do gauntlet*
