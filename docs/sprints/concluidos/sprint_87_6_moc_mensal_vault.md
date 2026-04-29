---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: cbc7595
---

# Sprint 87.6 — MOC mensal no vault Obsidian (R71-2)

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P2
**Onda**: KAPPA (legado pré-plan)

## Problema

Sync rico (Sprint 71) gerava notas Documentos/Fornecedores mas faltava agregado mensal MOC (Map of Content).

## Hipótese

`Pessoal/Casal/Financeiro/Meses/YYYY-MM.md` com frontmatter YAML + tabela docs + lista fornecedores + Dataview query. Helper `_label_mes_humano` PT-BR.

## Acceptance criteria

- MOC gerado por mês com frontmatter `sincronizado: true`.
- Soberania humana: tag `#sincronizado-automaticamente` preservada em mods manuais.

## Proof-of-work

Commit `cbc7595`. Dry-run sintético em `BORDO_DIR=/tmp/` gerou 933 bytes.
