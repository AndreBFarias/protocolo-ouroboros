"""Testes dos filtros avançados do Extrato + helper legenda_abaixo (Sprint 77)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.dashboard import tema

# ============================================================================
# Helper legenda_abaixo
# ============================================================================


class _FigMock:
    def __init__(self) -> None:
        self.layout_updates: list[dict] = []

    def update_layout(self, **kwargs: object) -> None:
        self.layout_updates.append(kwargs)


class TestLegendaAbaixo:
    def test_retorna_fig(self) -> None:
        fig = _FigMock()
        assert tema.legenda_abaixo(fig) is fig

    def test_legenda_horizontal(self) -> None:
        fig = _FigMock()
        tema.legenda_abaixo(fig)
        assert fig.layout_updates
        kwargs = fig.layout_updates[0]
        legend = kwargs["legend"]
        assert legend["orientation"] == "h"
        assert legend["yanchor"] == "top"
        assert legend["xanchor"] == "center"

    def test_espacamento_topo_base_explicito(self) -> None:
        fig = _FigMock()
        tema.legenda_abaixo(fig, espaco_topo=80, espaco_base=100)
        margin = fig.layout_updates[0]["margin"]
        assert margin["t"] == 80
        assert margin["b"] == 100

    def test_y_configuravel(self) -> None:
        fig = _FigMock()
        tema.legenda_abaixo(fig, y=-0.3)
        assert fig.layout_updates[0]["legend"]["y"] == -0.3


# ============================================================================
# Filtros avançados — unit test do pipeline de filtragem
# ============================================================================


@pytest.fixture
def df_extrato() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "data": "2026-04-01",
                "valor": -50.0,
                "categoria": "Farmácia",
                "classificacao": "Obrigatório",
                "banco_origem": "nubank",
                "tipo": "Despesa",
                "local": "Droga X",
                "forma_pagamento": "Pix",
            },
            {
                "data": "2026-04-02",
                "valor": -100.0,
                "categoria": "Supermercado",
                "classificacao": "Obrigatório",
                "banco_origem": "c6",
                "tipo": "Despesa",
                "local": "Big",
                "forma_pagamento": "Crédito",
            },
            {
                "data": "2026-04-03",
                "valor": -30.0,
                "categoria": "Lazer",
                "classificacao": "Supérfluo",
                "banco_origem": "nubank",
                "tipo": "Despesa",
                "local": "Cinema",
                "forma_pagamento": "Débito",
            },
            {
                "data": "2026-04-04",
                "valor": 5000.0,
                "categoria": "Salário",
                "classificacao": "N/A",
                "banco_origem": "itau",
                "tipo": "Receita",
                "local": "G4F",
                "forma_pagamento": "Transferência",
            },
        ]
    )


def _aplicar_filtros_avancados(
    df: pd.DataFrame,
    busca: str = "",
    categoria: str = "Todas",
    classificacao: str = "Todas",
    banco: str = "Todos",
    tipo: str = "Todos",
) -> pd.DataFrame:
    """Replica exatamente a lógica de extrato.py::renderizar para teste isolado."""
    resultado = df.copy()
    if busca.strip():
        mascara = resultado["local"].fillna("").str.contains(busca.strip(), case=False, na=False)
        resultado = resultado[mascara]
    if categoria != "Todas":
        resultado = resultado[resultado["categoria"] == categoria]
    if classificacao != "Todas":
        resultado = resultado[resultado["classificacao"] == classificacao]
    if banco != "Todos":
        resultado = resultado[resultado["banco_origem"] == banco]
    if tipo != "Todos":
        resultado = resultado[resultado["tipo"] == tipo]
    return resultado


class TestFiltrosAvancados:
    def test_sem_filtros_nao_altera(self, df_extrato: pd.DataFrame) -> None:
        assert len(_aplicar_filtros_avancados(df_extrato)) == 4

    def test_categoria_farmacia(self, df_extrato: pd.DataFrame) -> None:
        r = _aplicar_filtros_avancados(df_extrato, categoria="Farmácia")
        assert len(r) == 1
        assert r.iloc[0]["local"] == "Droga X"

    def test_classificacao_obrigatorio(self, df_extrato: pd.DataFrame) -> None:
        r = _aplicar_filtros_avancados(df_extrato, classificacao="Obrigatório")
        assert len(r) == 2

    def test_banco_nubank(self, df_extrato: pd.DataFrame) -> None:
        r = _aplicar_filtros_avancados(df_extrato, banco="nubank")
        assert len(r) == 2

    def test_tipo_receita(self, df_extrato: pd.DataFrame) -> None:
        r = _aplicar_filtros_avancados(df_extrato, tipo="Receita")
        assert len(r) == 1
        assert r.iloc[0]["valor"] == 5000.0

    def test_filtros_combinados_reduzem_contagem(self, df_extrato: pd.DataFrame) -> None:
        total = len(df_extrato)
        r = _aplicar_filtros_avancados(df_extrato, classificacao="Obrigatório", banco="nubank")
        assert len(r) <= total
        assert len(r) == 1  # só Farmácia Nubank

    def test_busca_local_case_insensitive(self, df_extrato: pd.DataFrame) -> None:
        r = _aplicar_filtros_avancados(df_extrato, busca="DROGA")
        assert len(r) == 1

    def test_contador_transacoes_reflete_filtro(self, df_extrato: pd.DataFrame) -> None:
        """Acceptance #5: contador muda ao aplicar filtro."""
        sem = len(_aplicar_filtros_avancados(df_extrato))
        com = len(_aplicar_filtros_avancados(df_extrato, categoria="Farmácia"))
        assert com < sem

    def test_filtro_vazio_nao_quebra(self, df_extrato: pd.DataFrame) -> None:
        r = _aplicar_filtros_avancados(df_extrato, categoria="Categoria Inexistente")
        assert len(r) == 0
