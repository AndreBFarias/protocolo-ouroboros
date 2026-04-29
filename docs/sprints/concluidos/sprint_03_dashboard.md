---
concluida_em: 2026-04-19
---

# Sprint 03 -- Dashboard Streamlit v1

## Status: Código integrado, bugs visuais pendentes (issue #3 reaberta)
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
- [x] Página Projeções: 3 cenários, gráfico patrimônio (via Sprint 05)
- [x] Página Metas: barras de progresso, prazos, prioridades (via Sprint 05)
- [x] Sidebar global: seletor de mês, toggle André/Vitória/Casal, saldo
- [x] Tema dark mode (#0E1117 fundo, #1E2130 cards, #4ECDC4 acentos)
- [x] .streamlit/config.toml configurado
- [ ] Auditoria visual completa via Chrome MCP
- [ ] Correção de bugs visuais identificados

## Bugs identificados na análise de código

### Bug 1: Cards com wrapping de texto
- **Arquivo:** `src/dashboard/paginas/visao_geral.py`
- **Causa:** Font-size 24px em `st.columns(3)` -- valores como "R$ 17.442,38" estouram coluna.
- **Correção:** Reduzir para 18-20px, adicionar `text-overflow: ellipsis; overflow: hidden`.

### Bug 2: Donut chart labels sobrepostas
- **Arquivo:** `src/dashboard/paginas/visao_geral.py`
- **Causa:** `textinfo="label+percent"` com fatias pequenas causa colisão de labels.
- **Correção:** Usar `textposition="inside"`, aumentar `hole=0.45`, `uniformtext_minsize=10`.

### Bug 3: Botões invisíveis em dark mode
- **Arquivo:** `src/dashboard/paginas/extrato.py`
- **Causa:** `st.download_button` herda tema sem contraste sobre #0E1117.
- **Correção:** CSS override em `app.py` para `[data-testid="stDownloadButton"]`.

### Bug 4: Contraste insuficiente card vs fundo
- **Arquivo:** `src/dashboard/app.py`
- **Causa:** Cards #1E2130 sobre fundo #0E1117 -- diferença sutil.
- **Correção:** Cards para #252840 ou borda `border: 1px solid #333`.

## Processo de auditoria (Chrome MCP)

1. Iniciar dashboard (`make dashboard`)
2. Chrome MCP: abrir http://localhost:8501
3. Para cada uma das 6 abas:
   - Navegar, identificar problemas visuais
   - Corrigir no código, re-verificar
4. Testar filtros (mês, pessoa) em cada aba
5. Testar navegação entre abas sem erro Python

## Arquivos a modificar

| Arquivo | Mudança |
|---------|---------|
| `src/dashboard/app.py` | Bloco `<style>` consolidado para dark mode |
| `src/dashboard/paginas/visao_geral.py` | Cards menores, donut fix |
| `src/dashboard/paginas/categorias.py` | Treemap textfont |
| `src/dashboard/paginas/extrato.py` | Botão download visível |
| `src/dashboard/paginas/contas.py` | Verificar contraste |
| `src/dashboard/paginas/metas.py` | Barra progresso 0% visível |
| `src/dashboard/paginas/projecoes.py` | Nota cenário negativo |

## Gauntlet

Fase `dashboard` cobre imports de todos os 8 módulos (8/8 OK). Renderização visual é validada via Chrome MCP, não automatizada.

## Critério de sucesso

- [ ] Todas as 6 abas renderizam sem erro Python
- [ ] Cards legíveis sem wrapping em resolução desktop
- [ ] Donut chart sem labels sobrepostas
- [ ] Botões visíveis e clicáveis em dark mode
- [ ] Navegação fluída entre abas

## Dependências

Sprint 02 (extratores completos). Sprint 05 (páginas Projeções e Metas).
