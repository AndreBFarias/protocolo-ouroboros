---
id: FONTE-03-THUNDERBIRD-ICS-LOCAL
titulo: Sprint FONTE-03 -- src/integrations/thunderbird_ics.py — calendars locais
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint FONTE-03 -- src/integrations/thunderbird_ics.py — calendars locais

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 5
**Esforço estimado**: 3h
**Depende de**: FONTE-01
**Fecha itens da auditoria**: nenhum

## Problema

Thunderbird Lightning armazena calendars em SQLite local.

## Hipótese

Reusar parser do FONTE-01 mas apontando para storage do Thunderbird.

## Implementação proposta

Módulo + path detection.

## Proof-of-work (runtime real)

Eventos do Thunderbird aparecem no grafo.

## Acceptance criteria

- Módulo + testes.
- Doc do path no Pop!_OS.

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
