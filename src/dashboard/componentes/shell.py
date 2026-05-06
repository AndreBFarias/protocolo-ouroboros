"""Shell global do dashboard: sidebar de 8 clusters + topbar — Sprint UX-RD-03.

Versão Python+Streamlit do contrato de ``novo-mockup/_shared/shell.js``
(funções ``_sidebarHTML`` e ``_topbarHTML``). Cada função emite um bloco
HTML pronto para ``st.markdown(html, unsafe_allow_html=True)`` e consome
exclusivamente classes definidas em ``src/dashboard/tema_css.py`` (UX-RD-02).

Topologia da sidebar (ordem canônica espelha ``CLUSTERS_VALIDOS`` em
``componentes/drilldown.py``):

  1. Inbox      -- fila de novos arquivos (UX-RD-15 implementa)
  2. Home       -- visão geral + 4 mini-views cross-area
  3. Finanças   -- Extrato, Contas, Pagamentos, Projeções
  4. Documentos -- Busca Global, Catalogação, Completude, Revisor,
                   Validação por Arquivo, Grafo + Obsidian
  5. Análise    -- Categorias, Análise, IRPF
  6. Metas      -- Metas
  7. Bem-estar  -- 12 telas pessoais não-financeiras (UX-RD-16+ implementa)
  8. Sistema    -- Skills D7, Styleguide, Índice (UX-RD-05 implementa)

Cada item usa link ``href="?cluster=<X>&tab=<Y>"`` para preservar o
deep-link da Sprint 100. A tab ``a class="sidebar-item active"`` recebe
o destaque visual via CSS já existente em ``tema_css.py`` (gradient +
``border-left 2px var(--accent-purple)``).

Segurança XSS: nomes de cluster, abas e segmentos do breadcrumb são
escapados via ``html.escape`` antes da concatenação. ``href`` usa apenas
componentes hardcoded em ``CLUSTERS_REDESIGN`` ou em ``ABAS_POR_CLUSTER``
de ``app.py`` (não há valores arbitrários em runtime).
"""

from __future__ import annotations

import html
import urllib.parse
from collections.abc import Iterable

# Estrutura canônica da sidebar redesenhada. Espelha 1:1 o array
# ``CLUSTERS_OUROBOROS`` de ``novo-mockup/_shared/shell.js``. Os nomes de aba
# coincidem com os labels usados em ``ABAS_POR_CLUSTER`` (em ``app.py``)
# para clusters que já têm páginas implementadas (Home, Finanças,
# Documentos, Análise, Metas). Os 3 clusters novos (Inbox, Bem-estar,
# Sistema) ainda não têm páginas em ``paginas/``; o dispatcher em
# ``main()`` mostra fallback graceful.
CLUSTERS_REDESIGN: tuple[dict, ...] = (
    {
        "nome": "Inbox",
        "abas": (
            {"nome": "Inbox", "implementada": False, "sprint_alvo": "UX-RD-15"},
        ),
    },
    {
        "nome": "Home",
        "abas": (
            {"nome": "Visão Geral", "implementada": True},
            {"nome": "Finanças", "implementada": True},
            {"nome": "Documentos", "implementada": True},
            {"nome": "Análise", "implementada": True},
            {"nome": "Metas", "implementada": True},
        ),
    },
    {
        "nome": "Finanças",
        "abas": (
            {"nome": "Extrato", "implementada": True},
            {"nome": "Contas", "implementada": True},
            {"nome": "Pagamentos", "implementada": True},
            {"nome": "Projeções", "implementada": True},
        ),
    },
    {
        "nome": "Documentos",
        "abas": (
            {"nome": "Busca Global", "implementada": True},
            {"nome": "Catalogação", "implementada": True},
            {"nome": "Completude", "implementada": True},
            {"nome": "Revisor", "implementada": True},
            {"nome": "Validação por Arquivo", "implementada": True},
            {"nome": "Grafo + Obsidian", "implementada": True},
        ),
    },
    {
        "nome": "Análise",
        "abas": (
            {"nome": "Categorias", "implementada": True},
            {"nome": "Análise", "implementada": True},
            {"nome": "IRPF", "implementada": True},
        ),
    },
    {
        "nome": "Metas",
        "abas": ({"nome": "Metas", "implementada": True},),
    },
    {
        "nome": "Bem-estar",
        "abas": (
            # Sprint UX-RD-17: Hoje e Humor estão implementadas; demais
            # 10 abas seguem com fallback graceful e sprint_alvo
            # apontando para a sprint que vai habilitar cada uma.
            {"nome": "Hoje", "implementada": True},
            {"nome": "Humor", "implementada": True},
            {"nome": "Diário", "implementada": False, "sprint_alvo": "UX-RD-18"},
            {"nome": "Eventos", "implementada": False, "sprint_alvo": "UX-RD-19"},
            {"nome": "Medidas", "implementada": False, "sprint_alvo": "UX-RD-20"},
            {"nome": "Treinos", "implementada": False, "sprint_alvo": "UX-RD-21"},
            {"nome": "Marcos", "implementada": False, "sprint_alvo": "UX-RD-22"},
            {"nome": "Alarmes", "implementada": False, "sprint_alvo": "UX-RD-23"},
            {"nome": "Contadores", "implementada": False, "sprint_alvo": "UX-RD-24"},
            {"nome": "Ciclo", "implementada": False, "sprint_alvo": "UX-RD-25"},
            {"nome": "Tarefas", "implementada": False, "sprint_alvo": "UX-RD-26"},
            {"nome": "Recap", "implementada": False, "sprint_alvo": "UX-RD-27"},
        ),
    },
    {
        "nome": "Sistema",
        "abas": (
            {"nome": "Skills D7", "implementada": False, "sprint_alvo": "UX-RD-05"},
        ),
    },
)


