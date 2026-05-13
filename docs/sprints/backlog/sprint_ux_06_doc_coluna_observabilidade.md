---
id: UX-06-DOC-COLUNA-OBSERVABILIDADE
titulo: Sprint UX-06 -- Coluna 'Doc?' com observabilidade (logs em falhas do grafo)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint UX-06 -- Coluna 'Doc?' com observabilidade (logs em falhas do grafo)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P3
**Onda**: 6
**Esforço estimado**: 1h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 16 da auditoria

## Problema

Falha no grafo cai em set vazio sem log.

## Hipótese

logger.warning + métrica de erro.

## Implementação proposta

Edit cirúrgico em extrato.py.

## Proof-of-work (runtime real)

Forçar erro SQL → log estruturado.

## Acceptance criteria

- Log + teste.

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
