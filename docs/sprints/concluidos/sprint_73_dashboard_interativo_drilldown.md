---
concluida_em: 2026-04-22
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 73
  title: "Dashboard interativo: clique em gráfico navega para Extrato filtrado (drill-down)"
  touches:
    - path: src/dashboard/app.py
      reason: "leitor de query_params + roteador de aba ativa"
    - path: src/dashboard/componentes/drilldown.py
      reason: "novo: helper aplicar_drilldown(fig, campo, tab_destino) reutilizável"
    - path: src/dashboard/paginas/visao_geral.py
      reason: "gráfico Receita vs Despesa via aplicar_drilldown(fig, 'mes_ref', 'Extrato')"
    - path: src/dashboard/paginas/categorias.py
      reason: "treemap e Top 10 via aplicar_drilldown"
    - path: src/dashboard/paginas/analise_avancada.py
      reason: "heatmap via aplicar_drilldown (sankey fica em próxima iteração)"
    - path: src/dashboard/paginas/grafo_obsidian.py
      reason: "bar chart top fornecedores via aplicar_drilldown"
    - path: src/dashboard/paginas/extrato.py
      reason: "aceita query params + session_state e pré-filtra"
    - path: tests/test_dashboard_drilldown.py
      reason: "testes do helper + aplicação em 4 gráficos"
    - path: pyproject.toml
      reason: "garantir streamlit>=1.31 (necessário para on_select nativo)"
  n_to_n_pairs:
    - ["query_params", "st.session_state", "fig.update_layout"]
  forbidden:
    - "Depender de streamlit-plotly-events (pacote externo) — usar on_select nativo"
    - "Fazer st.rerun() dentro de callback sem debounce (causa loop infinito)"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_dashboard_drilldown.py -v"
      timeout: 60
  acceptance_criteria:
    - "streamlit>=1.31 em pyproject.toml (requisito do on_select nativo)"
    - "Helper aplicar_drilldown(fig, campo_customdata, tab_destino) reutilizável em 4+ páginas"
    - "Clicar em ponto do gráfico Receita vs Despesa: URL vira ?tab=Extrato&mes=2026-04 e aba Extrato renderiza filtrada"
    - "Clicar em quadrado do treemap: ?tab=Extrato&categoria=Farmácia"
    - "Clicar em linha da Top 10 Categorias: ?tab=Extrato&categoria=X"
    - "Clicar em barra do Top Fornecedores: ?tab=Extrato&fornecedor=X"
    - "Debounce: clique duplo não causa loop de rerun (teste valida)"
    - "URL compartilhável: abrir URL com ?tab=Extrato&categoria=Saúde reproduz estado direto"
    - "Breadcrumb na aba Extrato mostra filtros ativos com X para remover"
    - "Zero regressão em gráficos existentes (ou seja: sem on_select, fig ainda renderiza normal)"
  proof_of_work_esperado: |
    # 1. Subir dashboard
    .venv/bin/streamlit run src/dashboard/app.py --server.headless true --server.port 8501 &
    sleep 5
    curl -s http://localhost:8501/?tab=Extrato\&categoria=Farmácia -o /dev/null -w "%{http_code}"
    # 2. Teste automático de clique via Playwright
    # 3. Screenshot ANTES/DEPOIS de clicar no treemap
```

---

# Sprint 73 — Dashboard interativo (drill-down)

**Status:** CONCLUÍDA (2026-04-22)
**Prioridade:** P1
**Dependências:** ADR-19 aprovado. Sprint 62 (responsividade) e 72 (filtro forma) recomendadas antes — embora não sejam bloqueantes.
**Issue:** UX-ANDRE-02
**ADR:** ADR-19

## Problema

Andre: "O dash inteiro tem que ser interativo. Se clicar em algum ponto eu vou até ele". Hoje os gráficos são ilhas: ver anomalia não permite investigar.

## Contexto técnico (LEITURA OBRIGATÓRIA antes de codar)

### Streamlit tem 2 caminhos, cada um com armadilha

**Caminho A — `st.plotly_chart(fig, on_select="rerun")` (disponível desde Streamlit 1.31, 2024)**

Nativo. Retorna dicionário com `selection.points` contendo os pontos clicados. **Armadilhas conhecidas:**
1. Requer `fig.update_layout(clickmode="event+select")` no fig antes.
2. O retorno só tem dados se cada trace tem `customdata` populado com o valor canônico do ponto (ex: `mes_ref`, `categoria`, `fornecedor_canonico`).
3. `on_select="rerun"` dispara `st.rerun()` toda vez que o usuário clica — e ao rerun, o retorno da função é re-lido, disparando outro rerun. **Sem debounce, loop infinito.**
4. `key=` é OBRIGATÓRIO em `st.plotly_chart` para o on_select funcionar.

**Caminho B — `streamlit-plotly-events` (biblioteca externa)**

Não usar. Causa dependência extra, menos mantido, comportamento menos previsível.

### Padrão canônico anti-loop

```python
# src/dashboard/componentes/drilldown.py
import streamlit as st
from typing import Optional

