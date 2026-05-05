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
from src.dashboard.componentes.shell import (  # noqa: E402
    instalar_atalhos_globais,
    renderizar_sidebar,
    renderizar_topbar,
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
    be_ciclo,
    be_cruzamentos,
    be_diario,
    be_editor_toml,
    be_eventos,
    be_hoje,
    be_humor,
    be_medidas,
    be_memorias,
    be_privacidade,
    be_recap,
    be_rotina,
    busca,
    catalogacao,
    categorias,
    completude,
    contas,
    extracao_tripla,
    extrato,
    grafo_obsidian,
    home_analise,
    home_dinheiro,
    home_docs,
    home_metas,
    inbox,
    irpf,
    metas,
    pagamentos,
    projecoes,
    revisor,
    skills_d7,
    styleguide,
    visao_geral,
)

# Sprint UX-RD-11: ``validacao_arquivos`` permanece importável como stub
# de retrocompat (rota ?tab=Validação+por+Arquivo é resolvida via
# ABA_ALIASES_LEGACY antes de cair no dispatcher). Não é referenciado
# diretamente neste módulo, mas o pacote ``paginas`` continua exportando-o.
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
        # Sprint UX-RD-11: aba "Validação por Arquivo" foi renomeada para
        # "Extração Tripla" (layout 3 colunas: lista | viewer | tabela
        # ETL × Opus × Humano). Retrocompat via alias em CLUSTER_ALIASES.
        "Extração Tripla",
        "Grafo + Obsidian",
    ],
    "Análise": ["Categorias", "Análise", "IRPF"],
    "Metas": ["Metas"],
    # Sprint UX-RD-03: clusters novos sem páginas implementadas. Cada
    # entrada lista as abas que aparecem no mockup; o dispatcher de
    # ``main()`` renderiza fallback graceful com ponteiro para a sprint
    # alvo. Mantemos as abas declaradas aqui para que o deep-link da
    # Sprint 100 (``?cluster=Inbox&tab=...``) seja preservado quando as
    # páginas vierem (UX-RD-15, UX-RD-16+, UX-RD-05).
    "Inbox": ["Inbox"],
    # Sprint UX-RD-17: cluster Bem-estar ganha 12 abas declaradas para o
    # deep-link (?cluster=Bem-estar&tab=<X>). Apenas "Hoje" e "Humor" têm
    # páginas reais nesta sprint; as demais caem em fallback graceful no
    # dispatcher abaixo até que UX-RD-18+ habilite cada uma.
    "Bem-estar": [
        "Hoje",
        "Humor",
        "Diário",
        "Eventos",
        "Medidas",
        "Treinos",
        "Marcos",
        "Alarmes",
        "Contadores",
        "Ciclo",
        "Tarefas",
        "Recap",
    ],
    # Sprint UX-RD-05: cluster Sistema ganha aba "Styleguide" além de
    # "Skills D7". Páginas implementadas em ``paginas/skills_d7.py`` e
    # ``paginas/styleguide.py``; dispatcher abaixo monta as abas reais.
    "Sistema": ["Skills D7", "Styleguide"],
}

