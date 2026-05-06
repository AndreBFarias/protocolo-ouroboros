# ruff: noqa: E501
"""Page-header canônico do redesign (UX-U-03).

Único ponto de emissão de ``<h1 class="page-title">`` em
``src/dashboard/paginas/*.py``. Garante consistência visual cross-páginas:
UPPERCASE 40px JetBrains Mono gradient text. Mockup-fonte:
``novo-mockup/_shared/components.css`` linhas 130-156 (page-header,
page-title, page-subtitle, page-meta).

Uso:

    from src.dashboard.componentes.page_header import renderizar_page_header
    st.markdown(
        renderizar_page_header(
            titulo="EXTRATO",
            subtitulo="Tabela densa com transações do período.",
            sprint_tag="UX-T-02",
            pills=[{"texto": "78 transações", "tipo": "d7-graduado"}],
        ),
        unsafe_allow_html=True,
    )
"""
from __future__ import annotations

import html as _html
from typing import Iterable, TypedDict


class Pill(TypedDict, total=False):
    """Pílula informativa do page-meta (status, contagem, sprint-tag etc.)."""

    texto: str
    tipo: str  # d7-graduado / d7-calibracao / d7-regredindo / humano-aprovado / generica


def _renderizar_pill(pill: Pill) -> str:
    tipo = str(pill.get("tipo", "")).strip() or "generica"
    texto = _html.escape(str(pill.get("texto", "")))
    return f'<span class="pill pill-{tipo}">{texto}</span>'


def renderizar_page_header(
    titulo: str,
    subtitulo: str = "",
    sprint_tag: str = "",
    pills: Iterable[Pill] = (),
) -> str:
    """Emite ``<header class="page-header">`` canônico para ``st.markdown``.

    Args:
        titulo: texto do h1. CSS faz UPPERCASE; passe em case natural.
        subtitulo: parágrafo descritivo curto (omitido se vazio).
        sprint_tag: ID da sprint vigente para a tela.
        pills: sequência de :class:`Pill` para o lado direito (status,
            contagens). Se vazia e sem ``sprint_tag``, ``page-meta`` é omitido.

    Returns:
        HTML pronto para ``st.markdown(..., unsafe_allow_html=True)``.
    """
    titulo_html = _html.escape(titulo)
    subtitulo_html = (
        f'<p class="page-subtitle">{_html.escape(subtitulo)}</p>'
        if subtitulo
        else ""
    )
    sprint_tag_html = (
        f'<span class="sprint-tag">{_html.escape(sprint_tag)}</span>'
        if sprint_tag
        else ""
    )
    pills_html = "".join(_renderizar_pill(p) for p in pills)
    page_meta_html = (
        f'<div class="page-meta">{sprint_tag_html}{pills_html}</div>'
        if (sprint_tag_html or pills_html)
        else ""
    )
    return (
        '<header class="page-header">'
        f'<div><h1 class="page-title">{titulo_html}</h1>{subtitulo_html}</div>'
        f"{page_meta_html}"
        "</header>"
    )


# "Tudo precisa de um título antes de existir." -- Borges (paráfrase)
