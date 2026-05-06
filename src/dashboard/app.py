"""Entrypoint principal do dashboard financeiro - Protocolo Ouroboros."""

import sys
from pathlib import Path

import streamlit as st

RAIZ_PROJETO: Path = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

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
    carregar_dados,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    formatar_moeda,
    obter_anos_disponiveis,
    obter_meses_disponiveis,
)
from src.dashboard.paginas import (  # noqa: E402
    analise_avancada,
    be_alarmes,
    be_ciclo,
    be_contadores,
    be_cruzamentos,  # noqa: F401  -- reabilitado por FIX-14 via &secao=
    be_diario,
    be_editor_toml,  # noqa: F401  -- reabilitado por FIX-14 via &secao=
    be_eventos,
    be_hoje,
    be_humor,
    be_marcos,
    be_medidas,
    be_memorias,  # noqa: F401  -- reabilitado por FIX-14 via &secao=
    be_privacidade,  # noqa: F401  -- reabilitado por FIX-14 via &secao=
    be_recap,
    be_rotina,  # noqa: F401  -- reabilitado por FIX-14 via &secao=
    be_tarefas,
    be_treinos,
    busca,
    catalogacao,
    categorias,
    completude,
    contas,
    extracao_tripla,
    extrato,
    grafo_obsidian,
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
    """UX-U-04: sidebar shell-only (zero widgets Streamlit).

    A sidebar emite APENAS o bloco HTML canônico do redesign
    (``renderizar_sidebar``: brand SVG, busca placeholder, 8 clusters
    com badges + footer "D7 cobertura observável").

    Filtros globais (granularidade, período, pessoa, forma de pagamento)
    foram migrados para ``_filtros_globais_main()``, que renderiza um
    expander compacto colapsado por default no início do conteúdo
    principal. Páginas de Onda T podem renderizar filtros próprios
    inline via ``componentes/filtros_pagina``.

    Args:
        dados: dicionário de DataFrames (passado para preservar
            assinatura; cabe a ``_filtros_globais_main`` consumir).
        aba_ativa: aba atual para destacar no shell HTML.

    Returns:
        Tupla compatível ``(periodo, pessoa, granularidade, cluster_ativo)``
        com valores efetivos lidos de ``st.session_state`` (populados
        pelo expander de filtros globais ou por defaults seguros).
    """
    cluster_ativo = _selecionar_cluster()

    with st.sidebar:
        st.markdown(
            renderizar_sidebar(cluster_ativo=cluster_ativo, aba_ativa=aba_ativa),
            unsafe_allow_html=True,
        )

    # Filtros globais migrados para o main como expander colapsado.
    periodo, pessoa, granularidade = _filtros_globais_main(dados)
    return periodo, pessoa, granularidade, cluster_ativo


def _filtros_globais_main(dados: dict) -> tuple[str, str, str]:
    """UX-U-04: filtros globais no main (substituem widgets da sidebar).

    Renderizados num ``st.expander`` colapsado por default, abaixo da
    topbar e antes do dispatcher. Cada página de Onda T pode optar por
    filtros inline próprios via ``componentes/filtros_pagina`` — neste
    caso o expander global continua presente mas cada um opera sobre
    namespace de session_state distinto.

    Returns:
        ``(periodo, pessoa, granularidade)`` para o dispatcher.
    """
    meses = obter_meses_disponiveis(dados)
    if not meses:
        st.warning("Nenhum dado disponível.")
        return "", "Todos", "Mês"

    from src.utils.pessoas import nome_de
    nome_a = nome_de("pessoa_a")
    nome_b = nome_de("pessoa_b")
    opcoes_pessoa = ["Todos", nome_a, nome_b]

    with st.expander("Filtros globais", expanded=False):
        col_g, col_p, col_pessoa, col_forma = st.columns([1, 1, 1, 1])

        with col_g:
            granularidade: str = st.selectbox(
                "Granularidade",
                ["Dia", "Semana", "Mês", "Ano"],
                index=2,
                key="seletor_granularidade",
            )

        with col_p:
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
                    periodo = (
                        st.selectbox("Semana", semanas, index=0, key="seletor_detalhe")
                        if semanas else mes_base
                    )
                elif granularidade == "Dia":
                    from src.dashboard.dados import obter_dias_do_mes
                    dias = obter_dias_do_mes(dados, mes_base)
                    periodo = (
                        st.selectbox("Dia", dias, index=0, key="seletor_detalhe")
                        if dias else mes_base
                    )
                else:
                    periodo = mes_base

        with col_pessoa:
            pessoa: str = st.selectbox(
                "Pessoa",
                opcoes_pessoa,
                index=0,
                key="seletor_pessoa",
            )

        with col_forma:
            forma_sel: str = st.selectbox(
                "Forma de pagamento",
                ["Todas", "Pix", "Débito", "Crédito", "Boleto", "Transferência"],
                index=0,
                key="seletor_forma_pagamento",
            )
            st.session_state["filtro_forma"] = None if forma_sel == "Todas" else forma_sel

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


def _renderizar_topbar_para(cluster: str, aba_ativa: str):
    """Cria placeholder st.empty() para o topbar e devolve (placeholder, breadcrumb).

    UX-U-02: o topbar tem slot de ações que cada página preenche via
    ``componentes/topbar_actions.renderizar_grupo_acoes``. Como o dispatcher
    de páginas roda DEPOIS do topbar, usamos placeholder reservando posição
    no DOM e preenchemos no fim (``_finalizar_topbar``) com o slot já populado.
    """
    breadcrumb = ["Ouroboros", cluster]
    if aba_ativa:
        breadcrumb.append(aba_ativa)
    placeholder = st.empty()
    st.session_state["topbar_acoes_html"] = ""
    return placeholder, breadcrumb


def _finalizar_topbar(placeholder, breadcrumb: list[str]) -> None:
    """Preenche o placeholder do topbar com o slot já populado pela página."""
    placeholder.markdown(renderizar_topbar(breadcrumb), unsafe_allow_html=True)


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

    # Sprint UX-RD-03 + UX-U-02: topbar via placeholder (preenchido após
    # dispatcher para capturar ações injetadas pela página corrente).
    _topbar_ph, _topbar_bc = _renderizar_topbar_para(cluster, aba_requerida_topbar)
    # FIX-12: âncora alvo do skip-link (WCAG 2.4.1).
    st.markdown('<div id="main-root" tabindex="-1"></div>', unsafe_allow_html=True)

    ctx = {"granularidade": granularidade, "periodo": periodo}

    # Sprint 92b (ADR-22): renderização por cluster. Cada cluster expõe apenas
    # suas abas via st.tabs, e radio na sidebar escolhe o cluster ativo. URL
    # antiga (?tab=X) continua funcional via MAPA_ABA_PARA_CLUSTER em
    # ler_filtros_da_url. A ordem de abas dentro de cada cluster segue o hero
    # numbering (01-13) definido na Sprint 92a.
    if cluster == "Home":
        # UX-T-01: cluster Home renderiza diretamente a Visão Geral canônica
        # (mockup 01-visao-geral.html). As 5 tabs internas (Visão Geral /
        # Finanças / Documentos / Análise / Metas) que duplicavam a sidebar
        # foram eliminadas — clusters próprios já oferecem essas vistas.
        # As páginas home_dinheiro/home_docs/home_analise/home_metas
        # continuam exportadas para retrocompat de deep-links externos
        # (será removido em sprint dedicada DEPRECATED-HOME-SUBVIEWS).
        visao_geral.renderizar(dados, periodo, pessoa, ctx)

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
        # FIX-14: deep-link interno via &secao= reabilita 5 páginas órfãs
        # (Memórias, Rotina, Cruzamentos, Privacidade, Editor-TOML) que
        # não têm aba top-level após a decisão A da FIX-10. Quando o
        # parâmetro está presente e válido, renderiza a página órfã no
        # lugar do dispatcher das 12 abas e retorna early.
        _SECOES_ORFAS_BEM_ESTAR = {
            "Memorias": be_memorias,
            "Rotina": be_rotina,
            "Cruzamentos": be_cruzamentos,
            "Privacidade": be_privacidade,
            "Editor-TOML": be_editor_toml,
        }
        secao_orfa = str(st.query_params.get("secao", ""))
        if secao_orfa and secao_orfa in _SECOES_ORFAS_BEM_ESTAR:
            _SECOES_ORFAS_BEM_ESTAR[secao_orfa].renderizar(
                dados, periodo, pessoa, ctx
            )
            st.markdown(
                '<a class="btn btn-ghost btn-sm" href="?cluster=Bem-estar&tab=Recap" '
                'style="margin-top:var(--sp-4); display:inline-block; '
                'text-decoration:none; color:var(--text-muted); '
                'border:1px solid var(--border-subtle); padding:6px 12px; '
                'border-radius:var(--r-sm);">'
                "&larr; Voltar para Recap"
                "</a>",
                unsafe_allow_html=True,
            )
            st.stop()

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
        # FIX-10: dispatcher 1:1 -- cada aba chama UMA página real.
        # Antes (UX-RD-19) Treinos+Marcos -> be_memorias e
        # Alarmes+Contadores+Tarefas -> be_rotina (5 abas-fantasma).
        # FIX-10 cria 5 páginas reais (be_treinos, be_marcos, be_alarmes,
        # be_contadores, be_tarefas). FIX-14 reabilita rota interna para
        # Memórias/Rotina/Cruzamentos/Privacidade/Editor TOML via &secao=.
        with tab_be_medidas:
            be_medidas.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_treinos:
            be_treinos.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_marcos:
            be_marcos.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_alarmes:
            be_alarmes.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_contadores:
            be_contadores.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_ciclo:
            be_ciclo.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_tarefas:
            be_tarefas.renderizar(dados, periodo, pessoa, ctx)
        with tab_be_recap:
            be_recap.renderizar(dados, periodo, pessoa, ctx)
            # FIX-14: expanders Cruzamentos/Privacidade/Editor TOML removidos
            # daqui. Acessíveis via &secao= URL param (a sprint FIX-14 reabilita).

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

    # UX-U-02: depois que o dispatcher rodou, a página corrente já populou
    # st.session_state['topbar_acoes_html'] (via topbar_actions.renderizar_grupo_acoes).
    # Agora preenchemos o placeholder do topbar com o slot já correto.
    _finalizar_topbar(_topbar_ph, _topbar_bc)

    # Sprint UX-RD-03: atalhos globais (g h, g i, g v, g r, g f, g c,
    # /, ?, Esc) instalados no fim de main(). Idempotente -- guard
    # ``__ouroborosAtalhosInstalados`` impede empilhamento de listeners
    # em re-runs do Streamlit.
    instalar_atalhos_globais()


if __name__ == "__main__":
    main()


# "A frugalidade inclui todas as outras virtudes." -- Cícero
