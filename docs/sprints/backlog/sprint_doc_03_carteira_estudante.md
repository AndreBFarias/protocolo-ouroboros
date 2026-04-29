# Sprint DOC-03 -- Extrator: carteira de estudante (JPEG/PDF + validade)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: LLM-01, ANTI-MIGUE-01
**Fecha itens da auditoria**: itens 19, 22 da auditoria honesta

## Problema

carteira de estudante (JPEG/PDF + validade) é documento cotidiano sem regra YAML nem extrator. Cai silenciosamente em _classificar/ ou roteamento-only.

## Hipótese

Spec do tipo + regra de classificação + extrator dedicado + fixtures sintéticas + 3 amostras reais para gate 4-way.

## Implementação proposta

1. Adicionar tipo em mappings/tipos_documento.yaml.
2. Criar src/extractors/carteira_estudante.py.
3. Registrar em src/intake/registry.py.
4. Fixture sintética em tests/fixtures/.
5. 3 amostras reais validadas no Revisor 4-way.

## Proof-of-work (runtime real)

`make conformance-carteira_estudante` retorna exit 0 (≥3 amostras 4-way verdes).

## Acceptance criteria

- Tipo em tipos_documento.yaml.
- Extrator src/extractors/carteira_estudante.py com 8+ testes.
- Fixture sintética + 3 amostras reais.
- Gate 4-way verde.

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
