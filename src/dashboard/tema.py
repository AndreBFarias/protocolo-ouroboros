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

# Sprint UX-RD-01: paleta migrada para a nova escala de fundo + texto
# espelhando ``novo-mockup/_shared/tokens.css``. Aliases legacy
# (`fundo`, `card_fundo`, `texto`, `texto_sec`, `positivo`, `negativo`,  # noqa: accent
# `neutro`, `alerta`, `destaque`, `superfluo`, `info`, `obrigatorio`,    # noqa: accent
# `questionavel`, `na`) foram preservados como chaves para retrocompat   # noqa: accent
# das 14 páginas existentes -- apenas o hex foi atualizado. Tokens novos
# (`card_elevado`, `fundo_inset`, `texto_muted`, `d7_*`, `humano_*`) são
# referenciados pelas páginas redesenhadas em UX-RD-02+.
#
# Escolha intencional: o dict ``DRACULA`` acima permanece com os hex
# Dracula originais, pois serve de fonte histórica para testes legados
# (test_dashboard_tema.py::test_sprint_ux111_*). A migração acontece
# apenas em ``CORES``, que é a interface pública consumida pelas páginas.
#
# ─────────────────────────────────────────────────────────────────────
# CORES — espelho Python de src/dashboard/css/tokens.css (Sprint UX-M-01).
# Manter sincronizado: editar AQUI e em tokens.css na MESMA sprint.
# Inconsistência = bug visual silencioso (CSS injetado usa um valor,
# código Python que formata strings usa outro).
# Fonte canônica do design: novo-mockup/_shared/tokens.css.
# ─────────────────────────────────────────────────────────────────────
CORES: dict[str, str] = {
    # --- Fundo (escala de profundidade nova) -------------------------------
    # bg-base: viewport / html, body
    "fundo": "#0e0f15",
    # bg-surface: cards, sidebar, headers
    "card_fundo": "#1a1d28",
    # bg-elevated: modais, popovers, drawer (NOVO)
    "card_elevado": "#232735",
    # bg-inset: code blocks, inputs profundos (NOVO)
    "fundo_inset": "#0a0b10",
    # --- Texto -------------------------------------------------------------
    # text-primary: corpo principal
    "texto": "#f8f8f2",
    # text-secondary: legendas, captions (era #c9c9cc -- UX-111 legado,
    # agora harmonizado com a paleta da Sprint UX-RD-01)
    "texto_sec": "#a8a9b8",
    # text-muted: rótulos secundários, placeholders, estados pendentes (NOVO)
    "texto_muted": "#6c6f7d",
    # --- Acentos Dracula (hex literais, sem mais herança de DRACULA) -------
    "positivo": "#50fa7b",
    "negativo": "#ff5555",
    "neutro": "#8be9fd",
    "alerta": "#ffb86c",
    "destaque": "#bd93f9",
    "superfluo": "#ff79c6",
    "info": "#f1fa8c",
    # --- Classificação financeira (alias semântico) ------------------------
    "obrigatorio": "#50fa7b",  # noqa: accent (chave canônica do dict legado)
    "questionavel": "#ffb86c",  # noqa: accent (chave canônica do dict legado)
    # `na` historicamente herdou de `comment`. Mantemos a mesma decisão
    # apontando agora para `texto_muted` -- um cinza estável para itens
    # neutros (transferências internas, receitas).
    "na": "#6c6f7d",
    # --- Estados D7: cobertura observável, não-gate (NOVO) -----------------
    # Espelha tokens.css --d7-* dos mockups.
    "d7_graduado": "#6b8e7f",
    "d7_calibracao": "#f1fa8c",
    "d7_regredindo": "#ffb86c",
    "d7_pendente": "#6c6f7d",
    # --- Estados de validação humana (NOVO) --------------------------------
    # Espelha tokens.css --humano-* dos mockups.
    "humano_aprovado": "#6b8e7f",
    "humano_rejeitado": "#ff5555",
    "humano_revisar": "#f1fa8c",
    "humano_pendente": "#6c6f7d",
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
#
# Espelho de src/dashboard/css/tokens.css `--fs-*` (Sprint UX-M-01).
# Tokens CSS canônicos: --fs-11..--fs-40. Manter sincronizado.
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
#
# Espelho de src/dashboard/css/tokens.css `--sp-*` (Sprint UX-M-01).
# Tokens CSS canônicos: --sp-1 (4px) .. --sp-16 (64px). Manter sincronizado.
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

    # FIX-06: trocar h1 por div.sidebar-brand-text. O brand canônico vem
    # do shell HTML (componentes/shell.py:_renderizar_brand_html); o h1
    # extra criava 2 h1 visíveis simultaneamente em todas as telas,
    # violando hierarquia HTML/A11y. O alt do img já provê acessibilidade.
    return (
        f'<div style="text-align:center; margin-bottom:{SPACING["md"]}px;">'
        f'<img src="data:image/png;base64,{b64}" '
        f'class="ouroboros-logo-img" '
        f'width="{largura_px}" '
        f'style="display:block; margin:0 auto;" '
        f'alt="Protocolo Ouroboros"/>'
        f'<div class="sidebar-brand-text" style="margin-top:{SPACING["sm"]}px; '
        f"font-family:var(--ff-mono); font-size:13px; font-weight:500; "
        f"letter-spacing:0.04em; text-transform:uppercase; "
        f"color:{CORES['destaque']}; "
        f'text-align:center;">Protocolo Ouroboros</div>'
        f"</div>"
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
# As funções ``callout_html``, ``progress_inline_html``, ``metric_semantic_html``
# e ``chip_html`` foram MIGRADAS para
# ``src/dashboard/componentes/ui.py`` em UX-M-02. Aliases shim no rodapé deste
# arquivo preservam imports legados (``from src.dashboard.tema import
# callout_html`` continua funcionando via re-export).
#
# ``icon_html`` PERMANECE aqui -- utilitário Feather, não é componente
# universal (é dependência interna usada por ``callout_html`` e algumas
# páginas).


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
    # ``chip_html`` foi migrado para ``componentes.ui`` em UX-M-02 e
    # re-exportado neste módulo via shim no rodapé. Quando esta função é
    # chamada em runtime, o módulo ``tema`` já está totalmente carregado
    # (incluindo o shim), então a referência a ``chip_html`` resolve
    # corretamente para o callable em ``ui``.
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


# ---------------------------------------------------------------------------
# Aliases shim para retrocompatibilidade -- Sprint UX-M-02 (Onda M).
# ---------------------------------------------------------------------------
# 9 funções de componentes visuais foram migradas para
# ``src/dashboard/componentes/ui.py`` (fronteira pública única). ``tema.py``
# mantém aliases shim aqui no rodapé para que páginas que faziam
# ``from src.dashboard.tema import callout_html`` (ou as outras 8) continuem
# funcionando sem edit.
#
# Sub-sprints UX-M-02.A..D migram páginas para imports diretos de
# ``componentes.ui``; após a migração, sprint UX-M-CLEANUP poderá remover
# estes shims (com depreciação documentada).
#
# Este import vem ao FINAL do módulo para evitar ciclo: ``ui.py`` importa
# ``CORES``, ``SPACING``, ``FONTE_*``, ``icon_html``, ``rgba_cor`` e
# ``rgba_cor_inline`` deste módulo; estas definições já estão prontas
# quando o intérprete chega aqui.
from src.dashboard.componentes.ui import (  # noqa: E402, F401
    callout_html,
    card_html,
    card_sidebar_html,
    chip_html,
    hero_titulo_html,
    label_uppercase_html,
    metric_semantic_html,
    progress_inline_html,
    subtitulo_secao_html,
)


# "Design não é como parece. Design é como funciona." -- Steve Jobs
