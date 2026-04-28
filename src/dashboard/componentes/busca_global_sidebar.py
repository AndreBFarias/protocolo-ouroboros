"""Componente de busca global na sidebar (Sprint UX-113).

Renderiza o campo de input "Buscar" como primeiro elemento abaixo do logo da
sidebar (acima do dropdown de Área). Quando submetido, delega para o roteador
da Sprint UX-114 (`busca_roteador.rotear`) que decide se a query casa nome de
aba (navega), nome de fornecedor (filtra Busca Global) ou texto livre.

Padrão "branch reversível" canônico (Sprint 97): se o roteador da UX-114 ainda
não foi mergeado, o componente faz fallback graceful -- registra a query no
session_state e loga um warning, sem quebrar o boot do dashboard.

Também injeta CSS específico da sidebar para corrigir glyphs cortados
("Mâs" no lugar de "Mês", "2A26-04" no lugar de "2026-04") reportados no
feedback do dono em 2026-04-27. Garante largura mínima 260px, white-space
nowrap em rótulos curtos e overflow-x oculto.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

CHAVE_SESSION_BUSCA: str = "busca_global_query"
"""Chave em ``st.session_state`` que carrega a query submetida pelo usuário."""

LARGURA_MINIMA_SIDEBAR_PX: int = 260
"""Largura mínima da sidebar para evitar truncamento de glyph."""

TAMANHO_MINIMO_ICONE_SEARCH_PX: int = 18
"""Tamanho mínimo do ícone de busca (lupa) para legibilidade."""


def css_sidebar_overflow_fix() -> str:
    """Retorna bloco CSS injetado pelo componente para corrigir overflow.

    Aplicado dentro do escopo da sidebar (touches autorizados pela UX-113).
    Garante:

    - ``min-width: 260px`` em ``[data-testid="stSidebar"]`` (sem isso o usuário
      pode arrastar e cortar rótulos como "Mês" para "Mâs").
    - ``overflow-x: hidden`` no container raiz da sidebar.
    - ``white-space: nowrap`` em ``label`` dos selectboxes e radios.
    - ``word-break: keep-all`` em rótulos curtos (não quebrar "Mês" na ê).
    - ``font-size: 18px`` no ícone SVG dentro do input de busca.
    - ``text-overflow: ellipsis`` no valor selecionado do selectbox -- a
      string "2026-04" cabe em qualquer largura >= 60px, mas o widget
      truncava no meio do glyph antes deste fix.
    """
    return f"""
    <style>
    /* Sprint UX-113: sidebar não pode estreitar abaixo de 260px sob risco
       de cortar glyph dos rótulos. Streamlit não expõe API estável para
       largura da sidebar, mas data-testid="stSidebar" aceita CSS direto. */
    [data-testid="stSidebar"] {{
        min-width: {LARGURA_MINIMA_SIDEBAR_PX}px !important;
        overflow-x: hidden !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        min-width: {LARGURA_MINIMA_SIDEBAR_PX - 32}px;
        overflow-x: hidden;
    }}
    /* Rótulos curtos ("Mês", "Pessoa", "Área") não devem quebrar entre
       letras nem ser cortados por overflow-x. word-break: keep-all impede
       quebra dentro da palavra; white-space: nowrap impede que renderer
       force \\n entre acento e letra base. */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] label p,
    [data-testid="stSidebar"] label span {{
        white-space: nowrap !important;
        word-break: keep-all !important;
        overflow: visible !important;
    }}
    /* Valor selecionado do selectbox ("2026-04", "Todos", "Mês") deve
       renderizar inteiro. Se a largura for menor, ellipsis -- nunca cortar
       glyph no meio. */
    [data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"],
    [data-testid="stSidebar"] [data-baseweb="select"] div[aria-selected="true"] {{
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
        overflow: hidden !important;
    }}
    /* Ícone search (lupa) do input de busca: o widget nativo do Streamlit
       renderiza um SVG ~12-14px que fica imperceptível. Promovemos para
       18px (mínimo legível em densidade média). */
    [data-testid="stSidebar"] [data-testid="stTextInput"] svg,
    [data-testid="stSidebar"] [data-testid="stTextInputRootElement"] svg {{
        width: {TAMANHO_MINIMO_ICONE_SEARCH_PX}px !important;
        height: {TAMANHO_MINIMO_ICONE_SEARCH_PX}px !important;
    }}
    </style>
    """


def _delegar_para_roteador(query: str) -> dict | None:
    """Chama o roteador da Sprint UX-114, com fallback graceful.

    Padrão "branch reversível": se o módulo ``busca_roteador`` não existe
    (UX-114 ainda não mergeada), retorna ``None`` e loga warning. O
    componente continua funcional -- só não há navegação automática.

    Returns:
        Dict do roteador (``{'kind': 'aba'|'fornecedor'|'livre', ...}``) ou
        ``None`` se o roteador ainda não está disponível.
    """
    try:
        from src.dashboard.componentes.busca_roteador import (
            rotear,  # type: ignore[import-not-found]
        )
    except ImportError:
        logger.warning(
            "busca_roteador (Sprint UX-114) ainda não está disponível; "
            "fallback graceful ativado, query salva apenas em session_state."
        )
        return None

    try:
        resultado: dict = rotear(query)
        return resultado
    except Exception as exc:  # noqa: BLE001 -- defensivo no boundary
        logger.warning("Roteador UX-114 levantou exceção em '%s': %s", query, exc)
        return None


def renderizar_input_busca() -> str:
    """Renderiza o campo de busca na sidebar e processa submissão.

    Deve ser chamado dentro de ``with st.sidebar:`` em ``app.py``. Sempre
    como o primeiro elemento abaixo do logo (Sprint UX-113 AC #1).

    Side effects:
        - Injeta ``css_sidebar_overflow_fix`` uma vez por render (idempotente
          via ``st.markdown``).
        - Salva query submetida em ``st.session_state[CHAVE_SESSION_BUSCA]``.
        - Quando UX-114 disponível e roteador retorna ``kind='aba'``, define
          ``query_params['cluster']`` e ``query_params['tab']`` para navegar.

    Returns:
        Query atualmente no input (string vazia se nada submetido).
    """
    # Lazy import para permitir monkeypatching em testes (padrão canônico
    # usado em ``componentes/drilldown.py``).
    import streamlit as st

    # CSS de correção do overflow é idempotente -- Streamlit deduplica blocos
    # markdown idênticos no mesmo render.
    st.markdown(css_sidebar_overflow_fix(), unsafe_allow_html=True)

    query: str = st.text_input(
        label="Busca Global",
        value=st.session_state.get(CHAVE_SESSION_BUSCA, ""),
        placeholder="",
        key="input_busca_global_sidebar",
        # Sprint UX-125 AC4: label "Busca Global" passa a ser visível
        # (Streamlit acessibilidade preservada). Placeholder vazio elimina
        # ruído de "Buscar (...)" duplicado com a label. Reverte a opção
        # de colapso aplicada anteriormente na UX-119 AC1.
        label_visibility="visible",
    )

    if query and query != st.session_state.get(CHAVE_SESSION_BUSCA, ""):
        # Query nova submetida (mudou desde a última render). Salva e roteia.
        st.session_state[CHAVE_SESSION_BUSCA] = query
        resultado = _delegar_para_roteador(query)
        if resultado is not None:
            _aplicar_resultado_roteador(resultado, st)

    return query


def _aplicar_resultado_roteador(resultado: dict, st_module: Any) -> None:
    """Aplica decisão do roteador atualizando ``st.query_params``.

    Contrato esperado do roteador (Sprint UX-114):

    - ``{'kind': 'aba', 'cluster': str, 'tab': str}`` -> navega via deep-link.
    - ``{'kind': 'fornecedor', 'fornecedor': str}`` -> abre Busca Global
      filtrada por fornecedor (cluster=Documentos, tab=Busca Global).
    - ``{'kind': 'livre', 'query': str}`` -> apenas filtra Busca Global pela
      string crua (cluster=Documentos, tab=Busca Global).

    Defensivo: kinds desconhecidos são ignorados com warning. Não-dicts
    também são tolerados (logam e seguem).

    O parâmetro ``st_module`` é o módulo ``streamlit`` (real ou mockado)
    repassado pelo chamador para preservar a substituição via
    ``monkeypatch.setitem(sys.modules, 'streamlit', fake)`` em testes.
    """
    if not isinstance(resultado, dict):
        logger.warning("Roteador retornou não-dict: %r", type(resultado).__name__)
        return

    kind = resultado.get("kind")
    if kind == "aba":
        cluster = resultado.get("cluster", "")
        tab = resultado.get("tab", "")
        if cluster:
            st_module.query_params["cluster"] = cluster
        if tab:
            st_module.query_params["tab"] = tab
    elif kind in ("fornecedor", "livre"):
        st_module.query_params["cluster"] = "Documentos"
        st_module.query_params["tab"] = "Busca Global"
    else:
        logger.warning("Roteador retornou kind desconhecido: %r", kind)


# "Quem busca primeiro, navega depois. Se navega primeiro, esquece o que
# buscava." -- princípio do mental model honesto, formalizado por Don Norman
# em The Design of Everyday Things.
