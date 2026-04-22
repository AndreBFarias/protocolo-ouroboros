"""Testes do filtro de forma de pagamento (Sprint 72)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.dashboard import dados


@pytest.fixture
def df_misto() -> pd.DataFrame:
    """DataFrame com 5 formas distintas, facilitando validação de filtros."""
    return pd.DataFrame(
        [
            {"data": "2026-04-01", "valor": -50.0, "forma_pagamento": "Pix", "tipo": "Despesa"},
            {
                "data": "2026-04-02",
                "valor": -100.0,
                "forma_pagamento": "Crédito",
                "tipo": "Despesa",
            },
            {"data": "2026-04-03", "valor": -30.0, "forma_pagamento": "Débito", "tipo": "Despesa"},
            {"data": "2026-04-04", "valor": -800.0, "forma_pagamento": "Boleto", "tipo": "Despesa"},
            {"data": "2026-04-05", "valor": -200.0, "forma_pagamento": "TED", "tipo": "Despesa"},
            {"data": "2026-04-06", "valor": -75.0, "forma_pagamento": "DOC", "tipo": "Despesa"},
            {"data": "2026-04-07", "valor": 5000.0, "forma_pagamento": "Pix", "tipo": "Receita"},
        ]
    )


class TestFiltrarPorFormaPagamento:
    def test_filtro_none_devolve_integro(self, df_misto: pd.DataFrame) -> None:
        resultado = dados.filtrar_por_forma_pagamento(df_misto, None)
        assert len(resultado) == len(df_misto)

    def test_filtro_todas_devolve_integro(self, df_misto: pd.DataFrame) -> None:
        resultado = dados.filtrar_por_forma_pagamento(df_misto, "Todas")
        assert len(resultado) == len(df_misto)

    def test_filtro_pix_pega_apenas_pix(self, df_misto: pd.DataFrame) -> None:
        resultado = dados.filtrar_por_forma_pagamento(df_misto, "Pix")
        assert len(resultado) == 2
        assert set(resultado["forma_pagamento"]) == {"Pix"}

    def test_filtro_credito_um_registro(self, df_misto: pd.DataFrame) -> None:
        resultado = dados.filtrar_por_forma_pagamento(df_misto, "Crédito")
        assert len(resultado) == 1
        assert resultado.iloc[0]["valor"] == -100.0

    def test_filtro_transferencia_agrupa_ted_e_doc(self, df_misto: pd.DataFrame) -> None:
        """Canonicalização via _FORMAS_CANONICAS: TED + DOC -> Transferência."""
        resultado = dados.filtrar_por_forma_pagamento(df_misto, "Transferência")
        assert len(resultado) == 2
        formas_orig = set(resultado["forma_pagamento"])
        assert formas_orig == {"TED", "DOC"}

    def test_filtro_forma_inexistente_devolve_vazio(self, df_misto: pd.DataFrame) -> None:
        resultado = dados.filtrar_por_forma_pagamento(df_misto, "Moeda de Ouro")
        assert len(resultado) == 0

    def test_filtro_coluna_ausente_devolve_integro(self) -> None:
        df = pd.DataFrame([{"data": "2026-04-01", "valor": -50.0, "tipo": "Despesa"}])
        resultado = dados.filtrar_por_forma_pagamento(df, "Pix")
        assert len(resultado) == 1

    def test_despesa_credito_nunca_excede_despesa_total(self, df_misto: pd.DataFrame) -> None:
        """Acceptance #5 — total com filtro <= total sem filtro."""
        total_sem = abs(df_misto[df_misto["tipo"] == "Despesa"]["valor"].sum())
        com_filtro = dados.filtrar_por_forma_pagamento(df_misto, "Crédito")
        total_com = abs(com_filtro[com_filtro["tipo"] == "Despesa"]["valor"].sum())
        assert total_com <= total_sem


class TestFiltroFormaAtivo:
    def test_sem_streamlit_retorna_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        monkeypatch.setitem(sys.modules, "streamlit", None)
        assert dados.filtro_forma_ativo() is None

    def test_valor_todas_vira_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        class FakeSt:
            session_state = {"filtro_forma": "Todas"}

        monkeypatch.setitem(sys.modules, "streamlit", FakeSt())
        assert dados.filtro_forma_ativo() is None

    def test_valor_none_vira_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        class FakeSt:
            session_state = {"filtro_forma": None}

        monkeypatch.setitem(sys.modules, "streamlit", FakeSt())
        assert dados.filtro_forma_ativo() is None

    def test_valor_concreto_retorna_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import sys

        class FakeSt:
            session_state = {"filtro_forma": "Pix"}

        monkeypatch.setitem(sys.modules, "streamlit", FakeSt())
        assert dados.filtro_forma_ativo() == "Pix"
