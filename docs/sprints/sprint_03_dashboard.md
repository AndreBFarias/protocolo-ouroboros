# Sprint 03 -- Dashboard Streamlit v1

## Status: Parcialmente concluída (issue #3 reaberta)
Data do commit inicial: 2026-04-14
Commit: 9a5bdb5
Issue: #3 (reaberta -- bugs de UI pendentes)

## Objetivo

Dashboard interativo em Streamlit para visualização completa das finanças. Interface funcional com navegação por páginas, filtros globais e tema escuro.

## Entregas

- [x] Página Visão Geral: cards de resumo, gráfico de barras mensal, pizza por classificação
- [x] Página Por Categoria: treemap de gastos, ranking de categorias, evolução temporal
- [x] Página Extrato Completo: tabela interativa com busca e filtros por coluna
- [x] Página Contas e Dívidas: status de contas fixas, calendário de vencimentos
- [x] Sidebar global: seletor de mês, toggle André/Vitória/Casal, exibição de saldo
- [x] Tema dark mode com cores consistentes
- [x] .streamlit/config.toml configurado

## O que ficou faltando

- Responsividade mobile: não testada em dispositivos móveis
- Bug crítico na página Contas: tabela HTML renderizava como texto bruto (corrigido parcialmente com st.dataframe)
- Cards de métricas: valores quebrando em 2 linhas ("R$ 8.726" / ",36") (corrigido parcialmente com white-space: nowrap)
- Gráfico donut: título "Distribuição por Classificação" truncado (corrigido)
- Labels do donut cortadas nas bordas
- Extrato: label "Classificação" quebrando em 2 linhas, selectboxes truncados ("Tod...")
- Projeções: títulos de cards truncados
- Páginas Projeções e Metas: movidas para Sprint 05
- Estética geral: pendente redesign visual completo (Sprint 08)

## Armadilhas conhecidas

- Streamlit tabs requerem JavaScript para troca visual, o que pode causar flickering
- Dark mode do Streamlit tem problemas de contraste com alguns componentes nativos
- st.dataframe tem performance ruim com mais de 5000 linhas

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/dashboard/app.py` | Aplicação principal Streamlit |
| `src/dashboard/paginas/visao_geral.py` | Página de visão geral |
| `src/dashboard/paginas/categorias.py` | Página de análise por categoria |
| `src/dashboard/paginas/extrato.py` | Página de extrato completo |
| `src/dashboard/paginas/contas.py` | Página de contas e dívidas |
| `src/dashboard/paginas/__init__.py` | Init do módulo páginas |
| `.streamlit/config.toml` | Configuração de tema e server |

## Critério de sucesso

Dashboard funcional e acessível via `./run.sh --dashboard`. Todas as 4 páginas renderizam corretamente com dados reais do pipeline.

## Dependências

Sprint 02 (extratores completos e infra de qualidade).
