# Sprint DOC-18 -- Holerite: declarativo em YAML + supervisor LLM detecta novo empregador

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: LLM-02
**Fecha itens da auditoria**: item 24 da auditoria

## Problema

_ASSINATURAS_HOLERITE em registry.py é hardcoded G4F+Infobase. Novo empregador cai silenciosamente.

## Hipótese

Mover assinaturas para mappings/assinaturas_holerite.yaml. Quando supervisor detecta PDF com layout de holerite mas sem casamento, propõe nova assinatura.

## Implementação proposta

Refator + hook supervisor.

## Proof-of-work (runtime real)

Subir holerite de empresa nova → proposta gerada em mappings/proposicoes/.

## Acceptance criteria

- YAML criado.
- Hook supervisor.
- 5+ testes.

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
