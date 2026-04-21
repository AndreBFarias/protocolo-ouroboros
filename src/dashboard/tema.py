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

    /* --- Grid responsivo de KPI cards (Sprint 62) ------------------------ */
    /* Grid fluido com minmax: 3 colunas em telas largas, 2 em médias e 1 em
       estreitas. Substitui `st.columns(3)` rígido quando renderizado como
       bloco HTML custom via kpi_grid_html(). */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: {SPACING["md"]}px;
        width: 100%;
    }}
    .kpi-grid > .kpi-card {{
        min-width: 0;  /* permite shrink abaixo do conteúdo */
    }}
    .kpi-card .kpi-label {{
        color: {CORES["texto_sec"]};
        font-size: {FLUID_LABEL_KPI};
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .kpi-card .kpi-valor {{
        font-size: {FLUID_VALOR_KPI};
        font-weight: bold;
        margin: {SPACING["xs"]}px 0 0 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    @media (max-width: {BREAKPOINT_COMPACTO}px) {{
        .kpi-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        /* Streamlit columns fallback: quando visao_geral ainda usa st.columns(3),
           força cada coluna a 50% em viewports compactos. */
        [data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            flex: 1 1 calc(50% - {SPACING["md"]}px) !important;
            min-width: calc(50% - {SPACING["md"]}px) !important;
        }}
    }}
    @media (max-width: {BREAKPOINT_MINIMO}px) {{
        .kpi-grid {{
            grid-template-columns: 1fr;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }}
    }}

    /* --- Gráfico: título não sobrepõe legenda (Sprint 62) --------------- */
    /* Plotly em viewport estreito cola a legenda horizontal no topo do
       gráfico. Garante espaçamento mínimo entre título e legenda. */
    .js-plotly-plot .plotly .g-gtitle {{
        margin-bottom: {SPACING["md"]}px;
    }}
    </style>
    """


LAYOUT_PLOTLY: dict = {
    "plot_bgcolor": CORES["fundo"],
    "paper_bgcolor": CORES["fundo"],
    "font": {"color": CORES["texto"], "size": FONTE_CORPO},
    "margin": {"l": 50, "r": 20, "t": 50, "b": 40},
    # Separadores PT-BR: vírgula decimal, ponto milhar. Aplicado globalmente
    # via spread em cada update_layout das páginas. Sprint 65.
    "separators": ",.",
}


def rgba_cor(cor_hex: str, alpha: float) -> str:
    """Converte cor hex (#RRGGBB) para rgba(r,g,b,alpha)."""
    cor = cor_hex.lstrip("#")
    r, g, b = int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


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
