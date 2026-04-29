---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: e472f3f
---

# Sprint 87.7 — Reconciliação boleto↔transação via grafo (R79-1)

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P2
**Onda**: KAPPA (legado pré-plan)

## Problema

Aba Pagamentos (Sprint 79) reconciliava boleto↔transação por texto; cobertura baixa em base real.

## Hipótese

`carregar_boletos_inteligente` wrapper que consulta grafo (threshold 10 arestas `documento_de`) e cai em fallback textual quando cobertura baixa. Sentinela `None` em `carregar_boletos_via_grafo` indica fallback.

## Acceptance criteria

- Threshold configurável.
- Retrocompatibilidade total com cobertura zero.

## Proof-of-work

Commit `e472f3f`. Padrão "sentinela None em wrapper inteligente" registrado no BRIEF.
