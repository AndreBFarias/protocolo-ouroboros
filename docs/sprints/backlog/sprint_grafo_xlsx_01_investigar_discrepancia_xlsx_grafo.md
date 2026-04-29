# Sprint GRAFO-XLSX-01 -- Investigar discrepância 6.093 XLSX vs 6.086 grafo (7 transações órfãs)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 4
**Esforço estimado**: 2h
**Depende de**: nenhuma
**Fecha itens da auditoria**: achado da auditoria visual 2026-04-29 §1.2

## Problema

XLSX tem 6.093 linhas no extrato. Grafo SQLite tem 6.086 nodes tipo transação. Delta de 7. Não há explicação documentada. Possível causa: dedup tardio no ingestor do grafo ou pipeline que escreve XLSX antes de escrever grafo.

## Hipótese

Comparar dataframes: para cada (data, valor, local) do XLSX, buscar node correspondente no grafo. Listar as 7 órfãs. Identificar padrão (tipo, banco, mês).

## Implementação proposta

scripts/auditar_discrepancia_grafo_xlsx.py com lookup completo + relatório data/output/discrepancia_grafo_xlsx.md.

## Proof-of-work (runtime real)

Lista das 7 órfãs com (data, valor, local, banco, hash).

## Acceptance criteria

- Relatório com causa raiz.
- Fix aplicado OU justificativa documentada.
- Smoke arit aceita delta documentado.

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
