# Sprint ANTI-MIGUE-06 -- Ramificar Sprint 87 (10 sub-tasks abertas) em sprints-filhas formais

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 1
**Esforço estimado**: 6h
**Depende de**: nenhuma
**Fecha itens da auditoria**: itens 11 e 34 da auditoria honesta

## Problema

Sprint 87 declarada concluída deixou 10 dependências abertas: boleto_pdf novo extrator, MOC mensal, reconciliação boleto↔transação, drill-down em mais plots, regras YAML para IRPF/DAS/CPF, backfill arquivo_original, reconciliação via grafo, legenda_abaixo em 4 plots, etc.

## Hipótese

Cada sub-task vira spec dedicada em backlog/ com prio + esforço + acceptance próprios. Spec mãe (Sprint 87) ganha link para as 10 filhas no frontmatter.

## Implementação proposta

Criar 10 specs sprint_87_1*.md a sprint_87_10*.md em backlog/, cada uma com mínimo 30 linhas (problema + hipótese + acceptance).

## Proof-of-work (runtime real)

ls docs/sprints/backlog/ | grep -c 'sprint_87_' deve retornar 10.

## Acceptance criteria

- 10 sprints-filhas formais em backlog/.
- Spec original anota 'concluida_em: <data>' e link para filhas.
- Zero TODO solto — cada item tem ID rastreável.

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
