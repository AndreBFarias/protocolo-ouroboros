# Sprint 03 - Dashboard Streamlit v1

## Objetivo

Dashboard interativo em Streamlit para visualização completa das finanças do casal. Interface funcional com navegação por páginas, filtros globais e tema escuro.

## Entregas

- [ ] Página Visão Geral: cards de resumo, gráfico de barras mensal, pizza por classificação, indicador de saúde financeira
- [ ] Página Por Categoria: treemap de gastos, ranking de categorias, evolução temporal, filtro por pessoa (André/Vitória)
- [ ] Página Extrato Completo: tabela interativa com busca, filtros por coluna, export CSV
- [ ] Página Contas e Dívidas: status de contas fixas, calendário de vencimentos, tracker de dívida Nubank
- [ ] Sidebar global: seletor de mês, toggle André/Vitória/Casal, exibição de saldo
- [ ] Tema dark mode com cores consistentes
- [ ] Layout responsivo

## Dependências

Sprint 2 (extratores completos e infra de qualidade).

## Critério de Sucesso

Dashboard funcional e acessível via `./run.sh --dashboard`. Todas as 4 páginas renderizam corretamente com dados reais do pipeline.

## Estimativa de Complexidade

**Alta.** Múltiplas páginas com visualizações interativas, estado global (sidebar), e integração com dados do pipeline. Estimativa: 2-3 semanas.
