"""Testes do módulo gap_documental (Sprint 75)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis import gap_documental as gd


@pytest.fixture
def df_extrato() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "data": "2026-03-17",
                "valor": -103.93,
                "categoria": "Natação",
                "tipo": "Despesa",
                "local": "SESC",
                "mes_ref": "2026-03",
                "banco_origem": "c6",
                "identificador": "tx-sesc-mar",
            },
            {
                "data": "2026-03-19",
                "valor": -800.0,
                "categoria": "Aluguel",
                "tipo": "Despesa",
                "local": "Ki-Sabor",
                "mes_ref": "2026-03",
                "banco_origem": "nubank",
                "identificador": "tx-alug-mar",
            },
            {
                "data": "2026-04-02",
                "valor": -50.0,
                "categoria": "Farmácia",
                "tipo": "Despesa",
                "local": "Droga X",
                "mes_ref": "2026-04",
                "banco_origem": "nubank",
                "identificador": "tx-farm-abr",
            },
            {
                "data": "2026-04-05",
                "valor": -30.0,
                "categoria": "Lazer",  # Não está em categorias_tracking
                "tipo": "Despesa",
                "local": "Cinema",
                "mes_ref": "2026-04",
                "banco_origem": "nubank",
                "identificador": "tx-lazer-abr",
            },
            {
                "data": "2026-04-10",
                "valor": 5000.0,
                "categoria": "Natação",  # É tracking mas tipo=Receita, deve pular
                "tipo": "Receita",
                "local": "Estorno SESC",
                "mes_ref": "2026-04",
                "banco_origem": "c6",
                "identificador": "tx-estorno",
            },
        ]
    )


class TestCarregarCategorias:
    def test_yaml_real_retorna_frozenset(self) -> None:
        cats = gd.carregar_categorias_obrigatorias()
        assert isinstance(cats, frozenset)
        assert "Farmácia" in cats
        assert "Natação" in cats


class TestCalcularCompletude:
    def test_filtro_categoria_obrigatoria(self, df_extrato: pd.DataFrame) -> None:
        categorias = frozenset({"Natação", "Aluguel", "Farmácia"})
        resumo = gd.calcular_completude(df_extrato, categorias_obrigatorias=categorias)
        # Lazer está fora (não obrigatória); Receita Natação é pulada (tipo!=Despesa/Imposto)
        assert "2026-03" in resumo
        assert "2026-04" in resumo
        assert "Lazer" not in resumo.get("2026-04", {})
        # Total de Natação em abril deve ser 0 (só tinha receita, não conta)
        assert "Natação" not in resumo.get("2026-04", {})

    def test_tudo_sem_doc_quando_ids_vazios(
        self, df_extrato: pd.DataFrame
    ) -> None:
        categorias = frozenset({"Natação", "Aluguel", "Farmácia"})
        resumo = gd.calcular_completude(df_extrato, categorias_obrigatorias=categorias)
        info_nat_mar = resumo["2026-03"]["Natação"]
        assert info_nat_mar["total"] == 1
        assert info_nat_mar["com_doc"] == 0
        assert info_nat_mar["sem_doc"] == 1
        assert len(info_nat_mar["orfas"]) == 1

    def test_ids_com_doc_marcam_como_coberto(
        self, df_extrato: pd.DataFrame
    ) -> None:
        categorias = frozenset({"Natação"})
        resumo = gd.calcular_completude(
            df_extrato,
            categorias_obrigatorias=categorias,
            ids_com_doc={"tx-sesc-mar"},
        )
        info = resumo["2026-03"]["Natação"]
        assert info["com_doc"] == 1
        assert info["sem_doc"] == 0

    def test_df_vazio_retorna_dict_vazio(self) -> None:
        resumo = gd.calcular_completude(pd.DataFrame(), frozenset({"X"}))
        assert resumo == {}

    def test_sem_categorias_retorna_dict_vazio(
        self, df_extrato: pd.DataFrame
    ) -> None:
        resumo = gd.calcular_completude(df_extrato, categorias_obrigatorias=frozenset())
        assert resumo == {}


class TestAlertas:
    def test_valor_alto_sem_doc_gera_alerta(
        self, df_extrato: pd.DataFrame
    ) -> None:
        resumo = gd.calcular_completude(
            df_extrato, categorias_obrigatorias=frozenset({"Aluguel"})
        )
        alertas_list = gd.alertas(resumo, valor_alto=500)
        assert any("Ki-Sabor" in a or "Aluguel" in a for a in alertas_list)

    def test_zero_cobertura_gera_alerta_quando_total_maior_que_2(
        self,
    ) -> None:
        df = pd.DataFrame(
            [
                {"mes_ref": "2026-04", "categoria": "Farmácia", "tipo": "Despesa",
                 "valor": -50.0, "local": "A", "data": "2026-04-01",
                 "banco_origem": "x", "identificador": f"id{i}"}
                for i in range(3)
            ]
        )
        resumo = gd.calcular_completude(df, categorias_obrigatorias=frozenset({"Farmácia"}))
        lista = gd.alertas(resumo)
        assert any("0 comprovantes" in a or "IRPF" in a for a in lista)


class TestOrfasParaCsv:
    def test_csv_tem_colunas_canonicas(self, df_extrato: pd.DataFrame) -> None:
        resumo = gd.calcular_completude(
            df_extrato, categorias_obrigatorias=frozenset({"Natação", "Aluguel"})
        )
        df = gd.orfas_para_csv(resumo)
        assert not df.empty
        assert set(df.columns) >= {
            "mes_ref",
            "categoria",
            "data",
            "valor",
            "local",
            "banco_origem",
            "identificador",
        }

    def test_resumo_vazio_vira_df_vazio(self) -> None:
        df = gd.orfas_para_csv({})
        assert df.empty
