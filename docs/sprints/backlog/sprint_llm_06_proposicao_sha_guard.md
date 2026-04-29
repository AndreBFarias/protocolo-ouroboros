# Sprint LLM-06 -- SHA-guard: proposta rejeitada com mesmo SHA não volta

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 2
**Esforço estimado**: 2h
**Depende de**: LLM-02
**Fecha itens da auditoria**: nenhum

## Problema

Sem guard, mesma proposta volta em cada rodada do supervisor.

## Hipótese

Tabela `proposicoes_rejeitadas (sha, motivo, ts)`. Antes de gravar proposta nova, supervisor verifica SHA na tabela.

## Implementação proposta

SQLite simples + lookup pré-gravação.

## Proof-of-work (runtime real)

Rejeitar proposição → 2ª rodada do supervisor não regenera.

## Acceptance criteria

- Tabela criada.
- Teste regressivo de não-duplicação.

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
