---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: vários (parte de 87.1-87.8)
---

# Sprint 87.9 — Testes novos para cobertura das mudanças 87.1-87.8

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P2
**Onda**: KAPPA (legado pré-plan)

## Problema

87.1-87.8 introduziram features sem garantia de regressão automática.

## Hipótese

Cada sub-sprint inclui testes próprios (não consolidados em um arquivo único). 87.9 é a "sub-sprint amarra" que verifica cobertura.

## Acceptance criteria

- Cobertura via baseline pytest crescida (~+63 testes pós-87 inteiro, 1046 -> 1109).
- Cada feature testável isoladamente.

## Proof-of-work

Sem commit dedicado — testes saíram nos commits 87.1-87.8. Padrão: agrupados como sub-sprint formal para auditabilidade.
