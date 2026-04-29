---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: 5cdaa1b
---

# Sprint 87.2 — Coluna "Doc?" do Extrato consulta o grafo (R74-3)

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P2
**Onda**: KAPPA (legado pré-plan)

## Problema

Coluna "Doc?" do Extrato olhava só categoria; gerava falso "tem doc" para tx sem documento real no grafo.

## Hipótese

Função pura `_marcar_tracking` (sem efeito colateral streamlit) consultando `transacoes_com_documento(db)` em `src/graph/queries.py`. Graceful degradation se grafo ausente.

## Acceptance criteria

- Coluna "Doc?" reflete arestas `documento_de` reais.
- Função pura testável sem mock streamlit.
- Falha do grafo cai em fallback silencioso (set vazio).

## Proof-of-work

Commit `5cdaa1b`: queries adicionadas, dashboard usa runtime grafo. Achado AC87-2-01 virou Sprint 87b (`identificador` no XLSX).
