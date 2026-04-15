# Design: Dupla 2 -- Sprint 16 (Dashboard Polish) + Sprint 10 (Grafos)

Data: 2026-04-14

---

## Contexto

O dashboard Streamlit tem 6 abas com tema Dracula (tema.py) e 92% de conformidade com cores centralizadas. A Sprint 16 refina a estética (contraste, espaçamento, cores hardcoded). A Sprint 10 adiciona uma nova aba de visualizações avançadas (Sankey, heatmap, tendências).

## Decisões de Design

- **Contraste de cards:** Borda sutil 1px `#6272A4` + `box-shadow: 0 2px 8px rgba(0,0,0,0.3)` nos geradores `card_html()` e `card_sidebar_html()` de `tema.py`. Propagação automática.
- **Novas visualizações:** Uma única aba "Análise" com Sankey + heatmap + tendências, em vez de 2 abas separadas.
- **Grafo de metas (networkx):** Removido do escopo. Complexidade alta, valor marginal.
- **Dependências:** Nenhuma nova. Plotly já suporta Sankey (`go.Sankey`) e Heatmap (`go.Heatmap`).

---

## Sprint 16: Dashboard Polish Visual

### tema.py

1. Adicionar `rgba_cor(cor_hex: str, alpha: float) -> str` para gerar RGBA a partir de CORES
2. Modificar `card_html()`: borda 1px `#6272A4` + box-shadow
3. Modificar `card_sidebar_html()`: mesma borda + shadow
4. Adicionar CSS global: margin-bottom 16px entre componentes Streamlit para "respiração"

### metas.py (prioridade alta -- 65% compliance)

1. Substituir 5x `#6272A4` hardcoded por `CORES["texto_sec"]`
2. Substituir 2x `#F8F8F2` hardcoded por `CORES["texto"]`
3. Substituir `#555` border por `CORES["card_fundo"]`
4. Substituir font sizes literais (15px, 13px) por `FONTE_TITULO`, `FONTE_MINIMA`
5. Aumentar padding interno dos cards de meta (16px -> 20px)
6. Barra de progresso 0%: min-width 4px para visibilidade
7. Texto secundário (prazo, notas, dependências): cor `texto_sec` com font-size `FONTE_CORPO`
8. Timeline: espaçamento entre marcadores (margin-bottom 24px)

### contas.py

1. Substituir 2x RGBA hardcoded por `rgba_cor(CORES["positivo"], 0.08)` e `rgba_cor(CORES["negativo"], 0.08)`
2. Tabela de dívidas: line-height 1.8 (era default ~1.4)
3. Cards resumo (Pago/Pendente/Total): padding 16px

### projecoes.py

1. Substituir `fillcolor="rgba(189, 147, 249, 0.1)"` por `rgba_cor(CORES["destaque"], 0.1)`
2. Cards de cenário: padding interno 16px -> 20px
3. Fill area do gráfico de simulação: opacidade 0.08 (mais sutil)

### visao_geral.py

1. 3 cards novos (taxa, supérfluos, maior gasto): font-size do valor para `FONTE_VALOR`
2. Indicador de saúde financeira: padding 20px, border-radius 8px
3. Barras de classificação: padding-left 8px para legibilidade

### categorias.py

1. Treemap: `textfont.size = FONTE_CORPO` (14px, era 13px)
2. Tabela Top 10: hover effect (`:hover { background: rgba(68,71,90,0.5) }`)
3. Alternância de cor nas linhas (`nth-child(even)` com `rgba_cor(CORES["card_fundo"], 0.3)`)

### extrato.py

1. Verificar headers do dataframe com Dracula
2. Filtros: margin-bottom 12px entre dropdowns

---

## Sprint 10: Página "Análise Avançada"

### Arquivo: `src/dashboard/paginas/analise_avancada.py` (~250 linhas)

### Componentes

**1. Sankey Diagram (topo)**
- Título: "Fluxo Financeiro"
- Dados: transações do período -> agrupar por (tipo, categoria, classificação)
- Nós: Receitas (verde), categorias de despesa (cores por classificação)
- Links: largura proporcional ao valor
- Plotly `go.Sankey` com `LAYOUT_PLOTLY`
- Mínimo de dados: pelo menos 5 transações para renderizar

**2. Heatmap de Gastos (meio)**
- Título: "Intensidade de Gastos"
- Estilo GitHub contributions
- Eixo X: semanas (últimos 3 meses)
- Eixo Y: dia da semana (segunda a domingo)
- Escala de cor: `#282A36` (sem gasto) a `#FF5555` (gasto máximo)
- Plotly `go.Heatmap` com colorscale customizada Dracula
- Tooltip: data + valor total do dia

**3. Tendências (base)**
- Título: "Tendências por Categoria"
- Top 5 categorias por gasto total
- Média móvel 3 meses
- Linhas com cores cíclicas: [positivo, negativo, neutro, alerta, destaque]
- Alerta visual se gasto subiu >20% vs trimestre anterior (anotação no gráfico)
- Plotly `go.Scatter` com `LAYOUT_PLOTLY`

### Integração em app.py

- Nova aba "Análise" após "Metas" (posição 7 de 7)
- Import: `from src.dashboard.paginas import analise_avancada`
- Passagem de contexto: `ctx` (granularidade, período)

---

## Validação

1. `make lint` (ruff + acentuação)
2. `make process` (pipeline)
3. Chrome MCP: abrir dashboard, verificar cada uma das 7 abas
4. Checklist visual por aba: contraste, espaçamento, fontes >= 13px, cores centralizadas
5. Gauntlet: deve manter 44/44

---

## Arquivos Modificados/Criados

| Arquivo | Ação | Sprint |
|---------|------|--------|
| `src/dashboard/tema.py` | MODIFICAR -- rgba_cor(), card borders, CSS spacing | 16 |
| `src/dashboard/paginas/metas.py` | MODIFICAR -- 9 cores + fonts hardcoded | 16 |
| `src/dashboard/paginas/contas.py` | MODIFICAR -- 2 RGBA + spacing | 16 |
| `src/dashboard/paginas/projecoes.py` | MODIFICAR -- 1 RGBA + padding | 16 |
| `src/dashboard/paginas/visao_geral.py` | MODIFICAR -- cards + indicador + barras | 16 |
| `src/dashboard/paginas/categorias.py` | MODIFICAR -- treemap font + tabela hover | 16 |
| `src/dashboard/paginas/extrato.py` | MODIFICAR -- headers + filtros spacing | 16 |
| `src/dashboard/paginas/analise_avancada.py` | NOVO -- Sankey + heatmap + tendências | 10 |
| `src/dashboard/app.py` | MODIFICAR -- nova aba "Análise" | 10 |

---

*"A simplicidade é a sofisticação suprema." -- Leonardo da Vinci*
