---
id: FONTE-01-GOOGLE-CALENDAR-ICS
titulo: Sprint FONTE-01 -- src/integrations/google_calendar.py — sync .ics
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint FONTE-01 -- src/integrations/google_calendar.py — sync .ics

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 5
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 37 da auditoria

## Problema

Agendas do casal não estão integradas à central de vida adulta.

## Hipótese

Lib `icalendar` lê .ics exportado/sincronizado. Eventos viram nodes tipo 'evento_agenda' no grafo.

## Implementação proposta

Módulo + node tipo + página dedicada (Onda 6).

## Proof-of-work (runtime real)

Subir .ics com 10 eventos → 10 nodes criados.

## Acceptance criteria

- Módulo + 5+ testes.
- Schema de node.
- Cron de sync configurável.

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
