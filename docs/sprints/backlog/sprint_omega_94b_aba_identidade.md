# Sprint OMEGA-94b -- Aba Identidade (RG/CNH/passaporte + alertas validade)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 6
**Esforço estimado**: 4h
**Depende de**: DOC-04, DOC-05
**Fecha itens da auditoria**: nenhum

## Problema

Documentos de identidade sem aba dedicada.

## Hipótese

Aba + alerta T-90d antes do vencimento.

## Implementação proposta

src/dashboard/paginas/identidade.py.

## Proof-of-work (runtime real)

Aba live.

## Acceptance criteria

- Aba.
- Alertas.

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
