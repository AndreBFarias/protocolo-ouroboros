# ruff: noqa: E501
"""Filtros inline por página (UX-U-04).

Helpers que páginas da Onda T podem usar opt-in para renderizar filtros
próprios em vez de depender do expander global ``_filtros_globais_main`` de
``app.py``. Cada helper retorna o valor selecionado e atualiza
``st.session_state``, mantendo compatibilidade com helpers de
``src/dashboard/dados.py`` (``filtrar_por_periodo``, ``filtrar_por_pessoa``,
``filtrar_por_forma_pagamento``, ``filtro_forma_ativo``).

Mockup-fonte: cada tela do redesign tem dropdowns de filtro próprios visíveis
no header (ex.: ``02-extrato.html`` tem período + categoria; ``22-eventos.html``
tem Modo + Período + Pessoa + Categoria).
"""

from __future__ import annotations

from typing import Iterable

FORMAS_PAGAMENTO: list[str] = [
    "Todas",
    "Pix",
    "Débito",
    "Crédito",
    "Boleto",
    "Transferência",
]
GRANULARIDADES: list[str] = ["Dia", "Semana", "Mês", "Ano"]


def renderizar_filtro_periodo(
    dados: dict,
    granularidade_padrao: str = "Mês",
    key_prefix: str = "filtro",
) -> tuple[str, str]:
    """Renderiza dropdown de granularidade + período inline na página.

    Args:
        dados: dict de DataFrames carregado por ``carregar_dados``.
        granularidade_padrao: opção pré-selecionada do selectbox.
        key_prefix: prefixo para chaves de ``session_state`` (use diferente
            do ``seletor_*`` para não colidir com expander global).

    Returns:
        ``(granularidade, periodo)`` selecionados.
    """
    import streamlit as st

    from src.dashboard.dados import (
        obter_anos_disponiveis,
        obter_dias_do_mes,
        obter_meses_disponiveis,
        obter_semanas_do_mes,
    )

    granularidade = st.selectbox(
        "Granularidade",
        GRANULARIDADES,
        index=GRANULARIDADES.index(granularidade_padrao),
        key=f"{key_prefix}_granularidade",
    )
    if granularidade == "Ano":
        opcoes = obter_anos_disponiveis(dados) or ["2026"]
    elif granularidade == "Mês":
        opcoes = obter_meses_disponiveis(dados) or ["2026-04"]
    elif granularidade == "Semana":
        mes_base = (
            obter_meses_disponiveis(dados)[0] if obter_meses_disponiveis(dados) else "2026-04"
        )
        opcoes = obter_semanas_do_mes(dados, mes_base) or ["S1"]
    else:
        mes_base = (
            obter_meses_disponiveis(dados)[0] if obter_meses_disponiveis(dados) else "2026-04"
        )
        opcoes = obter_dias_do_mes(dados, mes_base) or ["2026-04-01"]

    periodo = st.selectbox(
        "Período",
        opcoes,
        index=0,
        key=f"{key_prefix}_periodo",
    )
    return granularidade, periodo


def renderizar_filtro_pessoa(
    opcoes: Iterable[str] | None = None,
    key: str = "filtro_pessoa_inline",
) -> str:
    """Renderiza ``selectbox`` Pessoa.

    Returns:
        Pessoa selecionada (``"Todos"`` ou nome real resolvido em runtime).
    """
    import streamlit as st

    from src.utils.pessoas import nome_de

    if opcoes is None:
        nome_a = nome_de("pessoa_a")
        nome_b = nome_de("pessoa_b")
        opcoes = ["Todos", nome_a, nome_b]
    return st.selectbox("Pessoa", list(opcoes), index=0, key=key)


def renderizar_filtro_forma_pagamento(
    key: str = "filtro_forma_inline",
) -> str | None:
    """Renderiza ``selectbox`` Forma de pagamento e atualiza ``filtro_forma``.

    Returns:
        ``None`` se a opção for ``"Todas"`` (sem filtro), senão o valor.
    """
    import streamlit as st

    forma = st.selectbox(
        "Forma de pagamento",
        FORMAS_PAGAMENTO,
        index=0,
        key=key,
    )
    valor = None if forma == "Todas" else forma
    st.session_state["filtro_forma"] = valor
    return valor


def renderizar_grid_filtros(
    dados: dict,
    *,
    periodo: bool = True,
    pessoa: bool = True,
    forma_pagamento: bool = False,
    granularidade_padrao: str = "Mês",
    key_prefix: str = "filtro_pg",
) -> dict[str, str | None]:
    """Renderiza grid de filtros em colunas Streamlit. Cada página chama com
    os filtros que precisa.

    Returns:
        ``dict`` com chaves ``granularidade``, ``periodo``, ``pessoa``,
        ``forma`` (apenas as solicitadas).
    """
    import streamlit as st

    n_cols = 0
    if periodo:
        n_cols += 2
    if pessoa:
        n_cols += 1
    if forma_pagamento:
        n_cols += 1
    if n_cols == 0:
        return {}

    cols = st.columns(n_cols)
    resultado: dict[str, str | None] = {}
    i = 0
    if periodo:
        with cols[i]:
            g, p = renderizar_filtro_periodo(dados, granularidade_padrao, key_prefix)
            resultado["granularidade"] = g
        i += 1
        with cols[i]:
            resultado["periodo"] = p
        i += 1
    if pessoa:
        with cols[i]:
            resultado["pessoa"] = renderizar_filtro_pessoa(key=f"{key_prefix}_pessoa")
        i += 1
    if forma_pagamento:
        with cols[i]:
            resultado["forma"] = renderizar_filtro_forma_pagamento(key=f"{key_prefix}_forma")
        i += 1
    return resultado


# "Cada lugar tem suas próprias regras." -- Heráclito (paráfrase)
