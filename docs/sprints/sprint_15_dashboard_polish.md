# Sprint 15 -- Dashboard Polish Visual

## Status: Pendente
Issue: a criar

## Objetivo

Refinamento estético do dashboard após a Sprint 07 (infraestrutura Dracula + granularidade). Foco exclusivo em visual: espaçamento, contraste, respiração entre elementos, consistência de cores, hover states, e aprovação visual aba por aba via Chrome MCP.

## Contexto

A Sprint 07 entregou a infraestrutura completa (tema.py, granularidade, bugfixes, repaginação funcional das 6 abas). Porém o visual ainda está "cru" -- cards sem contraste suficiente, gráficos com cores agressivas, espaçamento apertado, tabelas com estilo nativo conflitando com Dracula.

## Problemas Visuais Identificados

### Gerais
- [ ] Cards com fundo #44475A sobre #282A36 -- contraste sutil demais
- [ ] Falta margin/padding entre seções (elementos colados)
- [ ] Cores hardcoded em HTML inline em vez de usar CORES do tema.py
- [ ] Gráficos Plotly com cores Dracula "crus" (sem opacidade/gradiente)

### Visão Geral
- [ ] 3 cards novos (taxa, supérfluos, maior gasto) precisam de mais destaque visual
- [ ] Indicador de saúde financeira precisa de melhor formatação
- [ ] Barras horizontais de classificação precisam de mais padding esquerdo

### Categorias
- [ ] Treemap precisa de textfont maior e mais legível
- [ ] Top 10 tabela HTML precisa de hover effect e alternância de cor

### Extrato
- [ ] st.dataframe tem headers com cor própria -- verificar consistência Dracula
- [ ] Busca e filtros precisam de melhor espaçamento

### Contas
- [ ] Tabela HTML de dívidas precisa de mais respiração entre linhas
- [ ] Cards de resumo (Pago/Pendente/Total) precisam de mais espaçamento

### Projeções
- [ ] Cards de cenário lado a lado precisam de mais padding interno
- [ ] Gráfico de simulação precisa de área de fill mais sutil

### Metas
- [ ] Cards de meta com layout apertado -- aumentar padding
- [ ] Barra de progresso 0% ainda muito pequena visualmente
- [ ] Texto secundário (prazo, notas, dependências) muito apagado
- [ ] Timeline precisa de mais espaçamento entre marcadores

## Processo

1. Para cada aba: ajustar CSS/HTML, reiniciar dashboard, validar visualmente
2. Iterar com o usuário até aprovação visual
3. Commit final quando todas as 6 abas estiverem aprovadas

## Critério de Sucesso

- [ ] Cada uma das 6 abas aprovada visualmente pelo usuário
- [ ] Nenhuma cor hardcoded fora do tema.py
- [ ] Espaçamento uniforme e respiração entre elementos
- [ ] Gauntlet 44/44
- [ ] Fonte mínima 13px mantida

## Dependências

Sprint 07 (concluída).

---

*"Os detalhes não são detalhes. Eles fazem o design." -- Charles Eames*
