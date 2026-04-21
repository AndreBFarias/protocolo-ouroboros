"""Tema dos mockups -- reexporta o Dracula existente com extensões locais.

MOCKUP wireframe para Sprints 20/51/52/53 -- não é código de produção.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ_PROJETO: Path = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from src.dashboard.tema import (  # noqa: E402
    CORES,
    DRACULA,
    LAYOUT_PLOTLY,
    card_html,
    card_sidebar_html,
    css_global,
    rgba_cor,
)

__all__ = [
    "CORES",
    "DRACULA",
    "LAYOUT_PLOTLY",
    "card_html",
    "card_sidebar_html",
    "css_global",
    "rgba_cor",
    "badge_html",
    "hero_titulo",
    "subtitulo_secao",
    "divisor",
]


def badge_html(texto: str, cor: str, *, fonte_px: int = 11) -> str:
    """Pill colorida reutilizavel nos mockups."""
    return (
        f'<span style="'
        f"background-color: {rgba_cor(cor, 0.18)};"
        f" color: {cor};"
        f" padding: 3px 10px;"
        f" border-radius: 999px;"
        f" font-size: {fonte_px}px;"
        f" font-weight: 600;"
        f" letter-spacing: 0.04em;"
        f" text-transform: uppercase;"
        f" border: 1px solid {rgba_cor(cor, 0.35)};"
        f'">{texto}</span>'
    )


def hero_titulo(numero: str, titulo: str, descricao: str) -> str:
    """Cabecalho grande de cada mockup."""
    return (
        f'<div style="margin: 0 0 24px 0;">'
        f'<div style="display: flex; align-items: baseline; gap: 16px;">'
        f'<span style="font-size: 48px; font-weight: 700; color: {CORES["destaque"]};'
        f' line-height: 1;">{numero}</span>'
        f'<span style="font-size: 28px; font-weight: 600; color: {CORES["texto"]};'
        f' line-height: 1.2;">{titulo}</span>'
        f"</div>"
        f'<p style="color: {CORES["texto_sec"]}; font-size: 15px;'
        f' margin: 8px 0 0 0; max-width: 780px; line-height: 1.5;">{descricao}</p>'
        f"</div>"
    )


def subtitulo_secao(texto: str, *, cor: str | None = None) -> str:
    """Cabecalho de secao padrao."""
    cor_efetiva = cor or CORES["neutro"]
    return (
        f'<h3 style="'
        f" color: {cor_efetiva};"
        f" font-size: 13px;"
        f" font-weight: 700;"
        f" letter-spacing: 0.12em;"
        f" text-transform: uppercase;"
        f" margin: 24px 0 12px 0;"
        f" border-bottom: 1px solid {rgba_cor(CORES['texto_sec'], 0.25)};"
        f' padding-bottom: 6px;">{texto}</h3>'
    )


def divisor() -> str:
    """Linha divisoria sutil."""
    return (
        f'<hr style="border: none;'
        f" border-top: 1px solid {rgba_cor(CORES['texto_sec'], 0.2)};"
        f' margin: 20px 0;">'
    )


# "A forma segue a função." -- Louis Sullivan
