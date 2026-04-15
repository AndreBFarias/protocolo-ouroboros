"""Tema visual centralizado do dashboard -- Dracula Theme."""

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

FONTE_MINIMA: int = 13
FONTE_CORPO: int = 14
FONTE_SUBTITULO: int = 16
FONTE_TITULO: int = 18
FONTE_VALOR: int = 20


def card_html(titulo: str, valor: str, cor: str) -> str:
    """Gera HTML de card compacto reutilizável."""
    return (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-left: 4px solid {cor};"
        f" border-radius: 8px;"
        f" padding: 16px 18px;"
        f" margin: 6px 0;"
        f" box-shadow: 0 2px 8px rgba(0,0,0,0.3);"
        f'">'
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: {FONTE_CORPO}px;"
        f' margin: 0;">{titulo}</p>'
        f'<p style="color: {cor};'
        f" font-size: {FONTE_VALOR}px;"
        f" font-weight: bold;"
        f" white-space: nowrap;"
        f' margin: 4px 0 0 0;">{valor}</p>'
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
        f" padding: 10px 14px;"
        f" margin-bottom: 8px;"
        f" box-shadow: 0 2px 6px rgba(0,0,0,0.25);"
        f'">'
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: {FONTE_MINIMA}px;"
        f' margin: 0;">{titulo}</p>'
        f'<p style="color: {cor};'
        f" font-size: {FONTE_TITULO}px;"
        f" font-weight: bold;"
        f' margin: 2px 0 0 0;">{valor}</p>'
        f"</div>"
    )


def css_global() -> str:
    """Retorna bloco CSS global para o dashboard Dracula."""
    return f"""
    <style>
    .block-container {{ padding-top: 2.5rem; }}
    [data-testid="stSidebar"] {{ background-color: {CORES["card_fundo"]}; }}
    [data-testid="stSidebar"] h1 {{ color: {CORES["destaque"]}; }}
    [data-testid="stDownloadButton"] button {{
        background-color: {CORES["card_fundo"]};
        color: {CORES["texto"]};
        border: 1px solid {CORES["destaque"]};
    }}
    [data-testid="stDownloadButton"] button:hover {{
        background-color: {CORES["destaque"]};
        color: {CORES["fundo"]};
    }}
    .stTabs [data-baseweb="tab-list"],
    .stTabs [data-baseweb="tab-list"] > div,
    .stTabs > div:first-child {{
        gap: 8px;
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
        font-size: 15px !important;
        padding: 16px 20px !important;
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
        font-size: 15px !important;
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
    .element-container {{ margin-bottom: 16px; }}
    [data-testid="stHorizontalBlock"] {{ gap: 16px; }}
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
