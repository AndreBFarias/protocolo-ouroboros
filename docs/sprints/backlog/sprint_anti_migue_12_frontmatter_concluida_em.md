# Sprint ANTI-MIGUE-12 -- Frontmatter concluida_em: YYYY-MM-DD em sprints concluídas

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 1
**Esforço estimado**: 2h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 46 da auditoria honesta

## Problema

Specs em concluidos/ sem campo de data de conclusão. Auditoria forense precisa cruzar com git log.

## Hipótese

Adicionar campo `concluida_em: YYYY-MM-DD` no frontmatter YAML de cada spec ao mover para concluidos/. Backfill: ler git log do mv para inferir data de specs antigas.

## Implementação proposta

1. Script scripts/backfill_concluida_em.py com `git log --diff-filter=A` para cada spec em concluidos/.
2. Padronizar checklist anti-migué a sempre incluir o campo.

## Proof-of-work (runtime real)

100% das specs em concluidos/ com campo concluida_em.

## Acceptance criteria

- Backfill aplicado.
- Hook ou check_anti_migue.sh valida presença do campo.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
