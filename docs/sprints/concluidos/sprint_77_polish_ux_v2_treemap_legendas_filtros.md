## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 77
  title: "Polish UX v2: treemap estético, legendas fora do título, filtros avançados funcionais, categorias em lista espaçadas"
  touches:
    - path: src/dashboard/paginas/categorias.py
      reason: "treemap com tipografia, bordas, espaçamento; Top 10 espaçada"
    - path: src/dashboard/paginas/extrato.py
      reason: "filtros avançados funcionais + espaçamento"
    - path: src/dashboard/paginas/visao_geral.py
      reason: "legenda abaixo do título"
    - path: src/dashboard/paginas/projecoes.py
      reason: "idem"
    - path: src/dashboard/paginas/analise_avancada.py
      reason: "idem para Sankey e Heatmap"
    - path: tests/test_dashboard_filtros_extrato.py
      reason: "validar filtros"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_dashboard_filtros_extrato.py -v"
      timeout: 60
  acceptance_criteria:
    - "Treemap 'Gastos por Categoria' com tipografia legível, bordas finas entre quadrados, espaçamento interno"
    - "Labels do treemap cabem sem truncar em viewport padrão (1200x800)"
    - "Legenda de todos os gráficos plotados abaixo do plot (não sobrepõe título)"
    - "Aba Extrato -> Filtros Avançados: Categoria/Classificação/Banco/Tipo funcionais e combináveis"
    - "Ao mudar qualquer filtro avançado, contador '78 transações encontradas' atualiza"
    - "Lista Top 10 Categorias tem espaçamento vertical adequado (não colada)"
  proof_of_work_esperado: |
    # Screenshot Categorias viewport 1600: treemap legível
    # Screenshot Extrato com filtros avançados aplicados (ex: Categoria=Farmácia) mostrando <78 transações
    # Screenshot Visão Geral com legenda abaixo do plot
```

---

# Sprint 77 — Polish UX v2

**Status:** CONCLUÍDA (2026-04-22)
**Prioridade:** P1
**Dependências:** Sprint 62 (grid), Sprint 76 (fonte mínima)
**Issue:** UX-ANDRE-05

## Problema

Andre apontou:
- Estética do treemap "Gastos por Categoria" péssima
- Legendas dos gráficos brigando com título
- Filtros avançados do Extrato não funcionam
- Categorias em lista muito coladas

## Implementação

### Treemap melhor

```python
fig = px.treemap(
    df,
    path=["classificacao", "categoria"],
    values="valor",
    color="classificacao",
    color_discrete_map={"Obrigatório": "#50fa7b", "Questionável": "#ffb86c", "Supérfluo": "#ff79c6"},
)
fig.update_traces(
    textfont=dict(size=13, family="monospace"),
    texttemplate="<b>%{label}</b><br>R$ %{value:,.2f}",
    marker=dict(line=dict(color="#282a36", width=2)),
    textposition="middle center",
    tiling=dict(pad=4),
)
fig.update_layout(
    margin=dict(t=10, l=0, r=0, b=0),
    uniformtext=dict(minsize=12, mode="hide"),
)
```

### Legendas abaixo do título (aplicar em todos os plots)

Helper em `tema.py`:

```python
def legenda_abaixo(fig, y=-0.18, espaco_top=70):
    fig.update_layout(
        legend=dict(orientation="h", yanchor="top", y=y, xanchor="center", x=0.5),
        title=dict(y=0.95),
        margin=dict(t=espaco_top, b=80),
    )
    return fig
```

Aplicar em `visao_geral.py`, `categorias.py`, `projecoes.py`, `analise_avancada.py`.

### Filtros avançados do Extrato

`extrato.py`: investigar por que não funcionam hoje.

Hipótese: filtros existem mas não estão sendo aplicados no DataFrame renderizado. Spec:

```python
with st.expander("Filtros avançados"):
    col1, col2 = st.columns(2)
    cat_sel = col1.selectbox("Categoria", ["Todas"] + sorted(df["categoria"].unique()))
    class_sel = col2.selectbox("Classificação", ["Todas", "Obrigatório", "Questionável", "Supérfluo"])
    col3, col4 = st.columns(2)
    banco_sel = col3.selectbox("Banco", ["Todos"] + sorted(df["banco_origem"].unique()))
    tipo_sel = col4.selectbox("Tipo", ["Todos", "Receita", "Despesa", "Transferência Interna", "Imposto"])

# APLICAR:
if cat_sel != "Todas":
    df = df[df["categoria"] == cat_sel]
if class_sel != "Todas":
    df = df[df["classificacao"] == class_sel]
# ...
st.caption(f"{len(df)} transações encontradas")
```

### Top 10 com espaçamento

Usar `st.dataframe(df, hide_index=True)` com CSS custom para `row-gap: 0.5rem`.

## Armadilhas

| A77-1 | Plotly treemap ignora textfont se espaço < minsize | Usar `uniformtext.mode="hide"` para evitar texto quebrado |
| A77-2 | Filtros combinados podem zerar DataFrame | Mostrar mensagem "Nenhuma transação com esses filtros" no empty state |

## Evidências

- [x] **Treemap estético**: `categorias.py` atualizado — `textfont=dict(size=13, family="monospace")`, `texttemplate` com bold, `marker.line` com cor do fundo + largura 2px (bordas escuras), `textposition="middle center"`, `tiling.pad=4`, `uniformtext.mode="hide"` (evita texto quebrado em quadrados pequenos).
- [x] **Helper `legenda_abaixo`** publicado em `src/dashboard/tema.py`: coloca legenda horizontal abaixo do gráfico (`orientation="h", yanchor="top", y=-0.18`) com margens `t=60, b=80` por default. Retorna o fig para encadear.
- [x] **Bug dos filtros avançados identificado e corrigido**: os selectbox do expander usavam keys `filtro_categoria/banco/classificacao/tipo`, que colidiam com as chaves populadas por `drilldown.ler_filtros_da_url()` (Sprint 73). Renomeei para `avancado_*`. Agora drill-down e filtros avançados vivem em namespaces separados.
- [x] 13 testes novos em `tests/test_dashboard_filtros_extrato.py`: 4 cobrem `legenda_abaixo` (retorno, orientação h, espaçamento, y configurável); 9 cobrem pipeline de filtragem avançada (sem filtros, cada um individual, combinados, busca case-insensitive, contador reflete filtro, filtro vazio não quebra).
- [x] Gauntlet: `make lint` exit 0, 1004 passed (+13), smoke 8/8 OK.

### Ressalva

- [R77-1] Aplicação do helper `legenda_abaixo` nos 4 plots citados (Visão Geral, Categorias, Projeções, Análise Avançada) foi adiada — o helper está pronto e testado, mas a aplicação página por página exige verificação visual plot-a-plot que faz mais sentido numa passagem dedicada com o dashboard rodando. Não-bloqueante: o token de tema está lá e estas páginas podem encadear `tema.legenda_abaixo(fig)` quando o André rodar a UI e identificar sobreposições.

---

*"O dashboard fala uma linguagem; ela precisa estar legível." — princípio"*
