# ruff: noqa: E501
"""Testes UX-U-03: helper de page-header canônico.

- Helper emite ``<h1 class="page-title">`` correto.
- Subtítulo, sprint-tag, pills aparecem quando passados.
- Nenhuma página em ``src/dashboard/paginas/*.py`` usa ``st.title`` ou
  ``st.markdown("# X")`` (regra de unicidade).
- 6 telas amostra: ``h1.page-title`` visível com ``text-transform: uppercase``.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Iterator

import pytest
from playwright.sync_api import sync_playwright

PORT = 8772


# === Testes unitários do helper ===


def test_helper_emite_h1_page_title() -> None:
    from src.dashboard.componentes.page_header import renderizar_page_header
    html = renderizar_page_header("EXTRATO")
    assert '<h1 class="page-title">EXTRATO</h1>' in html


def test_helper_inclui_subtitulo_quando_dado() -> None:
    from src.dashboard.componentes.page_header import renderizar_page_header
    html = renderizar_page_header("CONTAS", subtitulo="Saldos por banco")
    assert '<p class="page-subtitle">Saldos por banco</p>' in html


def test_helper_omite_subtitulo_quando_vazio() -> None:
    from src.dashboard.componentes.page_header import renderizar_page_header
    html = renderizar_page_header("CONTAS")
    assert "page-subtitle" not in html


def test_helper_inclui_sprint_tag() -> None:
    from src.dashboard.componentes.page_header import renderizar_page_header
    html = renderizar_page_header("X", sprint_tag="UX-T-01")
    assert '<span class="sprint-tag">UX-T-01</span>' in html


def test_helper_inclui_pills() -> None:
    from src.dashboard.componentes.page_header import renderizar_page_header
    html = renderizar_page_header("X", pills=[{"texto": "439 docs", "tipo": "d7-graduado"}])
    assert '<span class="pill pill-d7-graduado">439 docs</span>' in html


def test_helper_omite_page_meta_quando_vazio() -> None:
    from src.dashboard.componentes.page_header import renderizar_page_header
    html = renderizar_page_header("X")
    assert "page-meta" not in html


def test_helper_escapa_html_no_titulo() -> None:
    from src.dashboard.componentes.page_header import renderizar_page_header
    html = renderizar_page_header("<script>alert(1)</script>")
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html


# === Lint estrutural: nenhuma st.title/st.markdown('# X') em paginas/ ===


def test_zero_st_title_em_paginas() -> None:
    infratores = []
    for arq in os.listdir("src/dashboard/paginas"):
        if not arq.endswith(".py") or arq.startswith("_"):
            continue
        texto = Path(f"src/dashboard/paginas/{arq}").read_text(encoding="utf-8")
        if re.search(r'^\s*st\.title\(', texto, re.MULTILINE):
            infratores.append(arq)
    assert not infratores, f"st.title() ainda presente em: {infratores}; migrar para page_header"


def test_zero_st_markdown_h1_em_paginas() -> None:
    infratores = []
    for arq in os.listdir("src/dashboard/paginas"):
        if not arq.endswith(".py") or arq.startswith("_"):
            continue
        texto = Path(f"src/dashboard/paginas/{arq}").read_text(encoding="utf-8")
        # st.markdown("# Texto") -- matches "# " ou '# '
        if re.search(r'st\.markdown\(["\'][\s]*#[^#]', texto):
            infratores.append(arq)
    assert not infratores, (
        f'st.markdown("# X") ainda presente em: {infratores}; migrar para page_header'
    )


# === Integração: 6 telas amostra renderizam h1.page-title ===


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


TELAS_AMOSTRA = [
    ("Finanças", "Extrato", "EXTRATO"),
    ("Documentos", "Revisor", "REVISOR"),
    ("Análise", "Categorias", "CATEGORIAS"),
    ("Bem-estar", "Hoje", "BEM-ESTAR"),
    ("Sistema", "Skills D7", "SKILLS"),
]


@pytest.mark.parametrize("cluster,tab,h1_esperado", TELAS_AMOSTRA)
def test_pagina_renderiza_h1_page_title(cluster: str, tab: str, h1_esperado: str, streamlit_url: str) -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        url = f"{streamlit_url}/?cluster={urllib.parse.quote(cluster)}&tab={urllib.parse.quote(tab)}"
        page.goto(url)
        page.wait_for_timeout(6000)
        info = page.evaluate(
            """() => {
                const h1s = Array.from(document.querySelectorAll('h1.page-title')).filter(h => h.getBoundingClientRect().width > 0);
                return h1s.map(h => ({txt: h.textContent.trim().toUpperCase(), tt: getComputedStyle(h).textTransform}));
            }"""
        )
        assert len(info) >= 1, f"esperado >=1 h1.page-title visível em {cluster}/{tab}; achou {len(info)}"
        # text-transform deve ser uppercase
        assert info[0]["tt"] == "uppercase", f"page-title deve ser UPPERCASE; tt={info[0]['tt']}"
        # texto inclui marcador esperado
        assert h1_esperado in info[0]["txt"], (
            f"esperado titulo contendo {h1_esperado!r}, achei {info[0]['txt']!r}"
        )
        b.close()


# "Tudo precisa de um título antes de existir." -- Borges (paráfrase)