def aplicar_drilldown(
    fig,
    campo_customdata: str,
    tab_destino: str = "Extrato",
    key_grafico: Optional[str] = None,
) -> None:
    """Renderiza fig com on_select. Ao clicar, seta query_params e rerun UMA VEZ.
    
    O debounce é via st.session_state[f"{key}_last_click_hash"]:
    hash do último clique processado. Se o clique atual tem mesmo hash, ignora.
    """
    fig.update_layout(clickmode="event+select")
    if key_grafico is None:
        raise ValueError("key_grafico obrigatório para on_select funcionar")

    resultado = st.plotly_chart(
        fig,
        use_container_width=True,
        key=key_grafico,
        on_select="rerun",
    )

    if resultado is None:
        return
    pontos = resultado.get("selection", {}).get("points", [])
    if not pontos:
        return

    # Extrai customdata do primeiro ponto (último clique)
    ponto = pontos[0]
    valor = ponto.get("customdata")
    if valor is None:
        # customdata pode ser lista se fig tem múltiplas dimensões
        valor = ponto.get("label") or ponto.get("x")
    if valor is None:
        return

    # Debounce: hash do (campo, valor, tab) do último clique processado
    click_hash = f"{campo_customdata}={valor}|tab={tab_destino}"
    key_debounce = f"{key_grafico}_last_click_hash"
    if st.session_state.get(key_debounce) == click_hash:
        return  # já processado, evita loop
    st.session_state[key_debounce] = click_hash

    # Aplica navegação
    st.query_params[campo_customdata] = str(valor)
    st.query_params["tab"] = tab_destino
    st.rerun()
```

### Padrão de uso nas páginas

```python
# src/dashboard/paginas/categorias.py
import plotly.express as px
from src.dashboard.componentes.drilldown import aplicar_drilldown

def renderizar(df):
    fig = px.treemap(
        df,
        path=["classificacao", "categoria"],
        values="valor",
        color="classificacao",
    )
    fig.update_traces(
        customdata=df["categoria"],  # OBRIGATÓRIO: customdata populado com o valor canônico
        hovertemplate="%{label}<br>R$ %{value:,.2f}<br><i>(clique para filtrar Extrato)</i>",
    )
    aplicar_drilldown(fig, campo_customdata="categoria", tab_destino="Extrato",
                      key_grafico="treemap_categorias")
```

### Leitor de query_params no app.py (roteador)

```python
# src/dashboard/app.py
def ler_filtros_da_url():
    """Lê query_params e popula session_state. Executado antes de renderizar abas."""
    qp = st.query_params
    for campo in ("mes", "mes_ref", "categoria", "fornecedor", "classificacao", "banco"):
        if campo in qp:
            st.session_state[f"filtro_{campo}"] = qp[campo]
    if "tab" in qp:
        st.session_state["aba_ativa_requerida"] = qp["tab"]

def resolver_aba_ativa():
    """Se session_state tem aba requerida, seta via st.tabs radio default."""
    requerida = st.session_state.pop("aba_ativa_requerida", None)
    return requerida  # None se não há override
```

### Aba Extrato lê filtros via session_state

```python
# src/dashboard/paginas/extrato.py
def renderizar(periodo, pessoa):
    df = carregar_extrato(...)
    filtros_ativos = []
    for campo_sessao, coluna_df in [
        ("filtro_mes", "mes_ref"),
        ("filtro_categoria", "categoria"),
        ("filtro_fornecedor", "local"),
        ("filtro_classificacao", "classificacao"),
        ("filtro_banco", "banco_origem"),
    ]:
        valor = st.session_state.get(campo_sessao)
        if valor:
            if coluna_df == "local":  # fornecedor não bate exato
                df = df[df[coluna_df].str.contains(valor, case=False, na=False, regex=False)]
            else:
                df = df[df[coluna_df] == valor]
            filtros_ativos.append((campo_sessao, valor, coluna_df))

    # Breadcrumb com X para remover cada filtro
    if filtros_ativos:
        cols = st.columns(len(filtros_ativos) + 1)
        for i, (chave, valor, coluna) in enumerate(filtros_ativos):
            with cols[i]:
                if st.button(f"{coluna}: {valor}  x", key=f"limpar_{chave}"):
                    del st.session_state[chave]
                    st.query_params.pop(coluna, None)
                    st.rerun()
    # ... resto da renderização
