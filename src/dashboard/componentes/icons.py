"""Ícones Feather inline como SVG strings (Sprint 92c).

Feather Icons (https://feathericons.com) — licença MIT. SVGs copiados
literalmente do repositório upstream (commit aberto ao público) e
parametrizados em dois placeholders: ``{size}`` (px do width/height) e
``{color}`` (stroke).

Uso canônico via ``tema.icon_html(nome, tamanho, cor)``. Uso direto
``renderizar_svg(nome, tamanho=16, cor="currentColor")`` também permitido
quando o caller precisa concatenar com outro HTML.

Licença reproduzida em ``docs/licenses/feather.md`` conforme exigido pela
MIT. Não adicionamos nova dependência — SVGs ficam inline no código para
respeitar o princípio Local First (CLAUDE.md regra #4).
"""

from __future__ import annotations

# Cada SVG tem viewBox 24x24, stroke-width 2, linecap/linejoin round.
# ``{size}`` troca os atributos width/height. ``{color}`` troca o stroke.
# O atributo ``fill="none"`` é preservado para o traço mono-linha.

SEARCH_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="11" cy="11" r="8"/>'
    '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
    "</svg>"
)

CHECK_CIRCLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
    '<polyline points="22 4 12 14.01 9 11.01"/>'
    "</svg>"
)

ALERT_TRIANGLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 '
    '3.86a2 2 0 0 0-3.42 0z"/>'
    '<line x1="12" y1="9" x2="12" y2="13"/>'
    '<line x1="12" y1="17" x2="12.01" y2="17"/>'
    "</svg>"
)

ALERT_CIRCLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<line x1="12" y1="8" x2="12" y2="12"/>'
    '<line x1="12" y1="16" x2="12.01" y2="16"/>'
    "</svg>"
)

INFO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<line x1="12" y1="16" x2="12" y2="12"/>'
    '<line x1="12" y1="8" x2="12.01" y2="8"/>'
    "</svg>"
)

X_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="18" y1="6" x2="6" y2="18"/>'
    '<line x1="6" y1="6" x2="18" y2="18"/>'
    "</svg>"
)

ZOOM_IN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="11" cy="11" r="8"/>'
    '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
    '<line x1="11" y1="8" x2="11" y2="14"/>'
    '<line x1="8" y1="11" x2="14" y2="11"/>'
    "</svg>"
)

DOWNLOAD_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
    '<polyline points="7 10 12 15 17 10"/>'
    '<line x1="12" y1="15" x2="12" y2="3"/>'
    "</svg>"
)

EXTERNAL_LINK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    '<polyline points="15 3 21 3 21 9"/>'
    '<line x1="10" y1="14" x2="21" y2="3"/>'
    "</svg>"
)

FILTER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>'
    "</svg>"
)

CALENDAR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>'
    '<line x1="16" y1="2" x2="16" y2="6"/>'
    '<line x1="8" y1="2" x2="8" y2="6"/>'
    '<line x1="3" y1="10" x2="21" y2="10"/>'
    "</svg>"
)


FEATHER_ICONES: dict[str, str] = {
    "search": SEARCH_SVG,
    "check-circle": CHECK_CIRCLE_SVG,
    "alert-triangle": ALERT_TRIANGLE_SVG,
    "alert-circle": ALERT_CIRCLE_SVG,
    "info": INFO_SVG,
    "x": X_SVG,
    "zoom-in": ZOOM_IN_SVG,
    "download": DOWNLOAD_SVG,
    "external-link": EXTERNAL_LINK_SVG,
    "filter": FILTER_SVG,
    "calendar": CALENDAR_SVG,
}


def renderizar_svg(nome: str, tamanho: int = 16, cor: str = "currentColor") -> str:
    """Renderiza o SVG inline de um ícone Feather por nome.

    ``nome`` deve existir em ``FEATHER_ICONES``. Quando ausente, retorna string
    vazia (degradação silenciosa — dashboard nunca quebra por ícone faltante).
    ``tamanho`` em pixels; ``cor`` pode ser valor hex, nome CSS ou
    ``"currentColor"`` (herda cor do texto contextual).
    """
    tmpl = FEATHER_ICONES.get(nome)
    if tmpl is None:
        return ""
    return tmpl.format(size=tamanho, color=cor)


# "O diabo mora nos detalhes." -- Gustave Flaubert
