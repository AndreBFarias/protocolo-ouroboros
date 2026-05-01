"""Tema visual centralizado do dashboard -- Dracula Theme.

Sprint 20 introduziu fundação de design tokens: escala tipográfica hierárquica
(6 níveis + hero), spacing scale (xs→xxl) e helpers de render (hero, subtítulo,
label uppercase). Nomes antigos permanecem para retrocompatibilidade.

Sprint 76 adicionou: floor absoluto de 13px (`FONTE_MIN_ABSOLUTA`), padding
mínimo 16px nos retângulos das páginas, logo `assets/icon.png` renderizada
centralizada acima do título "Protocolo Ouroboros" na sidebar (cacheada em
`st.session_state`).
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

DRACULA: dict[str, str] = {
    "background": "#282A36",
    "current_line": "#44475A",
    "foreground": "#F8F8F2",
    # Sprint UX-111: customizado de #6272A4 para contraste maior contra fundo escuro.
    "comment": "#c9c9cc",
    "cyan": "#8BE9FD",
    "green": "#50FA7B",
    "orange": "#FFB86C",
    "pink": "#FF79C6",
    "purple": "#BD93F9",
    "red": "#FF5555",
    "yellow": "#F1FA8C",
}

CORES: dict[str, str] = {
    "fundo": DRACULA["background"],
    "card_fundo": DRACULA["current_line"],
    "texto": DRACULA["foreground"],
    "texto_sec": DRACULA["comment"],
    "positivo": DRACULA["green"],
    "negativo": DRACULA["red"],
    "neutro": DRACULA["cyan"],
    "alerta": DRACULA["orange"],
    "destaque": DRACULA["purple"],
    "superfluo": DRACULA["pink"],
    "info": DRACULA["yellow"],
    "obrigatorio": DRACULA["green"],
    "questionavel": DRACULA["orange"],
    "na": DRACULA["comment"],
}

MAPA_CLASSIFICACAO: dict[str, str] = {
    "Obrigatório": CORES["obrigatorio"],
    "Questionável": CORES["questionavel"],
    "Supérfluo": CORES["superfluo"],
    "N/A": CORES["texto_sec"],
}

# --- Escala tipográfica (Sprint 20) -----------------------------------------
# Mínimo absoluto é 13px (rebaixado de 14 pela Sprint 76 — legibilidade
# validada com o usuário primário em viewport 1600x1000). Saltos garantem hierarquia.
FONTE_MIN_ABSOLUTA: int = 13  # nenhum texto no app pode cair abaixo disso (Sprint 76)
FONTE_MINIMA: int = 14
FONTE_LABEL: int = 13  # uppercase pequeno (legenda, caption, badge)
FONTE_CORPO: int = 15
FONTE_SUBTITULO: int = 18
FONTE_TITULO: int = 22
FONTE_VALOR: int = 24  # cards KPI
FONTE_HERO: int = 28  # hero de página

# --- Padding canônico das páginas (Sprint 76) -------------------------------
# Retângulos internos (.main .block-container) devem ter padding >= 16px
# para evitar texto colado na borda. 24px é o padrão; páginas podem
# sobrescrever para mais (nunca menos).
PADDING_PAGINA_MIN_PX: int = 16
PADDING_PAGINA_PADRAO_PX: int = 24

# --- Tokens de spacing/borda do design system (Sprint UX-112) ---------------
# Tokens universais aplicados via css_global() a inputs, selects, multiselects,
# expanders e área de tabs. Páginas não devem hardcodear px equivalentes; toda
# regra deriva destes tokens.
# PADDING_INTERNO: padding em retângulos de conteúdo (mesmo valor canônico do
# .block-container, exposto como token para reúso explícito).
# PADDING_CHIP: padding interno em chips/badges/inputs pequenos.
# BORDA_RAIO: raio padrão de cantos arredondados.
# BORDA_ATIVA_PX: espessura da borda em estado :focus-within (destaque).
PADDING_INTERNO: int = 24
PADDING_CHIP: int = 16
BORDA_RAIO: int = 8
BORDA_ATIVA_PX: int = 2

# --- Tipografia fluida (Sprint 62) ------------------------------------------
# Tokens `clamp(min, preferido, max)` para redimensionamento contínuo em
# viewports estreitos. Evita truncamento de valores monetários grandes como
# "R$ 1.463,35" em cards KPI quando a coluna encolhe abaixo de 1200px.
FLUID_VALOR_KPI: str = "clamp(14px, 2vw, 22px)"
FLUID_LABEL_KPI: str = "clamp(10px, 1.2vw, 14px)"
FLUID_TITULO_GRAFICO: str = "clamp(14px, 1.6vw, 18px)"

# Breakpoints em px para media queries. Escolhas baseadas na auditoria
# 2026-04-21 que detectou quebra em 900×700.
BREAKPOINT_COMPACTO: int = 1000  # abaixo disso, cards 2×2
BREAKPOINT_MINIMO: int = 700  # abaixo disso, 1 coluna

# --- Spacing scale (Sprint 20) ----------------------------------------------
SPACING: dict[str, int] = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "xxl": 48,
}


# --- Logo da sidebar (Sprint 76) --------------------------------------------
_CAMINHO_LOGO: Path = Path(__file__).resolve().parents[2] / "assets" / "icon.png"


def logo_sidebar_html(largura_px: int = 120) -> str:
    """HTML da logo centralizada para inserir no topo da sidebar.

    Cacheia o base64 em `st.session_state["_logo_b64"]` (leitura única
    por sessão). Em ausência do arquivo (ex: repo sem `assets/icon.png`),
    devolve string vazia — caller deve tolerar. A checagem de existência
    acontece antes do cache (testes que removem o arquivo no meio do fluxo
    ainda recebem string vazia mesmo com cache quente).

    Sprint UX-118: largura padrão sobe de 96px para 120px e o ``<img>``
    ganha class ``ouroboros-logo-img``. CSS global (``css_global()``)
    declara ``max-width: 120px; height: auto; aspect-ratio: 724 / 733``
    para que a imagem não seja apertada para 64x65 pelo layout da sidebar
    (largura útil ~248px) e mantenha proporção próxima do quadrado da
    arte original (724x733px).
    """
    if not _CAMINHO_LOGO.exists():
        return ""

    try:
        import streamlit as st  # import atrasado: tema.py roda em testes sem streamlit
    except ImportError:  # pragma: no cover - streamlit é dep obrigatória em runtime
        st = None  # type: ignore[assignment]

    b64: str | None = None
    if st is not None and hasattr(st, "session_state"):
        b64 = st.session_state.get("_logo_b64")  # type: ignore[union-attr]

    if not b64:
        b64 = base64.b64encode(_CAMINHO_LOGO.read_bytes()).decode("ascii")
        if st is not None and hasattr(st, "session_state"):
            st.session_state["_logo_b64"] = b64  # type: ignore[union-attr]

    return (
        f'<div style="text-align:center; margin-bottom:{SPACING["md"]}px;">'
        f'<img src="data:image/png;base64,{b64}" '
        f'class="ouroboros-logo-img" '
        f'width="{largura_px}" '
        f'style="display:block; margin:0 auto;" '
        f'alt="Protocolo Ouroboros"/>'
        f'<h1 style="margin-top:{SPACING["sm"]}px; '
        f"font-family:monospace; "
        f"color:{CORES['destaque']}; "
        f'text-align:center;">Protocolo Ouroboros</h1>'
        f"</div>"
    )


def card_html(titulo: str, valor: str, cor: str) -> str:
    """Gera HTML de card compacto reutilizável."""
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

    Sprint UX-122: o primeiro parâmetro virou opcional (default ``""``). Quando
    vazio, o ``<span>`` do badge numérico é omitido completamente -- header
    mostra apenas o título. Retrocompatível: chamadas antigas com primeiro arg
    numérico seguem renderizando o badge como antes.
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
    """Cabeçalho de seção padrão uppercase com linha sutil. Sprint 20."""
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
    """Pequeno rótulo uppercase (meta-informação, legenda). Sprint 20."""
    cor_efetiva = cor or CORES["texto_sec"]
    return (
        f'<span style="color: {cor_efetiva};'
        f" font-size: {FONTE_LABEL}px;"
        f" font-weight: 600;"
        f" letter-spacing: 0.08em;"
        f' text-transform: uppercase;">{texto}</span>'
    )


def rgba_cor_inline(cor_hex: str, alpha: float) -> str:
    """Variante interna para uso durante carregamento do módulo."""
    cor = cor_hex.lstrip("#")
    r, g, b = int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# Sprint ANTI-MIGUE-08: ``css_global()`` foi movido para tema_css.py.
# Re-export local preserva contratos publicos
# (``from src.dashboard.tema import css_global``).
from src.dashboard.tema_css import css_global  # noqa: E402, F401

LAYOUT_PLOTLY: dict = {
    "plot_bgcolor": CORES["fundo"],
    "paper_bgcolor": CORES["fundo"],
    "font": {"color": CORES["texto"], "size": FONTE_CORPO},
    "margin": {"l": 50, "r": 20, "t": 50, "b": 40},
    # Separadores PT-BR: vírgula decimal, ponto milhar. Aplicado globalmente
    # via spread em cada update_layout das páginas. Sprint 65.
    "separators": ",.",
}


def legenda_abaixo(
    fig: Any,
    y: float = -0.18,
    espaco_topo: int = 60,
    espaco_base: int = 80,
) -> Any:
    """Coloca a legenda Plotly horizontal abaixo do gráfico (Sprint 77).

    Evita sobreposição entre título e legenda. Ajusta margens top/bottom
    para garantir área clicável. Retorna o próprio `fig` para encadear
    `.update_layout(...)`.
    """
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="top",
            y=y,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(t=espaco_topo, b=espaco_base, l=40, r=20),
    )
    return fig


def rgba_cor(cor_hex: str, alpha: float) -> str:
    """Converte cor hex (#RRGGBB) para rgba(r,g,b,alpha)."""
    cor = cor_hex.lstrip("#")
    r, g, b = int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# --- Sprint 92c: helpers canônicos de design system -------------------------
# Substituem padrões ad-hoc espalhados nas páginas (`st.warning`, `st.metric`,
# `st.progress`, `<div style=` manuais). Todos retornam string HTML; caller
# escolhe `st.markdown(..., unsafe_allow_html=True)`. Cores referenciam
# `var(--color-*)` publicadas em `css_global()`; fallback hex preservado via
# dupla atribuição `background: var(--color-x, #hex);` só quando faz diferença
# visual (alguns navegadores móveis ignoram vars em gradientes antigos).

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


def icon_html(nome_feather: str, tamanho: int = 16, cor: str | None = None) -> str:
    """Sprint 92c: renderiza ícone Feather SVG inline.

    ``nome_feather`` deve ser um dos 11 ícones registrados em
    ``src/dashboard/componentes/icons.py``. ``tamanho`` em px. ``cor`` aceita
    hex (``"#BD93F9"``), nome CSS ou ``None`` (usa ``currentColor``, herda do
    texto pai). Retorna string vazia quando o ícone não existe — caller não
    precisa validar.
    """
    from src.dashboard.componentes.icons import renderizar_svg

    cor_efetiva = cor if cor else "currentColor"
    return renderizar_svg(nome_feather, tamanho=tamanho, cor=cor_efetiva)


def callout_html(
    tipo: str,
    mensagem: str,
    titulo: str | None = None,
) -> str:
    """Sprint 92c: callout Dracula-consistente.

    ``tipo`` in ``{"info", "warning", "error", "success"}`` define cor da
    borda e ícone Feather. ``mensagem`` é o corpo; ``titulo`` opcional vira
    um `<strong>` acima da mensagem.

    Substitui ``st.warning`` / ``st.info`` / ``st.success`` / ``st.error``
    (paleta amarelada default do Streamlit destoa do tema escuro). Tipos
    desconhecidos caem em ``info`` para degradação silenciosa.
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
    92a.9): agora single-source no tema.
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
      * ``delta`` > 0 -> ``--color-positivo``
      * ``delta`` < 0 -> ``--color-negativo``
      * ``delta`` == 0 ou ``None`` -> ``--color-texto-sec`` (neutro)

    Caller pode forçar cor específica passando ``cor`` em hex. ``label`` em
    caps-lock reduzido; ``valor`` é string já formatada (ex: ``"R$ 1.234,56"``).
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


def breadcrumb_drilldown_html(filtros: dict[str, str]) -> str:
    """Sprint 92c: breadcrumb de filtros ativos de drill-down.

    Renderiza um bloco inteiro com prefixo descritivo + chip para cada
    filtro. Substitui o loop manual de ``st.button`` em ``extrato.py`` (que
    força rerun a cada clique). Este helper é apenas visual; o mecanismo
    de "X clicável para remover filtro" permanece no caller via
    ``st.button("×", key=...)`` + ``limpar_filtro(campo)``.

    Retorna HTML vazio quando ``filtros`` está vazio (degradação silenciosa).
    """
    if not filtros:
        return ""
    chips = "".join(
        chip_html(f"{campo}: {valor}", clicavel=False) for campo, valor in filtros.items()
    )
    return (
        '<div style="margin: var(--spacing-sm) 0;">'
        '<p style="color: var(--color-destaque);'
        " font-size: var(--font-corpo);"
        ' margin: 0 0 var(--spacing-xs) 0;">'
        "Filtros ativos:</p>"
        f'<div style="display: flex; flex-wrap: wrap; gap: var(--spacing-xs);">'
        f"{chips}"
        "</div>"
        "</div>"
    )


# --- Localização PT-BR de eixos de tempo (Sprint 65) ------------------------
# Plotly não traz locale pt-BR nativo. O projeto usa `mes_ref` no formato
# "YYYY-MM" como eixo x em vários gráficos (Receita vs Despesa, evolução de
# categorias, projeções). Este helper traduz rótulos para "Mmm/AA" (ex: Nov/25,
# Abr/26) e garante separadores decimais brasileiros. Usa `tickmode="array"`
# com `ticktext` explícito, pois Plotly sem locale renderiza "Nov 2025" em
# inglês ao interpretar strings "YYYY-MM" como datas.

MESES_PTBR: dict[int, str] = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}

MESES_PTBR_COMPLETO: dict[int, str] = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def formatar_mes_ptbr(mes_ref: str, *, completo: bool = False) -> str:
    """Traduz 'YYYY-MM' para 'Mmm/AA' (ou 'Mês Completo AAAA' se completo)."""
    if not isinstance(mes_ref, str) or "-" not in mes_ref:
        return str(mes_ref)
    partes = mes_ref.split("-")
    if len(partes) < 2:
        return mes_ref
    try:
        ano = int(partes[0])
        mes = int(partes[1])
    except ValueError:
        return mes_ref
    if mes not in MESES_PTBR:
        return mes_ref
    if completo:
        return f"{MESES_PTBR_COMPLETO[mes]} {ano}"
    return f"{MESES_PTBR[mes]}/{str(ano)[-2:]}"


def aplicar_locale_ptbr(fig, *, valores_eixo_x: list[str] | None = None):
    """Aplica locale PT-BR ao gráfico Plotly.

    - Traduz eixo x de 'YYYY-MM' para 'Mmm/AA' quando valores são passados.
    - Garante `separators=",."` (vírgula decimal, ponto milhar).
    - Retorna a figura (mutação in-place + retorno para encadeamento).

    Se `valores_eixo_x` for None, aplica apenas os separadores -- útil para
    gráficos cujo eixo x não é temporal (ex: bar chart de fornecedores).
    """
    fig.update_layout(separators=",.")
    if valores_eixo_x is not None and len(valores_eixo_x) > 0:
        ticktext = [formatar_mes_ptbr(v) for v in valores_eixo_x]
        fig.update_xaxes(
            tickmode="array",
            tickvals=list(valores_eixo_x),
            ticktext=ticktext,
        )
    return fig


# "Design não é como parece. Design é como funciona." -- Steve Jobs
