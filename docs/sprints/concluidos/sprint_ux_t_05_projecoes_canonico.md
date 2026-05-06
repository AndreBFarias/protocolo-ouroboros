---
concluida_em: 2026-05-06
---

## SPEC

```yaml
sprint:
  id: UX-T-05
  title: "Projeções canônico (mockup 05-projecoes.html)"
  prioridade: P1
  estimativa: 0.25 dia
  onda: T
  mockup_fonte: novo-mockup/mockups/05-projecoes.html
  depende_de: [UX-T-02, UX-U-02]
  touches:
    - path: src/dashboard/paginas/projecoes.py
      reason: "topbar-actions canônicas (Comparar cenários + Salvar cenário primary)."
  acceptance_criteria:
    - "Topbar tem 2 botões: Comparar cenários + Salvar cenário (primary)."
    - "Page-header já era canônico (UX-RD-08): mantido."
    - "3 cenários (pessimista/realista/otimista) preservados."
```

# Sprint UX-T-05 — Projeções canônico

Concluída 2026-05-06. Topbar-actions adicionadas. Cenários A/B/C e
KPI strip mantidos.

*"A projeção é fé numérica." — princípio do plano*
