"""Drill-down interativo via clique em gráfico Plotly — Sprint 73 (ADR-19).

Helper único `aplicar_drilldown(fig, campo_customdata, tab_destino, key_grafico)`
que renderiza o `fig` com `st.plotly_chart(..., on_select="rerun")`, captura o
ponto clicado via `customdata`, seta `st.query_params` e dispara exatamente UM
`st.rerun()`. O debounce é feito por hash em `st.session_state[f"{key}_last_click_hash"]`
para impedir loop infinito (rerun re-invoca on_select com o mesmo estado).

Leitor auxiliar `ler_filtros_da_url()` é chamado por `app.py` no início do
ciclo de renderização para popular `st.session_state` a partir de URLs
compartilháveis como `?tab=Extrato&categoria=Farmácia`.

Requisitos:
  - Streamlit >= 1.31 (on_select nativo).
  - Traces do Plotly com `customdata` populado pelo caller.
  - `key_grafico` único por gráfico (obrigatório para o `on_select` funcionar).
"""

from __future__ import annotations

from typing import Any

# Lista fechada de campos que o drill-down reconhece como filtros válidos
# (espelha as colunas relevantes da aba Extrato).
CAMPOS_FILTRO_RECONHECIDOS: frozenset[str] = frozenset(
    {
        "mes",
        "mes_ref",
        "categoria",
        "classificacao",
        "fornecedor",
        "banco",
        "banco_origem",
        "local",
        "forma",
        "forma_pagamento",
    }
)

# Chaves canônicas que o Extrato usa para ler filtros vindos do drill-down.
CHAVE_SESSION_ABA_ATIVA: str = "aba_ativa_requerida"


def _session_state() -> Any:
    """Devolve `st.session_state` quando streamlit está disponível."""
    import streamlit as st

    return st.session_state


def _extrair_valor_do_ponto(ponto: dict) -> Any:
    """Extrai o valor canônico do ponto clicado no Plotly."""
    valor = ponto.get("customdata")
    if valor is None:
        valor = ponto.get("label")
    if valor is None:
        valor = ponto.get("x")
    return valor


def aplicar_drilldown(
    fig: Any,
    campo_customdata: str,
    tab_destino: str,
    key_grafico: str,
) -> None:
    """Renderiza `fig` com drill-down e navega para aba filtrada ao clicar.

    Uso:

        fig = px.treemap(df, path=["classificacao", "categoria"], values="valor")
        fig.update_traces(customdata=df["categoria"])
        aplicar_drilldown(fig, "categoria", "Extrato", key_grafico="treemap_categ")

    - `campo_customdata`: nome do filtro que será gravado em `query_params`
      (ex: "categoria" ou "mes_ref").
    - `tab_destino`: nome da aba para onde navegar (ex: "Extrato").
    - `key_grafico`: chave única do gráfico; sem ela `on_select` não funciona
      no Streamlit 1.31+.
    """
    if not key_grafico:
        raise ValueError("key_grafico é obrigatório para on_select funcionar")
    import streamlit as st

    fig.update_layout(clickmode="event+select")
    resultado = st.plotly_chart(
        fig,
        use_container_width=True,
        key=key_grafico,
        on_select="rerun",
    )

    if not isinstance(resultado, dict):
        return
    pontos = resultado.get("selection", {}).get("points", []) or []
    if not pontos:
        return

    ponto = pontos[0]
    valor = _extrair_valor_do_ponto(ponto)
    if valor is None:
        return
    valor_str = str(valor)

    click_hash = f"{campo_customdata}={valor_str}|tab={tab_destino}"
    chave_debounce = f"{key_grafico}_last_click_hash"

    estado = _session_state()
    if estado.get(chave_debounce) == click_hash:
        return  # já processado: evita loop de rerun
    estado[chave_debounce] = click_hash

    # Normaliza campo: "mes" e "mes_ref" são intercambiáveis; idem "banco"/"banco_origem"
    # etc. O Extrato decide qual coluna usar ao aplicar o filtro.
    st.query_params[campo_customdata] = valor_str
    st.query_params["tab"] = tab_destino
    st.rerun()


def ler_filtros_da_url() -> None:
    """Copia `st.query_params` para `st.session_state` para filtros conhecidos.

    Deve ser chamado no início de `app.py` antes de renderizar abas. Idempotente:
    se o param não existe na URL, a session_state não é alterada.
    """
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        return

    qp = st.query_params
    # Converte `st.query_params` num dict simples para evitar surpresas com
    # streamlit retornando listas para keys duplicadas.
    for campo in CAMPOS_FILTRO_RECONHECIDOS:
        if campo in qp:
            valor = qp[campo]
            if isinstance(valor, list):
                valor = valor[0] if valor else ""
            st.session_state[f"filtro_{campo}"] = str(valor)

    if "tab" in qp:
        valor_tab = qp["tab"]
        if isinstance(valor_tab, list):
            valor_tab = valor_tab[0] if valor_tab else ""
        st.session_state[CHAVE_SESSION_ABA_ATIVA] = str(valor_tab)


def filtros_ativos_do_session_state() -> dict[str, str]:
    """Extrai filtros vindos de drill-down do session_state (Sprint 73).

    Usado pela aba Extrato para aplicar filtros e renderizar breadcrumb.
    Devolve dict apenas com chaves com valor não-vazio.
    """
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        return {}

    resultado: dict[str, str] = {}
    for campo in CAMPOS_FILTRO_RECONHECIDOS:
        chave = f"filtro_{campo}"
        if chave in st.session_state and st.session_state[chave]:
            resultado[campo] = str(st.session_state[chave])
    return resultado


def limpar_filtro(campo: str) -> None:
    """Remove um filtro específico do session_state e do query_params."""
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        return

    chave_sessao = f"filtro_{campo}"
    if chave_sessao in st.session_state:
        del st.session_state[chave_sessao]
    if campo in st.query_params:
        del st.query_params[campo]


# "Clicar num número e ir até a transação é o mínimo." — Andre, 2026-04-21
