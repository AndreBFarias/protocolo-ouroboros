---
id: MOB-01-VAULT-BRIDGE-MD
titulo: Sprint MOB-01 -- Backend lê .md do mobile e roteia para inbox
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint MOB-01 -- Backend lê .md do mobile e roteia para inbox

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 5
**Esforço estimado**: 5h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 31 da auditoria

## Problema

Mob-Ouroboros escreve .md em vault/daily/, vault/eventos/, etc. Backend não lê.

## Hipótese

src/intake/vault_bridge.py varre as 6 pastas-alvo no vault, lê frontmatter YAML, roteia para o pipeline conforme tipo. Idempotência via hash de conteúdo.

## Implementação proposta

Módulo + integração em --full-cycle.

## Proof-of-work (runtime real)

Subir .md em vault/daily/ → backend captura no próximo full-cycle.

## Acceptance criteria

- Módulo testado.
- 6 tipos cobertos (humor, evento, diario, treino, medida, financeiro).
- Idempotência por hash.

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
