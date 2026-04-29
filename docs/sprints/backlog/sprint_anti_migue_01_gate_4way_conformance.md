# Sprint ANTI-MIGUE-01 -- Gate 4-way conformance ≥3 amostras

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 1
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: fundação para Onda 3

## Problema

Tipos novos de documento entram em produção sem prova empírica de que ETL × Opus × Grafo × Humano concordam. Sprint pode declarar 'concluída' sem ter validado em amostras reais.

## Hipótese

Implementar `tests/conformance/4way_gate.py` que recebe `tipo` e exige ≥3 amostras com 4 dimensões batendo (output ETL, transcrição Opus, node no grafo, marcação humana). Comando `make conformance-<tipo>` fica obrigatório antes de mover spec de extrator de backlog para concluidos.

## Implementação proposta

1. Tabela `conformance_amostras` em SQLite (tipo, item_id, etl_ok, opus_ok, grafo_ok, humano_ok, ts).
2. CLI `python -m tests.conformance.4way_gate <tipo>` retorna exit 0 se ≥3 linhas verdes; exit 1 caso contrário.
3. `make conformance-<tipo>` integra ao Makefile.
4. `scripts/check_anti_migue.sh` chama o gate ao tentar mover spec de extrator para concluidos.

## Proof-of-work (runtime real)

Para tipo 'cnh' (que ainda não existe), comando deve retornar exit 1 com mensagem 'apenas N amostras 4-way' onde N<3. Após inserir 3 linhas verdes, retorna exit 0.

## Acceptance criteria

- Comando `make conformance-cnh` funciona em runtime real.
- Tabela SQLite criada com schema versionado.
- 5+ testes pytest cobrindo gate liberado, gate negado, gate com 1 dimensão falha.
- Linha em VALIDATOR_BRIEF.md rodapé descrevendo o gate.

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
