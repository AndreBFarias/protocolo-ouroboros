---
concluida_em: 2026-05-06
---

## SPEC consolidada T-06..T-10

```yaml
sprint:
  id: UX-T-06-10
  title: "Cluster Documentos canônico (busca/catalogação/completude/revisor/extração tripla)"
  prioridade: P1
  estimativa: 0.5 dia
  onda: T
  mockup_fonte: novo-mockup/mockups/06-busca-global.html / 07-catalogacao.html / 08-completude.html / 09-revisor.html / 10-validacao-arquivos.html
  depende_de: [UX-T-01, UX-U-02]
  touches:
    - path: src/dashboard/paginas/busca.py — topbar 'Filtros avançados' + 'Catalogação' (primary).
    - path: src/dashboard/paginas/catalogacao.py — topbar 'Reprocessar' + 'Adicionar tipo' (primary).
    - path: src/dashboard/paginas/completude.py — topbar 'Reprocessar' + 'Exportar gaps' (primary).
    - path: src/dashboard/paginas/revisor.py — topbar 'Próxima divergência' + 'Aprovar Opus & avançar' (primary).
    - path: src/dashboard/paginas/extracao_tripla.py — topbar 'Baixar lote' + 'Salvar validações' (primary).
  acceptance_criteria:
    - "Cada página renderiza topbar-actions com 2 botões canônicos do mockup."
    - "Page-headers já eram canônicos (UX-RD-09..RD-11): mantidos."
```

# Sprint UX-T-06..T-10 — Cluster Documentos

5 sprints consolidadas em uma spec porque cada página exigiu apenas
adição de topbar-actions canônicas. Page-headers, layouts e dados já
eram canônicos das ondas UX-RD-09 a UX-RD-11.

*"O catálogo é o índice da memória." — princípio do registro*
