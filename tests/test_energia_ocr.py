"""Testes dedicados de ExtratorEnergiaOCR (Sprint F 2026-04-23).

Cobre: função pura '_extrair_dados_ocr' (parse de texto OCR para lista de
dicts), corner cases (múltiplos meses, Kwh com variações de case), entrada
inválida (texto vazio, sem padrão de mês/valor), e o fluxo completo com
MOCK de 'pytesseract.image_to_string' (evita rodar OCR real).

Armadilha CLAUDE.md #10: Tesseract OCR para energia = valores R$ 100%
precisos, consumo kWh 67% (layout do app confunde). Fixture sintética
fornece texto com consumo/valor bem separados para garantir parse.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.extractors.energia_ocr import (
    ExtratorEnergiaOCR,
    _extrair_dados_ocr,
    _tentar_ocr,
)

FIXTURE_MOCK = (
    Path(__file__).parent / "fixtures" / "bancos" / "energia_ocr" / "sample_mock_output.txt"
)


class TestExtrairDadosOCR:
    def test_3_registros_parseados_do_mock(self) -> None:
        texto = FIXTURE_MOCK.read_text(encoding="utf-8")
        resultados = _extrair_dados_ocr(texto)

        assert len(resultados) == 3

    def test_campos_obrigatorios_presentes(self) -> None:
        texto = FIXTURE_MOCK.read_text(encoding="utf-8")
        resultados = _extrair_dados_ocr(texto)

        for r in resultados:
            assert "mes" in r
            assert "ano" in r
            assert "consumo_kwh" in r
            assert "valor" in r

    def test_valores_convertidos_para_float(self) -> None:
        texto = FIXTURE_MOCK.read_text(encoding="utf-8")
        resultados = _extrair_dados_ocr(texto)

        assert resultados[0]["valor"] == 289.45
        assert resultados[1]["valor"] == 256.30
        assert resultados[2]["valor"] == 178.90

    def test_consumo_kwh_como_int(self) -> None:
        texto = FIXTURE_MOCK.read_text(encoding="utf-8")
        resultados = _extrair_dados_ocr(texto)

        assert resultados[0]["consumo_kwh"] == 320
        assert resultados[1]["consumo_kwh"] == 285

    def test_mes_e_ano_como_int(self) -> None:
        texto = FIXTURE_MOCK.read_text(encoding="utf-8")
        resultados = _extrair_dados_ocr(texto)

        for r in resultados:
            assert isinstance(r["mes"], int)
            assert isinstance(r["ano"], int)
            assert 1 <= r["mes"] <= 12


class TestCornerCases:
    def test_kwh_minusculo_tambem_e_reconhecido(self) -> None:
        texto = "Mês\n01/2026\nConsumo\n150 kwh\nR$ 120,00"
        resultados = _extrair_dados_ocr(texto)
        assert len(resultados) == 1
        assert resultados[0]["consumo_kwh"] == 150

    def test_valor_sem_milhares(self) -> None:
        texto = "Mês\n05/2026\nConsumo\n100 Kwh\nR$ 89,99"
        resultados = _extrair_dados_ocr(texto)
        assert len(resultados) == 1
        assert resultados[0]["valor"] == 89.99

    def test_registro_sem_consumo_default_zero(self) -> None:
        """Padrão sem Kwh válido -> consumo=0 (não descarta registro)."""
        texto = "Mês\n07/2026\nR$ 200,00"
        resultados = _extrair_dados_ocr(texto)
        assert len(resultados) == 1
        assert resultados[0]["consumo_kwh"] == 0
        assert resultados[0]["valor"] == 200.00


class TestEntradaInvalida:
    def test_texto_vazio_retorna_lista_vazia(self) -> None:
        assert _extrair_dados_ocr("") == []

    def test_texto_sem_padrao_mes_valor(self) -> None:
        texto = "Alguma linha aleatória\nSem mês nem valor\n"
        assert _extrair_dados_ocr(texto) == []

    def test_pode_processar_rejeita_extensao_nao_imagem(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "conta_luz.pdf"
        arquivo.write_bytes(b"dummy")
        extrator = ExtratorEnergiaOCR(arquivo)

        assert extrator.pode_processar(arquivo) is False


class TestFluxoComMock:
    """Fluxo completo do extrator com pytesseract mockado."""

    def test_extrator_usa_mock_de_ocr(self, tmp_path: Path) -> None:
        """Substitui '_tentar_ocr' no módulo para retornar texto controlado."""
        arquivo = tmp_path / "neoenergia_sintetica.png"
        arquivo.write_bytes(b"fake-png-content")

        texto_mock = FIXTURE_MOCK.read_text(encoding="utf-8")

        with patch("src.extractors.energia_ocr._tentar_ocr", return_value=texto_mock):
            extrator = ExtratorEnergiaOCR(arquivo)
            transacoes = extrator.extrair()

        assert len(transacoes) == 3
        for tx in transacoes:
            assert tx.banco_origem == "Neoenergia"
            assert tx.forma_pagamento == "Boleto"
            assert tx.pessoa == "Casal"
            assert tx.tipo == "Despesa"

    def test_extrator_com_ocr_none_retorna_lista_vazia(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "neoenergia_ruim.png"
        arquivo.write_bytes(b"fake-png-ruim")

        with patch("src.extractors.energia_ocr._tentar_ocr", return_value=None):
            transacoes = ExtratorEnergiaOCR(arquivo).extrair()

        assert transacoes == []

    def test_pode_processar_por_nome_energia_na_pasta(self, tmp_path: Path) -> None:
        """Nome com pista de 'energia' dispensa tentar OCR."""
        arquivo = tmp_path / "energia_sintetica.png"
        arquivo.write_bytes(b"fake")

        extrator = ExtratorEnergiaOCR(arquivo)
        assert extrator.pode_processar(arquivo) is True


def test_tentar_ocr_retorna_none_em_arquivo_inexistente(tmp_path: Path) -> None:
    """_tentar_ocr tem try/except genérico -- erro de I/O vira None."""
    fantasma = tmp_path / "nao_existe.png"
    resultado = _tentar_ocr(fantasma)
    assert resultado is None


@pytest.mark.parametrize(
    "texto,qtd_esperada",
    [
        ("Mês\n01/2026\nConsumo\n100 Kwh\nR$ 50,00", 1),
        (
            "Mês\n01/2026\nConsumo\n100 Kwh\nR$ 50,00\n\nMês\n02/2026\nConsumo\n200 Kwh\nR$ 100,00",
            2,
        ),
        ("Sem padrão nenhum", 0),
    ],
)
def test_parametros_parse_variacoes(texto: str, qtd_esperada: int) -> None:
    assert len(_extrair_dados_ocr(texto)) == qtd_esperada


# "A energia não se cria nem se destrói, apenas se transforma." -- Lavoisier
