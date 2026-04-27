"""Testes dedicados de ExtratorSantanderPDF (Sprint F 2026-04-23).

Cobre: parse via '_extrair_transacoes' com texto-proxy, corner cases
(layout multi-coluna com parcela DD/MM, pagamento de fatura vira TI,
anuidade zerada ignorada, cashback/estorno preserva sinal), entrada
inválida (sem seção Detalhamento, valor corrompido).

Armadilha CLAUDE.md #12: Santander Black Way = cartão Elite Visa 7342.
Fixture usa máscara '4220 XXXX XXXX 7342' só para confirmar detecção
de cabeçalho (o extrator não depende dos dígitos).

Contrato VALIDATOR_BRIEF: santander_pdf._parse_valor_br tem lógica de
sinal negativo específica (strip '-' + inversão após float). Testamos
explicitamente esse comportamento (distinguido do itau_pdf).
"""

from datetime import date
from pathlib import Path

import pytest

from src.extractors.santander_pdf import ExtratorSantanderPDF

FIXTURE_TEXTO = Path(__file__).parent / "fixtures" / "bancos" / "santander_pdf" / "sample_texto.txt"


def _criar_arquivo_dummy(tmp_path: Path) -> Path:
    arquivo = tmp_path / "fatura_santander_sintetica.pdf"
    arquivo.write_bytes(b"dummy-pdf")
    return arquivo


class TestParseBasico:
    def test_5_transacoes_parseadas_da_secao_detalhamento(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorSantanderPDF(arquivo)
        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")

        transacoes = extrator._extrair_transacoes(texto, arquivo, vencimento=date(2026, 3, 10))

        # 5 itens: mercado, loja parcela, international, pagamento, farmácia cashback
        # (anuidade 0,00 ignorada)
        assert len(transacoes) == 5

    def test_banco_origem_santander_e_forma_credito(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorSantanderPDF(arquivo)
        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")

        transacoes = extrator._extrair_transacoes(texto, arquivo, vencimento=date(2026, 3, 10))

        for tx in transacoes:
            assert tx.banco_origem == "Santander"
            assert tx.forma_pagamento == "Crédito"

    def test_datas_inferidas_por_vencimento(self, tmp_path: Path) -> None:
        """Vencimento 10/03/2026 -> transações 02/XX casam com ano 2026."""
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorSantanderPDF(arquivo)
        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")

        transacoes = extrator._extrair_transacoes(texto, arquivo, vencimento=date(2026, 3, 10))

        for tx in transacoes:
            assert tx.data.year == 2026
            assert tx.data.month == 2


class TestCornerCases:
    def test_pagamento_de_fatura_vira_transferencia_interna_negativa(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorSantanderPDF(arquivo)
        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")

        transacoes = extrator._extrair_transacoes(texto, arquivo, vencimento=date(2026, 3, 10))

        pgto = [t for t in transacoes if "PAGAMENTO DE FATURA" in t.descricao]
        assert len(pgto) == 1
        assert pgto[0].tipo == "Transferência Interna"
        assert pgto[0].valor == -1000.00

    def test_compras_sao_despesa_com_valor_positivo(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorSantanderPDF(arquivo)
        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")

        transacoes = extrator._extrair_transacoes(texto, arquivo, vencimento=date(2026, 3, 10))

        compras = [t for t in transacoes if t.tipo == "Despesa"]
        for c in compras:
            assert c.valor > 0.0

    def test_anuidade_com_valor_zero_e_ignorada(self, tmp_path: Path) -> None:
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorSantanderPDF(arquivo)
        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")

        transacoes = extrator._extrair_transacoes(texto, arquivo, vencimento=date(2026, 3, 10))

        assert not any("ANUIDADE" in t.descricao.upper() for t in transacoes)

    def test_parcela_ddmm_reconhecida(self, tmp_path: Path) -> None:
        """Layout parcela: DD/MM DESCRIÇÃO DD/MM VALOR -- duas datas na mesma linha."""
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorSantanderPDF(arquivo)
        texto = FIXTURE_TEXTO.read_text(encoding="utf-8")

        transacoes = extrator._extrair_transacoes(texto, arquivo, vencimento=date(2026, 3, 10))

        parcela = [t for t in transacoes if "LOJA EXEMPLAR" in t.descricao]
        assert len(parcela) == 1
        assert parcela[0].valor == 120.00


class TestEntradaInvalida:
    def test_texto_sem_detalhamento_retorna_lista_vazia(self, tmp_path: Path) -> None:
        """_extrair_transacoes itera mas não encontra lançamentos se faltar seção."""
        arquivo = _criar_arquivo_dummy(tmp_path)
        extrator = ExtratorSantanderPDF(arquivo)
        texto = "Resumo da Fatura\nSaldo Anterior 0,00\nValor total 100,00\n"

        transacoes = extrator._extrair_transacoes(texto, arquivo, vencimento=date(2026, 3, 10))

        assert transacoes == []

    def test_pode_processar_rejeita_arquivo_sem_santander_no_caminho(self) -> None:
        arquivo = Path("/var/tmp/banco_outro/fatura.pdf")
        extrator = ExtratorSantanderPDF(arquivo)

        assert extrator.pode_processar(arquivo) is False

    def test_pode_processar_rejeita_arquivo_nao_pdf(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "santander_cc.csv"
        arquivo.write_bytes(b"dummy")
        extrator = ExtratorSantanderPDF(arquivo)

        assert extrator.pode_processar(arquivo) is False


class TestContratoParseValorBR:
    """BRIEF: Santander tem lógica de sinal negativo específica (strip
    '-' + inversão após float). Testamos para que refactor futuro não
    quebre."""

    def test_valor_simples_positivo(self) -> None:
        assert ExtratorSantanderPDF._parse_valor_br("1.234,56") == 1234.56

    def test_valor_com_sinal_negativo_preserva(self) -> None:
        assert ExtratorSantanderPDF._parse_valor_br("-50,00") == -50.00

    def test_valor_com_espaco_e_strip(self) -> None:
        assert ExtratorSantanderPDF._parse_valor_br("   85,90   ") == 85.90

    def test_entrada_totalmente_invalida_levanta(self) -> None:
        with pytest.raises(ValueError):
            ExtratorSantanderPDF._parse_valor_br("sem-numero")


# "A liberdade é o direito de fazer tudo o que as leis permitem." -- Montesquieu
