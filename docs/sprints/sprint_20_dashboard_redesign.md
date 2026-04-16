# Sprint 20 -- Dashboard Redesign: Layout, Tipografia e Harmonia Visual

## Status: Pendente

## Objetivo

Redesenhar o dashboard seguindo os padrões visuais do stilingue-social-listening-etl: CSS externo, layout factory para Plotly, cards com hover, tipografia hierárquica, legendas posicionadas, espaçamento consistente e logo integrada. O dashboard atual tem fontes apagadas, margens apertadas, títulos competindo com legendas e zero identidade visual.

## Referência de design

Dashboard stilingue (`~/Desenvolvimento/stilingue-social-listening-etl/dashboard/`):
- `tema.py`: layout factory `criar_layout_plotly()` com margins padronizadas, legendas em `y=-0.25` (horizontal, abaixo), hover com bordas, fundo transparente
- `style.css`: CSS externo com cards (border-radius 12px, box-shadow, hover translateY), tabelas estilizadas, scrollbar custom, tipografia Inter
- `componentes.py`: cards KPI reutilizáveis, wrappers `<div class="grafico-container">` para gráficos, tabelas HTML estilizadas

---

## Entregas

### 1. Infraestrutura CSS

- [ ] Criar `src/dashboard/style.css` com CSS externo (em vez de inline em tema.py)
- [ ] Migrar todo CSS de `tema.py` (linhas 47-165) para o arquivo .css
- [ ] Adicionar em `app.py`: `_carregar_css()` que lê e injeta o CSS
- [ ] Remover Streamlit chrome: `#MainMenu`, `footer`, `header`, `.stDeployButton` via CSS
- [ ] Definir max-width do container: `1360px` (evitar cards esticados em telas largas)

### 2. Tipografia hierárquica

Escala atual quebrada (13/14/16/18/20 -- diferenças mínimas). Nova escala:

- [ ] Implementar fonte Inter (Google Fonts) com fallback system
- [ ] Nova hierarquia:
  - Título de página: 1.4rem / 600 weight
  - Título de seção: 0.85rem / 600 / uppercase / letter-spacing 0.8px / borda inferior laranja
  - Label de card: 0.7rem / 500 / uppercase / letter-spacing 0.6px
  - Valor de card: 1.65rem / 700
  - Corpo de texto: 0.78rem
  - Header de tabela: 0.72rem / 600 / uppercase
  - Mínimo (legendas): 0.72rem

### 3. Cards KPI redesenhados

- [ ] Criar componente `render_card()` em `componentes.py` (ou equivalente):
  - Background branco (ou card_fundo do Dracula com bom contraste)
  - Border-radius 12px
  - Box-shadow sutil (0 2px 12px rgba)
  - Hover: translateY(-2px) + shadow mais forte
  - Padding 1.1rem 1.2rem
  - Label uppercase + valor grande + delta colorido
- [ ] Aplicar em: visao_geral.py (3 KPIs), contas.py (resumo), irpf.py (cards)

### 4. Plotly layout factory

- [ ] Criar `criar_layout_plotly(titulo, altura)` em `tema.py` (substituir dict LAYOUT_PLOTLY):
  - Fundo transparente (herda CSS)
  - Margins padrão: `l=60, r=40, t=50, b=40`
  - Título: posicionado em `x=0.02, y=0.97`, font 14px/600
  - Legendas: horizontal, `y=-0.25`, centralizada, font 11px
  - Grid: sutil (`rgba(255,255,255,0.06)` para dark theme)
  - Hover: fundo branco com borda
  - Eixos: tick font 11px
- [ ] Substituir todos os `fig.update_layout({**LAYOUT_PLOTLY, ...})` pela factory
- [ ] Wrapper para gráficos: `<div class="grafico-container"><p class="grafico-titulo">{titulo}</p>` + `st.plotly_chart()` + `</div>`
- [ ] Resolver colisão de anotações em projecoes.py (usar posições alternadas: "top left", "top right")

### 5. Logo e identidade

- [ ] Carregar `assets/icon.png` no sidebar (antes do título "Protocolo Ouroboros")
- [ ] Usar como favicon no `st.set_page_config(page_icon=...)`
- [ ] Redimensionar icon.png se necessário (513KB é grande demais para sidebar)

### 6. Tabelas estilizadas

- [ ] Criar CSS class `.tabela-estilizada` com:
  - Headers: fundo escuro, texto branco, uppercase, 0.72rem
  - Rows: hover com destaque sutil, alternating backgrounds
  - Padding: 0.5rem 0.8rem
  - Sticky header
- [ ] Substituir `st.dataframe()` no extrato por tabela HTML estilizada (ou manter st.dataframe com CSS override)
- [ ] Formatar coluna `data` sem horário (`strftime("%Y-%m-%d")`)

### 7. Espaçamento e ritmo vertical

- [ ] Definir 3 espaçadores padrão:
  - Grande: `<div style="height: 0.8rem"></div>` (entre seções)
  - Médio: `<div style="height: 0.5rem"></div>` (entre componentes)
  - Separador: `<hr>` com margin e cor personalizada
- [ ] Aplicar consistentemente em todas as páginas
- [ ] Gap entre colunas: 16px (via CSS em `[data-testid="stHorizontalBlock"]`)

### 8. Contraste e acessibilidade

- [ ] Recalibrar `texto_sec` de `#6272A4` para algo com ratio >= 4.5:1 no fundo escuro (ex: `#8892B0`)
- [ ] Verificar que todos os textos passam WCAG AA (4.5:1 para texto normal, 3:1 para texto grande)
- [ ] Bordas: aumentar opacidade de 20% para pelo menos 30%

### 9. Filtro de pessoa dinâmico

- [ ] Substituir `["Todos", "André", "Vitória"]` hardcoded por extração do DataFrame: `sorted(df["quem"].dropna().unique())`
- [ ] Remover "Infobase" e "apê" hardcoded das projeções (usar termos de `metas.yaml`)
- [ ] Fix "ESTE MES" -> "ESTE MÊS" em metas.py:265

---

## Armadilhas

- O stilingue usa tema CLARO (fundo #F5F5F5). Ouroboros usa Dracula (fundo #282A36). Adaptar cores, não copiar
- `st.dataframe()` tem CSS interno do Streamlit que conflita com custom CSS -- testar
- Plotly em dark mode precisa de eixos/grid com cores claras, não escuras
- `max-width: 1360px` pode conflitar com `layout="wide"` do Streamlit
- CSS class names podem colidir com classes internas do Streamlit

## Critério de sucesso

Dashboard visualmente harmônico: fontes legíveis, gráficos com espaço para legendas, cards com identidade, logo visível, zero sobreposição de texto. O stilingue é a referência -- não precisa ser idêntico, mas o nível de polish deve ser comparável.

---

*"A simplicidade é a sofisticação suprema." -- Leonardo da Vinci*
