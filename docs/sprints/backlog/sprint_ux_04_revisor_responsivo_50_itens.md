# Sprint UX-04 -- Revisor responsivo + scroll/expand em documentos com 50+ itens

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 6
**Esforço estimado**: 3h
**Depende de**: nenhuma
**Fecha itens da auditoria**: itens 12, 13 da auditoria

## Problema

Layout 4 colunas quebra em <1200px. 50+ subitens renderizam inline.

## Hipótese

use_container_width + media query CSS + expander para listas longas.

## Implementação proposta

revisor.py refactor.

## Proof-of-work (runtime real)

Screenshot em 900px legível + documento 50+ itens com expander.

## Acceptance criteria

- Responsividade.
- Expander.

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
