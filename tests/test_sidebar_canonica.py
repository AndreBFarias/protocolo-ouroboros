# ruff: noqa: E501
"""Testes de regressão para sidebar canônica (UX-U-01).

Garante que ao rolar dentro da sidebar todos os 8 clusters ficam acessíveis,
brand é SVG glyph ouroboros (FIX-07), busca placeholder tem kbd, e scrollbar
respeita tokens canônicos do mockup.
"""

from __future__ import annotations

import subprocess
import time
from typing import Iterator

import pytest
from playwright.sync_api import sync_playwright

PORT = 8770


@pytest.fixture(scope="module")
def streamlit_url() -> Iterator[str]:
    """Sobe Streamlit na porta de teste e cleanup ao final."""
    proc = subprocess.Popen(
        [
            ".venv/bin/streamlit",
            "run",
            "src/dashboard/app.py",
            "--server.port",
            str(PORT),
            "--server.headless",
            "true",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(8)
    try:
        yield f"http://127.0.0.1:{PORT}"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_sidebar_renderiza_oito_clusters(streamlit_url: str) -> None:
    """UX-U-01: 8 clusters do mockup canônico devem aparecer no DOM."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(5000)
        clusters = page.eval_on_selector_all(
            '[data-testid="stSidebar"] .sidebar-cluster-header',
            "els => els.map(e => e.textContent.trim())",
        )
        esperados = [
            "Inbox",
            "Home",
            "Finanças",
            "Documentos",
            "Análise",
            "Metas",
            "Bem-estar",
            "Sistema",
        ]
        for esp in esperados:
            assert any(esp.lower() in c.lower() for c in clusters), (
                f"cluster {esp} ausente; achei {clusters}"
            )
        b.close()


def test_sidebar_tem_overflow_auto(streamlit_url: str) -> None:
    """UX-U-01: stSidebar deve ter overflow-y auto/scroll para permitir rolagem interna."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(5000)
        overflow = page.evaluate(
            "getComputedStyle(document.querySelector('[data-testid=\"stSidebar\"]')).overflowY"
        )
        assert overflow in ("auto", "scroll"), f"esperado overflow-y auto/scroll, tem {overflow}"
        b.close()


def test_sidebar_brand_eh_svg_ouroboros(streamlit_url: str) -> None:
    """UX-U-01 + FIX-07: brand deve ser SVG glyph ouroboros (não letra 'O')."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(5000)
        has_svg = page.evaluate(
            "!!document.querySelector('[data-testid=\"stSidebar\"] .sidebar-brand svg')"
        )
        assert has_svg, (
            "brand glyph SVG ausente; deve usar componentes/glyphs.py:glyph('ouroboros')"
        )
        b.close()


def test_sidebar_busca_placeholder_tem_kbd(streamlit_url: str) -> None:
    """UX-U-01: busca canônica do shell tem kbd / como atalho visual."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(5000)
        kbd_text = page.evaluate(
            "document.querySelector('[data-testid=\"stSidebar\"] .sidebar-search kbd')?.textContent"
        )
        assert kbd_text and kbd_text.strip() == "/", (
            f"kbd da busca deve mostrar /; achei {kbd_text!r}"
        )
        b.close()


def test_sidebar_inbox_tem_badge(streamlit_url: str) -> None:
    """UX-U-01: cluster Inbox tem .badge para contagem (mesmo que '...' por hora)."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(5000)
        badge_count = page.evaluate(
            """
            (() => {
                const sb = document.querySelector('[data-testid="stSidebar"]');
                const headers = sb ? sb.querySelectorAll('.sidebar-cluster-header') : [];
                if (!headers.length) return 0;
                return headers[0].querySelectorAll('.badge').length;
            })()
            """
        )
        assert badge_count >= 1, "primeiro cluster (Inbox) deve ter .badge"
        b.close()


def test_sidebar_scrollbar_canonica_aplicada(streamlit_url: str) -> None:
    """UX-U-01: regra CSS @import de scrollbar canônica está em tema_css.py."""
    from pathlib import Path

    css_text = Path("src/dashboard/tema_css.py").read_text(encoding="utf-8")
    # marcador da regra adicionada na U-01
    assert 'data-testid="stSidebar"' in css_text and "::-webkit-scrollbar" in css_text, (
        "regra ::-webkit-scrollbar para stSidebar ausente em tema_css.py"
    )


# "Toda casa precisa de uma porta antes das janelas." -- adaptado de Lao-Tsé
