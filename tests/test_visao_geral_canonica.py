# ruff: noqa: E501
"""Testes UX-T-01: Visão Geral canônica (mockup 01-visao-geral.html).

Cobertura:
- Helpers do widget ``visao_geral_widgets`` retornam estruturas bem-formadas.
- Página renderiza KPIs agentic, OS 5 CLUSTERS, ATIVIDADE RECENTE, SPRINT ATUAL.
- Topbar-actions populada com 2 botões (Atualizar + Ir para Validação).
- Cluster Home não tem mais st.tabs duplicadas.
"""

from __future__ import annotations

import subprocess
import time
from typing import Iterator

import pytest
from playwright.sync_api import sync_playwright

PORT = 8774


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


# === Helpers ===


def test_calcular_kpis_agentic_retorna_chaves_esperadas() -> None:
    """KPIs canônicos devem ter as 4 chaves: arquivos, paridade, aguardando, regredindo."""
    from src.dashboard.componentes.visao_geral_widgets import calcular_kpis_agentic

    kpis = calcular_kpis_agentic()
    for k in [
        "arquivos_catalogados",
        "arquivos_delta",
        "paridade_pct",
        "paridade_meta",
        "aguardando_humano",
        "aguardando_breakdown",
        "skills_regredindo",
        "skills_nomes",
    ]:
        assert k in kpis, f"chave {k} ausente em calcular_kpis_agentic"


def test_montar_clusters_canonicos_retorna_seis_cards() -> None:
    """Mockup canônico tem 6 cards (Inbox, Finanças, Documentos, Análise, Metas, Sistema)."""
    from src.dashboard.componentes.visao_geral_widgets import montar_clusters_canonicos

    cards = montar_clusters_canonicos()
    assert len(cards) == 6, f"esperado 6 cards, achou {len(cards)}"
    nomes = [c["nome"] for c in cards]
    assert nomes == ["Inbox", "Finanças", "Documentos", "Análise", "Metas", "Sistema"]


def test_ler_atividade_recente_devolve_lista() -> None:
    """``ler_atividade_recente`` devolve lista (vazia ou com TimelineEntry)."""
    from src.dashboard.componentes.visao_geral_widgets import ler_atividade_recente

    entries = ler_atividade_recente(n=6)
    assert isinstance(entries, list)
    for e in entries:
        assert "when" in e and "glyph" in e and "what_html" in e


def test_ler_sprint_atual_devolve_dict_ou_none() -> None:
    """``ler_sprint_atual`` devolve dict com chaves canônicas ou None."""
    from src.dashboard.componentes.visao_geral_widgets import ler_sprint_atual

    meta = ler_sprint_atual()
    if meta is not None:
        for k in ["sprint_numero", "periodo", "titulo", "descricao", "pill_texto", "pill_tipo"]:
            assert k in meta, f"chave {k} ausente em ler_sprint_atual"


# === Lint estrutural ===


def test_app_home_nao_tem_st_tabs_duplicadas() -> None:
    """UX-T-01: cluster Home renderiza visao_geral diretamente, sem st.tabs."""
    from pathlib import Path

    texto = Path("src/dashboard/app.py").read_text(encoding="utf-8")
    inicio = texto.find('if cluster == "Home":')
    fim = texto.find('elif cluster == "Finanças":')
    bloco_home = texto[inicio:fim]
    assert "st.tabs(" not in bloco_home, (
        "cluster Home ainda contém st.tabs(...) — UX-T-01 elimina tabs duplicadas com sidebar"
    )


# === Integração ao vivo ===


def test_visao_geral_renderiza_kpis_agentic(streamlit_url: str) -> None:
    """Página tem 4 KPIs com labels canônicos."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.goto(streamlit_url + "/?cluster=Home&tab=Vis%C3%A3o+Geral")
        page.wait_for_timeout(8000)
        labels = page.evaluate(
            "Array.from(document.querySelectorAll('.vg-t01-kpi .l')).map(e => e.textContent.trim())"
        )
        assert "Arquivos catalogados" in labels, (
            f"label Arquivos catalogados ausente; achei {labels}"
        )
        assert "Paridade ETL ↔ Opus" in labels
        assert "Aguardando humano" in labels
        assert "Skills regredindo" in labels
        b.close()


def test_visao_geral_renderiza_clusters_canonicos(streamlit_url: str) -> None:
    """Página tem 6 cards no bloco OS 5 CLUSTERS."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url + "/?cluster=Home&tab=Vis%C3%A3o+Geral")
        page.wait_for_timeout(8000)
        n = page.evaluate("document.querySelectorAll('.vg-t01-cluster-card').length")
        assert n == 6, f"esperado 6 cluster cards, achou {n}"
        b.close()


def test_visao_geral_renderiza_atividade_recente(streamlit_url: str) -> None:
    """Página tem timeline com entries."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url + "/?cluster=Home&tab=Vis%C3%A3o+Geral")
        page.wait_for_timeout(8000)
        n = page.evaluate("document.querySelectorAll('.vg-t01-tl-item').length")
        assert n >= 1, f"esperado >=1 timeline item, achou {n}"
        b.close()


def test_visao_geral_renderiza_sprint_atual(streamlit_url: str) -> None:
    """Página tem card 'Sprint atual' OU placeholder graceful."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url + "/?cluster=Home&tab=Vis%C3%A3o+Geral")
        page.wait_for_timeout(8000)
        tem_card = page.evaluate("!!document.querySelector('.vg-t01-sprint-card')")
        assert tem_card, "card .vg-t01-sprint-card ausente"
        b.close()


def test_visao_geral_topbar_tem_botoes(streamlit_url: str) -> None:
    """Topbar-actions deve ter 2 botões (Atualizar + Ir para Validação)."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url + "/?cluster=Home&tab=Vis%C3%A3o+Geral")
        page.wait_for_timeout(8000)
        info = page.evaluate(
            """() => {
                const slot = document.querySelector('.topbar-actions');
                if (!slot) return {n: 0, labels: []};
                const btns = slot.querySelectorAll('a.btn, button.btn');
                return {n: btns.length, labels: Array.from(btns).map(b => b.textContent.trim().slice(0,30))};
            }"""
        )
        assert info["n"] == 2, (
            f"esperado 2 botões topbar, achou {info['n']}; labels={info['labels']}"
        )
        joined = " ".join(info["labels"]).lower()
        assert "atualizar" in joined
        assert "validação" in joined or "validacao" in joined
        b.close()


def test_visao_geral_zero_st_tabs_no_main(streamlit_url: str) -> None:
    """Cluster Home não deve renderizar st.tabs no main após UX-T-01."""
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context().new_page()
        page.goto(streamlit_url + "/?cluster=Home&tab=Vis%C3%A3o+Geral")
        page.wait_for_timeout(8000)
        n = page.evaluate(
            'document.querySelectorAll(\'section[data-testid="stMain"] [data-baseweb="tab-list"], section.main [data-baseweb="tab-list"]\').length'
        )
        assert n == 0, f"st.tabs ainda presente no cluster Home: {n} encontradas"
        b.close()


# "O início ressoa em todo o caminho." -- Heráclito (paráfrase)
