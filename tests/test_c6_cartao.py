"""Testes dedicados de ExtratorC6Cartao (Sprint F 2026-04-23).

Cobre: parse de faturas XLS do cartão C6 via MOCK do workbook xlrd
(decriptação real exige 'xlwt' indisponível no venv). Estratégia:
'unittest.mock.patch' substitui '_abrir_workbook' retornando um
MagicMock com interface xlrd.Book (sheet_by_index -> mock Sheet).

Cobertura: parse básico (3 transações), corner cases (pagamento de fatura
ignorado, parcela concatenada à descrição, conversão USD->BRL), entrada
inválida (xls sem fatura não processável, linhas curtas descartadas).

Armadilha CLAUDE.md #1: XLS C6 é encriptado -- decrypt real exige senha
em mappings/senhas.yaml + msoffcrypto-tool. Mock contorna o problema.
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.c6_cartao import ExtratorC6Cartao


def _mock_book(linhas: list[list]) -> MagicMock:
    """Fabrica mock xlrd.Book com 1 sheet contendo as linhas informadas."""
    sheet = MagicMock()
    sheet.nrows = len(linhas)
    sheet.row_values = lambda idx: linhas[idx]

    book = MagicMock()
    book.sheet_by_index = lambda idx: sheet
    return book


def _linhas_fixture_basica() -> list[list]:
    """Layout: linha 0 cab1, linha 1 cab colunas, linha 2+ dados."""
    return [
        ["cabecalho banco"],
        [
            "Data de compra",
            "Nome no cartao",
            "Final do Cartao",
            "Categoria",
            "Descricao",
            "Parcela",
            "Valor USD",
            "Cotacao BRL",
            "Valor BRL",
        ],
        # Compra simples
        [
            "05/02/2026",
            "ANDRE BATISTA",
            "1234",
            "Alimentacao",
            "MERCADO SINTETICO",
            "Única",
            0.0,
            0.0,
            85.90,
        ],
        # Parcela 2/6 -- descrição deve concatenar
        ["10/02/2026", "ANDRE BATISTA", "1234", "Lazer", "LOJA EXEMPLAR", "2/6", 0.0, 0.0, 120.00],
        # Compra em USD (sem BRL direto) -- calcula
        [
            "15/02/2026",
            "ANDRE BATISTA",
            "1234",
            "Servicos",
            "INTERNATIONAL STORE",
            "Única",
            25.00,
            5.20,
            0.0,
        ],
        # Pagamento de fatura -- deve ser IGNORADO
        [
            "20/02/2026",
            "ANDRE BATISTA",
            "1234",
            "Outros",
            "Pag Fatura Anterior",
            "Única",
            0.0,
            0.0,
            500.00,
        ],
    ]


def _criar_arquivo_dummy_c6_cartao(tmp_path: Path) -> Path:
    """pode_processar exige 'c6_cartao' no caminho ou 'fatura-cpf' no nome."""
    pasta = tmp_path / "andre" / "c6_cartao"
    pasta.mkdir(parents=True)
    arquivo = pasta / "fatura_sintetica.xls"
    arquivo.write_bytes(b"dummy-xls-sintetico-mockado")
    return arquivo


class TestParseBasico:
    def test_4_transacoes_incluindo_espelho_virtual(self, tmp_path: Path) -> None:
        """Sprint 82b: pagamento de fatura vira linha virtual TI em vez de ser ignorado."""
        arquivo = _criar_arquivo_dummy_c6_cartao(tmp_path)
        extrator = ExtratorC6Cartao(arquivo)

        with patch.object(
            ExtratorC6Cartao, "_abrir_workbook", return_value=_mock_book(_linhas_fixture_basica())
        ):
            transacoes = extrator.extrair()

        assert len(transacoes) == 4, "Pag Fatura vira espelho virtual (Sprint 82b)"
        virtuais = [t for t in transacoes if getattr(t, "_virtual", False)]
        assert len(virtuais) == 1
        assert virtuais[0].tipo == "Transferência Interna"

    def test_datas_convertidas_para_date_objeto(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy_c6_cartao(tmp_path)
        extrator = ExtratorC6Cartao(arquivo)

        with patch.object(
            ExtratorC6Cartao, "_abrir_workbook", return_value=_mock_book(_linhas_fixture_basica())
        ):
            transacoes = extrator.extrair()

        assert transacoes[0].data == date(2026, 2, 5)
        assert transacoes[1].data == date(2026, 2, 10)
        assert transacoes[2].data == date(2026, 2, 15)

    def test_banco_origem_e_forma_credito(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy_c6_cartao(tmp_path)
        extrator = ExtratorC6Cartao(arquivo)

        with patch.object(
            ExtratorC6Cartao, "_abrir_workbook", return_value=_mock_book(_linhas_fixture_basica())
        ):
            transacoes = extrator.extrair()

        for tx in transacoes:
            assert tx.banco_origem == "C6"
            assert tx.forma_pagamento == "Crédito"
        # Compras são Despesa; pagamento de fatura vira espelho virtual TI (Sprint 82b)
        compras = [t for t in transacoes if not getattr(t, "_virtual", False)]
        espelhos = [t for t in transacoes if getattr(t, "_virtual", False)]
        assert all(t.tipo == "Despesa" for t in compras)
        assert all(t.tipo == "Transferência Interna" for t in espelhos)


class TestCornerCases:
    def test_parcela_diferente_de_unica_e_concatenada_na_descricao(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy_c6_cartao(tmp_path)
        extrator = ExtratorC6Cartao(arquivo)

        with patch.object(
            ExtratorC6Cartao, "_abrir_workbook", return_value=_mock_book(_linhas_fixture_basica())
        ):
            transacoes = extrator.extrair()

        parcela = [t for t in transacoes if "LOJA EXEMPLAR" in t.descricao]
        assert len(parcela) == 1
        assert "2/6" in parcela[0].descricao

    def test_usd_convertido_via_cotacao_quando_brl_zero(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy_c6_cartao(tmp_path)
        extrator = ExtratorC6Cartao(arquivo)

        with patch.object(
            ExtratorC6Cartao, "_abrir_workbook", return_value=_mock_book(_linhas_fixture_basica())
        ):
            transacoes = extrator.extrair()

        internacional = [t for t in transacoes if "INTERNATIONAL" in t.descricao]
        assert len(internacional) == 1
        # 25.00 USD * 5.20 = 130.00 BRL
        assert internacional[0].valor == pytest.approx(130.00, abs=0.01)

    def test_pagamento_de_fatura_vira_espelho_virtual(self, tmp_path: Path) -> None:
        """Sprint 82b: linha 'Pag Fatura Anterior' deixa de ser descartada.

        Emitida como Transação com _virtual=True, tipo=Transferência Interna,
        valor absoluto preservado. Contraparte do débito em conta-corrente.
        """
        arquivo = _criar_arquivo_dummy_c6_cartao(tmp_path)
        extrator = ExtratorC6Cartao(arquivo)

        with patch.object(
            ExtratorC6Cartao, "_abrir_workbook", return_value=_mock_book(_linhas_fixture_basica())
        ):
            transacoes = extrator.extrair()

        espelhos = [t for t in transacoes if "Pag Fatura" in t.descricao]
        assert len(espelhos) == 1
        assert espelhos[0]._virtual is True
        assert espelhos[0].tipo == "Transferência Interna"
        assert espelhos[0].valor == 500.00
        assert espelhos[0].data == date(2026, 2, 20)


class TestEntradaInvalida:
    def test_arquivo_sem_c6cartao_no_caminho_e_rejeitado(self, tmp_path: Path) -> None:
        """Path sem a substring 'c6_cartao' e sem 'fatura-cpf' no nome
        e sem extensão .xls não deve ser aceito (usa .csv para evitar
        colisão com nome do tmp_path que pode conter 'c6_cartao')."""
        fora = tmp_path / "alguma_coisa.csv"
        fora.write_bytes(b"dummy")
        extrator = ExtratorC6Cartao(fora)

        assert extrator.pode_processar(fora) is False

    def test_linha_com_menos_de_9_colunas_e_ignorada(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy_c6_cartao(tmp_path)
        extrator = ExtratorC6Cartao(arquivo)

        linhas_curtas = [
            ["cabecalho"],
            ["cab", "col2"],
            ["linha", "com", "poucas", "colunas"],
        ]

        with patch.object(
            ExtratorC6Cartao, "_abrir_workbook", return_value=_mock_book(linhas_curtas)
        ):
            transacoes = extrator.extrair()

        assert transacoes == []

    def test_workbook_none_retorna_lista_vazia(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy_c6_cartao(tmp_path)
        extrator = ExtratorC6Cartao(arquivo)

        with patch.object(ExtratorC6Cartao, "_abrir_workbook", return_value=None):
            transacoes = extrator.extrair()

        assert transacoes == []


def test_fatura_cpf_no_nome_ativa_pode_processar(tmp_path: Path) -> None:
    """Nome com 'fatura-cpf' cobre caso em que pasta não tem 'c6_cartao'."""
    arquivo = tmp_path / "fatura-cpf-sintetico-2026-02.xls"
    arquivo.write_bytes(b"dummy")
    extrator = ExtratorC6Cartao(arquivo)

    assert extrator.pode_processar(arquivo) is True


# "A ciência do dinheiro se aprende sofrendo." -- La Rochefoucauld