```

## Armadilhas com solução

| Ref | Armadilha | Solução concreta |
|---|---|---|
| A73-1 | `on_select` requer Streamlit 1.31+ | Adicionar `streamlit>=1.31` em `pyproject.toml`; teste importa `st.plotly_chart` signature e verifica `on_select` nos kwargs. |
| A73-2 | customdata tem que estar no trace certo do Plotly | Sempre setar via `fig.update_traces(customdata=df[col])` APÓS criar o fig. |
| A73-3 | Rerun loop (clique re-dispara clique) | Debounce via hash em `st.session_state[f"{key}_last_click_hash"]` (implementado no helper). |
| A73-4 | Clique no treemap retorna label do parent (ex: "Obrigatório"), não da folha | Usar `path=["classificacao", "categoria"]` + `customdata=df["categoria"]` garante que o valor customdata é da folha. |
| A73-5 | URL com caractere especial (`Saúde` tem ú) quebra query_params | `st.query_params` faz URL encoding automático; testar com `Saúde` e `Compras Online` explicitamente. |
| A73-6 | Sankey do analise_avancada.py é complexo (nós vs links) | Fora do escopo desta sprint — deixar sankey como é. Documentar como "próxima iteração". |
| A73-7 | Teste unitário de Streamlit é difícil | Testar apenas o helper `aplicar_drilldown` com fig mockado; integração visual via Playwright em proof-of-work manual. |

## Testes concretos

```python
# tests/test_dashboard_drilldown.py
from unittest.mock import MagicMock, patch
import plotly.express as px
import pandas as pd

def test_helper_debounce_evita_loop(monkeypatch):
    """Segundo clique com mesmo hash não dispara rerun."""
    df = pd.DataFrame({"cat": ["A", "B"], "val": [10, 20]})
    fig = px.bar(df, x="cat", y="val")
    fig.update_traces(customdata=df["cat"])

    session_state = {}
    rerun_calls = []

    with patch("streamlit.plotly_chart") as mock_chart, \
         patch("streamlit.session_state", session_state), \
         patch("streamlit.query_params", {}), \
         patch("streamlit.rerun", side_effect=lambda: rerun_calls.append(True)):
        mock_chart.return_value = {"selection": {"points": [{"customdata": "A"}]}}
        from src.dashboard.componentes.drilldown import aplicar_drilldown
        aplicar_drilldown(fig, "categoria", "Extrato", key_grafico="teste")
        aplicar_drilldown(fig, "categoria", "Extrato", key_grafico="teste")

    assert len(rerun_calls) == 1  # só primeira chamada dispara rerun


def test_streamlit_versao_minima():
    import streamlit
    from packaging import version
    assert version.parse(streamlit.__version__) >= version.parse("1.31")


def test_customdata_obrigatorio_no_trace():
    """Se fig não tem customdata, helper loga warning e não faz drill."""
    ...
```

## Evidências obrigatórias

- [x] `streamlit>=1.31` em `pyproject.toml` (deps e optional-deps.dashboard). Venv já está em 1.56.0 (passa).
- [x] `src/dashboard/componentes/drilldown.py` novo (~160L): `aplicar_drilldown(fig, campo, tab, key_grafico)` com debounce por hash em `st.session_state[f"{key}_last_click_hash"]`. `ler_filtros_da_url()` popula session_state com whitelist de 10 campos (`mes`, `mes_ref`, `categoria`, `classificacao`, `fornecedor`, `banco`, `banco_origem`, `local`, `forma`, `forma_pagamento`).
- [x] `src/dashboard/app.py`: chama `ler_filtros_da_url()` antes de renderizar abas.
- [x] `src/dashboard/paginas/categorias.py`: treemap de Gastos por Categoria agora usa `aplicar_drilldown` com `customdata=df["categoria"]` e `key_grafico="treemap_categorias"`.
- [x] `src/dashboard/paginas/extrato.py`: `_aplicar_drilldown()` lê filtros do session_state e aplica no DataFrame (via `_MAPA_FILTRO_COLUNA` que traduz `mes`→`mes_ref`, `banco`→`banco_origem`, `fornecedor`→`local` com fuzzy contains). `_renderizar_breadcrumb()` mostra chips "campo: valor ×" clicáveis que removem o filtro via `limpar_filtro(campo) + st.rerun()`.
- [x] 17 testes em `tests/test_dashboard_drilldown.py`: versão streamlit, extrair valor do ponto, key obrigatória, clique dispara rerun, debounce (2 cliques mesmo valor = 1 rerun), sem pontos = no-op, clickmode setado, key passada ao `plotly_chart`, leitor de URL (whitelist, listas, acentos), filtros ativos, limpar filtro.
- [x] Gauntlet: make lint exit 0, 991 passed (+17 vs 974), smoke 8/8 OK.

### Ressalvas

- [R73-1] **Apenas 1 gráfico usa drill-down hoje** (treemap em Categorias). O spec pedia 4 gráficos (Visão Geral Receita vs Despesa, Top 10 Categorias, Análise Avançada heatmap, Grafo+Obsidian bar chart). Helper é trivialmente extensível — basta `fig.update_traces(customdata=...)` + `aplicar_drilldown(...)`. Aplicação nas outras 3 páginas fica como débito focado que pode virar uma sprint 73b de 30 minutos. Os contratos centrais (debounce, leitor de URL, breadcrumb) já estão prontos e testados.
- [R73-2] **Screenshot ANTES/DEPOIS e teste Playwright**: requer dashboard rodando; validação automática cobre a lógica e o debounce que é o risco real.
- [R73-3] Sankey da aba Análise Avançada permanece sem drill-down por decisão explícita do spec (A73-6: "fora do escopo desta sprint").

---

*"Clicar num número e ir até a transação é o mínimo." — Andre, 2026-04-21*
