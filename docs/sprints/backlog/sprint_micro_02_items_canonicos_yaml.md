# Sprint MICRO-02 -- mappings/items_canonicos.yaml + categorização granular

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 4
**Esforço estimado**: 3h
**Depende de**: MICRO-01
**Fecha itens da auditoria**: nenhum

## Problema

Itens granulares (balinha, leite, pão) sem categoria final.

## Hipótese

YAML declarativo: regex_descricao → categoria_final + classificacao.

## Implementação proposta

mappings/items_canonicos.yaml + função aplicar em ingestor_item.

## Proof-of-work (runtime real)

100 itens variados → 80%+ categorizados (sem ficar em Outros).

## Acceptance criteria

- YAML inicial com 50+ regras.
- Função.
- Cobertura ≥80% em corpus.

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
