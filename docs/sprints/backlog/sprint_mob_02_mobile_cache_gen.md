---
id: MOB-02-MOBILE-CACHE-GEN
titulo: Sprint MOB-02 -- Backend gera vault/.ouroboros/cache/{financas,humor-heatmap}.json
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint MOB-02 -- Backend gera vault/.ouroboros/cache/{financas,humor-heatmap}.json

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 5
**Esforço estimado**: 4h
**Depende de**: MOB-01
**Fecha itens da auditoria**: item 31 da auditoria

## Problema

Mob-Ouroboros tela 22 (Mini Financeiro) e 21 (Mini Humor) precisam destes JSONs. Não são gerados.

## Hipótese

src/cache/mobile_cache.py com 2 funções: gerar_financas_cache() e gerar_humor_heatmap_cache(). Encadear em --full-cycle.

## Implementação proposta

Módulo + JSON schemas documentados em docs/MOBILE_CACHE.md.

## Proof-of-work (runtime real)

Após --full-cycle, ambos JSONs existem com dados válidos.

## Acceptance criteria

- Módulo testado.
- JSONs gerados em runtime.
- Schema documentado para o mobile consumir.

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
