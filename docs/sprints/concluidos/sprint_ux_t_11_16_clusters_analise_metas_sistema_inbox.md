---
concluida_em: 2026-05-06
---

## SPEC consolidada T-11..T-16

```yaml
sprint:
  id: UX-T-11-16
  title: "Clusters Análise/Metas/Sistema/Inbox canônicos"
  prioridade: P1
  estimativa: 0.5 dia
  onda: T
  mockup_fonte: novo-mockup/mockups/{11-categorias,12-analise,13-metas,14-skills-d7,15-irpf,16-inbox}.html
  depende_de: [UX-T-01, UX-U-02]
  touches:
    - path: src/dashboard/paginas/categorias.py — topbar 'Nova regra' + 'Recategorizar' (primary).
    - path: src/dashboard/paginas/analise_avancada.py — topbar 'Categorias' + 'Exportar relatório' (primary).
    - path: src/dashboard/paginas/metas.py — topbar 'Skills D7' + 'Nova meta' (primary).
    - path: src/dashboard/paginas/skills_d7.py — topbar 'Recalibrar' + 'Logs' (primary).
    - path: src/dashboard/paginas/irpf.py — topbar 'Recalcular' + 'Gerar pacote' (primary).
    - path: src/dashboard/paginas/inbox.py — topbar 'Abrir pasta' + 'Atualizar fila' (primary).
  acceptance_criteria:
    - "Cada página renderiza topbar-actions com 2 botões canônicos do mockup."
    - "Page-headers já eram canônicos: mantidos."
```

# Sprint UX-T-11..T-16 — Análise / Metas / Sistema / Inbox

6 páginas com topbar-actions adicionadas. Templates idênticos das T-06..T-10.

*"Cada cluster é uma faceta do mesmo todo." — princípio do sistema*
