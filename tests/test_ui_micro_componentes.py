"""Testa as 6 funções HTML adicionadas em UX-V-02.

Não renderiza no Streamlit; valida apenas que retornam HTML não vazio
com classes esperadas e que ``minificar()`` foi aplicado (resultado
em uma única linha, sem indentação Python crua).
"""

from __future__ import annotations

import pytest

from src.dashboard.componentes.ui import (
    bar_uso_html,
    donut_inline_html,
    insight_card_html,
    prazo_ritmo_falta_html,
    sparkline_html,
    tab_counter_html,
)


def _sem_indentacao_python(html: str) -> bool:
    """Validação UX-RD-04: nenhuma linha com >=4 espaços iniciais.

    Como ``minificar()`` colapsa todo whitespace em um único espaço, o
    resultado idealmente fica em uma única linha; este helper protege
    contra regressões em que a minificação seja desabilitada.
    """
    return all(not linha.startswith("    ") for linha in html.splitlines())


def test_sparkline_lista_vazia_retorna_string_vazia() -> None:
    assert sparkline_html([]) == ""
    assert sparkline_html([1.0]) == ""


def test_sparkline_render_basico() -> None:
    html = sparkline_html([1.0, 2.0, 3.0, 2.5])
    assert 'class="sparkline"' in html
    assert "<polyline" in html
    assert _sem_indentacao_python(html)


def test_bar_uso_total_zero_retorna_vazio() -> None:
    assert bar_uso_html(usado=0, total=0) == ""


def test_bar_uso_render_com_label_e_cor_por_pct() -> None:
    html = bar_uso_html(usado=95, total=100, label="quase cheio")
    assert 'data-pct="95.0"' in html
    assert "var(--accent-red)" in html
    assert "quase cheio" in html


def test_donut_clampa_percentual_e_render() -> None:
    assert "100%" in donut_inline_html(150)
    assert "0%" in donut_inline_html(-10)
    html = donut_inline_html(71)
    assert "71%" in html
    assert "var(--accent-yellow)" in html


def test_prazo_ritmo_falta_estrutura_canonica() -> None:
    html = prazo_ritmo_falta_html("SET/2026", "+R$ 2.500/MES", "5 MESES")
    assert html.count('class="prf-celula"') == 3
    assert "SET/2026" in html
    assert "5 MESES" in html


def test_tab_counter_ativo_aplica_classe() -> None:
    inativo = tab_counter_html("Fluxo", 3)
    ativo = tab_counter_html("Fluxo", 3, ativo=True)
    assert "tab-counter-ativo" not in inativo
    assert "tab-counter-ativo" in ativo


def test_insight_card_tipo_invalido_cai_em_descoberta() -> None:
    html = insight_card_html("invalido", "T", "C")
    assert "insight-descoberta" in html


@pytest.mark.parametrize(
    "tipo,label_esperado",
    [
        ("positivo", "POSITIVO"),
        ("atencao", "ATENÇÃO"),
        ("descoberta", "DESCOBERTA"),
        ("previsao", "PREVISÃO"),
    ],
)
def test_insight_card_tipos_validos(tipo: str, label_esperado: str) -> None:
    """UX-V-2.6 fix: rótulo PT-BR canônico (não tipo.upper() ASCII)."""
    html = insight_card_html(tipo, "Título", "Corpo")
    assert f"insight-{tipo}" in html
    assert label_esperado in html


def test_todos_micro_componentes_minificados() -> None:
    """Lição UX-RD-04: HTML inline não pode ter indentação Python crua."""
    amostras = [
        sparkline_html([1, 2, 3]),
        bar_uso_html(50, 100, label="meio"),
        donut_inline_html(50),
        prazo_ritmo_falta_html("a", "b", "c"),
        tab_counter_html("x", 1),
        insight_card_html("positivo", "t", "c"),
    ]
    for html in amostras:
        assert _sem_indentacao_python(html), f"indentação perigosa: {html[:80]}"


# "A medida do componente é seu uso, não sua existência." -- princípio UX-V-02