def _href_para(cluster: str, aba: str | None = None) -> str:
    """Monta query-string ``?cluster=...&tab=...`` com URL-encoding.

    Sempre devolve string que começa com ``?``. ``cluster`` é obrigatório;
    ``aba`` é omitida quando ``None``.
    """
    params: list[tuple[str, str]] = [("cluster", cluster)]
    if aba is not None:
        params.append(("tab", aba))
    return "?" + urllib.parse.urlencode(params)


def _renderizar_brand_html() -> str:
    """Bloco do brand (topo da sidebar): glyph SVG ouroboros + nome em mono uppercase.

    FIX-07: porta o glyph 'ouroboros' do mockup canônico (componentes/glyphs.py)
    em vez de placeholder letra "O". Antes: ``<span>O</span>`` (visualmente lia
    "OOuroboros"); agora: ``<svg viewBox="0 0 24 24">...</svg>`` herdando cor.
    """
    from src.dashboard.componentes.glyphs import glyph  # noqa: PLC0415

    return (
        '<a class="sidebar-brand" href="?cluster=Home" '
        'style="text-decoration:none;color:inherit;">'
        f'{glyph("ouroboros", tamanho_px=20, classe="sidebar-brand-glyph")}'
        "<span>Ouroboros</span>"
        "</a>"
    )


def _renderizar_busca_html() -> str:
    """Bloco do campo de busca placeholder + tecla `/`.

    Sprint UX-RD-03 usa o input HTML estático espelhando o mockup. O
    componente Streamlit interativo (``renderizar_input_busca`` da Sprint
    UX-113/114) continua sendo renderizado via Python por ``app.py`` --
    este input HTML é apenas decorativo, mostra o placeholder e o ``kbd``,
    e provê o alvo de foco para a tecla ``/`` mesmo antes do componente
    Streamlit hidratar.
    """
    return (
        '<div class="sidebar-search">'
        '<span class="sidebar-search-icon" aria-hidden="true">?</span>'
        '<input type="text" placeholder="Buscar fornecedor, sha8, valor..." '
        'aria-label="Buscar (atalho: tecla /)" '
        'data-ouroboros-busca="placeholder" />'
        "<kbd>/</kbd>"
        "</div>"
    )


