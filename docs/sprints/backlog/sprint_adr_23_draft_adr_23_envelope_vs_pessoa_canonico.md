---
id: ADR-23-DRAFT-ADR-23-ENVELOPE-VS-PESSOA-CANONICO
titulo: 'Sprint ADR-23-DRAFT -- ADR-23: decisão envelope vs pessoa como path canônico'
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint ADR-23-DRAFT -- ADR-23: decisão envelope vs pessoa como path canônico

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P3
**Onda**: 6
**Esforço estimado**: 1h (decisão) + variável (execução)
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 47 da auditoria + AUDIT2-ENVELOPE-VS-PESSOA-CANONICO

## Problema

ADR-21 aprovou fusão; sem ADR-23 detalhando próximos passos.

## Hipótese

Decisão arquitetural com supervisor humano sobre path canônico.

## Implementação proposta

Discussão + draft ADR + execução conforme decisão.

## Proof-of-work (runtime real)

ADR-23 publicada.

## Acceptance criteria

- ADR.
- Pipeline padroniza canônico.

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
