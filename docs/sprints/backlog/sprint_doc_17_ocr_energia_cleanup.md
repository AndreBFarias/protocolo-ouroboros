# Sprint DOC-17 -- OCR energia com cleanup pré-regex (kWh distorcido)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 23 da auditoria

## Problema

Regex `(\d{2,4})\s*[Kk][Ww][Hh]` falha em kwhh, khwh, kWHh.

## Hipótese

Pré-cleanup: re.sub para normalizar variantes de kWh para 'kWh'. Validação anti-zero (consumo == 0 dispara warning).

## Implementação proposta

Editar src/extractors/energia_ocr.py.

## Proof-of-work (runtime real)

3 amostras reais com OCR distorcido → kWh correto.

## Acceptance criteria

- Função normalize_kwh().
- Teste com 5+ variantes.
- Gate 4-way.

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
