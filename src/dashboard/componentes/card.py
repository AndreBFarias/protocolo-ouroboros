"""Cards KPI com responsividade embutida (Sprint 62).

Motivação: em viewport 900×700, o layout `st.columns(3)` rígido trunca
valores monetários grandes (ex: "R$ 1.463,35" vira "R$ 1.463"). Este módulo
oferece um grid CSS fluido via `grid-template-columns: repeat(auto-fit, ...)`
que quebra naturalmente para 2×2 ou 1 coluna conforme a largura disponível.

Tipografia usa `clamp(min, preferido, max)` para que valores encolham
continuamente em vez de estourar a caixa.
"""

from __future__ import annotations

from src.dashboard.tema import (
    CORES,
    FLUID_LABEL_KPI,
    FLUID_VALOR_KPI,
    SPACING,
)


def kpi_card_html(titulo: str, valor: str, cor: str) -> str:
    """Retorna HTML de um único card KPI com classes responsivas.

    Classes usadas (definidas em `tema.css_global`):
      - `.kpi-card`: container do card
      - `.kpi-label`: texto do título (uppercase pequeno)
      - `.kpi-valor`: valor principal (monetário ou percentual)

    O CSS global aplica `clamp()` e `text-overflow: ellipsis` nos filhos,
    garantindo que valores grandes não estourem a largura disponível.
    """
    return (
        f'<div class="kpi-card" style="'
        f"background-color: {CORES['card_fundo']};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-left: 4px solid {cor};"
        f" border-radius: 8px;"
        f" padding: {SPACING['md']}px {SPACING['md'] + 2}px;"
        f" box-shadow: 0 2px 8px rgba(0,0,0,0.3);"
        f'">'
        f'<p class="kpi-label">{titulo}</p>'
        f'<p class="kpi-valor" style="color: {cor};">{valor}</p>'
        f"</div>"
    )


def kpi_grid_html(cards: list[tuple[str, str, str]]) -> str:
    """Agrupa vários cards em um grid responsivo.

    Args:
        cards: lista de tuplas `(titulo, valor, cor)` na ordem de exibição.

    Returns:
        HTML com classe `.kpi-grid` que usa `grid-template-columns: auto-fit`.
        CSS global converte automaticamente 3×1 → 2×2 → 1 coluna conforme
        os breakpoints definidos em `tema.BREAKPOINT_COMPACTO` e
        `tema.BREAKPOINT_MINIMO`.
    """
    blocos = "".join(kpi_card_html(t, v, c) for t, v, c in cards)
    return f'<div class="kpi-grid">{blocos}</div>'


def css_inline_fluido() -> str:
    """CSS inline mínimo com `@media` queries e tokens `clamp()`.

    Retorna um bloco `<style>` standalone para páginas que precisam do
    comportamento responsivo sem importar todo o `css_global()`. Útil em
    testes e em páginas auxiliares.
    """
    return f"""
    <style>
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: {SPACING["md"]}px;
    }}
    .kpi-card .kpi-valor {{
        font-size: {FLUID_VALOR_KPI};
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .kpi-card .kpi-label {{
        font-size: {FLUID_LABEL_KPI};
    }}
    @media (max-width: 1000px) {{
        .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 700px) {{
        .kpi-grid {{ grid-template-columns: 1fr; }}
    }}
    </style>
    """


# "A boa arquitetura torna invisíveis as coisas complicadas." -- Christopher Alexander
