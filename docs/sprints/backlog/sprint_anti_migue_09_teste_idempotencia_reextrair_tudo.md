# Sprint ANTI-MIGUE-09 -- Teste de idempotência para `--reextrair-tudo`

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 1
**Esforço estimado**: 3h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 38 da auditoria honesta

## Problema

`./run.sh --reextrair-tudo` é destrutivo (limpa nodes documento) mas não tem teste de idempotência. Se rodar 2x seguidas, grafo deveria convergir; sem teste, é assumido.

## Hipótese

Teste sintético com fixtures conhecidas: rodar reextração 2x e comparar contagem de nodes/edges. Tolerância 0 (idempotente).

## Implementação proposta

tests/test_run_sh_idempotente.py com fixture mínima (1 PDF DAS, 1 holerite). Rodar reextração via subprocess 2x, comparar counts.

## Proof-of-work (runtime real)

Teste passa em ambiente CI limpo.

## Acceptance criteria

- Teste regressivo no pytest baseline.

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
