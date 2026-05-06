# ruff: noqa: E501
"""Helper para páginas injetarem botões na topbar (UX-U-02).

Cada página chama ``renderizar_grupo_acoes(...)`` no início de seu ``renderizar()``
e o resultado é registrado em ``st.session_state['topbar_acoes_html']``.

A função ``renderizar_topbar`` em ``componentes/shell.py`` lê esse valor e
injeta no slot ``<div class="topbar-actions">``. ``main()`` em ``app.py``
reseta o slot ao início de cada run para evitar leak entre páginas.

Mockup-fonte: ``components.css:.topbar-actions`` e ``00-shell-navegacao.html``.
"""
from __future__ import annotations

import html as _html
from typing import Iterable, TypedDict


class Acao(TypedDict, total=False):
    """Estrutura canônica de uma ação na topbar.

    SIDEBAR-CANON-FIX (2026-05-06): campo ``kbd`` removido — mockup
    canônico (00-shell-navegacao.html / 01-visao-geral.html) NÃO usa
    pílula ``<kbd>`` em botões da topbar. Antes esse campo causava
    vazamento de texto (ex.: "Atualizar r").

    - ``label`` (obrigatório): texto visível no botão.
    - ``href``: se presente, vira ``<a>`` (link); senão vira ``<button>``.
    - ``primary``: ``True`` aplica classe ``btn-primary`` (cor accent).
    - ``glyph``: nome do glyph SVG em ``componentes/glyphs.py``.
    - ``title``: tooltip (atributo ``title`` HTML).
    """

    label: str
    href: str
    primary: bool
    glyph: str
    title: str


def _renderizar_acao(acao: Acao) -> str:
    """Renderiza UMA ação como HTML link/button da topbar."""
    label = _html.escape(str(acao.get("label", "")))
    href = acao.get("href")
    classe = "btn btn-primary btn-sm" if acao.get("primary") else "btn btn-sm"
    glyph_nome = acao.get("glyph")
    glyph_html = ""
    if glyph_nome:
        try:
            from src.dashboard.componentes.glyphs import glyph as _glyph
            glyph_html = _glyph(glyph_nome, tamanho_px=14)
        except Exception:
            glyph_html = ""
    title_attr = ""
    if acao.get("title"):
        title_attr = f' title="{_html.escape(str(acao["title"]), quote=True)}"'
    conteudo = f'{glyph_html}<span>{label}</span>'
    if href:
        href_esc = _html.escape(str(href), quote=True)
        return (
            f'<a class="{classe}" href="{href_esc}"{title_attr} '
            'style="text-decoration:none;display:inline-flex;'
            'align-items:center;gap:6px;">'
            f'{conteudo}</a>'
        )
    return f'<button class="{classe}" type="button"{title_attr}>{conteudo}</button>'


def renderizar_grupo_acoes(acoes: Iterable[Acao]) -> None:
    """Define o HTML das ações da topbar para esta run.

    Deve ser chamado por cada página em seu ``renderizar()`` ANTES do
    dispatcher de tabs. ``main()`` em ``app.py`` reseta o estado antes de
    cada run, então só persiste o valor da página corrente.
    """
    import streamlit as st

    html_acoes = "".join(_renderizar_acao(a) for a in acoes)
    st.session_state["topbar_acoes_html"] = html_acoes


def consumir_acoes_html() -> str:
    """Lê (sem resetar) o HTML das ações da topbar para esta run."""
    try:
        import streamlit as st
        return st.session_state.get("topbar_acoes_html", "")
    except Exception:
        return ""


def resetar_slot() -> None:
    """Reseta o slot. Chamado por ``main()`` no início de cada run."""
    try:
        import streamlit as st
        st.session_state["topbar_acoes_html"] = ""
    except Exception:
        pass


# "Aja como o vento e seja como o tempo." -- Sun Tzu (paráfrase)