def _renderizar_cluster_html(
    cluster: dict, cluster_ativo: str, aba_ativa: str
) -> str:
    """Bloco de um cluster: header + lista de itens (abas)."""
    nome_cluster = cluster["nome"]
    nome_seguro = html.escape(nome_cluster)

    itens_html: list[str] = []
    for aba in cluster["abas"]:
        nome_aba = aba["nome"]
        ativa = nome_cluster == cluster_ativo and nome_aba == aba_ativa
        # Quando o cluster é o ativo e nenhuma aba específica foi marcada,
        # destacamos a primeira aba implementada (default visual).
        classe = "sidebar-item active" if ativa else "sidebar-item"
        # FIX-12: aria-current="page" no item ativo para tecnologias
        # assistivas (WCAG 1.3.1 Info and Relationships).
        aria_current = ' aria-current="page"' if ativa else ""
        href = _href_para(nome_cluster, nome_aba)
        rotulo = html.escape(nome_aba)
        if not aba.get("implementada", True):
            sprint_alvo = aba.get("sprint_alvo", "")
            badge = (
                f'<span class="count" title="A implementar em {html.escape(sprint_alvo)}">'
                "...</span>"
            )
        else:
            badge = ""
        itens_html.append(
            f'<a class="{classe}"{aria_current} href="{href}" data-cluster="{nome_seguro}" '
            f'data-aba="{rotulo}">{rotulo}{badge}</a>'
        )

    # UX-U-01: badge canônica no header do cluster (mockup 00-shell-navegacao
    # mostra <span class="badge">3</span> no Inbox). Por hora apenas Inbox
    # recebe badge; valor placeholder "..." enquanto contagem real do
    # data/raw/_inbox/ não está implementada.
    badge_cluster_html = ""
    if nome_cluster == "Inbox":
        badge_cluster_html = '<span class="badge" title="Arquivos pendentes na fila">...</span>'

    return (
        '<div class="sidebar-cluster">'
        '<div class="sidebar-cluster-header">'
        f'<span style="display:inline-flex;align-items:center;gap:8px;">'
        f"{nome_seguro}</span>"
        f"{badge_cluster_html}"
        "</div>"
        + "".join(itens_html)
        + "</div>"
    )


def renderizar_sidebar(cluster_ativo: str, aba_ativa: str = "") -> str:
    """Devolve o HTML completo da sidebar redesenhada (8 clusters).

    Args:
        cluster_ativo: nome do cluster atualmente ativo (ex: "Home"). Se
            o nome não estiver em ``CLUSTERS_REDESIGN``, nenhum item é
            destacado (graceful).
        aba_ativa: nome da aba dentro do cluster ativo. Se vazia, nenhuma
            aba específica é destacada.

    Returns:
        Bloco HTML pronto para ``st.markdown(html, unsafe_allow_html=True)``
        DENTRO de ``with st.sidebar:``.
    """
    blocos: list[str] = []
    # FIX-12: skip-link no início da sidebar (WCAG 2.4.1 Bypass Blocks).
    # Invisível por padrão; aparece quando recebe foco via Tab.
    blocos.append(
        '<a class="skip-link sr-only-focusable" href="#main-root">'
        "Pular para conteúdo principal"
        "</a>"
    )
    blocos.append(_renderizar_brand_html())
    blocos.append(_renderizar_busca_html())
    for cluster in CLUSTERS_REDESIGN:
        blocos.append(_renderizar_cluster_html(cluster, cluster_ativo, aba_ativa))
    blocos.append(
        '<div class="sidebar-footer" '
        'style="margin-top:auto;padding:12px 16px;'
        "border-top:1px solid var(--border-subtle);"
        "font-size:11px;color:var(--text-muted);"
        'font-family:var(--ff-mono);">'
        "<div>D7 - cobertura observável</div>"
        "</div>"
    )
    # ``aside.sidebar`` envolve o bloco completo. ``aria-label`` para AT.
    return (
        '<aside class="sidebar ouroboros-sidebar-redesign" aria-label="Navegação">'
        + "".join(blocos)
        + "</aside>"
    )


