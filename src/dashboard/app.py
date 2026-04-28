"""Entrypoint principal do dashboard financeiro - Protocolo Ouroboros."""

import sys
from pathlib import Path

import streamlit as st

RAIZ_PROJETO: Path = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.dashboard.componentes.busca_global_sidebar import (  # noqa: E402
    renderizar_input_busca,
)
from src.dashboard.componentes.drilldown import (  # noqa: E402
    CHAVE_SESSION_ABA_ATIVA,
    CHAVE_SESSION_CLUSTER_ATIVO,
    CLUSTERS_VALIDOS,
    gerar_html_ativar_aba,
    ler_filtros_da_url,
)
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
    completude,
    contas,
    extrato,
    grafo_obsidian,
    home_analise,
    home_dinheiro,
    home_docs,
    home_metas,
    irpf,
    metas,
    pagamentos,
    projecoes,
    revisor,
    visao_geral,
)
from src.dashboard.tema import (  # noqa: E402
    CORES,
    card_sidebar_html,
    css_global,
    logo_sidebar_html,
)

# Sprint 100: ordem canônica das abas dentro de cada cluster. Replica a ordem
# usada nas chamadas `st.tabs(...)` em `main()` -- precisa bater 1:1 porque o
# JS injetado por `gerar_html_ativar_aba` navega o DOM por índice. Manter os
# dois sincronizados é responsabilidade desta constante; mudar a ordem em um
# lado sem o outro quebra deep-link silenciosamente.
ABAS_POR_CLUSTER: dict[str, list[str]] = {
    # Sprint UX-123: cluster Home ganhou 4 mini-views cross-area filtradas
    # por dia mais recente disponível. Sprint UX-125: tabs renomeadas para
    # espelhar nomes dos clusters-irmãos (sem sufixo "hoje" repetitivo).
    # Visão Geral permanece em índice 0 (default da URL antiga). Como
    # "Finanças/Documentos/Análise/Metas" também são nomes de clusters
    # próprios, MAPA_ABA_PARA_CLUSTER em drilldown.py registra apenas
    # cluster canônico para essas chaves; as tabs do Home são acessadas
    # com ?cluster=Home&tab=<X> explícito.
    "Home": [
        "Visão Geral",
        "Finanças",
        "Documentos",
        "Análise",
        "Metas",
    ],
    # Sprint UX-125: cluster "Dinheiro" renomeado para "Finanças" (termo
    # mais profissional). Backward-compat via CLUSTER_ALIASES em drilldown.py.
    "Finanças": ["Extrato", "Contas", "Pagamentos", "Projeções"],
    "Documentos": [
        "Busca Global",
        "Catalogação",
        "Completude",
        "Revisor",
        "Grafo + Obsidian",
    ],
    "Análise": ["Categorias", "Análise", "IRPF"],
    "Metas": ["Metas"],
}


