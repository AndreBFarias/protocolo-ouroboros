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

from pathlib import Path

# ---------------------------------------------------------------------------
# Imports internos -- componentes já modulares (re-exports)
# ---------------------------------------------------------------------------
from src.dashboard.componentes.html_utils import minificar
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
    # Helper de carregamento de CSS por página
    "carregar_css_pagina",
    # Micro-componentes UX-V-02 (6)
    "sparkline_html",
    "bar_uso_html",
    "donut_inline_html",
    "prazo_ritmo_falta_html",
    "tab_counter_html",
    "insight_card_html",
    # Sync observabilidade (UX-V-04)
    "ler_sync_info",
    "sync_indicator_html",
    # Fallback estado-inicial (UX-V-03)
    "fallback_estado_inicial_html",
    # UX-V-01: chip-bar de filtros globais
    "chip_bar_filtros_globais",
]


# ---------------------------------------------------------------------------
# Helper -- CSS dedicado por página
# ---------------------------------------------------------------------------
_RAIZ_CSS_PAGINAS = Path(__file__).resolve().parent.parent / "css" / "paginas"


def carregar_css_pagina(nome: str) -> str:
    """Retorna ``<style>...</style>`` carregado de ``css/paginas/<nome>.css``.

    Padrão Onda M para CSS específico de página: classes que NÃO duplicam
    ``components.css`` ficam em arquivo dedicado, não inline em Python.
    Quando o arquivo não existe, retorna string vazia (no-op seguro).
    """
    css_path = _RAIZ_CSS_PAGINAS / f"{nome}.css"
    if not css_path.exists():
        return ""
    return f"<style>\n{css_path.read_text(encoding='utf-8')}\n</style>"


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


