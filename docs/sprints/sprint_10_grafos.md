# Sprint 10 -- Grafos e Visualizações Avançadas

## Status: Pendente
Issue: a criar

## Objetivo

Adicionar visualizações avançadas ao dashboard: fluxo financeiro interativo, heatmaps temporais e análise de tendências.

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

Sprint 05 (relatórios e projeções) + Sprint 08 (dashboard v2).
