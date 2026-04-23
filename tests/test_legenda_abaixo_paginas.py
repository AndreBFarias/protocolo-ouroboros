"""Testa adoção do helper `tema.legenda_abaixo` em páginas do dashboard.

Sprint 87.8 (R77-1): padroniza legenda plotly horizontal abaixo do gráfico
via helper único. Spec pede aplicação em pelo menos 4 plots (Receita vs
Despesa, projeções, heatmap, sankey). Testes garantem que futura edição
acidental não remove o helper.
"""

from __future__ import annotations

import re
from pathlib import Path

PAGINAS_ESPERADAS: tuple[Path, ...] = (
    Path("src/dashboard/paginas/visao_geral.py"),
    Path("src/dashboard/paginas/projecoes.py"),
    Path("src/dashboard/paginas/analise_avancada.py"),
)


def test_helper_existe_em_tema() -> None:
    conteudo = Path("src/dashboard/tema.py").read_text(encoding="utf-8")
    assert "def legenda_abaixo(" in conteudo, (
        "Helper legenda_abaixo deve existir em src/dashboard/tema.py"
    )


def test_paginas_importam_modulo_tema() -> None:
    for caminho in PAGINAS_ESPERADAS:
        texto = caminho.read_text(encoding="utf-8")
        assert "from src.dashboard import tema" in texto, (
            f"{caminho} precisa importar o módulo tema para chamar legenda_abaixo"
        )


def test_legenda_abaixo_em_pelo_menos_4_plots() -> None:
    """Acceptance do spec 87.8: helper aplicado em >=4 plots."""
    total = 0
    for caminho in PAGINAS_ESPERADAS:
        texto = caminho.read_text(encoding="utf-8")
        total += len(re.findall(r"tema\.legenda_abaixo\(", texto))
    assert total >= 4, f"Apenas {total} chamadas a tema.legenda_abaixo nas páginas"


def test_visao_geral_usa_legenda_abaixo() -> None:
    texto = Path("src/dashboard/paginas/visao_geral.py").read_text(encoding="utf-8")
    assert "tema.legenda_abaixo(fig)" in texto


def test_projecoes_usa_legenda_abaixo_nos_dois_plots() -> None:
    texto = Path("src/dashboard/paginas/projecoes.py").read_text(encoding="utf-8")
    assert texto.count("tema.legenda_abaixo(fig)") >= 2


def test_analise_avancada_usa_legenda_abaixo_heatmap_e_sankey() -> None:
    texto = Path("src/dashboard/paginas/analise_avancada.py").read_text(encoding="utf-8")
    assert texto.count("tema.legenda_abaixo(fig)") >= 2


# "A padronização é a base silenciosa de toda elegância." -- Aristóteles