# Sprint UX-RD-03: mapa cluster -> sprint que vai habilitar suas páginas.
# Usado pelo fallback do dispatcher para mostrar mensagem informativa
# quando o cluster está em CLUSTERS_VALIDOS mas as páginas ainda não
# existem.
SPRINT_ALVO_POR_CLUSTER: dict[str, str] = {
    "Inbox": "UX-RD-15",
    "Bem-estar": "UX-RD-16",
    "Sistema": "UX-RD-05",
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
    """Resolve o cluster ativo a partir do session_state.

    Sprint 92b (ADR-22): 5 áreas canônicas. ``CHAVE_SESSION_CLUSTER_ATIVO``
    é populado pela URL via ``ler_filtros_da_url`` quando aplicável.

    Sprint UX-121: cluster "Hoje" renomeado para "Home" (alias backward-compat
    via ``CLUSTER_ALIASES``). Sprint UX-125: ``?cluster=Dinheiro`` -> "Finanças".

    Sprint UX-RD-03: o widget ``st.selectbox`` foi substituído pela sidebar
    HTML redesenhada (``shell.renderizar_sidebar``). Os 8 clusters são
    apresentados como links ``<a href="?cluster=X">``; clicar recarrega a
    página com a query string e ``ler_filtros_da_url`` popula o
    session_state. Esta função agora apenas resolve o cluster atual lendo
    o session_state e aplicando default ("Home") quando a URL não
    especifica nada. Mantida com a mesma assinatura para não quebrar
    chamadores. A primeira execução (sem cluster na URL) retorna "Home"
    como ponto de entrada cognitivo padrão.
    """
    cluster_na_url = st.session_state.get(CHAVE_SESSION_CLUSTER_ATIVO, "")
    if cluster_na_url in CLUSTERS_VALIDOS:
        return cluster_na_url
    # Default: Home (índice 1 no novo CLUSTERS_VALIDOS, pois Inbox vem antes
    # mas Home é o ponto de entrada cognitivo do usuário recorrente).
    return "Home"


def _sidebar(dados: dict, aba_ativa: str = "") -> tuple[str, str, str, str]:
    """Renderiza sidebar com filtros globais e retorna seleções.

    Sprint UX-RD-03: a sidebar passou a ter duas camadas:

      1. Bloco HTML estático (``shell.renderizar_sidebar``) com brand,
         busca placeholder, 8 clusters e itens de aba. Cada item é um
         link ``<a href="?cluster=X&tab=Y">`` que recarrega a página
         para acionar o roteamento via ``ler_filtros_da_url``.
      2. Widgets Streamlit interativos (busca real, granularidade, mês,
         pessoa, forma de pagamento) renderizados depois, abaixo do
         bloco HTML, dentro do mesmo ``with st.sidebar:``. Compõem a
         camada de filtros globais existentes (preservados das sprints
         UX-113/119/126).

    Returns:
        Tupla com (período selecionado, pessoa, granularidade, cluster).
    """
    cluster_ativo = _selecionar_cluster()

    with st.sidebar:
        # Sprint UX-RD-03: bloco HTML do shell redesenhado. Contém brand,
        # busca placeholder e 8 clusters/abas como links navegáveis. O
        # selectbox dropdown da Sprint UX-113 foi substituído.
        st.markdown(
            renderizar_sidebar(cluster_ativo=cluster_ativo, aba_ativa=aba_ativa),
            unsafe_allow_html=True,
        )

        # Sprint UX-126 AC5/AC6: logo + caption "Dados de ..." continuam
        # exibidos como bloco compacto abaixo da navegação por
        # compatibilidade. Acceptance da UX-RD-03 não pede remover --
        # remoção fica para sprint de "limpeza visual sidebar" futura.
        logo_html = logo_sidebar_html(largura_px=120)
        if logo_html:
            st.markdown(logo_html, unsafe_allow_html=True)
        else:
            st.title("Protocolo Ouroboros")

        if CAMINHO_XLSX.exists():
            import os
            from datetime import datetime

            mtime = os.path.getmtime(CAMINHO_XLSX)
            ultima = datetime.fromtimestamp(mtime)
            data_str = ultima.strftime("%d/%m/%Y")
            hora_str = ultima.strftime("%H:%M")
            st.markdown(
                "<div class='ouroboros-sidebar-caption' "
                "style='text-align:center; line-height:1.4;'>"
                f"<p style='margin:0; font-size:13px; color:var(--color-texto-sec);'>"
                f"Dados de {data_str}</p>"
                f"<p style='margin:0; font-size:13px; color:var(--color-texto-sec);'>"
                f"— {hora_str} —</p>"
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # Sprint UX-113: campo Buscar interativo (Streamlit). Coexiste com
        # o input HTML decorativo da sidebar redesenhada -- a tecla `/`
        # foca o input HTML (sem reload), e este componente Python lida
        # com a submissão real via roteador da Sprint UX-114.
        renderizar_input_busca()

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

        # Sprint MOB-bridge-1 / ADR-24: o dashboard local-first exibe
        # ``display_name`` real ao dono (resolvido via ``nome_de`` em
        # runtime, sem persistência), mas o filtro interno opera sobre
        # identificador genérico ``pessoa_a`` / ``pessoa_b`` / ``casal``.
        from src.utils.pessoas import nome_de

        nome_a = nome_de("pessoa_a")
        nome_b = nome_de("pessoa_b")
        opcoes_pessoa = ["Todos", nome_a, nome_b]
        pessoa: str = st.selectbox(
            "Pessoa",
            opcoes_pessoa,
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


def _renderizar_topbar_para(cluster: str, aba_ativa: str) -> None:
    """Emite topbar com breadcrumb 'Ouroboros / <Cluster> / <Aba>' atual."""
    breadcrumb = ["Ouroboros", cluster]
    if aba_ativa:
        breadcrumb.append(aba_ativa)
    st.markdown(renderizar_topbar(breadcrumb), unsafe_allow_html=True)


def _renderizar_fallback_cluster(cluster: str) -> None:
    """Mensagem informativa para clusters declarados mas sem páginas.

    Sprint UX-RD-03: clusters Inbox, Bem-estar e Sistema entraram em
    ``CLUSTERS_VALIDOS`` antes das páginas existirem. Em vez de crash,
    mostramos um ``st.info`` apontando a sprint que vai habilitar as
    páginas.
    """
    sprint_alvo = SPRINT_ALVO_POR_CLUSTER.get(cluster, "futura")
    st.info(
        f"Cluster '{cluster}' está reservado pelo redesign mas as páginas ainda "
        f"não foram implementadas. A sprint {sprint_alvo} habilita o conteúdo. "
        "Use a sidebar para voltar a um cluster ativo."
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

    aba_requerida_topbar: str = str(st.session_state.get(CHAVE_SESSION_ABA_ATIVA, ""))
    periodo, pessoa, granularidade, cluster = _sidebar(dados, aba_ativa=aba_requerida_topbar)

    if not periodo:
        st.stop()

    # Sprint UX-RD-03: topbar com breadcrumb antes do conteúdo principal.
    _renderizar_topbar_para(cluster, aba_requerida_topbar)

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
        # Sprint UX-RD-11: aba "Validação por Arquivo" -> "Extração Tripla".
        # ``validacao_arquivos.py`` virou stub de retrocompat (visualizado
        # apenas se rota antiga for explicitada em código futuro).
        (
            tab_busca,
            tab_catalogacao,
            tab_completude,
            tab_revisor,
            tab_extracao_tripla,
            tab_grafo_obsidian,
        ) = st.tabs(
            [
                "Busca Global",
                "Catalogação",
                "Completude",
                "Revisor",
                "Extração Tripla",
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
        with tab_extracao_tripla:
            extracao_tripla.renderizar(dados, periodo, pessoa, ctx)
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

    elif cluster == "Sistema":
        # Sprint UX-RD-05: cluster Sistema com 2 abas reais.
        # Skills D7 = painel analítico do classificador; Styleguide = QA
        # visual dos tokens/classes do redesign.
        tab_skills, tab_styleguide = st.tabs(["Skills D7", "Styleguide"])
        with tab_skills:
            skills_d7.renderizar(dados, periodo, pessoa, ctx)
        with tab_styleguide:
            styleguide.renderizar(dados, periodo, pessoa, ctx)

    elif cluster == "Inbox":
        # Sprint UX-RD-15: cluster Inbox tem página real -- dropzone, fila
        # de arquivos lida de <raiz>/inbox/, drawer sidecar e bloco
        # skill-instr apontando para o CLI. Fallback graceful era apenas
        # placeholder até esta sprint.
        (tab_inbox,) = st.tabs(["Inbox"])
        with tab_inbox:
            inbox.renderizar(dados, periodo, pessoa, ctx)

    elif cluster == "Bem-estar":
        # Sprint UX-RD-17: dispatcher real do cluster Bem-estar com 12
        # abas declaradas (deep-link). Apenas "Hoje" e "Humor" têm
        # páginas reais nesta sprint; demais ficam em fallback graceful
        # apontando a sprint que vai habilitá-las (UX-RD-18+).
        (
            tab_be_hoje,
            tab_be_humor,
            tab_be_diario,
            tab_be_eventos,
            tab_be_medidas,
            tab_be_treinos,
            tab_be_marcos,
            tab_be_alarmes,
            tab_be_contadores,
            tab_be_ciclo,
            tab_be_tarefas,
            tab_be_recap,
        ) = st.tabs(
            [
                "Hoje",
                "Humor",
                "Diário",
                "Eventos",
                "Medidas",
                "Treinos",
                "Marcos",
                "Alarmes",
                "Contadores",
                "Ciclo",
                "Tarefas",
                "Recap",
            ]
        )
        with tab_be_hoje:
            be_hoje.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_humor:
            be_humor.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_diario:
            # Sprint UX-RD-18: aba "Diário" agora é página real --
            # lista cronológica DESC com border-left semântica, chips
            # emoção, slider intensidade e form modal "Registrar diário".
            be_diario.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_eventos:
            # Sprint UX-RD-18: aba "Eventos" agora é página real --
            # timeline cronológica DESC + sidebar lateral "Bairros
            # frequentes" agregada do cache (NUNCA hardcoded).
            be_eventos.renderizar(dados, periodo, pessoa, ctx)
        # Sprint UX-RD-19: as 8 abas restantes ganharam página real.
        # Mapeamento aba (12 declaradas) -> página (8 entregues):
        # Medidas->be_medidas; Treinos+Marcos->be_memorias (sub-abas);
        # Alarmes+Contadores+Tarefas->be_rotina; Ciclo->be_ciclo;
        # Recap->be_recap. As páginas Cruzamentos/Privacidade/Editor TOML
        # do mockup ficam acessíveis via expanders dentro de Recap para
        # preservar o invariante N=12 abas em ABAS_POR_CLUSTER["Bem-estar"].
        with tab_be_medidas:
            be_medidas.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_treinos:
            be_memorias.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_marcos:
            be_memorias.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_alarmes:
            be_rotina.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_contadores:
            be_rotina.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_ciclo:
            be_ciclo.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_tarefas:
            be_rotina.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_recap:
            be_recap.renderizar(dados, periodo, pessoa, ctx)
            with st.expander("Cruzamentos", expanded=False):
                be_cruzamentos.renderizar(dados, periodo, pessoa, ctx)
            with st.expander("Privacidade A ↔ B", expanded=False):
                be_privacidade.renderizar(dados, periodo, pessoa, ctx)
            with st.expander("Editor TOML (rotina)", expanded=False):
                be_editor_toml.renderizar(dados, periodo, pessoa, ctx)

    else:
        # Defensivo: cluster inválido em session_state. Não deveria ocorrer
        # porque ler_filtros_da_url só popula valores em CLUSTERS_VALIDOS,
        # mas mantemos o fallback para evitar tela branca.
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

    # Sprint UX-RD-03: atalhos globais (g h, g i, g v, g r, g f, g c,
    # /, ?, Esc) instalados no fim de main(). Idempotente -- guard
    # ``__ouroborosAtalhosInstalados`` impede empilhamento de listeners
    # em re-runs do Streamlit.
    instalar_atalhos_globais()


if __name__ == "__main__":
    main()


# "A frugalidade inclui todas as outras virtudes." -- Cícero
