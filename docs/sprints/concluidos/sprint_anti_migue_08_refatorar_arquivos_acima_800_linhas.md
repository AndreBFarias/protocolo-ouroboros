---
concluida_em: 2026-04-29
commits:
  - 0900ff9 refactor(dashboard): extrai consultas de grafo de dados.py
  - 08a38ab refactor(dashboard): extrai logica pura do revisor
  - 727599e refactor(graph): extrai ingestores de prescricao e garantia
  - b15834e refactor(dashboard): extrai css_global de tema.py
proof_of_work: |
  find src -name '*.py' -exec wc -l {} \; | awk '$1>800'
  -> 0 linhas (acceptance criteria #1 cumprido)
  pytest: 2022 passed (baseline 2020) -- zero regressao (acceptance #2)
  make lint: exit 0 (acceptance #3)
---

# Sprint ANTI-MIGUE-08 -- Refatorar 4 arquivos > 800 linhas (CLAUDE.md §convenções)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 1
**Esforço estimado**: 8h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 40 da auditoria honesta

## Problema

Quatro arquivos violam o limite de 800 linhas: tema.py (1.191), ingestor_documento.py (940), revisor.py (888), dados.py (830). Arquivos grandes degradam manutenibilidade.

## Hipótese

Cada arquivo tem responsabilidades extraíveis: tema.py → tokens/helpers/icones; ingestor → ingestor_doc/ingestor_item/ingestor_metadata; revisor → revisor_dimensoes/revisor_render/revisor_export; dados → dados/dados_revisor.

## Implementação proposta

1 arquivo por sub-sprint (4 sub-sprints). Cada uma: extrair módulo, atualizar imports, garantir testes verdes, garantir lint verde.

## Proof-of-work (runtime real)

wc -l src/dashboard/tema.py etc. — todos < 800.

## Acceptance criteria

- 0 arquivos > 800 linhas em src/.
- Pytest baseline mantido.
- Lint exit 0.

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
