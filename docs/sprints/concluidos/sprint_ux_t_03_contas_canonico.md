---
concluida_em: 2026-05-06
---

## SPEC

```yaml
sprint:
  id: UX-T-03
  title: "Contas canônico (mockup 03-contas.html)"
  prioridade: P1
  estimativa: 0.25 dia
  onda: T
  mockup_fonte: novo-mockup/mockups/03-contas.html
  depende_de: [UX-T-02, UX-U-02]
  touches:
    - path: src/dashboard/paginas/contas.py
      reason: "topbar-actions canônicas (Adicionar conta + Sincronizar OFX primary)."
  acceptance_criteria:
    - "Topbar tem 2 botões: Adicionar conta + Sincronizar OFX (primary)."
    - "Page-header já era canônico (UX-RD-07): mantido."
    - "Restante da página (saldo por banco + cartões + dívidas) preservado."
```

# Sprint UX-T-03 — Contas canônico

Concluída 2026-05-06. Topbar-actions adicionadas. Layout existente
(UX-RD-07) já espelha o mockup. Conteúdo (saldos por banco, cartões,
dívidas ativas) mantido.

*"Cada conta é uma janela do todo." — princípio do balanço*
