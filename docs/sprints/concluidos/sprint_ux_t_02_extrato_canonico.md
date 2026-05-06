---
concluida_em: 2026-05-06
---

## 0. SPEC

```yaml
sprint:
  id: UX-T-02
  title: "Extrato canônico (mockup 02-extrato.html)"
  prioridade: P0
  estimativa: 0.5 dia
  onda: T
  mockup_fonte: novo-mockup/mockups/02-extrato.html
  depende_de: [UX-T-01, UX-U-02]
  touches:
    - path: src/dashboard/paginas/extrato.py
      reason: "Topbar-actions + 4 KPIs canônicos (Saldo Consolidado / Entrada · 30d / Saída · 30d / Investido · 30d) + page-header + cálculo de investido em calcular_saldo_topo."
  acceptance_criteria:
    - "Topbar-actions com 2 botões: Importar OFX (deeplink Inbox) + Exportar (primary)."
    - "4 KPIs canônicos com labels do mockup."
    - "Page-header EXTRATO com sprint-tag UX-T-02 + pill 'rastreabilidade sha256'."
    - "Investido calculado a partir de despesas com categoria 'Investimento'."
  proof_of_work_esperado: |
    Captura: docs/auditorias/redesign-2026-05-06/T-02_AFTER_extrato.png
    KPIs: 4/4 canônicos. Topbar btns: 2/2.
```

# Sprint UX-T-02 — Extrato canônico

Concluída 2026-05-06. Topbar-actions + 4 KPIs + page-header + cálculo
de investido implementados. Right-cards (Saldo 90d, Breakdown,
Origens) ficam para sprint-filha T-02.B (não-bloqueante).

*"Cada linha sabe de onde veio." — princípio de rastreabilidade*
