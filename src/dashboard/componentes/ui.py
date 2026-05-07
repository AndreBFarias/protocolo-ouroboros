# ruff: noqa: E501
"""Componentes universais HTML para o dashboard Ouroboros.

Sprint UX-M-02 (Onda M -- modularização) consolida em **fronteira pública
única** os componentes visuais reutilizáveis do dashboard. Princípio: ZERO
duplicação visual -- toda página usa as mesmas funções, importadas deste
módulo.

Conteúdo da fronteira pública:

1. **Re-exports** de componentes já modularizados:
   * ``page_header`` -- de ``componentes.page_header.renderizar_page_header``
     (Onda U-03; emite ``<h1 class="page-title">`` canônico).
   * ``topbar_actions`` -- de ``componentes.topbar_actions.renderizar_grupo_acoes``
     (Onda U-02; injeta botões no slot ``<div class="topbar-actions">``).

2. **Migrados de ``src/dashboard/tema.py``** (assinatura preservada 100%
   para retrocompatibilidade -- ``tema.py`` mantém aliases shim importando
   destas funções):
   * ``card_html`` -- KPI/info card genérico.
   * ``card_sidebar_html`` -- card específico de sidebar (largura compacta).
   * ``hero_titulo_html`` -- hero legado (badge numérico opcional + título).
   * ``subtitulo_secao_html`` -- cabeçalho de seção uppercase.
   * ``label_uppercase_html`` -- pequeno rótulo MAIÚSCULO.
   * ``callout_html`` -- callout info/warning/success/error.
   * ``progress_inline_html`` -- barra de progresso fina.
   * ``metric_semantic_html`` -- métrica com cor semântica por delta.
   * ``chip_html`` -- chip estilizado para tags/filtros.

3. **NOVOS** (substituem padrões ad-hoc espalhados nas páginas; CSS dos
   componentes virá em UX-M-03):
   * ``kpi_card`` -- KPI canônico (label MAIÚSCULO + valor grande + sub-label).
   * ``data_row`` -- linha de resultado (título + meta inline + snippet).
   * ``group_card`` -- moldura de grupo de resultados (header + linhas).

Imports canônicos das páginas (sub-sprints UX-M-02.A..D fazem migração)::

    from src.dashboard.componentes.ui import (
        page_header,
        topbar_actions,
        card_html,
        callout_html,
        chip_html,
        kpi_card,
        data_row,
        group_card,
    )

Padrões aplicados: VALIDATOR_BRIEF (b) acentuação PT-BR, (g) citação de
filósofo no rodapé, (h) limite 800 linhas.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Imports internos -- componentes já modulares (re-exports)
# ---------------------------------------------------------------------------
from src.dashboard.componentes.page_header import (
    renderizar_page_header as page_header,
)
from src.dashboard.componentes.topbar_actions import (
    renderizar_grupo_acoes as topbar_actions,
)

# ---------------------------------------------------------------------------
# Imports internos -- tokens visuais (CORES, SPACING, FONTE_*)
# ---------------------------------------------------------------------------
# Estes tokens vivem em ``tema.py`` (espelho Python de ``css/tokens.css`` --
# Sprint UX-M-01). As funções migradas usam estes tokens; tema.py NÃO
# pode importar de ui.py para evitar ciclo, então a direção é
# ``ui.py -> tema (tokens)`` e ``tema (aliases shim) -> ui.py (funções)``.
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    FONTE_HERO,
    FONTE_LABEL,
    FONTE_SUBTITULO,
    FONTE_VALOR,
    SPACING,
    icon_html,
    rgba_cor,
    rgba_cor_inline,
)

__all__ = [
    # Re-exports
    "page_header",
    "topbar_actions",
    # Migrados de tema.py (9)
    "card_html",
    "card_sidebar_html",
    "hero_titulo_html",
    "subtitulo_secao_html",
    "label_uppercase_html",
    "callout_html",
    "progress_inline_html",
    "metric_semantic_html",
    "chip_html",
    # Novos (3)
    "kpi_card",
    "data_row",
    "group_card",
]


# ---------------------------------------------------------------------------
# Tabelas internas (callout) -- migradas de tema.py
# ---------------------------------------------------------------------------
_CALLOUT_CORES: dict[str, str] = {
    "info": CORES["neutro"],
    "warning": CORES["alerta"],
    "error": CORES["negativo"],
    "success": CORES["positivo"],
}

_CALLOUT_ICONE: dict[str, str] = {
    "info": "info",
    "warning": "alert-triangle",
    "error": "alert-circle",
    "success": "check-circle",
}


# ---------------------------------------------------------------------------
# Componentes migrados de tema.py (9)
# ---------------------------------------------------------------------------
def card_html(titulo: str, valor: str, cor: str) -> str:
    """Gera HTML de card compacto reutilizável.

    Migrado de ``tema.py`` em UX-M-02. ``tema.card_html`` permanece como
    alias shim importando desta função para retrocompatibilidade.
    """
    return (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-left: 4px solid {cor};"
        f" border-radius: 8px;"
        f" padding: {SPACING['md']}px {SPACING['md'] + 2}px;"
        f" margin: {SPACING['sm']}px 0;"
        f" box-shadow: 0 2px 8px rgba(0,0,0,0.3);"
        f'">'
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: {FONTE_LABEL}px;"
        f" font-weight: 600;"
        f" letter-spacing: 0.08em;"
        f" text-transform: uppercase;"
        f' margin: 0;">{titulo}</p>'
        f'<p style="color: {cor};'
        f" font-size: {FONTE_VALOR}px;"
        f" font-weight: bold;"
        f" white-space: nowrap;"
        f' margin: {SPACING["xs"]}px 0 0 0;">{valor}</p>'
        f"</div>"
    )


def card_sidebar_html(titulo: str, valor: str, cor: str) -> str:
    """Gera HTML de card compacto para sidebar.

    Sprint UX-118: ``margin-left: 0`` e ``box-sizing: border-box`` impedem
    que a borda esquerda 3px colorida transborde o ``padding-left`` de
    16px (PADDING_CHIP) aplicado pelo seletor
    ``[data-testid="stSidebar"] > div:first-child`` da Sprint UX-116. Sem
    estes dois ajustes, o card aparenta "vazar" o retângulo interno da
    sidebar.

    Migrado de ``tema.py`` em UX-M-02. ``tema.card_sidebar_html``
    permanece como alias shim.
    """
    return (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-left: 3px solid {cor};"
        f" border-radius: 6px;"
        f" padding: {SPACING['sm'] + 2}px {SPACING['md'] - 2}px;"
        f" margin-left: 0;"
        f" margin-bottom: {SPACING['sm']}px;"
        f" box-sizing: border-box;"
        f" box-shadow: 0 2px 6px rgba(0,0,0,0.25);"
        f'">'
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: {FONTE_LABEL}px;"
        f' margin: 0;">{titulo}</p>'
        f'<p style="color: {cor};'
        f" font-size: {FONTE_SUBTITULO}px;"
        f" font-weight: bold;"
        f' margin: 2px 0 0 0;">{valor}</p>'
        f"</div>"
    )


def hero_titulo_html(numero: str = "", texto: str = "", descricao: str | None = None) -> str:
    """Cabeçalho grande de página (display / hero). Sprint 20.

    Sprint UX-122: o primeiro parâmetro virou opcional (default ``""``).
    Quando vazio, o ``<span>`` do badge numérico é omitido completamente --
    header mostra apenas o título. Retrocompatível: chamadas antigas com
    primeiro arg numérico seguem renderizando o badge como antes.

    Migrado de ``tema.py`` em UX-M-02.
    """
    bloco_desc = ""
    if descricao:
        bloco_desc = (
            f'<p style="color: {CORES["texto_sec"]}; font-size: {FONTE_CORPO}px;'
            f" margin: {SPACING['sm']}px 0 0 0; max-width: 780px;"
            f' line-height: 1.5;">{descricao}</p>'
        )
    bloco_numero = ""
    if numero:
        bloco_numero = (
            f'<span style="font-size: 48px; font-weight: 700;'
            f" color: {CORES['destaque']};"
            f' line-height: 1;">{numero}</span>'
        )
    return (
        f'<div style="margin: 0 0 {SPACING["lg"]}px 0;">'
        f'<div style="display: flex; align-items: baseline; gap: {SPACING["md"]}px;">'
        f"{bloco_numero}"
        f'<span style="font-size: {FONTE_HERO}px; font-weight: 700;'
        f" color: {CORES['texto']};"
        f' line-height: 1.2;">{texto}</span>'
        f"</div>"
        f"{bloco_desc}"
        f"</div>"
    )


def subtitulo_secao_html(texto: str, *, cor: str | None = None) -> str:
    """Cabeçalho de seção padrão uppercase com linha sutil. Sprint 20.

    Migrado de ``tema.py`` em UX-M-02.
    """
    cor_efetiva = cor or CORES["neutro"]
    return (
        f'<h3 style="'
        f" color: {cor_efetiva};"
        f" font-size: {FONTE_LABEL}px;"
        f" font-weight: 700;"
        f" letter-spacing: 0.12em;"
        f" text-transform: uppercase;"
        f" margin: {SPACING['lg']}px 0 {SPACING['sm'] + 4}px 0;"
        f" border-bottom: 1px solid {rgba_cor_inline(CORES['texto_sec'], 0.25)};"
        f' padding-bottom: {SPACING["xs"] + 2}px;">{texto}</h3>'
    )


def label_uppercase_html(texto: str, *, cor: str | None = None) -> str:
    """Pequeno rótulo uppercase (meta-informação, legenda). Sprint 20.

    Migrado de ``tema.py`` em UX-M-02.
    """
    cor_efetiva = cor or CORES["texto_sec"]
    return (
        f'<span style="color: {cor_efetiva};'
        f" font-size: {FONTE_LABEL}px;"
        f" font-weight: 600;"
        f" letter-spacing: 0.08em;"
        f' text-transform: uppercase;">{texto}</span>'
    )


def callout_html(
    tipo: str,
    mensagem: str,
    titulo: str | None = None,
) -> str:
    """Sprint 92c: callout Dracula-consistente.

    ``tipo`` in ``{"info", "warning", "error", "success"}`` define cor da
    borda e ícone Feather. ``mensagem`` é o corpo; ``titulo`` opcional vira
    um ``<strong>`` acima da mensagem.

    Substitui ``st.warning`` / ``st.info`` / ``st.success`` / ``st.error``
    (paleta amarelada default do Streamlit destoa do tema escuro). Tipos
    desconhecidos caem em ``info`` para degradação silenciosa.

    Migrado de ``tema.py`` em UX-M-02.
    """
    cor = _CALLOUT_CORES.get(tipo, _CALLOUT_CORES["info"])
    nome_icone = _CALLOUT_ICONE.get(tipo, _CALLOUT_ICONE["info"])
    icone = icon_html(nome_icone, tamanho=18, cor=cor)
    titulo_html = ""
    if titulo:
        titulo_html = (
            f'<strong style="color: {cor}; font-size: var(--font-corpo);'
            f' display: block; margin-bottom: var(--spacing-xs);">{titulo}</strong>'
        )
    return (
        '<div style="'
        "background-color: var(--color-card-fundo);"
        f" border-left: 4px solid {cor};"
        " border-radius: 6px;"
        " padding: var(--spacing-md);"
        " margin: var(--spacing-sm) 0;"
        " display: flex;"
        " gap: var(--spacing-sm);"
        ' align-items: flex-start;">'
        f'<span style="color: {cor}; flex-shrink: 0; line-height: 1;">{icone}</span>'
        '<div style="flex: 1;">'
        f"{titulo_html}"
        f'<span style="color: var(--color-texto); font-size: var(--font-corpo);">'
        f"{mensagem}</span>"
        "</div>"
        "</div>"
    )


def progress_inline_html(
    pct: float,
    cor: str | None = None,
    label: str | None = None,
) -> str:
    """Sprint 92c: barra de progresso fina para embutir em card/linha.

    ``pct`` no intervalo ``[0.0, 1.0]`` (clampado). ``cor`` do preenchido:
    quando ``None``, usa ``--color-destaque`` (Dracula roxo brand). ``label``
    opcional fica acima da barra (ex: ``"78% -- R$ 7.800 / R$ 10.000"``).

    Consolida a versão local de ``metas.py::_progress_inline_html`` (Sprint
    92a.9): single-source na fronteira ``ui.py``.

    Migrado de ``tema.py`` em UX-M-02.
    """
    pct_clamped = max(0.0, min(float(pct), 1.0))
    largura = pct_clamped * 100
    cor_final = cor if cor else "var(--color-destaque)"
    label_html = ""
    if label:
        label_html = (
            '<p style="color: var(--color-texto-sec);'
            " font-size: var(--font-label);"
            ' margin: 0 0 var(--spacing-xs) 0;">'
            f"{label}</p>"
        )
    return (
        f"{label_html}"
        '<div style="height: 4px;'
        f" background: {rgba_cor(CORES['texto_sec'], 0.25)};"
        " border-radius: 2px;"
        ' margin: var(--spacing-xs) 0 0 0;">'
        f'<div style="width: {largura:.1f}%; height: 100%;'
        f" background: {cor_final};"
        ' border-radius: 2px;"></div>'
        "</div>"
    )


def metric_semantic_html(
    label: str,
    valor: str,
    delta: float | None = None,
    cor: str | None = None,
) -> str:
    """Sprint 92c: metric card com coloração semântica por sinal.

    Substitui ``st.metric`` que não permite colorir o valor (apenas o delta).
    Regra de cor automática quando ``cor`` é ``None``:
      * ``delta > 0`` -> ``--color-positivo``
      * ``delta < 0`` -> ``--color-negativo``
      * ``delta == 0`` ou ``None`` -> ``--color-texto-sec`` (neutro)

    Caller pode forçar cor específica passando ``cor`` em hex. ``label`` em
    caps-lock reduzido; ``valor`` é string já formatada (ex: ``"R$ 1.234,56"``).

    Migrado de ``tema.py`` em UX-M-02.
    """
    if cor:
        cor_efetiva = cor
    elif delta is None or delta == 0:
        cor_efetiva = "var(--color-texto-sec)"
    elif delta > 0:
        cor_efetiva = "var(--color-positivo)"
    else:
        cor_efetiva = "var(--color-negativo)"

    delta_html = ""
    if delta is not None and delta != 0:
        sinal = "+" if delta > 0 else ""
        delta_cor = "var(--color-positivo)" if delta > 0 else "var(--color-negativo)"
        delta_html = (
            f'<p style="color: {delta_cor};'
            " font-size: var(--font-label);"
            ' margin: var(--spacing-xs) 0 0 0;">'
            f"{sinal}{delta:.1f}%</p>"
        )

    return (
        '<div style="padding: var(--spacing-xs) 0;">'
        '<p style="color: var(--color-texto-sec);'
        " font-size: var(--font-label);"
        ' margin: 0 0 var(--spacing-xs) 0;">'
        f"{label}</p>"
        f'<p style="color: {cor_efetiva};'
        " font-size: var(--font-hero);"
        " font-weight: 700;"
        ' margin: 0;">'
        f"{valor}</p>"
        f"{delta_html}"
        "</div>"
    )


def chip_html(
    texto: str,
    cor: str | None = None,
    clicavel: bool = True,
) -> str:
    """Sprint 92c: chip visual para tags, tipos, filtros ativos.

    ``cor`` da borda + texto; padrão ``--color-destaque``. Quando
    ``clicavel=True``, adiciona ``cursor: pointer`` e hover sutil; quando
    ``False``, chip é puramente decorativo (sem pointer).

    Uso canônico: tipos do multiselect do Grafo Obsidian, tags de filtros
    ativos no breadcrumb do Extrato.

    Migrado de ``tema.py`` em UX-M-02.
    """
    cor_final = cor if cor else "var(--color-destaque)"
    cursor = "pointer" if clicavel else "default"
    hover_opacity = "0.85" if clicavel else "1"
    return (
        '<span style="'
        "display: inline-block;"
        " padding: var(--spacing-xs) var(--spacing-sm);"
        " margin: 2px 4px 2px 0;"
        " border-radius: 12px;"
        f" border: 1px solid {cor_final};"
        f" color: {cor_final};"
        " font-size: var(--font-label);"
        " font-weight: 600;"
        f" cursor: {cursor};"
        f" opacity: {hover_opacity};"
        ' background-color: transparent;">'
        f"{texto}"
        "</span>"
    )


# ---------------------------------------------------------------------------
# NOVOS componentes (3) -- Sprint UX-M-02
# ---------------------------------------------------------------------------
# Substituem padrões ad-hoc espalhados nas páginas. CSS escopado dos
# componentes virá em UX-M-03 (.kpi-card, .data-row, .group-card em
# src/dashboard/css/components.css). Por ora, estilo inline garante
# autonomia em qualquer página antes da migração CSS.

_KPI_ACCENT_PERMITIDOS: dict[str, str] = {
    "purple": CORES["destaque"],
    "cyan": CORES["neutro"],
    "green": CORES["positivo"],
    "yellow": CORES["info"],
    "red": CORES["negativo"],
    "orange": CORES["alerta"],
    "pink": CORES["superfluo"],
}


def kpi_card(
    label: str,
    valor: str,
    sub_label: str = "",
    accent: str = "purple",
) -> str:
    """KPI card canônico: label MAIÚSCULO + valor grande + sub-label.

    Substitui as ~5 classes locais espalhadas (``.vg-t01-kpi``,
    ``.kpi-card``, ``.pat-card`` etc.). Usar em todas as páginas com KPIs
    em ``st.columns``.

    Args:
        label: rótulo curto (será UPPERCASE via CSS ``text-transform``).
        valor: número/texto formatado (ex: ``"48"``, ``"R$ 776.571,59"``).
        sub_label: contexto secundário (ex: ``"11 tipos no grafo"``).
            Quando vazio, o ``<div class="kpi-sub">`` é omitido.
        accent: cor da borda esquerda. Aceita ``"purple"`` (padrão),
            ``"cyan"``, ``"green"``, ``"yellow"``, ``"red"``, ``"orange"``,
            ``"pink"``. Valores desconhecidos caem em ``"purple"``.

    Returns:
        HTML pronto para ``st.markdown(..., unsafe_allow_html=True)``.

    Exemplo::

        from src.dashboard.componentes.ui import kpi_card
        st.markdown(
            kpi_card("Saldo do mês", "R$ 1.234,56", "vs R$ 980 anterior", accent="green"),
            unsafe_allow_html=True,
        )
    """
    cor_borda = _KPI_ACCENT_PERMITIDOS.get(accent, _KPI_ACCENT_PERMITIDOS["purple"])
    sub_html = ""
    if sub_label:
        sub_html = (
            f'<div class="kpi-sub" style="'
            f"color: {CORES['texto_muted']};"
            f" font-size: {FONTE_LABEL}px;"
            f' margin-top: {SPACING["xs"]}px;">{sub_label}</div>'
        )
    return (
        f'<div class="kpi-card kpi-card--{accent}" style="'
        f"background-color: {CORES['card_fundo']};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-left: 4px solid {cor_borda};"
        f" border-radius: 8px;"
        f" padding: {SPACING['md']}px {SPACING['md'] + 2}px;"
        f' margin: {SPACING["sm"]}px 0;">'
        f'<div class="kpi-label" style="'
        f"color: {CORES['texto_sec']};"
        f" font-size: {FONTE_LABEL}px;"
        f" font-weight: 600;"
        f" letter-spacing: 0.08em;"
        f" text-transform: uppercase;"
        f' margin: 0;">{label}</div>'
        f'<div class="kpi-valor" style="'
        f"color: {cor_borda};"
        f" font-size: {FONTE_VALOR}px;"
        f" font-weight: 700;"
        f" white-space: nowrap;"
        f' margin: {SPACING["xs"]}px 0 0 0;">{valor}</div>'
        f"{sub_html}"
        f"</div>"
    )


def data_row(
    titulo_html: str,
    meta_dict: dict[str, str] | None = None,
    snippet_html: str = "",
) -> str:
    """Linha de resultado com título + meta inline + snippet opcional.

    Padrão visual de busca/listagem: título à esquerda, lista de
    pares ``chave: valor`` em cinza pequeno à direita, snippet
    (preview/explicação) abaixo. Substitui markup ad-hoc em
    ``busca.py``, ``revisor.py``, ``catalogacao.py``.

    Args:
        titulo_html: HTML já renderizado para o título (caller pode
            embutir links, ícones, badges). Não é re-escapado.
        meta_dict: pares chave/valor renderizados como
            ``"chave: valor"`` separados por ``·``. Quando ``None`` ou
            vazio, o bloco meta é omitido.
        snippet_html: trecho descritivo abaixo do título. HTML cru
            (caller responsável por escape). Omitido quando vazio.

    Returns:
        HTML pronto para ``st.markdown(..., unsafe_allow_html=True)``.

    Exemplo::

        from src.dashboard.componentes.ui import data_row
        st.markdown(
            data_row(
                titulo_html='<a href="?id=42">Compra na Padaria</a>',
                meta_dict={"data": "2026-04-12", "valor": "R$ 18,40"},
                snippet_html="<em>Categoria: Alimentação · Obrigatório</em>",
            ),
            unsafe_allow_html=True,
        )
    """
    meta_html = ""
    if meta_dict:
        partes = " · ".join(
            f'<span style="color: {CORES["texto_muted"]};">{chave}:</span> '
            f'<span style="color: {CORES["texto_sec"]};">{valor}</span>'
            for chave, valor in meta_dict.items()
        )
        meta_html = (
            f'<div class="data-row__meta" style="'
            f"font-size: {FONTE_LABEL}px;"
            f' margin-top: {SPACING["xs"]}px;">{partes}</div>'
        )
    snippet_block = ""
    if snippet_html:
        snippet_block = (
            f'<div class="data-row__snippet" style="'
            f"color: {CORES['texto_sec']};"
            f" font-size: {FONTE_LABEL + 1}px;"
            f' margin-top: {SPACING["xs"]}px;">{snippet_html}</div>'
        )
    return (
        f'<div class="data-row" style="'
        f"padding: {SPACING['sm'] + 2}px 0;"
        f' border-bottom: 1px solid {rgba_cor_inline(CORES["texto_sec"], 0.15)};">'
        f'<div class="data-row__titulo" style="'
        f"color: {CORES['texto']};"
        f" font-size: {FONTE_LABEL + 2}px;"
        f' font-weight: 600;">{titulo_html}</div>'
        f"{meta_html}"
        f"{snippet_block}"
        f"</div>"
    )


def group_card(
    titulo: str,
    linhas_html: str,
    contagem: str = "",
    pill_label: str = "",
) -> str:
    """Moldura de grupo de resultados (header + linhas).

    Cartão visual que agrupa várias ``data_row`` (ou outro conteúdo
    HTML) sob um cabeçalho com título + contagem + pílula opcional.
    Padrão de Busca Global, Revisor 4-way, Catalogação.

    Args:
        titulo: rótulo do grupo (ex: ``"Documentos com divergência"``).
        linhas_html: HTML já renderizado de todas as linhas do grupo.
            Caller usa ``"".join(data_row(...) for ... in ...)`` ou
            equivalente.
        contagem: texto curto à direita do título (ex: ``"12 itens"``).
            Omitido quando vazio.
        pill_label: pílula colorida ao lado do contagem (ex:
            ``"d7-graduado"`` -> chip verde). Aceita os tipos da
            função ``chip_html``. Omitido quando vazio.

    Returns:
        HTML pronto para ``st.markdown(..., unsafe_allow_html=True)``.

    Exemplo::

        from src.dashboard.componentes.ui import group_card, data_row
        linhas = "".join(data_row(f"<b>Item {i}</b>") for i in range(3))
        st.markdown(
            group_card(
                titulo="Pendências do Revisor",
                linhas_html=linhas,
                contagem="3 itens",
                pill_label="atenção",
            ),
            unsafe_allow_html=True,
        )
    """
    pill_html = ""
    if pill_label:
        pill_html = chip_html(pill_label, clicavel=False)
    contagem_html = ""
    if contagem:
        contagem_html = (
            f'<span class="group-card__contagem" style="'
            f"color: {CORES['texto_muted']};"
            f" font-size: {FONTE_LABEL}px;"
            f' margin-right: {SPACING["sm"]}px;">{contagem}</span>'
        )
    header_extras = ""
    if contagem_html or pill_html:
        header_extras = (
            f'<div style="display: flex; align-items: center; gap: {SPACING["xs"]}px;">'
            f"{contagem_html}{pill_html}"
            f"</div>"
        )
    return (
        f'<div class="group-card" style="'
        f"background-color: {CORES['card_fundo']};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-radius: 8px;"
        f" padding: {SPACING['md']}px;"
        f' margin: {SPACING["md"]}px 0;">'
        f'<div class="group-card__header" style="'
        f"display: flex;"
        f" align-items: center;"
        f" justify-content: space-between;"
        f" margin-bottom: {SPACING['sm']}px;"
        f' padding-bottom: {SPACING["sm"]}px;'
        f' border-bottom: 1px solid {rgba_cor_inline(CORES["texto_sec"], 0.2)};">'
        f'<h4 style="'
        f"color: {CORES['texto']};"
        f" font-size: {FONTE_LABEL + 3}px;"
        f" font-weight: 700;"
        f" letter-spacing: 0.04em;"
        f" margin: 0;"
        f' text-transform: uppercase;">{titulo}</h4>'
        f"{header_extras}"
        f"</div>"
        f'<div class="group-card__body">{linhas_html}</div>'
        f"</div>"
    )


# "A unidade é a forma da multiplicidade." -- Plotino
