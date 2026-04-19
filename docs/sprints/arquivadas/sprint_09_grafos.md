# Sprint 09 -- Grafos e Visualizações Avançadas

**Status:** ABSORVIDA
**Data de arquivamento:** 2026-04-18
**Motivo:** Sankey e heatmap temporal passam a fazer parte da sprint 27b (motores avançados do grafo).
**Substituída por:** Sprint 27b
**Plano referência:** `/home/andrefarias/.claude/plans/o-que-eu-quero-twinkly-wreath.md`

> Esta sprint foi arquivada na reorganização do roadmap em 2026-04-18.
> O conteúdo abaixo é preservado para consulta histórica.

---

## Conteúdo histórico

## Status: Pendente (escopo refinado em 2026-04-16)

## Relação com Sprint 29 (UX Navegável)

A Sprint 29 entrega o **navegador de grafo interativo** (pyvis, exploratório: clique num nó, expande vizinhança). Esta sprint 09 cobre uma categoria diferente: **visualizações analíticas estáticas** que mostram padrões de fluxo e tendências sem requerer navegação -- Sankey de receita→categorias, heatmap estilo GitHub de intensidade diária, trend analysis com média móvel.

Ambas sobrevivem, com escopos complementares:
- **Sprint 29**: "me mostra tudo que encosta na Neoenergia" (exploração).
- **Sprint 09**: "me mostra o fluxo agregado de 2025 em um quadro" (síntese).

Fonte de dados comum: grafo SQLite da Sprint 27.

## Objetivo

Adicionar visualizações analíticas avançadas ao dashboard: fluxo financeiro agregado, heatmaps temporais, análise de tendências -- complementando o navegador interativo da Sprint 29.

## Entregas

- [ ] Sankey diagram via Plotly (receitas -> categorias -> destinos)
- [ ] Heatmap de gastos estilo GitHub contributions (intensidade por dia)
- [ ] Trend analysis (média móvel, sazonalidade por categoria)
- [ ] Grafo de dependência de metas (networkx + renderização Streamlit)

## Armadilhas conhecidas

- Sankey diagram exige dados no formato source-target-value, transformação não trivial
- Heatmap com poucos meses de dados pode parecer vazio e confuso
- networkx tem renderização nativa feia, considerar pyvis ou plotly para grafos
- Performance pode degradar com muitos nós no grafo interativo

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/dashboard/paginas/fluxo.py` | Página de fluxo financeiro (Sankey) |
| `src/dashboard/paginas/tendencias.py` | Página de heatmap e trend analysis |
| `src/dashboard/app.py` | Novas tabs adicionadas |

## Critério de sucesso

Visualizações interativas funcionais no dashboard. Sankey renderiza com dados reais. Heatmap exibe pelo menos 3 meses de histórico. Trend analysis identifica sazonalidade básica.

## Dependências

Sprint 05 (relatórios e projeções) + Sprint 07 (dashboard v2).
