# Sprint LLM-03 -- Supervisor propõe regra de categoria para fornecedor frequente

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 2
**Esforço estimado**: 4h
**Depende de**: LLM-01
**Fecha itens da auditoria**: nenhum

## Problema

Fornecedores frequentes que caem em 'Outros' deveriam virar regra. Hoje requer humano editar mappings/categorias.yaml manualmente.

## Hipótese

Após pipeline, supervisor analisa fornecedores em 'Outros' com >=3 ocorrências e propõe regra YAML em mappings/proposicoes/.

## Implementação proposta

1. Supervisor.propor_regra(fornecedor, ocorrencias) → SugestaoRegra(regex, categoria, classificacao).
2. Hook no relatório mensal: lista propostas pendentes.
3. Revisor 4-way ganha aba Proposições com aceitar/rejeitar.

## Proof-of-work (runtime real)

Após pipeline com ≥3 transações 'Vivendas' em Outros, mappings/proposicoes/ tem regra sugerida.

## Acceptance criteria

- Schema Pydantic SugestaoRegra.
- Hook em pipeline ou relatório.
- Aba Proposições no Revisor.

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
