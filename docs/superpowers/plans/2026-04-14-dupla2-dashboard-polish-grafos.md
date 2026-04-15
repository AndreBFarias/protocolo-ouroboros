# Dupla 2: Dashboard Polish + Grafos -- Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refinar visualmente todas as 6 abas do dashboard Dracula e adicionar uma 7a aba com Sankey, heatmap e tendências.

**Architecture:** Mudanças centralizadas em `tema.py` (helper `rgba_cor`, bordas em cards, CSS de espaçamento) propagam automaticamente para todas as páginas. Cores hardcoded em 3 arquivos são substituídas por referências a `CORES`. Nova página `analise_avancada.py` usa Plotly `go.Sankey` e `go.Heatmap` com dados derivados do extrato.

**Tech Stack:** Streamlit, Plotly (go.Sankey, go.Heatmap, go.Scatter), pandas, tema.py centralizado.

---

### Task 1: Atualizar tema.py -- rgba_cor, bordas, CSS espaçamento

**Files:**
- Modify: `src/dashboard/tema.py:49-68` (card_html), `:71-89` (card_sidebar_html), `:92-155` (css_global)

- [ ] **Step 1: Adicionar helper rgba_cor() após LAYOUT_PLOTLY (linha 163)**

```python
def rgba_cor(cor_hex: str, alpha: float) -> str:
    """Converte cor hex (#RRGGBB) para rgba(r,g,b,alpha)."""
    cor = cor_hex.lstrip("#")
    r, g, b = int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
```

- [ ] **Step 2: Atualizar card_html() -- adicionar borda + shadow**

Substituir o div style em `card_html()` (linhas 52-57):

```python
def card_html(titulo: str, valor: str, cor: str) -> str:
    """Gera HTML de card compacto reutilizável."""
    return (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border-left: 4px solid {cor};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-left: 4px solid {cor};"
        f" border-radius: 8px;"
        f" padding: 16px 18px;"
        f" margin: 6px 0;"
        f" box-shadow: 0 2px 8px rgba(0,0,0,0.3);"
        f'">'
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: {FONTE_CORPO}px;"
        f' margin: 0;">{titulo}</p>'
        f'<p style="color: {cor};'
        f" font-size: {FONTE_VALOR}px;"
        f" font-weight: bold;"
        f" white-space: nowrap;"
        f' margin: 4px 0 0 0;">{valor}</p>'
        f"</div>"
    )
```

- [ ] **Step 3: Atualizar card_sidebar_html() -- mesma borda + shadow**

Mesma abordagem: adicionar `border: 1px solid {CORES['texto_sec']}33;` e `box-shadow: 0 2px 6px rgba(0,0,0,0.25);`

- [ ] **Step 4: Adicionar CSS de espaçamento global em css_global()**

Adicionar antes do `</style>`:

```css
.element-container { margin-bottom: 16px; }
[data-testid="stHorizontalBlock"] { gap: 16px; }
```

- [ ] **Step 5: Verificar sintaxe e importações**

```bash
.venv/bin/python -c "from src.dashboard.tema import rgba_cor, card_html, CORES; print(rgba_cor(CORES['positivo'], 0.08))"
```

Esperado: `rgba(80, 250, 123, 0.08)`

- [ ] **Step 6: Commit**

```bash
git add src/dashboard/tema.py
git commit -m "refactor: tema.py -- rgba_cor(), bordas em cards, CSS espaçamento"
```

---

### Task 2: Corrigir metas.py -- 9 cores hardcoded + fonts

**Files:**
- Modify: `src/dashboard/paginas/metas.py:90-155` (_card_meta), `:244-318` (timeline)

- [ ] **Step 1: Substituir cores hardcoded em _card_meta()**

Substituições no corpo de `_card_meta()`:

| Linha | De | Para |
|-------|----|----|
| 97 | `color: #6272A4` | `color: {CORES["texto_sec"]}` |
| 98 | `font-size: 13px` | `font-size: {FONTE_MINIMA}px` |
| 106 | `color: #6272A4` | `color: {CORES["texto_sec"]}` |
| 107 | `font-size: 13px` | `font-size: {FONTE_MINIMA}px` |
| 136 | `color: #F8F8F2` | `color: {CORES["texto"]}` |
| 137 | `font-size: 15px` | `font-size: {FONTE_SUBTITULO}px` |
| 143 | `color: #6272A4` | `color: {CORES["texto_sec"]}` |
| 144 | `font-size: 13px` | `font-size: {FONTE_MINIMA}px` |

