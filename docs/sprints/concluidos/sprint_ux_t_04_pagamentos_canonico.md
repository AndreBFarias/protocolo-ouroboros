---
concluida_em: 2026-05-06
---

## SPEC

```yaml
sprint:
  id: UX-T-04
  title: "Pagamentos canônico (mockup 04-pagamentos.html)"
  prioridade: P1
  estimativa: 0.25 dia
  onda: T
  mockup_fonte: novo-mockup/mockups/04-pagamentos.html
  depende_de: [UX-T-02, UX-U-02]
  touches:
    - path: src/dashboard/paginas/pagamentos.py
      reason: "topbar-actions canônicas (Marcar pago + Adicionar primary)."
  acceptance_criteria:
    - "Topbar tem 2 botões: Marcar pago + Adicionar (primary)."
    - "Page-header já era canônico (UX-RD-07): mantido."
    - "Calendário 14d + lista lateral preservados."
```

# Sprint UX-T-04 — Pagamentos canônico

Concluída 2026-05-06. Topbar-actions adicionadas. Layout (calendário
14d + lista) preservado.

*"O que vence amanhã foi previsto ontem." — princípio do prazo*
