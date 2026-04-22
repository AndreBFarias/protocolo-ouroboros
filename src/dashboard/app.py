"""Entrypoint principal do dashboard financeiro - Protocolo Ouroboros."""

import sys
from pathlib import Path

import streamlit as st

RAIZ_PROJETO: Path = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.dashboard.componentes.drilldown import ler_filtros_da_url  # noqa: E402
from src.dashboard.dados import (  # noqa: E402
    CAMINHO_XLSX,
    carregar_dados,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    formatar_moeda,
    obter_anos_disponiveis,
    obter_meses_disponiveis,
)
from src.dashboard.paginas import (  # noqa: E402
    analise_avancada,
    busca,
    catalogacao,
    categorias,
    contas,
    extrato,
    grafo_obsidian,
    irpf,
    metas,
    projecoes,
    visao_geral,
)
from src.dashboard.tema import (  # noqa: E402
    CORES,
    card_sidebar_html,
    css_global,
    logo_sidebar_html,
)


def _configurar_pagina() -> None:
    """Configura layout e metadados da página."""
    st.set_page_config(
        page_title="Protocolo Ouroboros",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(css_global(), unsafe_allow_html=True)


def _sidebar(dados: dict) -> tuple[str, str, str]:
    """Renderiza sidebar com filtros globais e retorna seleções.

    Returns:
        Tupla com (período selecionado, pessoa, granularidade).
    """
    with st.sidebar:
        # Sprint 76: logo acima do título, centralizados, cacheado em session_state.
        logo_html = logo_sidebar_html()
        if logo_html:
            st.markdown(logo_html, unsafe_allow_html=True)
        else:
            st.title("Protocolo Ouroboros")

        if CAMINHO_XLSX.exists():
            import os
            from datetime import datetime

            mtime = os.path.getmtime(CAMINHO_XLSX)
            ultima = datetime.fromtimestamp(mtime)
            st.caption(f"Dados de {ultima.strftime('%d/%m/%Y às %H:%M')}")

        st.markdown("---")

        meses = obter_meses_disponiveis(dados)

        if not meses:
            st.warning("Nenhum dado disponível.")
            return "", "Todos", "Mês"

        granularidade: str = st.selectbox(
            "Granularidade",
            ["Dia", "Semana", "Mês", "Ano"],
            index=2,
            key="seletor_granularidade",
        )

        if granularidade == "Ano":
            anos = obter_anos_disponiveis(dados)
            periodo: str = st.selectbox(
                "Período",
                anos,
                index=0,
                key="seletor_periodo",
            )
        else:
            mes_base: str = st.selectbox(
                "Mês",
                meses,
                index=0,
                key="seletor_mes_base",
            )

            if granularidade == "Semana":
                from src.dashboard.dados import obter_semanas_do_mes

                semanas = obter_semanas_do_mes(dados, mes_base)
                if semanas:
                    periodo = st.selectbox(
                        "Semana",
                        semanas,
                        index=0,
                        key="seletor_detalhe",
                    )
                else:
                    periodo = mes_base
            elif granularidade == "Dia":
                from src.dashboard.dados import obter_dias_do_mes

                dias = obter_dias_do_mes(dados, mes_base)
                if dias:
                    periodo = st.selectbox(
                        "Dia",
                        dias,
                        index=0,
                        key="seletor_detalhe",
                    )
                else:
                    periodo = mes_base
            else:
                periodo = mes_base

        pessoa: str = st.selectbox(
            "Pessoa",
            ["Todos", "André", "Vitória"],
            index=0,
            key="seletor_pessoa",
        )

        # Sprint 72: filtro global por forma de pagamento. O valor é
        # salvo em session_state sob a chave "filtro_forma"; cada página
        # consulta via dados.filtro_forma_ativo() e aplica via
        # dados.filtrar_por_forma_pagamento().
        forma_sel: str = st.selectbox(
            "Forma de pagamento",
            ["Todas", "Pix", "Débito", "Crédito", "Boleto", "Transferência"],
            index=0,
            key="seletor_forma_pagamento",
        )
        st.session_state["filtro_forma"] = (
            None if forma_sel == "Todas" else forma_sel
        )

        st.markdown("---")

        _cards_sidebar(dados, periodo, pessoa, granularidade)

        return periodo, pessoa, granularidade


def _cards_sidebar(dados: dict, periodo: str, pessoa: str, granularidade: str) -> None:
    """Exibe cards de resumo na sidebar."""
    if "extrato" not in dados:
        return

    from src.dashboard.dados import filtrar_por_forma_pagamento, filtro_forma_ativo

    ext = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(
            filtrar_por_periodo(dados["extrato"], granularidade, periodo),
            pessoa,
        ),
        filtro_forma_ativo(),
    )
    receita = ext[ext["tipo"] == "Receita"]["valor"].sum()
    despesa = ext[ext["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum()
    saldo = receita - despesa

    st.markdown(
        card_sidebar_html("Receita", formatar_moeda(receita), CORES["positivo"]),
        unsafe_allow_html=True,
    )
    st.markdown(
        card_sidebar_html("Despesa", formatar_moeda(despesa), CORES["negativo"]),
        unsafe_allow_html=True,
    )

    cor_saldo = CORES["positivo"] if saldo >= 0 else CORES["negativo"]
    st.markdown(
        card_sidebar_html("Saldo", formatar_moeda(saldo), cor_saldo),
        unsafe_allow_html=True,
    )


def main() -> None:
    """Função principal do dashboard."""
    _configurar_pagina()

    # Sprint 73 (ADR-19): lê filtros de drill-down da URL antes de renderizar
    # qualquer componente, populando session_state com chaves filtro_*.
    ler_filtros_da_url()

    dados = carregar_dados()

    if not dados:
        st.error("Nenhum dado encontrado. Verifique se o arquivo XLSX existe em data/output/.")
        st.stop()

    periodo, pessoa, granularidade = _sidebar(dados)

    if not periodo:
        st.stop()

    (
        tab_visao,
        tab_categorias,
        tab_extrato,
        tab_contas,
        tab_projecoes,
        tab_metas,
        tab_analise,
        tab_irpf,
        tab_catalogacao,
        tab_busca,
        tab_grafo_obsidian,
    ) = st.tabs(
        [
            "Visão Geral",
            "Categorias",
            "Extrato",
            "Contas",
            "Projeções",
            "Metas",
            "Análise",
            "IRPF",
            "Catalogação",
            "Busca Global",
            "Grafo + Obsidian",
        ]
    )

    ctx = {"granularidade": granularidade, "periodo": periodo}

    with tab_visao:
        visao_geral.renderizar(dados, periodo, pessoa, ctx)

    with tab_categorias:
        categorias.renderizar(dados, periodo, pessoa, ctx)

    with tab_extrato:
        extrato.renderizar(dados, periodo, pessoa, ctx)

    with tab_contas:
        contas.renderizar(dados, periodo, pessoa)

    with tab_projecoes:
        projecoes.renderizar(dados, periodo, pessoa)

    with tab_metas:
        metas.renderizar(dados, periodo, pessoa)

    with tab_analise:
        analise_avancada.renderizar(dados, periodo, pessoa, ctx)

    with tab_irpf:
        irpf.renderizar(dados, periodo, pessoa, ctx)

    with tab_catalogacao:
        catalogacao.renderizar(dados, periodo, pessoa, ctx)

    with tab_busca:
        busca.renderizar(dados, periodo, pessoa, ctx)

    with tab_grafo_obsidian:
        grafo_obsidian.renderizar(dados, periodo, pessoa, ctx)


if __name__ == "__main__":
    main()


# "A frugalidade inclui todas as outras virtudes." -- Cícero