Também: `padding: 16px` -> `padding: 20px` no container div (linha 131).

- [ ] **Step 2: Corrigir timeline -- cores + espaçamento**

Na seção de timeline:
- `border-left: 2px solid #555` -> `border-left: 2px solid {CORES["card_fundo"]}`
- `color: #F8F8F2` -> `color: {CORES["texto"]}`
- Adicionar `margin-bottom: 24px` nos marcadores da timeline

- [ ] **Step 3: Barra de progresso 0% visível**

Se `st.progress` não aceita min-width, adicionar fallback: se progresso == 0, mostrar texto "0%" em vez da barra vazia.

- [ ] **Step 4: Verificar sintaxe**

```bash
.venv/bin/ruff check src/dashboard/paginas/metas.py --quiet
```

- [ ] **Step 5: Commit**

```bash
git add src/dashboard/paginas/metas.py
git commit -m "fix: metas.py -- substituir 9 cores hardcoded por CORES e FONTE_*"
```

---

### Task 3: Corrigir contas.py + projecoes.py -- RGBA + spacing

**Files:**
- Modify: `src/dashboard/paginas/contas.py:50-52`
- Modify: `src/dashboard/paginas/projecoes.py:259`

- [ ] **Step 1: contas.py -- substituir RGBA hardcoded**

Importar `rgba_cor` de tema e substituir linhas 50-52:

```python
from src.dashboard.tema import CORES, FONTE_CORPO, FONTE_MINIMA, rgba_cor

# Na função, substituir:
cor_fundo = (
    rgba_cor(CORES["positivo"], 0.08) if status == "Pago"
    else rgba_cor(CORES["negativo"], 0.08)
)
```

Também: aumentar line-height nas `<td>` de `padding: 10px` para `padding: 12px 10px` para mais respiração.

- [ ] **Step 2: projecoes.py -- substituir RGBA hardcoded**

Importar `rgba_cor` e substituir linha 259:

```python
fillcolor=rgba_cor(CORES["destaque"], 0.08),
```

- [ ] **Step 3: Verificar e commitar**

```bash
.venv/bin/ruff check src/dashboard/paginas/contas.py src/dashboard/paginas/projecoes.py --quiet
git add src/dashboard/paginas/contas.py src/dashboard/paginas/projecoes.py
git commit -m "fix: contas/projecoes -- substituir RGBA hardcoded por rgba_cor()"
```

---

### Task 4: Polish menor -- visao_geral + categorias + extrato

**Files:**
- Modify: `src/dashboard/paginas/visao_geral.py`
- Modify: `src/dashboard/paginas/categorias.py`
- Modify: `src/dashboard/paginas/extrato.py`

- [ ] **Step 1: visao_geral.py**

- Cards novos (taxa, supérfluos, maior gasto): garantir font-size FONTE_VALOR no valor
- Indicador de saúde financeira: adicionar `padding: 20px; border-radius: 8px` no div
- Barras de classificação horizontal: adicionar `margin-left: 8px` para padding esquerdo

- [ ] **Step 2: categorias.py**

- Treemap: `textfont=dict(size=FONTE_CORPO)` (14px em vez de 13)
- Tabela Top 10: adicionar alternância de cor `nth-child(even)` com fundo sutil
- Hover effect na tabela: `tr:hover { background: rgba(68,71,90,0.5); }`

- [ ] **Step 3: extrato.py**

- Filtros: adicionar `st.markdown('<div style="margin-bottom: 12px;"></div>', ...)` entre dropdowns
- Verificar consistência de cores no dataframe (limitado pelo st.dataframe)

- [ ] **Step 4: Verificar e commitar**

```bash
.venv/bin/ruff check src/dashboard/paginas/visao_geral.py src/dashboard/paginas/categorias.py src/dashboard/paginas/extrato.py --quiet
git add src/dashboard/paginas/visao_geral.py src/dashboard/paginas/categorias.py src/dashboard/paginas/extrato.py
git commit -m "refactor: polish visual em visao_geral, categorias e extrato"
```

---

### Task 5: Criar analise_avancada.py -- Sankey + Heatmap + Tendências

**Files:**
- Create: `src/dashboard/paginas/analise_avancada.py`

- [ ] **Step 1: Estrutura base e imports**

```python
"""Página de análise avançada: Sankey, heatmap e tendências."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.dados import filtrar_por_periodo, filtrar_por_pessoa, formatar_moeda
from src.dashboard.tema import CORES, FONTE_CORPO, FONTE_SUBTITULO, LAYOUT_PLOTLY, rgba_cor
```

