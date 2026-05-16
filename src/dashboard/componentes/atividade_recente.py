# ruff: noqa: E501
"""Componente Atividade Recente + Sprint Atual da Visão Geral (UX-V-2.7-FIX).

Extraído de ``paginas/visao_geral.py`` para honrar limite ``(h)`` 800L e
para isolar a coluna direita do bloco dual da Visão Geral.

API pública:
    - ``atividade_recente_html(entries)`` -> str: timeline de eventos
      recentes com glyphs SVG canônicos.
    - ``sprint_atual_html(meta)`` -> str: card "Sprint atual" com pill
      de status (em execução / em calibração / concluída).
"""

from __future__ import annotations


def atividade_recente_html(entries: list[dict]) -> str:
    """Timeline de eventos recentes com ícones SVG canônicos.

    Cada linha recebe glyph SVG do mapeamento ``GLYPHS`` (em
    ``componentes/glyphs.py``) conforme campo ``glyph`` do
    ``TimelineEntry`` -- espelha o mockup ``_visao-render.js`` que
    chama ``glyph(ic, 16)`` em cada ``tlItem``.

    Fallback (entrada sem ``glyph`` ou glyph inexistente): mantém o
    container vazio ``<span class="ic"></span>`` para preservar o
    grid; a Atividade Recente continua legível.
    """
    from src.dashboard.componentes.glyphs import GLYPHS, glyph
    from src.dashboard.componentes.html_utils import minificar

    def _icone(nome: str) -> str:
        if nome and nome in GLYPHS:
            return glyph(nome, tamanho_px=14)
        return ""

    if not entries:
        body = (
            '<div class="vg-t01-tl-item"><span class="when">—</span>'
            '<span class="ic"></span>'
            '<span class="what">Sem atividade recente registrada.</span></div>'
        )
    else:
        body = "".join(
            '<div class="vg-t01-tl-item">'
            f'<span class="when">{e["when"]}</span>'
            f'<span class="ic">{_icone(e.get("glyph", ""))}</span>'
            f'<span class="what">{e["what_html"]}</span>'
            "</div>"
            for e in entries
        )
    return minificar(
        '<h2 class="vg-t01-section-label">Atividade recente</h2>'
        '<div class="vg-t01-card">'
        f'<div class="vg-t01-timeline">{body}</div>'
        "</div>"
    )


def sprint_atual_html(meta: dict | None) -> str:
    """Card 'SPRINT ATUAL' canônico."""
    from src.dashboard.componentes.html_utils import minificar

    if not meta:
        return minificar(
            '<h2 class="vg-t01-section-label" style="margin-top:20px;">Sprint atual</h2>'
            '<div class="vg-t01-card vg-t01-sprint-card">'
            '<div style="font-size:13px;color:var(--text-muted);">'
            "Nenhuma sprint registrada."
            "</div>"
            "</div>"
        )
    pill_classe = f"pill pill-{meta.get('pill_tipo', 'd7-pendente')}"
    return minificar(
        '<h2 class="vg-t01-section-label" style="margin-top:20px;">Sprint atual</h2>'
        '<div class="vg-t01-card vg-t01-sprint-card">'
        '<div class="vg-t01-sprint-head">'
        "<div>"
        f'<div class="meta">{meta["sprint_numero"]} · {meta["periodo"]}</div>'
        f'<div class="titulo">{meta["titulo"]}</div>'
        "</div>"
        f'<span class="{pill_classe}">{meta["pill_texto"]}</span>'
        "</div>"
        f'<div class="desc">{meta["descricao"]}</div>'
        "</div>"
    )


# "O presente é índice da direção." -- Bergson (paráfrase)