def _configurar_pagina() -> None:
    """Configura layout e metadados da página."""
    st.set_page_config(
        page_title="Protocolo Ouroboros",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(css_global(), unsafe_allow_html=True)


def _selecionar_cluster() -> str:
    """Renderiza o seletor de clusters na sidebar e devolve o cluster ativo.

    Sprint 92b (ADR-22): 5 áreas canônicas (Home / Finanças / Documentos /
    Análise / Metas). `CHAVE_SESSION_CLUSTER_ATIVO` é populado pela URL via
    `ler_filtros_da_url` quando aplicável (backward compatibility); caso
    contrário, default é o primeiro cluster ("Home").

    Sprint UX-121: cluster "Hoje" renomeado para "Home". URLs antigas
    (?cluster=Hoje) continuam funcionando via CLUSTER_ALIASES no leitor
    de query_params. Sprint UX-125 estende o padrão para
    ?cluster=Dinheiro -> "Finanças".

    Sprint UX-113: widget mudou de ``st.radio`` para ``st.selectbox``
    (dropdown). Economiza ~120px de altura vertical na sidebar (5 linhas
    -> 1 linha colapsada), liberando espaço para o campo Buscar acima.
    A lógica de cluster permanece N-para-N com ``ABAS_POR_CLUSTER`` e
    ``MAPA_ABA_PARA_CLUSTER`` -- só a UI mudou.
    """
    cluster_na_url = st.session_state.get(CHAVE_SESSION_CLUSTER_ATIVO, "")
    if cluster_na_url in CLUSTERS_VALIDOS:
        indice_default = CLUSTERS_VALIDOS.index(cluster_na_url)
    else:
        indice_default = 0

    cluster_escolhido: str = st.selectbox(
        "Área",
        list(CLUSTERS_VALIDOS),
        index=indice_default,
        key=CHAVE_SESSION_CLUSTER_ATIVO,
    )
    return cluster_escolhido


def _sidebar(dados: dict) -> tuple[str, str, str, str]:
    """Renderiza sidebar com filtros globais e retorna seleções.

    Returns:
        Tupla com (período selecionado, pessoa, granularidade, cluster).
    """
    with st.sidebar:
        # P2.2 2026-04-23: logo compacto (64px) para liberar espaço vertical
        # na sidebar -- antes 96px gastava ~150px totais só no cabeçalho.
        logo_html = logo_sidebar_html(largura_px=64)
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

        # Sprint UX-113: campo Buscar é o primeiro elemento abaixo do logo --
        # ponto de entrada cognitivo da sidebar. Submeter delega para o
        # roteador da Sprint UX-114 (fallback graceful enquanto UX-114 não
        # mergeia: salva em session_state apenas).
        renderizar_input_busca()

        # Sprint UX-119 AC4: separadores `st.markdown("---")` que existiam
        # entre Buscar / Área / Granularidade / Mês / Pessoa / Forma foram
        # removidos. Os 6 controles formam agora um bloco visual contínuo;
        # o respiro entre eles vem do margin-bottom uniforme dos elementos
        # do Streamlit. Os separadores ANTES (logo+caption) e DEPOIS (cards
        # Receita/Despesa/Saldo) permanecem porque marcam fronteiras
        # semânticas distintas (cabeçalho da sidebar / resumo financeiro).

        # Sprint 92b (ADR-22) + UX-113: seletor de cluster como dropdown.
        # Fica acima dos filtros de período/pessoa para reforçar a hierarquia
        # (área > filtros), mas abaixo do campo Buscar -- mental model
        # "buscar primeiro, navegar depois".
        cluster_ativo = _selecionar_cluster()

        meses = obter_meses_disponiveis(dados)

        if not meses:
            st.warning("Nenhum dado disponível.")
            return "", "Todos", "Mês", cluster_ativo

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
        st.session_state["filtro_forma"] = None if forma_sel == "Todas" else forma_sel

        st.markdown("---")

        _cards_sidebar(dados, periodo, pessoa, granularidade)

        return periodo, pessoa, granularidade, cluster_ativo


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

    periodo, pessoa, granularidade, cluster = _sidebar(dados)

    if not periodo:
        st.stop()

    ctx = {"granularidade": granularidade, "periodo": periodo}

    # Sprint 92b (ADR-22): renderização por cluster. Cada cluster expõe apenas
    # suas abas via st.tabs, e radio na sidebar escolhe o cluster ativo. URL
    # antiga (?tab=X) continua funcional via MAPA_ABA_PARA_CLUSTER em
    # ler_filtros_da_url. A ordem de abas dentro de cada cluster segue o hero
    # numbering (01-13) definido na Sprint 92a.
    if cluster == "Home":
        # Sprint UX-123: 5 abas no Home -- Visao Geral (existente) + 4
        # mini-views cross-area filtradas pelo dia mais recente do dataset.
        # Sprint UX-125: labels das tabs espelham clusters-irmãos (sem
        # sufixo "hoje"). Arquivos físicos (home_dinheiro.py etc.) mantêm
        # nome interno para evitar git mv massivo.
        # Ordem casa 1:1 com ABAS_POR_CLUSTER["Home"] (deep-link da Sprint 100).
        (
            tab_visao,
            tab_financas,
            tab_documentos,
            tab_analise,
            tab_metas,
        ) = st.tabs(
            [
                "Visão Geral",
                "Finanças",
                "Documentos",
                "Análise",
                "Metas",
            ]
        )
        with tab_visao:
            visao_geral.renderizar(dados, periodo, pessoa, ctx)
        with tab_financas:
            home_dinheiro.renderizar(dados, periodo, pessoa, ctx)
        with tab_documentos:
            home_docs.renderizar(dados, periodo, pessoa, ctx)
        with tab_analise:
            home_analise.renderizar(dados, periodo, pessoa, ctx)
        with tab_metas:
            home_metas.renderizar(dados, periodo, pessoa, ctx)

    elif cluster == "Finanças":
        (
            tab_extrato,
            tab_contas,
            tab_pagamentos,
            tab_projecoes,
        ) = st.tabs(["Extrato", "Contas", "Pagamentos", "Projeções"])
        with tab_extrato:
            extrato.renderizar(dados, periodo, pessoa, ctx)
        with tab_contas:
            contas.renderizar(dados, periodo, pessoa)
        with tab_pagamentos:
            pagamentos.renderizar(dados, periodo, pessoa, ctx)
        with tab_projecoes:
            projecoes.renderizar(dados, periodo, pessoa)

    elif cluster == "Documentos":
        (
            tab_busca,
            tab_catalogacao,
            tab_completude,
            tab_revisor,
            tab_grafo_obsidian,
        ) = st.tabs(
            [
                "Busca Global",
                "Catalogação",
                "Completude",
                "Revisor",
                "Grafo + Obsidian",
            ]
        )
        with tab_busca:
            busca.renderizar(dados, periodo, pessoa, ctx)
        with tab_catalogacao:
            catalogacao.renderizar(dados, periodo, pessoa, ctx)
        with tab_completude:
            completude.renderizar(dados, periodo, pessoa, ctx)
        with tab_revisor:
            revisor.renderizar(dados, periodo, pessoa, ctx)
        with tab_grafo_obsidian:
            grafo_obsidian.renderizar(dados, periodo, pessoa, ctx)

    elif cluster == "Análise":
        (
            tab_categorias,
            tab_analise,
            tab_irpf,
        ) = st.tabs(["Categorias", "Análise", "IRPF"])
        with tab_categorias:
            categorias.renderizar(dados, periodo, pessoa, ctx)
        with tab_analise:
            analise_avancada.renderizar(dados, periodo, pessoa, ctx)
        with tab_irpf:
            irpf.renderizar(dados, periodo, pessoa, ctx)

    elif cluster == "Metas":
        (tab_metas,) = st.tabs(["Metas"])
        with tab_metas:
            metas.renderizar(dados, periodo, pessoa)

    else:
        # Defensivo: cluster inválido em session_state (não deveria ocorrer
        # dado que o radio é fechado em CLUSTERS_VALIDOS). Fallback para Hoje.
        st.warning(f"Cluster desconhecido '{cluster}'. Exibindo Visão Geral.")
        visao_geral.renderizar(dados, periodo, pessoa, ctx)

    # Sprint 100: deep-link `?tab=<X>` ativo. Lê a aba requerida (populada por
    # `ler_filtros_da_url` quando ?tab=X estava na URL) e injeta o JS que
    # clica na tab correspondente após o Streamlit montar o DOM. Também
    # instala write-back: clicar em outra tab atualiza ?tab=<NomeClicado> via
    # `history.replaceState`, mantendo URL compartilhável e browser back
    # operando entre cliques semânticos.
    aba_requerida: str = str(st.session_state.get(CHAVE_SESSION_ABA_ATIVA, ""))
    abas_do_cluster: list[str] = ABAS_POR_CLUSTER.get(cluster, [])
    if abas_do_cluster:
        html_js = gerar_html_ativar_aba(aba_requerida, abas_do_cluster)
        if html_js:
            from streamlit.components import v1 as components

            components.html(html_js, height=0)


if __name__ == "__main__":
    main()


# "A frugalidade inclui todas as outras virtudes." -- Cícero
