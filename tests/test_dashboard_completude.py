"""Testes da aba Completude -- Sprint 92a item 3.

Valida (a) filtro de ruído por volume mínimo de transações, (b) colorscale
trocado para [alerta, info, positivo] (laranja-amarelo-verde, sem vermelho
saturado) -- acceptance criteria da Sprint 92a #3.
"""

from __future__ import annotations

import pandas as pd

from src.dashboard.paginas.completude import (
    LIMIAR_MIN_TX_FILTRO_RUIDO,
    _heatmap,
    filtrar_categorias_por_volume,
)

# ---------------------------------------------------------------------------
# Sprint 92a item 3 -- toggle de ruido no heatmap de completude
# ---------------------------------------------------------------------------


def _df_sintetico() -> pd.DataFrame:
    return pd.DataFrame(
        [
            # Aluguel: 3 tx (passa filtro)
            {"categoria": "Aluguel", "valor": 2000.0, "mes_ref": "2026-01"},
            {"categoria": "Aluguel", "valor": 2000.0, "mes_ref": "2026-02"},
            {"categoria": "Aluguel", "valor": 2000.0, "mes_ref": "2026-03"},
            # Energia: 2 tx (passa filtro no limiar exato)
            {"categoria": "Energia", "valor": 120.0, "mes_ref": "2026-01"},
            {"categoria": "Energia", "valor": 130.0, "mes_ref": "2026-02"},
            # Plano de saúde: 1 tx (filtrado pelo ruído)
            {"categoria": "Saúde", "valor": 500.0, "mes_ref": "2026-01"},
            # Água: 0 tx (não aparece em extrato mas está na lista obrigatória)
        ]
    )


def test_filtrar_categorias_por_volume_remove_abaixo_do_limiar() -> None:
    """Categoria com 1 tx é filtrada; >=2 sobrevive."""
    extrato = _df_sintetico()
    obrigatorias = ["Aluguel", "Energia", "Saúde", "Água"]

    resultado = filtrar_categorias_por_volume(extrato, obrigatorias)

    assert "Aluguel" in resultado  # 3 tx
    assert "Energia" in resultado  # 2 tx (limiar exato)
    assert "Saúde" not in resultado  # 1 tx
    assert "Água" not in resultado  # 0 tx


def test_filtrar_categorias_respeita_limiar_parametrizado() -> None:
    """`minimo_tx=3` corta também Energia (2 tx)."""
    extrato = _df_sintetico()
    obrigatorias = ["Aluguel", "Energia"]

    resultado = filtrar_categorias_por_volume(extrato, obrigatorias, minimo_tx=3)

    assert resultado == ["Aluguel"]


def test_filtrar_categorias_extrato_vazio_mantem_lista_intacta() -> None:
    """Sem dados, retorna a lista canônica para não esconder config do usuário."""
    extrato = pd.DataFrame(columns=["categoria", "valor", "mes_ref"])
    obrigatorias = ["Aluguel", "Energia"]

    assert filtrar_categorias_por_volume(extrato, obrigatorias) == obrigatorias


def test_filtrar_categorias_lista_vazia_retorna_lista_vazia() -> None:
    """Sem categorias obrigatórias configuradas, nada a filtrar."""
    extrato = _df_sintetico()
    assert filtrar_categorias_por_volume(extrato, []) == []


def test_limiar_default_e_2_transacoes() -> None:
    """Sprint 92a explicita: limiar default documentado como 2."""  # noqa: accent
    assert LIMIAR_MIN_TX_FILTRO_RUIDO == 2


def test_completude_toggle_reduz_categorias() -> None:
    """Acceptance spec: toggle filtra categorias abaixo do limiar."""
    extrato = _df_sintetico()
    obrigatorias = ["Aluguel", "Energia", "Saúde", "Água"]

    # Toggle ativo (default).
    filtradas = filtrar_categorias_por_volume(extrato, obrigatorias)
    # Toggle desativado: lista completa é usada direto.
    completas = list(obrigatorias)

    assert len(filtradas) < len(completas)
    assert len(filtradas) == 2
    assert len(completas) == 4


# ---------------------------------------------------------------------------
# Sprint 92a item 3 -- colorscale laranja-amarelo-verde (sem vermelho saturado)
# ---------------------------------------------------------------------------


def test_heatmap_usa_colorscale_laranja_amarelo_verde() -> None:
    """Paleta do heatmap NÃO deve ter vermelho saturado (#FF5555) em nenhum stop."""
    from src.dashboard.tema import CORES

    resumo = {
        "2026-01": {"Aluguel": {"total": 2, "com_doc": 1, "sem_doc": 1, "orfas": []}},
        "2026-02": {"Aluguel": {"total": 2, "com_doc": 2, "sem_doc": 0, "orfas": []}},
    }

    fig = _heatmap(resumo)
    assert fig is not None

    heatmap_trace = fig.data[0]
    cores_paleta = [stop[1].lower() for stop in heatmap_trace.colorscale]

    # Paleta nova: alerta (laranja), info (amarelo), positivo (verde).
    assert CORES["alerta"].lower() in cores_paleta
    assert CORES["info"].lower() in cores_paleta
    assert CORES["positivo"].lower() in cores_paleta
    # Paleta antiga usava negativo (vermelho) -- NÃO deve aparecer.
    assert CORES["negativo"].lower() not in cores_paleta


# "Um heatmap honesto mostra o que falta -- não grita." -- princípio UX
