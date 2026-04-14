# Sprint 09 - Grafos e Visualizações Avançadas

## Objetivo

Adicionar visualizações avançadas ao dashboard: fluxo financeiro interativo, grafos de dependência, heatmaps temporais e análise de tendências.

## Entregas

- [ ] Grafo de fluxo financeiro: Sankey diagram via Plotly (receitas -> categorias -> destinos)
- [ ] Grafo de dependência de metas: networkx + renderização Streamlit (qual meta depende de qual)
- [ ] Heatmap de gastos: calendário estilo GitHub contributions (intensidade de gasto por dia)
- [ ] Trend analysis: média móvel, detecção de tendências de alta/baixa, sazonalidade por categoria

## Dependências

Sprint 5 (relatórios e projeções) + Sprint 7 (LLM local para enriquecer análises de tendência).

## Critério de Sucesso

Visualizações interativas funcionais no dashboard. Sankey renderiza com dados reais. Heatmap exibe pelo menos 3 meses de histórico. Trend analysis identifica pelo menos sazonalidade básica.

## Estimativa de Complexidade

**Média.** Bibliotecas de visualização (Plotly, networkx) fazem o trabalho pesado. Desafio principal é preparar os dados no formato correto e manter performance com volume grande. Estimativa: 1.5-2 semanas.
