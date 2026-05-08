# ruff: noqa: E501
"""Componente de cards dos clusters canônicos da Visão Geral (UX-V-2.7-FIX).

Extraído de ``paginas/visao_geral.py`` (que estourou 996 linhas / limite
``(h)`` 800L). Mantém o HTML do bloco "OS 5 CLUSTERS" + os estilos T-01
canônicos (KPIs agentic, cards-cluster, timeline e card sprint).

API pública:
    - ``estilos_t01_canonicos()`` -> str: CSS local UX-T-01.
    - ``clusters_canonicos_html(cards)`` -> str: 6 cards a partir de lista
      de dicts (formato do ``visao_geral_widgets.montar_clusters_canonicos``).
"""
from __future__ import annotations


def estilos_t01_canonicos() -> str:
    """CSS local UX-T-01 -- espelha estilo inline do mockup canônico."""
    return """
    <style>
      .vg-t01 { font-family: var(--ff-sans); }
      .vg-t01-kpis {
        display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
        margin: 0 0 16px;
      }
      .vg-t01-kpi {
        background: var(--bg-surface); border: 1px solid var(--border-subtle);
        border-radius: var(--r-md); padding: 16px;
        display: flex; flex-direction: column; gap: 6px;
        text-decoration: none; color: inherit;
        transition: border-color .15s, transform .15s;
      }
      .vg-t01-kpi:hover { border-color: var(--accent-purple); transform: translateY(-2px); }
      .vg-t01-kpi .l {
        font-family: var(--ff-mono); font-size: var(--fs-11);
        letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted);
      }
      .vg-t01-kpi .v {
        font-family: var(--ff-mono); font-size: 32px; font-weight: 500;
        line-height: 1; font-variant-numeric: tabular-nums;
      }
      .vg-t01-kpi .d {
        font-family: var(--ff-mono); font-size: var(--fs-12); color: var(--text-muted);
      }
      .vg-t01-kpi.up   .v { color: var(--d7-graduado); }
      .vg-t01-kpi.warn .v { color: var(--accent-yellow); }
      .vg-t01-kpi.bad  .v { color: var(--accent-red); }

      .vg-t01-section-label {
        font-family: var(--ff-mono); font-size: var(--fs-13);
        letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted);
        margin: 0 0 8px;
      }
      .vg-t01-cluster-grid {
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
      }
      .vg-t01-cluster-card,
      .vg-t01-cluster-card:link,
      .vg-t01-cluster-card:visited,
      .vg-t01-cluster-card:hover,
      .vg-t01-cluster-card:active,
      .vg-t01-cluster-card h3,
      .vg-t01-cluster-card .desc,
      .vg-t01-cluster-card .stats span,
      .vg-t01-cluster-card .stats strong {
        text-decoration: none !important;
        color: inherit !important;
      }
      .vg-t01-cluster-card {
        background: var(--bg-surface); border: 1px solid var(--border-subtle);
        border-radius: var(--r-md); padding: 16px;
        display: flex; flex-direction: column; gap: 8px;
        color: var(--text-primary) !important;
        transition: border-color .15s, transform .15s;
      }
      .vg-t01-cluster-card:hover {
        border-color: var(--accent-purple);
        transform: translateY(-2px);
      }
      .vg-t01-cluster-card h3 {
        font-family: var(--ff-mono); font-size: var(--fs-15); font-weight: 500;
        margin: 0; letter-spacing: -0.01em;
      }
      .vg-t01-cluster-head {
        display: flex; align-items: center; gap: 8px;
      }
      .vg-t01-cluster-ic {
        color: var(--accent-purple);
        display: inline-flex; align-items: center;
      }
      .vg-t01-cluster-ic svg { color: var(--accent-purple); }
      .vg-t01-cluster-card .desc {
        font-size: var(--fs-13); color: var(--text-muted); line-height: 1.5;
      }
      .vg-t01-cluster-card .stats {
        display: flex; gap: 12px; margin-top: auto; padding-top: 8px;
        border-top: 1px solid var(--border-subtle);
      }
      .vg-t01-cluster-card .stats span {
        font-family: var(--ff-mono); font-size: var(--fs-11); color: var(--text-secondary);
      }
      .vg-t01-cluster-card .stats strong {
        color: var(--text-primary); margin-right: 4px;
      }

      .vg-t01-card { background: var(--bg-surface); border: 1px solid var(--border-subtle);
                     border-radius: var(--r-md); padding: 16px; }
      .vg-t01-tl-item {
        display: grid; grid-template-columns: 90px 24px 1fr; gap: 8px;
        padding: 8px 0; border-bottom: 1px dashed var(--border-subtle);
      }
      .vg-t01-tl-item:last-child { border-bottom: 0; }
      .vg-t01-tl-item .when {
        font-family: var(--ff-mono); font-size: var(--fs-11); color: var(--text-muted);
        padding-top: 2px;
      }
      .vg-t01-tl-item .ic { color: var(--accent-purple); padding-top: 2px; }
      .vg-t01-tl-item .what {
        font-size: var(--fs-13);
        color: var(--text-secondary);
        line-height: 1.45;
      }
      .vg-t01-tl-item .what strong { color: var(--text-primary); font-family: var(--ff-mono); }
      .vg-t01-tl-item .what code { color: var(--accent-purple); }

      .vg-t01-sprint-card { margin-top: 16px; }
      .vg-t01-sprint-head {
        display: flex; align-items: baseline; justify-content: space-between;
        margin-bottom: 12px;
      }
      .vg-t01-sprint-head .meta {
        font-family: var(--ff-mono); font-size: 11px; letter-spacing: 0.06em;
        text-transform: uppercase; color: var(--text-muted);
      }
      .vg-t01-sprint-head .titulo {
        font-family: var(--ff-mono); font-size: 18px; font-weight: 500; margin-top: 4px;
      }
      .vg-t01-sprint-card .desc {
        font-size: 13px; color: var(--text-secondary); line-height: 1.5;
      }
      .vg-t01-sprint-card .desc strong { color: var(--text-primary); }
    </style>
    """


