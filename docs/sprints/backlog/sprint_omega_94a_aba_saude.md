# Sprint OMEGA-94a -- Aba Saúde (receitas, exames, plano + alertas validade)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 6
**Esforço estimado**: 5h
**Depende de**: DOC-09, DOC-10, DOC-11
**Fecha itens da auditoria**: nenhum

## Problema

Documentos de saúde não têm visualização integrada.

## Hipótese

Aba dedicada + alertas (CNH, exame, receita prestes a vencer).

## Implementação proposta

src/dashboard/paginas/saude.py + mappings/categorias_saude.yaml.

## Proof-of-work (runtime real)

Aba live com dados do casal.

## Acceptance criteria

- Aba.
- Alertas.
- Mappings.

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
