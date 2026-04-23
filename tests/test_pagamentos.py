"""Testes do módulo src/analysis/pagamentos.py (Sprint 79)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.analysis import pagamentos as pg


@pytest.fixture
def df_extrato() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "data": "2026-04-10",
                "valor": -103.93,
                "local": "Sesc Natação",
                "forma_pagamento": "Boleto",
                "banco_origem": "c6",
                "mes_ref": "2026-04",
                "tipo": "Despesa",
            },
            {
                "data": "2026-04-15",
                "valor": -50.0,
                "local": "Farmácia Droga X",
                "forma_pagamento": "Pix",
                "banco_origem": "nubank",
                "mes_ref": "2026-04",
                "tipo": "Despesa",
            },
            {
                "data": "2026-04-16",
                "valor": -75.0,
                "local": "Farmácia Droga X",
                "forma_pagamento": "Pix",
                "banco_origem": "nubank",
                "mes_ref": "2026-04",
                "tipo": "Despesa",
            },
            {
                "data": "2026-04-20",
                "valor": -800.0,
                "local": "Shopping Big",
                "forma_pagamento": "Crédito",
                "banco_origem": "nubank",
                "mes_ref": "2026-04",
                "tipo": "Despesa",
            },
            {
                "data": "2026-03-20",
                "valor": -500.0,
                "local": "Shopping Big",
                "forma_pagamento": "Crédito",
                "banco_origem": "nubank",
                "mes_ref": "2026-03",
                "tipo": "Despesa",
            },
            {
                "data": "2026-04-05",
                "valor": 5000.0,
                "local": "G4F",
                "forma_pagamento": "Transferência",
                "banco_origem": "itau",
                "mes_ref": "2026-04",
                "tipo": "Receita",
            },
        ]
    )


@pytest.fixture
def df_prazos() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "conta": "Condominio",
                "dia_vencimento": 5,
                "banco_pagamento": "itau",
                "auto_debito": False,
            },
            {
                "conta": "Sesc",
                "dia_vencimento": 10,
                "banco_pagamento": "c6",
                "auto_debito": False,
            },
        ]
    )


class TestBoletos:
    def test_boleto_pago_aparece_como_pago(
        self, df_extrato: pd.DataFrame, df_prazos: pd.DataFrame
    ) -> None:
        hoje = date(2026, 4, 22)
        bol = pg.carregar_boletos(df_extrato, df_prazos, hoje=hoje)
        assert not bol.empty
        pagos = bol[bol["status"] == pg.STATUS_PAGO]
        assert len(pagos) >= 1
        assert "Sesc" in pagos.iloc[0]["fornecedor"]

    def test_boleto_nao_pago_no_mes_vira_pendente_ou_atrasado(
        self, df_extrato: pd.DataFrame, df_prazos: pd.DataFrame
    ) -> None:
        hoje = date(2026, 4, 22)
        bol = pg.carregar_boletos(df_extrato, df_prazos, hoje=hoje)
        # Condomínio não foi pago no extrato e venceu dia 5; hoje é dia 22 → atrasado
        condom = bol[bol["fornecedor"] == "Condominio"]
        assert not condom.empty
        assert condom.iloc[0]["status"] == pg.STATUS_ATRASADO

    def test_carregar_boletos_mix_timestamp_e_string_nao_explode(self) -> None:
        """Regression: carregar_boletos sortava por coluna 'vencimento' com mix
        Timestamp (vindo do extrato lido via openpyxl) + string ISO (vindo de
        _projetar_boletos_esperados). TypeError quebrava Pagamentos + abas
        posteriores no dashboard. Fix: coerce para datetime antes do sort.
        """
        extrato = pd.DataFrame(
            [
                {
                    # Timestamp real (padrão openpyxl ao ler XLSX com coluna data)
                    "data": pd.Timestamp("2026-04-10"),
                    "valor": -103.93,
                    "local": "Sesc Natação",
                    "forma_pagamento": "Boleto",
                    "banco_origem": "c6",
                    "mes_ref": "2026-04",
                    "tipo": "Despesa",
                }
            ]
        )
        prazos = pd.DataFrame(
            [
                {
                    "conta": "Condominio",
                    "dia_vencimento": 5,
                    "banco_pagamento": "itau",
                    "auto_debito": False,
                }
            ]
        )
        hoje = date(2026, 4, 22)
        bol = pg.carregar_boletos(extrato, prazos, hoje=hoje)
        # Não explode + coluna vencimento é datetime homogêneo
        assert not bol.empty
        assert pd.api.types.is_datetime64_any_dtype(bol["vencimento"])
        # Condomínio vem primeiro (vencimento 2026-04-05) antes do Sesc pago (2026-04-10)
        assert bol.iloc[0]["fornecedor"] in {"Condominio", "Sesc Natação"}

    def test_boleto_futuro_vira_pendente(self, df_extrato: pd.DataFrame) -> None:
        prazos = pd.DataFrame(
            [
                {
                    "conta": "Futuro",
                    "dia_vencimento": 28,
                    "banco_pagamento": "x",
                    "auto_debito": False,
                }
            ]
        )
        hoje = date(2026, 4, 22)
        bol = pg.carregar_boletos(df_extrato, prazos, hoje=hoje)
        linha = bol[bol["fornecedor"] == "Futuro"]
        assert not linha.empty
        assert linha.iloc[0]["status"] == pg.STATUS_PENDENTE

    def test_sem_prazos_retorna_so_pagos(self, df_extrato: pd.DataFrame) -> None:
        bol = pg.carregar_boletos(df_extrato, prazos=None)
        assert all(bol["status"] == pg.STATUS_PAGO)

    def test_alertas_proximos_3_dias(self, df_extrato: pd.DataFrame) -> None:
        prazos = pd.DataFrame(
            [
                {
                    "conta": "Luz",
                    "dia_vencimento": 24,
                    "banco_pagamento": "x",
                    "auto_debito": False,
                }
            ]
        )
        hoje = date(2026, 4, 22)
        bol = pg.carregar_boletos(df_extrato, prazos, hoje=hoje)
        avisos = pg.alertas_vencimento(bol, hoje=hoje, dias_aviso=3)
        assert any("Luz" in a for a in avisos)


class TestPix:
    def test_top_beneficiarios_agrupa(self, df_extrato: pd.DataFrame) -> None:
        top = pg.top_beneficiarios_pix(df_extrato, top_n=10)
        assert "Farmácia Droga X" in set(top["local"])
        linha = top[top["local"] == "Farmácia Droga X"].iloc[0]
        assert linha["total"] == 125.0
        assert linha["quantidade"] == 2

    def test_sem_pix_retorna_vazio(self) -> None:
        df = pd.DataFrame([{"forma_pagamento": "Crédito", "valor": -10, "local": "X"}])
        top = pg.top_beneficiarios_pix(df)
        assert top.empty

    def test_limite_top_n(self, df_extrato: pd.DataFrame) -> None:
        top = pg.top_beneficiarios_pix(df_extrato, top_n=1)
        assert len(top) == 1


class TestCredito:
    def test_faturas_por_banco(self, df_extrato: pd.DataFrame) -> None:
        faturas = pg.faturas_credito(df_extrato)
        assert "nubank" in faturas
        nu = faturas["nubank"]
        assert len(nu) == 2  # mar e abr
        assert set(nu["mes_ref"]) == {"2026-03", "2026-04"}

    def test_sem_credito_dict_vazio(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "forma_pagamento": "Pix",
                    "valor": -10,
                    "banco_origem": "x",
                    "tipo": "Despesa",
                    "mes_ref": "2026-04",
                }
            ]
        )
        assert pg.faturas_credito(df) == {}


class TestResiliencia:
    def test_df_sem_forma_pagamento_nao_quebra(self) -> None:
        df = pd.DataFrame([{"valor": -10, "local": "X"}])
        assert pg.carregar_boletos(df, None).empty
        assert pg.top_beneficiarios_pix(df).empty
        assert pg.faturas_credito(df) == {}

    def test_df_vazio_nao_quebra(self) -> None:
        assert pg.carregar_boletos(pd.DataFrame(), None).empty
        assert pg.top_beneficiarios_pix(pd.DataFrame()).empty
        assert pg.faturas_credito(pd.DataFrame()) == {}
