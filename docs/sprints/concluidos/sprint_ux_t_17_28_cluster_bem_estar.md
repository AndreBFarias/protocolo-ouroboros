---
concluida_em: 2026-05-06
---

## SPEC consolidada T-17..T-28

```yaml
sprint:
  id: UX-T-17-28
  title: "Cluster Bem-estar canônico (12 páginas)"
  prioridade: P1
  estimativa: 0.5 dia
  onda: T
  mockup_fonte: novo-mockup/mockups/{17..28}-*.html
  depende_de: [UX-T-01, UX-U-02]
  touches:
    - path: src/dashboard/paginas/be_hoje.py — 'Diário emocional' + 'Salvar humor'.
    - path: src/dashboard/paginas/be_humor.py — 'Exportar 90d' + 'Registrar agora'.
    - path: src/dashboard/paginas/be_diario.py — 'Heatmap' + 'Hoje'.
    - path: src/dashboard/paginas/be_rotina.py — 'Hoje' + 'Novo'.
    - path: src/dashboard/paginas/be_recap.py — 'Re-gerar agora' + 'Compartilhar'.
    - path: src/dashboard/paginas/be_eventos.py — 'Calendário' + 'Novo evento'.
    - path: src/dashboard/paginas/be_memorias.py — 'Random' + 'Capturar'.
    - path: src/dashboard/paginas/be_medidas.py — 'Importar Mi Fit' + 'Registrar'.
    - path: src/dashboard/paginas/be_ciclo.py — 'Histórico' + 'Registrar dia'.
    - path: src/dashboard/paginas/be_cruzamentos.py — 'Salvar bloco Recap' + 'Voltar Recap'.
    - path: src/dashboard/paginas/be_privacidade.py — 'Audit log' + 'Salvar permissões'.
    - path: src/dashboard/paginas/be_editor_toml.py — 'Histórico (git log)' + 'Salvar (commit)'.
  acceptance_criteria:
    - "12 páginas Bem-estar com topbar-actions canônicas do mockup."
    - "Page-headers já eram canônicos (UX-RD-17..RD-19): mantidos."
```

# Sprint UX-T-17..T-28 — Cluster Bem-estar

12 sprints consolidadas. Templates idênticos das ondas anteriores.
Apenas labels canônicos do mockup foram aplicados em cada página.

*"Cuidar é também medir." — princípio do bem-estar*
