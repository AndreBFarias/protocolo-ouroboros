# Sprint MICRO-01 -- Edges transação→nfce→item no grafo em runtime

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 4
**Esforço estimado**: 5h
**Depende de**: DOC-02, DOC-19
**Fecha itens da auditoria**: nenhum

## Problema

Drill-down 'paguei R$ 800 Vivendas → 3 itens granulares' impossível porque edge transação→item não existe.

## Hipótese

Após linking transação↔documento (Sprint 95), expandir: para cada edge documento_de, criar edges transação→nfce e nfce→item.

## Implementação proposta

src/transform/linking_micro.py + integração no pipeline.

## Proof-of-work (runtime real)

Transação Vivendas tem 1 nfce + 3 itens acessíveis via grafo.

## Acceptance criteria

- Edges criadas em runtime real.
- 8+ testes.

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
