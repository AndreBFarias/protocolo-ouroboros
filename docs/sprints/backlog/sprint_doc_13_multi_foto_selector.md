# Sprint DOC-13 -- Multi-foto: escolher melhor entre N fotos do mesmo documento

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 20 da auditoria (P0 duplicação garantida)

## Problema

Usuário tira 3 fotos da mesma NF; OCR extrai 3x e cria 3 transações.

## Hipótese

Heurística: para cada grupo de fotos com timestamp próximo (±5min) + similaridade phash, calcular score (nitidez Laplaciana + OCR confidence + % de texto). Escolher a de maior score.

## Implementação proposta

src/intake/multi_foto_selector.py com função `escolher_melhor(fotos: list[Path]) -> Path`. Integrar em inbox_processor antes do OCR.

## Proof-of-work (runtime real)

Subir 3 fotos da mesma NF → pipeline cria 1 transação, não 3.

## Acceptance criteria

- Função pura testável.
- 8+ testes (1 foto, 3 fotos similares, 2 docs diferentes).
- Hook em inbox_processor.

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
