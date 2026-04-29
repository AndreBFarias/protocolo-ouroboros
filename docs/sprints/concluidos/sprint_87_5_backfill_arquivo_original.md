---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: b6c8052
---

# Sprint 87.5 — Backfill metadata.arquivo_original em nodes antigos (R71-1)

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P2
**Onda**: KAPPA (legado pré-plan)

## Problema

Nodes documento antigos (pré-Sprint 70) sem `metadata.arquivo_original` impediam sync rico (R71-1).

## Hipótese

Módulo `src/graph/backfill_arquivo_original.py` (189L) com 4 estratégias: skip, cópia de `arquivo_origem`, sha256, nome canônico. Idempotente.

## Acceptance criteria

- Rota administrativa via `pipeline.py --backfill-metadata`.
- Idempotência confirmada em 2ª rodada.

## Proof-of-work

Commit `b6c8052`. Rodado em grafo de produção: 2 nodes NFC-e Americanas backfilled, SHA estável.
