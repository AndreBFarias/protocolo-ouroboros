# Sprint ANTI-MIGUE-11 -- Pin pyvis<1.0 em pyproject.toml + lock file

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P3
**Onda**: 1
**Esforço estimado**: 30min
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 42 da auditoria honesta

## Problema

pyvis>=0.3 sem upper-bound. Major release pode quebrar grafo full-page sem warning.

## Hipótese

Pinar `pyvis>=0.3,<1.0` + adicionar uv.lock ou requirements-lock.txt.

## Implementação proposta

Editar pyproject.toml + gerar lock + commit.

## Proof-of-work (runtime real)

pip install --dry-run resolve para versão < 1.0.

## Acceptance criteria

- pyproject.toml com upper-bound
- Lock file versionado.

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