- [ ] **Step 2: Implementar _preparar_dados_sankey()**

Agrupa transações por tipo -> categoria -> classificação e retorna listas source/target/value para `go.Sankey`.

```python
def _preparar_dados_sankey(df: pd.DataFrame) -> dict:
    """Prepara dados source-target-value para Sankey."""
    despesas = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()
    if despesas.empty:
        return {"labels": [], "source": [], "target": [], "value": [], "colors": []}

    # Nó 0 = "Receitas"
    labels = ["Receitas"]
    colors = [CORES["positivo"]]
    cat_indices: dict[str, int] = {}
    source, target, value = [], [], []

    # Agrupar por categoria
    por_cat = despesas.groupby("categoria")["valor"].sum().sort_values(ascending=False).head(10)

    for cat, val in por_cat.items():
        if cat not in cat_indices:
            cat_indices[cat] = len(labels)
            classif = despesas[despesas["categoria"] == cat]["classificacao"].mode()
            cor = CORES.get("obrigatorio" if len(classif) == 0 else {
                "Obrigatório": "obrigatorio",
                "Questionável": "questionavel",
                "Supérfluo": "superfluo",
            }.get(classif.iloc[0], "texto_sec"), CORES["texto_sec"])
            labels.append(str(cat))
            colors.append(cor)

        source.append(0)
        target.append(cat_indices[cat])
        value.append(float(val))

    return {"labels": labels, "source": source, "target": target, "value": value, "colors": colors}
```

- [ ] **Step 3: Implementar _preparar_dados_heatmap()**

```python
def _preparar_dados_heatmap(df: pd.DataFrame) -> dict:
    """Prepara dados para heatmap estilo GitHub contributions."""
    despesas = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()
    if despesas.empty or "data" not in despesas.columns:
        return {"z": [], "x": [], "y": []}

    despesas["data_dt"] = pd.to_datetime(despesas["data"], errors="coerce")
    despesas = despesas.dropna(subset=["data_dt"])
    despesas["dia_semana"] = despesas["data_dt"].dt.dayofweek
    despesas["semana"] = despesas["data_dt"].dt.isocalendar().week.astype(int)

    pivot = despesas.pivot_table(
        index="dia_semana", columns="semana", values="valor", aggfunc="sum", fill_value=0
    )

    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    return {"z": pivot.values.tolist(), "x": [f"S{s}" for s in pivot.columns], "y": dias[:len(pivot.index)]}
```

- [ ] **Step 4: Implementar _renderizar_tendencias()**

Média móvel 3 meses das top 5 categorias.

