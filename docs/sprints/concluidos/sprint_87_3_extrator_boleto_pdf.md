---
concluida_em: 2026-04-23
sprint_pai: sprint_87_ressalvas_claude_debitos_tecnicos
commit: 2e39afb
---

# Sprint 87.3 — Extrator de boleto PDF (R74-1, R70-3)

**Origem**: ramificação retroativa via Sprint ANTI-MIGUE-06 (2026-04-28).
**Prioridade**: P1
**Onda**: KAPPA (legado pré-plan)

## Problema

Boletos PDF nativos sem extrator dedicado. GTC-01 end-to-end (boleto SESC R$ 103,93 do casal) só funcionava via classifier; sem extrator, dados estruturados não chegavam ao grafo.

## Hipótese

`src/extractors/boleto_pdf.py` (~600L) com chave canônica via linha digitável de 47 dígitos. Fallback CNPJ sintético `BOLETO|sha256[:12]` quando PDF não expõe CNPJ. Integrado em `scripts/reprocessar_documentos.py`.

## Acceptance criteria

- 15 testes cobrindo parser de linha digitável, fallback, idempotência.
- 2 boletos SESC reais detectados em volume.
- Padrão `BOLETO|sha256[:12]` registrado como canônico.

## Proof-of-work

Commit `2e39afb`. 601 linhas + 15 testes. Dry-run em `data/raw/casal/boletos/` confirma detecção.
