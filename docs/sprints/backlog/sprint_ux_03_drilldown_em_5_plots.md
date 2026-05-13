---
id: UX-03-DRILLDOWN-EM-5-PLOTS
titulo: Sprint UX-03 -- Drill-down em Sankey + Heatmap + Bar Pagamentos + Line Projeções
  + Bar Completude
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint UX-03 -- Drill-down em Sankey + Heatmap + Bar Pagamentos + Line Projeções + Bar Completude

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 6
**Esforço estimado**: 5h
**Depende de**: nenhuma
**Fecha itens da auditoria**: itens 7–11 da auditoria

## Problema

5 gráficos sem clique→filtro. Exploração presa em top-level.

## Hipótese

Aplicar helper aplicar_drilldown() (Sprint 73) em cada um.

## Implementação proposta

Edits em 5 páginas.

## Proof-of-work (runtime real)

Cada gráfico filtra Extrato ao clicar.

## Acceptance criteria

- 5 drill-downs ativos.
- Validação visual.

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
