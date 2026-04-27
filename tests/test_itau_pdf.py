"""Testes dedicados de ExtratorItauPDF (Sprint F 2026-04-23).

Cobre: parse via método '_extrair_de_texto' usando texto-proxy que
emula output do pdfplumber, corner cases (SALDO DO DIA ignorado, DARF
como Imposto, REND PAGO como Receita), entrada inválida (linha sem
valor, PDF sem senha válida).

Armadilha CLAUDE.md #2: Itaú PDF é protegido -- senha em senhas.yaml +
pdfplumber (NUNCA PyPDF2). Não usamos PDF binário; texto-proxy evita
dependência de PDF real (LGPD).

Contrato VALIDATOR_BRIEF: itau_pdf._parse_valor_br propositadamente
levanta ValueError em entrada inválida (em contraste com helper
central 'src/utils/parse_br.py'). Testamos esse contrato.
"""

from datetime import date
from pathlib import Path

import pytest

from src.extractors.itau_pdf import ExtratorItauPDF

FIXTURE_TEXTO = Path(__file__).parent / "fixtures" / "bancos" / "itau_pdf" / "sample_texto.txt"


def _criar_arquivo_dummy(tmp_path: Path) -> Path:
    arquivo = tmp_path / "itau_sintetico.pdf"
    arquivo.write_bytes(b"dummy-pdf-content")
    return arquivo


class TestParseBasico:
    def test_5_transacoes_parseadas_fixture_texto(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        assert len(transacoes) == 5

    def test_datas_sao_objetos_date(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        assert transacoes[0].data == date(2026, 2, 5)
        assert transacoes[-1].data == date(2026, 2, 25)

    def test_banco_origem_itau_e_pessoa_andre(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        for tx in transacoes:
            assert tx.banco_origem == "Itaú"
            assert tx.pessoa == "André"


class TestCornerCases:
    def test_saldo_do_dia_e_ignorado(self, tmp_path: Path) -> None:
        """Linhas contendo 'SALDO DO DIA' não são transações."""
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        for tx in transacoes:
            assert "SALDO" not in tx.descricao.upper()

    def test_darf_reconhecido_como_imposto(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        darf = [t for t in transacoes if "DARF" in t.descricao]
        assert len(darf) == 1
        assert darf[0].tipo == "Imposto"

    def test_rend_pago_aplic_vira_receita(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        rend = [t for t in transacoes if "REND PAGO" in t.descricao]
        assert len(rend) == 1
        assert rend[0].tipo == "Receita"

    def test_salario_vira_receita(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        sal = [t for t in transacoes if "SALARIO" in t.descricao]
        assert len(sal) == 1
        assert sal[0].tipo == "Receita"
        assert sal[0].valor == 5000.00

    def test_pix_enviado_com_valor_negativo_e_despesa(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        pix = [t for t in transacoes if "PIX" in t.descricao]
        assert len(pix) == 1
        assert pix[0].tipo == "Despesa"
        assert pix[0].valor == -250.00
        assert pix[0].forma_pagamento == "Pix"


class TestEntradaInvalida:
    def test_texto_vazio_retorna_lista_vazia(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        transacoes = extrator._extrair_de_texto("", arquivo)

        assert transacoes == []

    def test_texto_sem_lancamento_valido_retorna_lista_vazia(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorItauPDF(arquivo)

        texto = "Alguma linha qualquer sem padrão de data\nOutra linha\n"
        transacoes = extrator._extrair_de_texto(texto, arquivo)

        assert transacoes == []

    def test_parse_valor_br_lanca_value_error_em_entrada_invalida(self) -> None:
        """Contrato documentado no BRIEF: Itaú propositadamente levanta
        ValueError para o caller tratar via try/except -- fallback
        silencioso contaminaria dados."""
        with pytest.raises(ValueError):
            ExtratorItauPDF._parse_valor_br("nao-e-numero")

    def test_pode_processar_exige_itau_no_caminho(self) -> None:
        """Path sem 'itau' e extensão PDF não deve casar. Usa path
        fabricado (não tmp_path) para evitar colisão com nome pytest."""
        arquivo = Path("/var/tmp/banco_generico/extrato.pdf")
        extrator = ExtratorItauPDF(arquivo)

        assert extrator.pode_processar(arquivo) is False


def test_parse_valor_br_converte_formato_brasileiro() -> None:
    """Contrato canônico: 1.234,56 -> 1234.56."""
    assert ExtratorItauPDF._parse_valor_br("1.234,56") == 1234.56
    assert ExtratorItauPDF._parse_valor_br("-250,00") == -250.00
    assert ExtratorItauPDF._parse_valor_br("0,99") == 0.99


# "O bom senso é a coisa mais bem partilhada do mundo." -- Descartes