```python
def _renderizar_tendencias(df_total: pd.DataFrame) -> None:
    """Renderiza gráfico de tendências por categoria."""
    despesas = df_total[df_total["tipo"].isin(["Despesa", "Imposto"])].copy()
    if despesas.empty:
        return

    por_mes_cat = despesas.groupby(["mes_ref", "categoria"])["valor"].sum().reset_index()
    top5 = despesas.groupby("categoria")["valor"].sum().nlargest(5).index.tolist()

    cores_ciclo = [CORES["positivo"], CORES["negativo"], CORES["neutro"], CORES["alerta"], CORES["destaque"]]
    fig = go.Figure()

    for i, cat in enumerate(top5):
        dados_cat = por_mes_cat[por_mes_cat["categoria"] == cat].sort_values("mes_ref")
        dados_cat["media_movel"] = dados_cat["valor"].rolling(window=3, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=dados_cat["mes_ref"], y=dados_cat["media_movel"],
            name=cat, line=dict(color=cores_ciclo[i % len(cores_ciclo)], width=2),
            mode="lines+markers", marker=dict(size=5),
        ))

    fig.update_layout(**LAYOUT_PLOTLY, title="Tendências -- Média Móvel 3 Meses (Top 5)",
                       legend=dict(orientation="h", y=-0.2), height=400)
    st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 5: Implementar renderizar() principal**

```python
def renderizar(dados: dict, periodo: str, pessoa: str, ctx: dict | None = None) -> None:
    """Renderiza página de análise avançada."""
    df = dados.get("extrato")
    if df is None or df.empty:
        st.info("Sem dados para análise.")
        return

    df_filtrado = filtrar_por_pessoa(df, pessoa)
    granularidade = ctx.get("granularidade", "Mês") if ctx else "Mês"
    df_periodo = filtrar_por_periodo(df_filtrado, periodo, granularidade)

    # Sankey
    st.subheader("Fluxo Financeiro")
    dados_sankey = _preparar_dados_sankey(df_periodo)
    if dados_sankey["labels"]:
        fig_sankey = go.Figure(go.Sankey(
            node=dict(
                pad=20, thickness=20, line=dict(color=CORES["fundo"], width=0.5),
                label=dados_sankey["labels"], color=dados_sankey["colors"],
            ),
            link=dict(
                source=dados_sankey["source"], target=dados_sankey["target"],
                value=dados_sankey["value"],
                color=[rgba_cor(dados_sankey["colors"][s], 0.3) for s in dados_sankey["source"]],
            ),
        ))
        fig_sankey.update_layout(**LAYOUT_PLOTLY, title="", height=400)
        st.plotly_chart(fig_sankey, use_container_width=True)
    else:
        st.info("Dados insuficientes para o diagrama Sankey.")

    st.markdown("---")

    # Heatmap
    st.subheader("Intensidade de Gastos")
    dados_heat = _preparar_dados_heatmap(df_periodo)
    if dados_heat["z"]:
        colorscale = [[0, CORES["fundo"]], [0.5, CORES["alerta"]], [1, CORES["negativo"]]]
        fig_heat = go.Figure(go.Heatmap(
            z=dados_heat["z"], x=dados_heat["x"], y=dados_heat["y"],
            colorscale=colorscale, showscale=True,
            hovertemplate="Semana %{x}<br>%{y}<br>R$ %{z:,.2f}<extra></extra>",
        ))
        fig_heat.update_layout(**LAYOUT_PLOTLY, title="", height=300)
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Dados insuficientes para o heatmap.")

    st.markdown("---")

    # Tendências (usa todos os dados, não filtrados por período)
    st.subheader("Tendências por Categoria")
    _renderizar_tendencias(df_filtrado)
```

- [ ] **Step 6: Adicionar citação de filósofo no final**

```python
# "O todo é maior que a soma das partes." -- Aristóteles
```

- [ ] **Step 7: Verificar sintaxe**

```bash
.venv/bin/python -c "import ast; ast.parse(open('src/dashboard/paginas/analise_avancada.py').read()); print('OK')"
.venv/bin/ruff check src/dashboard/paginas/analise_avancada.py --quiet
```

- [ ] **Step 8: Commit**

```bash
git add src/dashboard/paginas/analise_avancada.py
git commit -m "feat: página Análise Avançada -- Sankey, heatmap e tendências"
```

---

### Task 6: Integrar nova aba em app.py + validação visual

**Files:**
- Modify: `src/dashboard/app.py:1-10` (imports), `:176-198` (tabs)

- [ ] **Step 1: Adicionar import**

```python
from src.dashboard.paginas import analise_avancada
```

- [ ] **Step 2: Atualizar st.tabs de 6 para 7**

```python
tab_visao, tab_categorias, tab_extrato, tab_contas, tab_projecoes, tab_metas, tab_analise = st.tabs(
    ["Visão Geral", "Categorias", "Extrato", "Contas", "Projeções", "Metas", "Análise"]
)
```

E adicionar:

```python
with tab_analise:
    analise_avancada.renderizar(dados, periodo, pessoa, ctx)
```

- [ ] **Step 3: Verificar e commitar**

```bash
.venv/bin/ruff check src/dashboard/app.py --quiet
git add src/dashboard/app.py
git commit -m "feat: integrar aba Análise no dashboard (7 abas)"
```

- [ ] **Step 4: Lançar dashboard e validar visualmente via Chrome MCP**

```bash
make dashboard
```

Para cada uma das 7 abas:
- Verificar contraste dos cards (borda + shadow visíveis)
- Verificar espaçamento entre seções (16px margin)
- Verificar fontes >= 13px
- Verificar que zero cores estão hardcoded
- Na aba Análise: Sankey renderiza, heatmap renderiza, tendências renderiza

- [ ] **Step 5: Commit final consolidado (se houver fixes pós-validação)**

```bash
git add -A
git commit -m "fix: ajustes visuais pós-validação da Dupla 2"
```

---

## Verificação Final

1. `make lint` (ruff + acentuação) -- PASS
2. `make process` (pipeline) -- PASS (se dados disponíveis)
3. `python -m src.utils.validator` -- PASS
4. Chrome MCP: 7 abas aprovadas visualmente
5. Gauntlet: 44/44
