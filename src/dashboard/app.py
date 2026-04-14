"""Entrypoint principal do dashboard financeiro - Controle de Bordo."""

import sys
from pathlib import Path

import streamlit as st

RAIZ_PROJETO: Path = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.dashboard.dados import (  # noqa: E402
    carregar_dados,
    filtrar_por_mes,
    formatar_moeda,
    obter_meses_disponiveis,
)
from src.dashboard.paginas import categorias, contas, extrato, visao_geral  # noqa: E402

CORES: dict[str, str] = {
    "positivo": "#4ECDC4",
    "negativo": "#FF6B6B",
    "neutro": "#45B7D1",
    "card_fundo": "#1E2130",
}


def _configurar_pagina() -> None:
    """Configura layout e metadados da página."""
    st.set_page_config(
        page_title="Controle de Bordo",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .block-container { padding-top: 1rem; }
        [data-testid="stSidebar"] { background-color: #1E2130; }
        [data-testid="stSidebar"] h1 { color: #4ECDC4; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar(dados: dict) -> tuple[str, str]:
    """Renderiza sidebar com filtros globais e retorna seleções.

    Returns:
        Tupla com (mês selecionado, pessoa selecionada).
    """
    with st.sidebar:
        st.title("Controle de Bordo")
        st.markdown("---")

        meses = obter_meses_disponiveis(dados)

        if not meses:
            st.warning("Nenhum dado disponível.")
            return "", "Todos"

        mes_selecionado: str = st.selectbox(
            "Mês de referência",
            meses,
            index=0,
            key="seletor_mes",
        )

        pessoa: str = st.radio(
            "Pessoa",
            ["Todos", "André", "Vitória"],
            index=0,
            key="seletor_pessoa",
            horizontal=True,
        )

        st.markdown("---")

        _cards_sidebar(dados, mes_selecionado, pessoa)

        return mes_selecionado, pessoa


def _cards_sidebar(dados: dict, mes: str, pessoa: str) -> None:
    """Exibe cards de resumo na sidebar."""
    if "resumo_mensal" not in dados:
        return

    resumo = dados["resumo_mensal"]
    resumo_mes = filtrar_por_mes(resumo, mes)

    if pessoa != "Todos" and "extrato" in dados:
        from src.dashboard.dados import filtrar_por_pessoa

        ext = filtrar_por_pessoa(
            filtrar_por_mes(dados["extrato"], mes), pessoa
        )
        receita = ext[ext["tipo"] == "Receita"]["valor"].sum()
        despesa = ext[ext["tipo"] == "Despesa"]["valor"].sum()
        saldo = receita - despesa
    elif not resumo_mes.empty:
        receita = float(resumo_mes["receita_total"].iloc[0])
        despesa = float(resumo_mes["despesa_total"].iloc[0])
        saldo = float(resumo_mes["saldo"].iloc[0])
    else:
        receita = 0.0
        despesa = 0.0
        saldo = 0.0

    st.markdown(
        _card_html("Receita", formatar_moeda(receita), CORES["positivo"]),
        unsafe_allow_html=True,
    )
    st.markdown(
        _card_html("Despesa", formatar_moeda(despesa), CORES["negativo"]),
        unsafe_allow_html=True,
    )

    cor_saldo = CORES["positivo"] if saldo >= 0 else CORES["negativo"]
    st.markdown(
        _card_html("Saldo", formatar_moeda(saldo), cor_saldo),
        unsafe_allow_html=True,
    )


def _card_html(titulo: str, valor: str, cor: str) -> str:
    """Gera HTML de card compacto para sidebar."""
    return f"""
    <div style="
        background-color: {CORES['card_fundo']};
        border-left: 3px solid {cor};
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
    ">
        <p style="color: #888; font-size: 12px; margin: 0;">{titulo}</p>
        <p style="color: {cor}; font-size: 18px; font-weight: bold; margin: 2px 0 0 0;">{valor}</p>
    </div>
    """


def main() -> None:
    """Função principal do dashboard."""
    _configurar_pagina()

    dados = carregar_dados()

    if not dados:
        st.error("Nenhum dado encontrado. Verifique se o arquivo XLSX existe em data/output/.")
        st.stop()

    mes_selecionado, pessoa = _sidebar(dados)

    if not mes_selecionado:
        st.stop()

    tab_visao, tab_categorias, tab_extrato, tab_contas = st.tabs(
        ["Visão Geral", "Categorias", "Extrato", "Contas"]
    )

    with tab_visao:
        visao_geral.renderizar(dados, mes_selecionado, pessoa)

    with tab_categorias:
        categorias.renderizar(dados, mes_selecionado, pessoa)

    with tab_extrato:
        extrato.renderizar(dados, mes_selecionado, pessoa)

    with tab_contas:
        contas.renderizar(dados, mes_selecionado, pessoa)


if __name__ == "__main__":
    main()


# "A frugalidade inclui todas as outras virtudes." -- Cícero
