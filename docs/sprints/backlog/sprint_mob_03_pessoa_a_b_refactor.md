# Sprint MOB-03 -- Refactor PESSOA_A/PESSOA_B + mappings/pessoas.yaml (paridade com mobile)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 5
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: nenhum

## Problema

Mob-Ouroboros usa convenção PESSOA_A/PESSOA_B. Backend hardcoda 'André'/'Vitória'. Quebra anonimato e portabilidade.

## Hipótese

Substituir literais por lookup em mappings/pessoas.yaml. Manter compatibilidade backward via aliases.

## Implementação proposta

Refactor + script backfill no XLSX.

## Proof-of-work (runtime real)

grep 'André\|Vitória' src/ → 0 matches em código.

## Acceptance criteria

- Mappings + lookup.
- Refactor completo.
- Pytest baseline.

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