def renderizar_topbar(
    breadcrumb: Iterable[str], acoes: Iterable[dict] | None = None
) -> str:
    """Devolve o HTML completo da topbar com breadcrumb + slot de ações.

    Args:
        breadcrumb: segmentos do caminho atual (ex: ``["Ouroboros", "Home",
            "Visão Geral"]``). O último segmento recebe a classe ``current``
            (cor primary). Os demais ficam em ``text-secondary`` separados
            por ``/`` em ``border-strong``.
        acoes: iterável opcional de dicts ``{"label": str, "href": str|None,
            "primary": bool}``. Esta sprint emite apenas o slot vazio; sprints
            de página (UX-RD-04+) vão preencher.

    Returns:
        Bloco HTML pronto para ``st.markdown(html, unsafe_allow_html=True)``
        no início de ``main()``, antes do conteúdo principal.
    """
    # FIX-05: segmentos não-current viram <a href="?cluster=...">; current
    # permanece <span>. Mockup canônico (components.css:114-121) define
    # .breadcrumb .seg como elemento clicável; current é a página atual
    # (não-clicável). Importação atrasada de CLUSTERS_VALIDOS para evitar
    # ciclo. "Ouroboros" (primeiro segmento) aponta para ?cluster=Home.
    from src.dashboard.componentes.drilldown import CLUSTERS_VALIDOS  # noqa: PLC0415

    segmentos = list(breadcrumb)
    n = len(segmentos)
    partes_seg: list[str] = []
    for i, seg in enumerate(segmentos):
        ultimo = i == n - 1
        rotulo = html.escape(seg)
        sep = "" if ultimo else '<span class="sep">/</span>'
        if ultimo:
            partes_seg.append(f'<span class="seg current">{rotulo}</span>{sep}')
        else:
            # primeiro segmento "Ouroboros" -> Home; demais -> cluster homônimo se válido
            if i == 0:
                href_pai = "?cluster=Home"
            elif seg in CLUSTERS_VALIDOS:
                href_pai = f"?cluster={html.escape(seg, quote=True)}"
            else:
                href_pai = "?cluster=Home"
            partes_seg.append(
                f'<a class="seg" href="{href_pai}" '
                'style="text-decoration:none;color:inherit;">'
                f'{rotulo}</a>{sep}'
            )

    partes_acoes: list[str] = []
    for acao in acoes or []:
        label = html.escape(str(acao.get("label", "")))
        href = acao.get("href")
        classe = "btn btn-primary btn-sm" if acao.get("primary") else "btn btn-sm"
        if href:
            href_esc = html.escape(str(href), quote=True)
            partes_acoes.append(
                f'<a class="{classe}" href="{href_esc}" '
                'style="text-decoration:none;display:inline-flex;'
                'align-items:center;gap:6px;">'
                f"{label}</a>"
            )
        else:
            partes_acoes.append(f'<button class="{classe}">{label}</button>')

    # UX-U-02: slot dinâmico vindo de st.session_state['topbar_acoes_html'],
    # alimentado pelo helper componentes/topbar_actions.renderizar_grupo_acoes()
    # que cada página pode chamar no início de seu renderizar(). main() em
    # app.py reseta o slot antes de cada run para evitar leak entre páginas.
    acoes_session_html = ""
    try:
        import streamlit as _st
        acoes_session_html = _st.session_state.get("topbar_acoes_html", "")
    except Exception:
        acoes_session_html = ""

    slot_html = "".join(partes_acoes) + acoes_session_html

    return (
        '<header class="topbar ouroboros-topbar-redesign">'
        f'<nav class="breadcrumb" aria-label="Localização">{"".join(partes_seg)}</nav>'
        f'<div class="topbar-actions">{slot_html}</div>'
        "</header>"
    )


def instalar_atalhos_globais() -> None:
    """Injeta o JS de atalhos via ``st.components.v1.html(..., height=0)``.

    Idempotente: o script tem guard ``window.__ouroborosAtalhosInstalados``
    que impede múltiplos listeners. Pode ser chamada uma vez por execução
    de ``main()`` sem efeito colateral acumulativo.
    """
    try:
        from streamlit.components import v1 as components
    except ImportError:  # pragma: no cover -- streamlit indisponível em testes puros
        return

    from src.dashboard.componentes.atalhos_teclado import gerar_html_atalhos

    components.html(gerar_html_atalhos(), height=0)


# "Tudo flui, nada permanece." -- Heráclito
