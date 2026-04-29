---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: 05f773a
---

# Sprint 87.8 — Helper legenda_abaixo em 5 plots (R77-1)

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P3
**Onda**: KAPPA (legado pré-plan)

## Problema

Sprint 77 publicou `tema.legenda_abaixo(fig)` mas só 1 plot consumia; legendas inconsistentes.

## Hipótese

Aplicar `legenda_abaixo` em 4 plots adicionais (visão geral, projeções, sankey, heatmap = 5 total). Testes estáticos via `re.findall` no source garantem persistência.

## Acceptance criteria

- 5 plots padronizados.
- Teste regressivo via re.findall.

## Proof-of-work

Commit `05f773a`. Padrão "teste estático por re.findall no source" registrado.
