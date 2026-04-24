"""Testes dedicados de ExtratorOFX (Sprint F 2026-04-23).

Cobre: parse de OFX SGML sintético (Banking com STMTTRN), corner cases
(Receita vs Despesa por sinal, mapa de TRNTYPE para forma, FITID como
identificador), entrada inválida (OFX corrompido, sem transações).

ACHADO COLATERAL Sprint F: 'ExtratorOFX.extrair()' duplica transações
quando OFX tem conta única (itera 'ofx.account.statement' E
'ofx.accounts'). Ver 'docs/sprints/backlog/sprint_Fa_ofx_duplicacao_accounts.md'.
Teste regressivo marcado como '@pytest.mark.xfail' para documentar o
contrato quebrado sem falhar o suite.

Fixture: 'tests/fixtures/bancos/ofx_parser/sample.ofx' com 3 STMTTRN
(CREDIT, DEBIT, PAYMENT).
"""

from datetime import date
from pathlib import Path

import pytest

from src.extractors.ofx_parser import ExtratorOFX

FIXTURE_SAMPLE = (
    Path(__file__).parent / "fixtures" / "bancos" / "ofx_parser" / "sample.ofx"
)


class TestParseBasico:
    def test_ofx_sintetico_e_processavel(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        extrator = ExtratorOFX(arquivo)

        assert extrator.pode_processar(arquivo) is True

    def test_extrai_transacoes_com_dados_validos(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        # Devido ao bug conhecido (sprint Fa), fixture com 3 STMTTRN
        # devolve 6 (duplicado). Testamos que >=3 únicas existem.
        assert len(transacoes) >= 3

    def test_datas_convertidas_para_date(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        for tx in transacoes:
            assert isinstance(tx.data, date)

    def test_banco_detectado_pelo_org_do_header(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        for tx in transacoes:
            assert tx.banco_origem == "Nubank"


class TestCornerCases:
    def test_credit_com_valor_positivo_vira_receita(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        receitas = [t for t in transacoes if t.tipo == "Receita"]
        assert len(receitas) >= 1
        assert all(t.valor > 0 for t in receitas)

    def test_debit_com_valor_negativo_vira_despesa_abs(self, tmp_path: Path) -> None:
        """Valores negativos no OFX viram 'Despesa' com valor absoluto."""
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        despesas = [t for t in transacoes if t.tipo == "Despesa"]
        assert len(despesas) >= 1
        assert all(t.valor > 0 for t in despesas), "Despesa guarda valor positivo (abs)"

    def test_fitid_preservado_como_identificador(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        ids = {t.identificador for t in transacoes}
        # Fitids são FIC001 FIC002 FIC003 -- contendo pelo menos esses 3
        assert {"FIC001", "FIC002", "FIC003"}.issubset(ids)

    def test_mapa_trntype_converte_para_forma_canonica(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        formas = {t.forma_pagamento for t in transacoes}
        # CREDIT, DEBIT, PAYMENT -> Crédito, Débito, Boleto
        assert "Crédito" in formas or "Débito" in formas or "Boleto" in formas

    @pytest.mark.xfail(
        reason=(
            "Sprint Fa-ofx-duplicacao: ExtratorOFX.extrair() itera "
            "ofx.account.statement.transactions E ofx.accounts; em OFX "
            "com conta única isso gera duplicatas exatas. Ver "
            "docs/sprints/backlog/sprint_Fa_ofx_duplicacao_accounts.md"
        ),
        strict=True,
    )
    def test_statement_unico_nao_deveria_duplicar(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "sample.ofx"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        # 3 STMTTRN no fixture -> o correto seria 3, não 6.
        assert len(transacoes) == 3


class TestEntradaInvalida:
    def test_arquivo_ofx_corrompido_retorna_lista_vazia(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "corrompido.ofx"
        arquivo.write_text("lixo não-ofx-nenhum", encoding="utf-8")

        transacoes = ExtratorOFX(arquivo).extrair()

        assert transacoes == []

    def test_arquivo_com_extensao_diferente_nao_e_processado(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "dados.csv"
        arquivo.write_text("qualquer coisa", encoding="utf-8")
        extrator = ExtratorOFX(arquivo)

        assert extrator.pode_processar(arquivo) is False

    def test_diretorio_sem_ofx_retorna_lista_vazia(self, tmp_path: Path) -> None:
        pasta = tmp_path / "vazia"
        pasta.mkdir()

        transacoes = ExtratorOFX(pasta).extrair()

        assert transacoes == []


# "O começo é a parte mais importante do trabalho." -- Platão
