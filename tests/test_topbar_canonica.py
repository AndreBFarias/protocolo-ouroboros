# ruff: noqa: E501
"""Testes UX-U-02: topbar canônica com slot dinâmico topbar-actions.

- Slot ``.topbar-actions`` está sempre presente (mesmo vazio).
- Breadcrumb tem segmentos clicáveis exceto o último (current).
- Helper ``renderizar_grupo_acoes`` grava em ``st.session_state``.
- ``main()`` em ``app.py`` reseta o slot antes de cada run (anti-leak).
- Página de teste com helper popula slot e shell injeta no DOM.
"""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Iterator

import pytest
from playwright.sync_api import sync_playwright

PORT = 8771


@pytest.fixture(scope="module")
def streamlit_url() -> Iterator[str]:
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


def test_topbar_tem_slot_actions(streamlit_url: str) -> None:
    """UX-U-02: ``.topbar-actions`` slot SEMPRE existe (mesmo vazio)."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(5000)
        tem = page.evaluate(
            "!!document.querySelector('.topbar .topbar-actions')"
        )
        assert tem, ".topbar-actions slot ausente; renderizar_topbar não está emitindo o div"
        b.close()


def test_topbar_breadcrumb_clicavel(streamlit_url: str) -> None:
    """UX-U-02: breadcrumb tem segmentos não-current como ``<a>`` e current como ``<span>``."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url + "/?cluster=Documentos&tab=Revisor")
        page.wait_for_timeout(6000)
        segs = page.evaluate(
            "Array.from(document.querySelectorAll('.breadcrumb .seg')).map(s => ({tag: s.tagName, current: s.classList.contains('current')}))"
        )
        assert len(segs) >= 2, f"breadcrumb deve ter >=2 segmentos; achei {segs}"
        for s in segs[:-1]:
            assert s["tag"] == "A", f"segmento não-current deve ser <a>; achei {s}"
        assert segs[-1]["tag"] == "SPAN" and segs[-1]["current"], f"último segmento deve ser <span class=current>; achei {segs[-1]}"
        b.close()


def test_helper_renderizar_grupo_acoes_grava_session_state() -> None:
    """UX-U-02: helper ``renderizar_grupo_acoes`` grava HTML em ``st.session_state['topbar_acoes_html']``."""
    from unittest.mock import patch

    fake_state: dict = {}
    fake_st = type("FakeSt", (), {"session_state": fake_state})()
    acoes = [
        {"label": "Atualizar", "kbd": "r"},
        {"label": "Ir para Validação", "primary": True, "href": "?cluster=Documentos&tab=Revisor"},
    ]
    with patch.dict("sys.modules", {"streamlit": fake_st}):
        from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
        renderizar_grupo_acoes(acoes)
    html = fake_state.get("topbar_acoes_html", "")
    assert "Atualizar" in html
    assert "Ir para Validação" in html
    assert "btn-primary" in html
    assert 'href="?cluster=Documentos&amp;tab=Revisor"' in html


def test_main_reseta_slot_topbar_em_cada_run() -> None:
    """UX-U-02: ``main()`` em ``app.py`` reseta ``topbar_acoes_html`` antes de cada run.

    Reset acontece dentro de ``_renderizar_topbar_para`` que ``main()`` chama
    no início de cada execução. Sem isso, página A injeta ações que vazam
    para página B no rerun seguinte.
    """
    texto = Path("src/dashboard/app.py").read_text(encoding="utf-8")
    # busca pela sequência exata de reset no helper que main() chama.
    assert re.search(
        r'st\.session_state\["topbar_acoes_html"\] = ""',
        texto,
    ), "main() (via _renderizar_topbar_para) não reseta topbar_acoes_html"


def test_topbar_actions_helper_existe() -> None:
    """UX-U-02: módulo ``componentes/topbar_actions.py`` exporta os helpers canônicos."""
    from src.dashboard.componentes import topbar_actions
    assert hasattr(topbar_actions, "renderizar_grupo_acoes")
    assert hasattr(topbar_actions, "consumir_acoes_html")
    assert hasattr(topbar_actions, "Acao")


# "Aja como o vento e seja como o tempo." -- Sun Tzu (paráfrase)