def hero_titulo_html(  # acento ok -- noqa-acento
    numero: str = "",
    texto: str = "",
    descricao: str | None = None,  # acento ok -- noqa-acento
) -> str:
    """Cabeçalho grande de página (display / hero). Sprint 20.

    Sprint UX-122: o primeiro parâmetro virou opcional (default ``""``).
    Quando vazio, o ``<span>`` do badge numérico é omitido completamente --
    header mostra apenas o título. Retrocompatível: chamadas antigas com
    primeiro arg numérico seguem renderizando o badge como antes.

    Migrado de ``tema.py`` em UX-M-02.
    """
    bloco_desc = ""
    if descricao:  # acento ok -- noqa-acento
        bloco_desc = (
            f'<p style="color: {CORES["texto_sec"]}; font-size: {FONTE_CORPO}px;'
            f" margin: {SPACING['sm']}px 0 0 0; max-width: 780px;"
            f' line-height: 1.5;">{descricao}</p>'  # acento ok -- noqa-acento
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


# ---------------------------------------------------------------------------
# === Micro-componentes UX-V-02 ===
# ---------------------------------------------------------------------------
# Sprint UX-V-02 (Onda V -- paridade visual) entrega 6 micro-componentes
# transversais consumidos por páginas da Leva V-2: sparkline (Contas/Medidas),
# bar_uso (Contas/Categorias), donut_inline + prazo_ritmo_falta (Metas),
# tab_counter (Análise/Memórias) e insight_card (Análise/Cruzamentos).
#
# Esta sprint apenas ENTREGA a fronteira; migração das páginas é escopo das
# sprints V-2.x. CSS canônico vive em ``src/dashboard/css/components.css``.
#
# Referência: docs/sprints/concluidos/sprint_ux_v_02_micro_componentes.md.

# acento ok -- noqa-acento (bloco): chaves canônicas do enum de insight são ASCII por contrato
# de domínio. Renomear quebraria callers e dados serializados. Acento aplicado
# apenas na label visível ("ATENÇÃO" / "PREVISÃO") via _INSIGHT_TIPO_LABEL.
_INSIGHT_TIPOS_VALIDOS = {"positivo", "atencao", "descoberta", "previsao"}  # acento ok -- noqa-acento

# Labels canônicos PT-BR (UX-V-2.6 fix: tipo.upper() resultava em ASCII --  # acento ok -- noqa-acento
# "ATENCAO" / "PREVISAO" sem acento; rótulo correto vem deste mapa).  # acento ok -- noqa-acento
_INSIGHT_TIPO_LABEL = {
    "positivo": "POSITIVO",
    "atencao": "ATENÇÃO",  # acento ok -- noqa-acento
    "descoberta": "DESCOBERTA",
    "previsao": "PREVISÃO",  # acento ok -- noqa-acento
}


def sparkline_html(
    valores: list[float],
    *,
    cor: str | None = None,
    largura: int = 80,
    altura: int = 24,
) -> str:
    """Sparkline SVG inline minimalista (sem libs externas).

    Args:
        valores: série numérica (>=2 pontos). Lista vazia ou ponto único
            retornam string vazia (degradação graciosa, ADR-10).
        cor: hex/var token. Default ``var(--accent-purple)``.
        largura: pixels (default 80).
        altura: pixels (default 24).

    Returns:
        ``<span class="sparkline">...</span>`` minificado.
    """
    if not valores or len(valores) < 2:
        return ""
    cor_efetiva = cor or "var(--accent-purple)"
    minimo, maximo = min(valores), max(valores)
    intervalo = (maximo - minimo) or 1.0
    n = len(valores)
    pontos = " ".join(
        f"{(i / (n - 1)) * largura:.2f},{altura - ((v - minimo) / intervalo) * altura:.2f}"
        for i, v in enumerate(valores)
    )
    return minificar(
        f"""
        <span class="sparkline">
          <svg viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}">
            <polyline class="sparkline-line"
              fill="none" stroke="{cor_efetiva}" stroke-width="1.5"
              points="{pontos}" />
          </svg>
        </span>
        """
    )


def bar_uso_html(
    usado: float,
    total: float,
    *,
    label: str = "",
    cor: str | None = None,
) -> str:
    """Barra horizontal de uso percentual usado/total.

    Args:
        usado: valor consumido (numerador).
        total: capacidade total (denominador). ``<= 0`` retorna string vazia.
        label: texto pequeno acima da barra (ex.: ``"36% usado"``).
        cor: override; default escolhe por percentual
            (>=90 vermelho, >=60 laranja, senão verde).

    Returns:
        ``<div class="bar-uso">...</div>`` minificado.
    """
    if total <= 0:
        return ""
    pct = max(0.0, min(100.0, (usado / total) * 100.0))
    if cor is None:
        if pct >= 90:
            cor = "var(--accent-red)"
        elif pct >= 60:
            cor = "var(--accent-orange)"
        else:
            cor = "var(--accent-green)"
    label_html = f'<span class="bar-uso-label">{label}</span>' if label else ""
    return minificar(
        f"""
        <div class="bar-uso" data-pct="{pct:.1f}">
          {label_html}
          <div class="bar-uso-track">
            <span class="bar-uso-fill" style="width:{pct:.2f}%; background:{cor};"></span>
          </div>
        </div>
        """
    )


def donut_inline_html(
    percentual: float,
    *,
    tamanho: int = 60,
    cor: str | None = None,
) -> str:
    """Donut SVG compacto com percentual no centro.

    Args:
        percentual: 0..100 (clamped automaticamente).
        tamanho: pixels do quadrado SVG (default 60).
        cor: stroke do arco; default por percentual
            (=100 verde, >=70 amarelo, >=30 roxo, senão vermelho).

    Returns:
        ``<span class="donut-mini">...</span>`` minificado.
    """
    pct = max(0.0, min(100.0, percentual))
    if cor is None:
        if pct >= 100:
            cor = "var(--accent-green)"
        elif pct >= 70:
            cor = "var(--accent-yellow)"
        elif pct >= 30:
            cor = "var(--accent-purple)"
        else:
            cor = "var(--accent-red)"
    raio = (tamanho - 8) / 2  # margem 4px
    centro = tamanho / 2
    circ = 2 * 3.14159 * raio
    offset = circ * (1 - pct / 100)
    return minificar(
        f"""
        <span class="donut-mini" style="width:{tamanho}px;height:{tamanho}px;">
          <svg viewBox="0 0 {tamanho} {tamanho}">
            <circle class="donut-mini-track"
              cx="{centro}" cy="{centro}" r="{raio:.2f}"
              fill="none" stroke="var(--bg-elevated)" stroke-width="4" />
            <circle class="donut-mini-fill"
              cx="{centro}" cy="{centro}" r="{raio:.2f}"
              fill="none" stroke="{cor}" stroke-width="4"
              stroke-dasharray="{circ:.2f}" stroke-dashoffset="{offset:.2f}"
              transform="rotate(-90 {centro} {centro})" />
          </svg>
          <span class="donut-mini-pct">{pct:.0f}%</span>
        </span>
        """
    )


def prazo_ritmo_falta_html(prazo: str, ritmo: str, falta: str) -> str:
    """Layout de 3 colunas (PRAZO / RITMO / FALTA) usado em cards de meta.

    Args:
        prazo: texto curto (ex.: ``"SET/2026"``).
        ritmo: texto curto (ex.: ``"+R$ 2.500/MÊS"``).
        falta: texto curto (ex.: ``"5 MESES"``).

    Returns:
        ``<div class="prazo-ritmo-falta">...</div>`` minificado.
    """
    return minificar(
        f"""
        <div class="prazo-ritmo-falta">
          <div class="prf-celula">
            <span class="prf-rotulo">PRAZO</span>
            <span class="prf-valor">{prazo}</span>
          </div>
          <div class="prf-celula">
            <span class="prf-rotulo">RITMO</span>
            <span class="prf-valor">{ritmo}</span>
          </div>
          <div class="prf-celula">
            <span class="prf-rotulo">FALTA</span>
            <span class="prf-valor">{falta}</span>
          </div>
        </div>
        """
    )


def tab_counter_html(label: str, count: int, *, ativo: bool = False) -> str:
    """Tab inline com counter (ex.: ``"Fluxo de caixa  3"``).

    Renderiza apenas o HTML do rótulo + counter, embarcável em
    ``st.tabs([...])`` via custom CSS ou em radio horizontal. Não
    implementa comportamento de tab (responsabilidade da página).

    Args:
        label: texto da tab.
        count: número exibido pequeno após o label.
        ativo: se True aplica classe ``.tab-counter-ativo`` (cor accent).

    Returns:
        ``<span class="tab-counter">...</span>`` minificado.
    """
    classe = "tab-counter tab-counter-ativo" if ativo else "tab-counter"
    return minificar(
        f"""
        <span class="{classe}">
          {label}
          <span class="tab-counter-num">{count}</span>
        </span>
        """
    )


def insight_card_html(tipo: str, titulo: str, corpo: str) -> str:
    """Card lateral de insight derivado.

    Args:
        tipo: ``"positivo" | "atencao" | "descoberta" | "previsao"``.  # acento ok -- noqa-acento
            Outro valor cai em ``"descoberta"`` (degradação graciosa,
            ADR-10) -- não levanta erro.
        titulo: heading curto (<=60 chars idealmente).
        corpo: parágrafo (HTML safe esperado; chamador escapa input
            não-confiável).

    Returns:
        ``<div class="insight-card insight-{tipo}">...</div>`` minificado.
    """
    if tipo not in _INSIGHT_TIPOS_VALIDOS:
        tipo = "descoberta"
    return minificar(
        f"""
        <div class="insight-card insight-{tipo}">
          <span class="insight-card-tipo">{_INSIGHT_TIPO_LABEL[tipo]}</span>
          <h4 class="insight-card-titulo">{titulo}</h4>
          <p class="insight-card-corpo">{corpo}</p>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# === Sync indicator (UX-V-04) ===
# ---------------------------------------------------------------------------
# Componente discreto que expõe quando o pipeline vault → cache → dashboard
# rodou pela última vez. Fallback resiliente (ADR-10): se o cache não existe
# ou está corrompido, renderiza "sync: nunca" sem quebrar a página.
#
# Pareado com ``src.obsidian.sync_rico._gravar_last_sync`` (escritor).


def ler_sync_info() -> dict | None:
    """Lê ``.ouroboros/cache/last_sync.json`` da raiz do projeto.

    Retorna o payload (dict) quando o arquivo existe e é JSON válido.
    Retorna ``None`` quando ausente, ilegível ou malformado -- chamadores
    devem tratar ambos os casos como "nunca sincronizado" (graceful, ADR-10).
    """
    import json
    try:
        raiz = Path(__file__).resolve().parents[3]
        arquivo = raiz / ".ouroboros" / "cache" / "last_sync.json"
        if not arquivo.exists():
            return None
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def sync_indicator_html(sync_info: dict | None = None) -> str:
    """Chip pequeno mostrando idade da última sync vault → cache.

    - Verde (default): sync < 1h.
    - Amarelo (``sync-indicator-stale``): sync entre 1h e 24h.
    - Amarelo + "rode --sync": sync > 24h ou nunca.
    """
    from datetime import datetime, timezone

    if sync_info is None:
        sync_info = ler_sync_info()

    if not sync_info or "data" not in sync_info:
        return (
            '<span class="sync-indicator sync-indicator-stale" '
            'title="Nunca sincronizado">sync: nunca</span>'
        )

    try:
        ts = datetime.fromisoformat(sync_info["data"])
    except (ValueError, TypeError):
        return (
            '<span class="sync-indicator sync-indicator-stale" '
            'title="Timestamp inválido">sync: ?</span>'
        )

    agora = datetime.now(tz=ts.tzinfo or timezone.utc)
    delta_horas = (agora - ts).total_seconds() / 3600

    if delta_horas < 1:
        classe = ""
        minutos = max(0, int(delta_horas * 60))
        rotulo = f"sync agora ({minutos}min atrás)"
    elif delta_horas < 24:
        classe = "sync-indicator-stale"
        rotulo = f"sync {int(delta_horas)}h atrás"
    else:
        classe = "sync-indicator-stale"
        dias = int(delta_horas / 24)
        rotulo = f"sync {dias}d atrás (rode --sync)"

    n = sync_info.get("n_arquivos", "?")
    titulo = f"Última sync: {sync_info['data']} · {n} arquivos"
    classe_final = f"sync-indicator {classe}".strip()
    return (
        f'<span class="{classe_final}" title="{titulo}">{rotulo}</span>'
    )


# ---------------------------------------------------------------------------
# Chip-bar de filtros globais (UX-V-01)
# ---------------------------------------------------------------------------


def chip_bar_filtros_globais(dados: dict) -> tuple[str, str, str]:
    """Chip-bar fina canônica de filtros globais (UX-V-01).

    Substitui o ``st.expander("Filtros globais", ...)`` legado em
    ``app.py:_filtros_globais_main``. Preserva 100% do contrato:

    - Mesmas 7 chaves de session_state: ``seletor_granularidade``,
      ``seletor_periodo``, ``seletor_mes_base``, ``seletor_detalhe``,  # acento ok -- noqa-acento
      ``seletor_pessoa``, ``seletor_forma_pagamento``, ``filtro_forma``.
    - Mesmo retorno: ``(periodo, pessoa, granularidade)``.  # acento ok -- noqa-acento
    - Mesma lógica condicional de período por granularidade
      (Ano: anos disponíveis; Mês: meses; Semana: meses + semanas;
      Dia: meses + dias).

    O que muda é APENAS o layout visual: chip-bar fina ao invés de
    expander. Pipeline downstream (37 sítios consumindo session_state)
    continua intacto.

    Args:
        dados: dicionário de DataFrames; consumido por
            ``obter_meses_disponiveis`` etc.

    Returns:
        ``(periodo, pessoa, granularidade)`` para o dispatcher.  # acento ok -- noqa-acento
    """
    import streamlit as st

    from src.dashboard.dados import (
        obter_anos_disponiveis,
        obter_dias_do_mes,
        obter_meses_disponiveis,
        obter_semanas_do_mes,
    )
    from src.utils.pessoas import nome_de

    meses = obter_meses_disponiveis(dados)
    if not meses:
        st.warning("Nenhum dado disponível.")
        return "", "Todos", "Mês"

    nome_a = nome_de("pessoa_a")
    nome_b = nome_de("pessoa_b")
    opcoes_pessoa = ["Todos", nome_a, nome_b]

    # Estado atual lido de session_state com defaults (espelha visual).
    granularidade_atual = st.session_state.get("seletor_granularidade", "Mês")
    pessoa_atual = st.session_state.get("seletor_pessoa", "Todos")
    forma_atual = st.session_state.get("seletor_forma_pagamento", "Todas")
    periodo_chip = _resumir_periodo_chip(granularidade_atual)

    # Refator V-01.b (2026-05-07): cada chip da chip-bar é agora um
    # st.popover Streamlit nativo. Clicar abre dropdown com selectbox
    # dentro. Substitui chip-bar HTML estática + 4 selectboxes verbosos
    # por interface coesa, fina e funcional. Streamlit >= 1.32.
    #
    # Layout: 4 colunas estreitas que renderizam só os labels dos
    # popovers (que já são os "chips"). CSS em _chip_bar.css adapta os
    # botões de popover para ter visual de chip fino.
    cols = st.columns([1, 1, 1, 1, 6])  # 4 chips + spacer

    with cols[0]:
        with st.popover(
            f"granularidade: {granularidade_atual}",
            use_container_width=True,
        ):
            granularidade: str = st.selectbox(
                "Granularidade",
                ["Dia", "Semana", "Mês", "Ano"],
                index=2,
                key="seletor_granularidade",
            )

    with cols[1]:
        with st.popover(
            f"período: {periodo_chip}",
            use_container_width=True,
        ):
            if granularidade == "Ano":
                anos = obter_anos_disponiveis(dados)
                periodo: str = st.selectbox(  # acento ok -- noqa-acento
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
                    semanas = obter_semanas_do_mes(dados, mes_base)
                    periodo = (  # acento ok -- noqa-acento
                        st.selectbox(
                            "Semana", semanas, index=0,
                            key="seletor_detalhe",
                        )
                        if semanas
                        else mes_base
                    )
                elif granularidade == "Dia":
                    dias = obter_dias_do_mes(dados, mes_base)
                    periodo = (  # acento ok -- noqa-acento
                        st.selectbox(
                            "Dia", dias, index=0,
                            key="seletor_detalhe",
                        )
                        if dias
                        else mes_base
                    )
                else:
                    periodo = mes_base  # acento ok -- noqa-acento

    with cols[2]:
        with st.popover(
            f"pessoa: {pessoa_atual}",
            use_container_width=True,
        ):
            pessoa: str = st.selectbox(
                "Pessoa",
                opcoes_pessoa,
                index=0,
                key="seletor_pessoa",
            )

    with cols[3]:
        with st.popover(
            f"forma: {forma_atual}",
            use_container_width=True,
        ):
            forma_sel: str = st.selectbox(
                "Forma de pagamento",
                ["Todas", "Pix", "Débito", "Crédito", "Boleto", "Transferência"],
                index=0,
                key="seletor_forma_pagamento",
            )
            st.session_state["filtro_forma"] = (
                None if forma_sel == "Todas" else forma_sel
            )

    return periodo, pessoa, granularidade  # acento ok -- noqa-acento


def _resumir_periodo_chip(granularidade: str) -> str:
    """Retorna texto curto para o chip de período baseado na granularidade.

    Lê do ``st.session_state`` quando disponível; cai em placeholder
    ``...`` no primeiro frame. O chip é apenas display visual -- o valor
    real do filtro vem do selectbox invisível abaixo da chip-bar.
    """
    import streamlit as st

    if granularidade == "Ano":
        return st.session_state.get("seletor_periodo", "...")
    mes = st.session_state.get("seletor_mes_base", "...")
    if granularidade == "Semana":
        return st.session_state.get("seletor_detalhe", mes)
    if granularidade == "Dia":
        return st.session_state.get("seletor_detalhe", mes)
    return mes


# ===========================================================================
# Fallback estado-inicial-atrativo (UX-V-03)
# ===========================================================================
#
# Origem dos dados de Bem-estar: app companion ``Protocolo-Mob-Ouroboros``
# (Expo + React Native, em refundação golden-zebra) escreve ``.md`` no vault
# Obsidian compartilhado. Desktop lê via ``obsidian/sync_rico.py`` -> caches
# em ``.ouroboros/cache/*.json`` -> dashboard renderiza.
#
# Quando o cache está vazio, os antigos callouts pobres do tipo "Arquivo X
# não encontrado" davam zero contexto ao usuário. UX-V-03 substitui por um
# estado inicial atrativo: skeleton mockup-like opaco + CTA explicando o
# pipeline mob -> vault -> cache -> dashboard. Sem semear demo (violaria
# regra 6 do CLAUDE.md "nunca inventar dados").
# ===========================================================================


def fallback_estado_inicial_html(
    *,
    titulo: str,
    descricao: str,  # acento ok -- noqa-acento
    skeleton_html: str = "",
    cta_label: str = "Use o app Ouroboros Mobile",
    cta_secao: str = "geral",
    sync_info: dict | None = None,
) -> str:
    """Fallback estado-inicial-atrativo para páginas com dado vazio.

    Substitui callouts pobres (``"Arquivo X não encontrado"``,
    ``"Nenhum registro de Y"``) por um bloco rico que combina:

    1. **Skeleton opaco** do layout final (placeholder visual do mockup).
    2. **Heading** ``"<TITULO> · sem registros ainda"``.
    3. **Descrição** explicando origem dos dados (mob -> vault -> cache).
    4. **CTA** apontando para o app companion ``Protocolo-Mob-Ouroboros``.
    5. **Linha sync-info** lida de ``.ouroboros/cache/last_sync.json`` (UX-V-04
       será responsável por escrever esse arquivo). Se ausente, exibe
       ``"Sincronização: nunca"``.

    Padrões aplicados: VALIDATOR_BRIEF (b) acentuação PT-BR completa,
    (o) subregra retrocompatível -- ``sync_info=None`` mantém estado pré
    UX-V-04 sem quebrar nada.

    Args:
        titulo: Heading do bloco em UPPERCASE (ex: ``"HUMOR · sem registros
            ainda"``).
        descricao: Parágrafo explicando como popular (ex: ``"Registre seu  # acento ok -- noqa-acento
            humor no app Ouroboros Mobile..."``). HTML inline permitido
            (``<code>``, ``<strong>``).
        skeleton_html: HTML opcional do skeleton mockup-like. Se vazio, omite
            o bloco visual de placeholder. Geralmente combina ``.skel-bloco``
            com KPI cards / grid placeholders.
        cta_label: Texto principal do CTA. Default ``"Use o app Ouroboros
            Mobile"``.
        cta_secao: Identificador da seção (ex: ``"humor"``, ``"medidas"``).
            Vai para ``data-secao`` para tracking visual / QA.
        sync_info: Dict opcional ``{"data": "2026-05-07T14:32",
            "n_arquivos": 12}`` lido por :func:`ler_sync_info`. Se ``None``
            ou sem chave ``"data"``, mostra ``"Sincronização: nunca"``.

    Returns:
        Bloco HTML minificado, pronto para ``st.markdown(...,
        unsafe_allow_html=True)``.
    """
    skeleton = (
        f'<div class="fallback-skeleton">{skeleton_html}</div>'
        if skeleton_html
        else ""
    )
    if sync_info and "data" in sync_info:
        sync_str = (
            f'Última sync: <strong>{sync_info["data"]}</strong>'
            f' · {sync_info.get("n_arquivos", "?")} arquivos lidos do vault'
        )
    else:
        sync_str = (
            "Sincronização: <strong>nunca</strong> -- rode "
            "<code>./run.sh --sync</code> após registrar no app."
        )

    return minificar(
        f"""
        <div class="fallback-estado" data-secao="{cta_secao}">
          {skeleton}
          <div class="fallback-cta">
            <h3 class="fallback-titulo">{titulo}</h3>
            <p class="fallback-descricao">{descricao}</p>
            <p class="fallback-acao">
              <strong>{cta_label}</strong> (Android) para começar a
              registrar. O app escreve <code>.md</code> no vault Obsidian
              compartilhado; o dashboard lê via sync.
            </p>
            <p class="fallback-sync-info">{sync_str}</p>
          </div>
        </div>
        """
    )



