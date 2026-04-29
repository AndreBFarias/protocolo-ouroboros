# Sprint MAKE-AM-01 -- Adicionar target make anti-migue + make conformance-<tipo>

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 1
**Esforço estimado**: 1h
**Depende de**: ANTI-MIGUE-01
**Fecha itens da auditoria**: achado da auditoria visual 2026-04-29 §3.1

## Problema

Makefile não tem target `make anti-migue` nem `make conformance-<tipo>`. Sem eles, o gate anti-migué de 9 checks não tem entry point único — cada Opus precisa lembrar de rodar lint+smoke+pytest+conformance separados.

## Hipótese

Targets compostos: `make anti-migue` roda lint+smoke+pytest+conformance-todos. Falha se qualquer um falhar.

## Implementação proposta

1. Makefile: target `anti-migue: lint smoke test`.
2. Makefile: target `conformance-%:` que roda `pytest tests/conformance/ -k $*`.
3. Documentar no CLAUDE.md §workflow.

## Proof-of-work (runtime real)

make anti-migue exit 0 quando tudo verde; exit 1 se qualquer falhar.

## Acceptance criteria

- Target funcional.
- Documentado em CLAUDE.md.
- Hook pre-push opcional usa.

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