def clusters_canonicos_html(cards: list[dict]) -> str:
    """Bloco "OS 5 CLUSTERS" do mockup com 6 cards descritivos.

    SIDEBAR-CANON-FIX (2026-05-06): cada card recebe glyph SVG canônico
    no header (mockup ``_visao-render.js`` linha 130 usa ``glyph(ic, 18)``).
    """
    from src.dashboard.componentes.glyphs import glyph
    from src.dashboard.componentes.html_utils import minificar

    cards_html = []
    for c in cards:
        glyph_nome = c.get("glyph", "")
        glyph_html = glyph(glyph_nome, tamanho_px=18) if glyph_nome else ""
        cards_html.append(
            f'<a class="vg-t01-cluster-card" href="{c["href"]}" target="_self"'
            ' style="text-decoration:none;color:inherit;">'
            '<div class="vg-t01-cluster-head">'
            f'<span class="vg-t01-cluster-ic">{glyph_html}</span>'
            f'<h3>{c["nome"]}</h3>'
            "</div>"
            f'<div class="desc">{c["descricao"]}</div>'
            '<div class="stats">'
            f'<span><strong>{c["stat1_value"]}</strong>{c["stat1_label"]}</span>'
            f'<span><strong>{c["stat2_value"]}</strong>{c["stat2_label"]}</span>'
            "</div>"
            "</a>"
        )
    return minificar(
        '<h2 class="vg-t01-section-label">Os 5 clusters</h2>'
        '<div class="vg-t01-cluster-grid">'
        f'{"".join(cards_html)}'
        "</div>"
    )


# "Cada parte é índice do todo." -- Heráclito
