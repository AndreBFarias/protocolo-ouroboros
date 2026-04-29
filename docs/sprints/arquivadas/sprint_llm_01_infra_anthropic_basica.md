# Sprint LLM-01 -- Infraestrutura LLM básica (anthropic SDK + cost_tracker + cache)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 2
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 29 da auditoria honesta (ADR-08 órfã)

## Problema

ADR-08 aprovada em 2025; zero implementação. src/llm/ não existe, anthropic não em deps.

## Hipótese

Camada mínima: src/llm/__init__.py + supervisor.py (chamada única) + cost_tracker.py (registra tokens). Cache LRU em-memória + fallback para SQLite persistente.

## Implementação proposta

1. Adicionar `anthropic>=0.40` em pyproject.toml.
2. src/llm/supervisor.py com classe Supervisor + método `chamar()`.
3. src/llm/cost_tracker.py com SQLite data/output/llm_costs.sqlite.
4. .env-exemplo com ANTHROPIC_API_KEY documentado.
5. Cache LRU @ functools.lru_cache em prompts determinísticos.

## Proof-of-work (runtime real)

supervisor.chamar('teste') retorna resposta + custo registrado em SQLite.

## Acceptance criteria

- Pasta src/llm/ criada com 3 arquivos.
- anthropic em deps + .env-exemplo.
- 10+ testes cobrindo cache hit, cost tracking, fallback offline.

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
