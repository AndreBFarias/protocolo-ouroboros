# ruff: noqa: E501
"""Testes UX-U-04 + UX-V-01: sidebar shell-only e filtros globais.

- Sidebar tem ZERO selectbox e ZERO text_input após refactor radical.
- 8 clusters do shell HTML continuam acessíveis.
- Filtros globais no main usam chip-bar fina (UX-V-01) com 4 chips
  visíveis e 4 selectbox invisíveis (``label_visibility=collapsed``).
  O ``st.expander("Filtros globais")`` legado foi substituído.
- Helper ``componentes/filtros_pagina.py`` exporta os 4 helpers canônicos.
"""
from __future__ import annotations

import subprocess
import time
from typing import Iterator

import pytest
from playwright.sync_api import sync_playwright

PORT = 8773


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


def test_sidebar_zero_selectbox(streamlit_url: str) -> None:
    """UX-U-04: sidebar é shell HTML puro; nenhum selectbox interno."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(6000)
        n = page.evaluate(
            "document.querySelectorAll('[data-testid=\"stSidebar\"] [data-testid=\"stSelectbox\"]').length"
        )
        assert n == 0, f"esperado 0 selectbox na sidebar; achou {n}"
        b.close()


def test_sidebar_zero_text_input(streamlit_url: str) -> None:
    """UX-U-04: sidebar é shell HTML puro; nenhum text_input interno."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(6000)
        n = page.evaluate(
            "document.querySelectorAll('[data-testid=\"stSidebar\"] [data-testid=\"stTextInput\"]').length"
        )
        assert n == 0, f"esperado 0 text_input na sidebar; achou {n}"
        b.close()


def test_sidebar_continua_com_8_clusters(streamlit_url: str) -> None:
    """UX-U-04: shell mantém acesso aos 8 clusters após corte dos widgets."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(6000)
        clusters = page.evaluate(
            "Array.from(document.querySelectorAll('[data-testid=\"stSidebar\"] .sidebar-cluster-header')).map(e => e.textContent.trim())"
        )
        esperados = ["Inbox", "Home", "Finanças", "Documentos", "Análise", "Metas", "Bem-estar", "Sistema"]
        for esp in esperados:
            assert any(esp.lower() in c.lower() for c in clusters), f"cluster {esp} ausente; achei {clusters}"
        b.close()


def test_filtros_globais_main_tem_chip_bar(streamlit_url: str) -> None:
    """UX-V-01: filtros globais migraram para chip-bar fina sem expander.

    Substitui o teste original ``test_filtros_globais_main_tem_expander``
    (UX-U-04) -- a chip-bar exibe 4 chips visíveis sempre e os 4 selectbox
    estão renderizados de forma invisível (``label_visibility=collapsed``)
    diretamente abaixo, sem precisar de click em expander. Contrato 3-tuple
    e 7 chaves de session_state preservados.
    """
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(streamlit_url)
        page.wait_for_timeout(6000)
        info = page.evaluate(
            """() => {
                const sidebar_selects = document.querySelectorAll('[data-testid="stSidebar"] [data-testid="stSelectbox"]');
                const all_selects = document.querySelectorAll('[data-testid="stSelectbox"]');
                let main_count = 0;
                all_selects.forEach(s => {
                    let p = s.closest('[data-testid="stSidebar"]');
                    if (!p) main_count++;
                });
                const chip_bar = document.querySelectorAll('.chip-bar-globais').length;
                const chips = document.querySelectorAll('.chip-bar-globais .chip-filtro').length;
                const expanders_filtros = Array.from(
                    document.querySelectorAll('[data-testid="stExpander"], details')
                ).filter(e => (e.textContent || '').includes('Filtros globais')).length;
                return {
                    sidebar: sidebar_selects.length,
                    main: main_count,
                    chip_bar: chip_bar,
                    chips: chips,
                    expanders_filtros: expanders_filtros,
                };
            }"""
        )
        assert info["sidebar"] == 0, f"esperado 0 selectbox sidebar; achou {info['sidebar']}"
        assert info["main"] >= 4, (
            f"esperado >=4 selectbox no main (granularidade+periodo+pessoa+forma); achou {info['main']}"
        )
        assert info["chip_bar"] >= 1, (
            f"esperado chip-bar fina .chip-bar-globais visível; achou {info['chip_bar']}"
        )
        assert info["chips"] >= 4, (
            f"esperado 4 chips (granularidade/período/pessoa/forma); achou {info['chips']}"
        )
        assert info["expanders_filtros"] == 0, (
            f"expander 'Filtros globais' deve sumir após UX-V-01; achou {info['expanders_filtros']}"
        )
        b.close()


def test_helper_filtros_pagina_existe() -> None:
    """UX-U-04: módulo ``componentes/filtros_pagina.py`` exporta helpers canônicos."""
    from src.dashboard.componentes import filtros_pagina
    assert hasattr(filtros_pagina, "renderizar_filtro_periodo")
    assert hasattr(filtros_pagina, "renderizar_filtro_pessoa")
    assert hasattr(filtros_pagina, "renderizar_filtro_forma_pagamento")
    assert hasattr(filtros_pagina, "renderizar_grid_filtros")
    assert filtros_pagina.FORMAS_PAGAMENTO[0] == "Todas"
    assert "Mês" in filtros_pagina.GRANULARIDADES


def test_helper_filtro_pessoa_devolve_string() -> None:
    """UX-U-04: helper ``renderizar_filtro_pessoa`` retorna string da seleção."""
    import sys
    from unittest.mock import patch

    class FakeSt:
        session_state: dict = {}
        @staticmethod
        def selectbox(label, opcoes, index=0, key=None):
            return opcoes[index]

    with patch.dict(sys.modules, {"streamlit": FakeSt()}):
        from src.dashboard.componentes.filtros_pagina import renderizar_filtro_pessoa
        valor = renderizar_filtro_pessoa(opcoes=["Todos", "André", "Vitória"])
        assert valor == "Todos"


def test_helper_filtro_forma_atualiza_session_state() -> None:
    """UX-U-04: ``renderizar_filtro_forma_pagamento`` grava ``filtro_forma`` em session_state."""
    import sys
    from unittest.mock import patch

    class FakeSt:
        session_state: dict = {}
        @staticmethod
        def selectbox(label, opcoes, index=0, key=None):
            return opcoes[1]  # Pix

    fake = FakeSt()
    with patch.dict(sys.modules, {"streamlit": fake}):
        from src.dashboard.componentes.filtros_pagina import renderizar_filtro_forma_pagamento
        valor = renderizar_filtro_forma_pagamento()
        assert valor == "Pix"
        assert fake.session_state["filtro_forma"] == "Pix"


# "Cada lugar tem suas próprias regras." -- Heráclito (paráfrase)
