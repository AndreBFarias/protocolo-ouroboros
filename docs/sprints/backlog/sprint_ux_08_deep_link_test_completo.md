---
id: UX-08-DEEP-LINK-TEST-COMPLETO
titulo: Sprint UX-08 -- Cobertura de teste deep-link ?tab= em todas 13 abas + 5 clusters
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint UX-08 -- Cobertura de teste deep-link ?tab= em todas 13 abas + 5 clusters

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P3
**Onda**: 6
**Esforço estimado**: 2h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 18 da auditoria

## Problema

Sprint 100 deu por encerrada sem teste cobrindo todas as combinações.

## Hipótese

Pytest parametrizado com 13×5 cenários.

## Implementação proposta

tests/test_dashboard_deeplink_tab.py.

## Proof-of-work (runtime real)

Pytest passa todos os cenários.

## Acceptance criteria

- 65 cenários cobertos.

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
