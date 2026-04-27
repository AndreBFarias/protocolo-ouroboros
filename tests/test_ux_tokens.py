"""Testes dos tokens de UX do dashboard (Sprint 76).

Garante que:
  - Floor absoluto de 13px está publicado como `FONTE_MIN_ABSOLUTA`.
  - CSS global referencia o floor em regra aplicável ao container principal.
  - Regra de padding mínimo para `.main .block-container` existe.
  - Helper `logo_sidebar_html()` retorna HTML válido quando `assets/icon.png`
    existe, e string vazia graceful quando não.
  - Hierarquia tipográfica nunca declara tamanho inferior a
    `FONTE_MIN_ABSOLUTA`.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.dashboard import tema


def test_fonte_min_absoluta_eh_13() -> None:
    assert tema.FONTE_MIN_ABSOLUTA == 13


def test_todos_tokens_tipograficos_respeitam_floor() -> None:
    """Nenhum valor de fonte declarado no módulo pode cair abaixo do floor."""
    nomes = [
        "FONTE_MIN_ABSOLUTA",
        "FONTE_MINIMA",
        "FONTE_LABEL",
        "FONTE_CORPO",
        "FONTE_SUBTITULO",
        "FONTE_TITULO",
        "FONTE_VALOR",
        "FONTE_HERO",
    ]
    for nome in nomes:
        valor = getattr(tema, nome)
        assert valor >= tema.FONTE_MIN_ABSOLUTA, (
            f"{nome}={valor} está abaixo do floor de {tema.FONTE_MIN_ABSOLUTA}"
        )


def test_padding_pagina_min_respeita_spec() -> None:
    """Spec da Sprint 76 exige padding interno >= 16px nos retângulos."""
    assert tema.PADDING_PAGINA_MIN_PX >= 16
    assert tema.PADDING_PAGINA_PADRAO_PX >= tema.PADDING_PAGINA_MIN_PX


def test_css_global_menciona_floor_13px() -> None:
    css = tema.css_global()
    assert f"max({tema.FONTE_MIN_ABSOLUTA}px" in css, (
        "css_global() deveria aplicar floor via max(13px, ...)"
    )


def test_css_global_declara_padding_bloco() -> None:
    css = tema.css_global()
    assert ".main .block-container" in css
    # Tem que declarar padding numérico, não apenas padding-top.
    match = re.search(r"\.main\s+\.block-container\s*\{[^}]*padding:\s*(\d+)px", css)
    assert match is not None, "regra de padding para .main .block-container ausente"
    valor_px = int(match.group(1))
    assert valor_px >= tema.PADDING_PAGINA_MIN_PX


def test_css_global_floor_plotly() -> None:
    css = tema.css_global()
    # Plotly tem sua própria escala; regra específica é obrigatória.
    assert ".js-plotly-plot .plotly text" in css
    assert f"{tema.FONTE_MIN_ABSOLUTA}px" in css


def test_logo_sidebar_html_retorna_string() -> None:
    """Sem streamlit no ambiente de teste, retorna HTML ou string vazia."""
    html = tema.logo_sidebar_html()
    # Quando assets/icon.png existe (CI do projeto), devolve HTML.
    if tema._CAMINHO_LOGO.exists():
        assert html.startswith("<div") and html.endswith("</div>")
        assert "data:image/png;base64," in html
        assert "Protocolo Ouroboros" in html
        assert "text-align:center" in html
    else:
        assert html == ""


def test_logo_sidebar_graceful_quando_arquivo_sumir(monkeypatch, tmp_path: Path) -> None:
    """Se `_CAMINHO_LOGO` não existir, devolve string vazia sem exceção."""
    monkeypatch.setattr(tema, "_CAMINHO_LOGO", tmp_path / "nao_existe.png")
    html = tema.logo_sidebar_html()
    assert html == ""


def test_logo_sidebar_largura_configuravel() -> None:
    if not tema._CAMINHO_LOGO.exists():
        return
    html = tema.logo_sidebar_html(largura_px=128)
    assert 'width="128"' in html
