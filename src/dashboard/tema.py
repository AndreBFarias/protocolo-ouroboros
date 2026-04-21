"""Tema visual centralizado do dashboard -- Dracula Theme.

Sprint 20 introduziu fundação de design tokens: escala tipográfica hierárquica
(6 níveis + hero), spacing scale (xs→xxl) e helpers de render (hero, subtítulo,
label uppercase). Nomes antigos permanecem para retrocompatibilidade.
"""

DRACULA: dict[str, str] = {
    "background": "#282A36",
    "current_line": "#44475A",
    "foreground": "#F8F8F2",
    "comment": "#6272A4",
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
# Mínimo absoluto é 14px. Saltos garantem hierarquia visível.
FONTE_MINIMA: int = 14
FONTE_LABEL: int = 13  # uppercase pequeno (legenda, caption, badge)
FONTE_CORPO: int = 15
FONTE_SUBTITULO: int = 18
FONTE_TITULO: int = 22
FONTE_VALOR: int = 24  # cards KPI
FONTE_HERO: int = 28  # hero de página

# --- Spacing scale (Sprint 20) ----------------------------------------------
SPACING: dict[str, int] = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "xxl": 48,
}


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
    """Gera HTML de card compacto para sidebar."""
    return (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-left: 3px solid {cor};"
        f" border-radius: 6px;"
        f" padding: {SPACING['sm'] + 2}px {SPACING['md'] - 2}px;"
        f" margin-bottom: {SPACING['sm']}px;"
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


def hero_titulo_html(numero: str, texto: str, descricao: str | None = None) -> str:
    """Cabeçalho grande de página (display / hero). Sprint 20."""
    bloco_desc = ""
    if descricao:
        bloco_desc = (
            f'<p style="color: {CORES["texto_sec"]}; font-size: {FONTE_CORPO}px;'
            f" margin: {SPACING['sm']}px 0 0 0; max-width: 780px;"
            f' line-height: 1.5;">{descricao}</p>'
        )
    return (
        f'<div style="margin: 0 0 {SPACING["lg"]}px 0;">'
        f'<div style="display: flex; align-items: baseline; gap: {SPACING["md"]}px;">'
        f'<span style="font-size: 48px; font-weight: 700;'
        f" color: {CORES['destaque']};"
        f' line-height: 1;">{numero}</span>'
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


def css_global() -> str:
    """Retorna bloco CSS global para o dashboard Dracula."""
    return f"""
    <style>
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        font-size: {FONTE_CORPO}px;
    }}
    .block-container {{ padding-top: {SPACING["xl"]}px; }}
    [data-testid="stSidebar"] {{ background-color: {CORES["card_fundo"]}; }}
    [data-testid="stSidebar"] h1 {{ color: {CORES["destaque"]}; }}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {{ font-size: {FONTE_CORPO}px; }}
    [data-testid="stDownloadButton"] button {{
        background-color: {CORES["card_fundo"]};
        color: {CORES["texto"]};
        border: 1px solid {CORES["destaque"]};
        font-size: {FONTE_CORPO}px;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        background-color: {CORES["destaque"]};
        color: {CORES["fundo"]};
    }}
    h1 {{ font-size: {FONTE_HERO}px !important; font-weight: 700 !important; }}
    h2 {{ font-size: {FONTE_TITULO}px !important; font-weight: 700 !important; }}
    h3 {{ font-size: {FONTE_SUBTITULO}px !important; font-weight: 600 !important; }}
    p, li, span, div {{ font-size: {FONTE_CORPO}px; }}
    .stTabs [data-baseweb="tab-list"],
    .stTabs [data-baseweb="tab-list"] > div,
    .stTabs > div:first-child {{
        gap: {SPACING["sm"]}px;
        background-color: {CORES["card_fundo"]};
        border-radius: 8px;
        min-height: 60px !important;
        height: auto !important;
        overflow: visible !important;
        overflow-y: visible !important;
        overflow-x: auto !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {CORES["texto_sec"]} !important;
        font-size: {FONTE_CORPO}px !important;
        padding: {SPACING["md"]}px {SPACING["md"] + 4}px !important;
        height: auto !important;
        min-height: 48px !important;
        white-space: nowrap !important;
        overflow: visible !important;
        display: flex !important;
        align-items: center !important;
    }}
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] div {{
        color: inherit !important;
        font-size: {FONTE_CORPO}px !important;
        overflow: visible !important;
        line-height: 1.4 !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {CORES["texto"]} !important;
        font-weight: bold !important;
        border-bottom: 3px solid {CORES["destaque"]} !important;
    }}
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] div {{
        color: {CORES["texto"]} !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {CORES["texto"]} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: transparent !important;
        display: none !important;
    }}
    .element-container {{ margin-bottom: {SPACING["md"]}px; }}
    [data-testid="stHorizontalBlock"] {{ gap: {SPACING["md"]}px; }}
    </style>
    """


LAYOUT_PLOTLY: dict = {
    "plot_bgcolor": CORES["fundo"],
    "paper_bgcolor": CORES["fundo"],
    "font": {"color": CORES["texto"], "size": FONTE_CORPO},
    "margin": {"l": 50, "r": 20, "t": 50, "b": 40},
}


def rgba_cor(cor_hex: str, alpha: float) -> str:
    """Converte cor hex (#RRGGBB) para rgba(r,g,b,alpha)."""
    cor = cor_hex.lstrip("#")
    r, g, b = int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# "Design não é como parece. Design é como funciona." -- Steve Jobs
