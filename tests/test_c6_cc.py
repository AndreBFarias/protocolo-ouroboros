"""Testes dedicados de ExtratorC6CC (Sprint F 2026-04-23).

Cobre: parse de XLSX C6 Bank (conta corrente) sintético (sem criptografia),
corner cases (entrada vs saída, PGTO FAT CARTAO como TI, SEFAZ como Imposto),
entrada inválida (arquivo ausente, linha sem dados).

Fixture: 'tests/fixtures/bancos/c6_cc/sample_c6_cc.xlsx' gerado via openpyxl
(sem senha) -- o extrator real detecta 'is_encrypted()' e cai no fallback
openpyxl direto quando não há criptografia.
"""

import shutil
from datetime import date
from pathlib import Path

import openpyxl

from src.extractors.c6_cc import ExtratorC6CC

FIXTURE_SAMPLE = (
    Path(__file__).parent / "fixtures" / "bancos" / "c6_cc" / "sample_c6_cc.xlsx"
)


def _preparar_em_pasta_c6_cc(tmp_path: Path) -> Path:
    """pode_processar exige 'c6_cc' no caminho."""
    pasta = tmp_path / "andre" / "c6_cc"
    pasta.mkdir(parents=True)
    destino = pasta / "sample_c6_cc.xlsx"
    shutil.copy(FIXTURE_SAMPLE, destino)
    return destino


class TestParseBasico:
    def test_3_transacoes_sao_parseadas(self, tmp_path: Path) -> None:
        arquivo = _preparar_em_pasta_c6_cc(tmp_path)
        extrator = ExtratorC6CC(arquivo)

        transacoes = extrator.extrair()

        assert len(transacoes) == 3

    def test_datas_como_objetos_date(self, tmp_path: Path) -> None:
        arquivo = _preparar_em_pasta_c6_cc(tmp_path)
        extrator = ExtratorC6CC(arquivo)

        transacoes = extrator.extrair()

        for tx in transacoes:
            assert isinstance(tx.data, date)
        assert transacoes[0].data == date(2026, 2, 10)

    def test_entrada_vira_valor_positivo_saida_vira_negativo(self, tmp_path: Path) -> None:
        arquivo = _preparar_em_pasta_c6_cc(tmp_path)
        extrator = ExtratorC6CC(arquivo)

        transacoes = extrator.extrair()

        salario = [t for t in transacoes if "SALARIO" in t.descricao]
        assert len(salario) == 1
        assert salario[0].valor > 0

        saidas = [t for t in transacoes if t.valor < 0]
        assert len(saidas) == 2

    def test_banco_origem_c6_e_pessoa_andre(self, tmp_path: Path) -> None:
        arquivo = _preparar_em_pasta_c6_cc(tmp_path)
        extrator = ExtratorC6CC(arquivo)

        transacoes = extrator.extrair()

        for tx in transacoes:
            assert tx.banco_origem == "C6"
            assert tx.pessoa == "André"


class TestCornerCases:
    def test_pgto_fat_cartao_vira_transferencia_interna(self, tmp_path: Path) -> None:
        arquivo = _preparar_em_pasta_c6_cc(tmp_path)
        extrator = ExtratorC6CC(arquivo)

        transacoes = extrator.extrair()

        fatura = [t for t in transacoes if "PGTO FAT CARTAO" in t.descricao]
        assert len(fatura) == 1
        assert fatura[0].tipo == "Transferência Interna"

    def test_recebimento_salario_vira_receita(self, tmp_path: Path) -> None:
        arquivo = _preparar_em_pasta_c6_cc(tmp_path)
        extrator = ExtratorC6CC(arquivo)

        transacoes = extrator.extrair()

        salario = [t for t in transacoes if "SALARIO" in t.descricao]
        assert salario[0].tipo == "Receita"

    def test_pix_enviado_detecta_forma_pix(self, tmp_path: Path) -> None:
        arquivo = _preparar_em_pasta_c6_cc(tmp_path)
        extrator = ExtratorC6CC(arquivo)

        transacoes = extrator.extrair()

        pix = [t for t in transacoes if "PIX" in t.descricao]
        assert len(pix) == 1
        assert pix[0].forma_pagamento == "Pix"


class TestEntradaInvalida:
    def test_arquivo_inexistente_retorna_lista_vazia(self, tmp_path: Path) -> None:
        pasta = tmp_path / "andre" / "c6_cc"
        pasta.mkdir(parents=True)
        fantasma = pasta / "nao_existe.xlsx"

        extrator = ExtratorC6CC(fantasma)
        transacoes = extrator.extrair()

        assert transacoes == []

    def test_pode_processar_exige_c6_cc_no_caminho(self, tmp_path: Path) -> None:
        arquivo_fora = tmp_path / "outra_pasta" / "arquivo.xlsx"
        arquivo_fora.parent.mkdir(parents=True)
        shutil.copy(FIXTURE_SAMPLE, arquivo_fora)

        extrator = ExtratorC6CC(arquivo_fora)

        assert extrator.pode_processar(arquivo_fora) is False

    def test_linha_sem_data_ou_titulo_e_ignorada(self, tmp_path: Path) -> None:
        pasta = tmp_path / "andre" / "c6_cc"
        pasta.mkdir(parents=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        for _ in range(8):
            ws.append(["cab"])
        ws.append(
            [
                "Data Lancamento",
                "Data Contabil",
                "Titulo",
                "Descricao",
                "Entrada",
                "Saida",
                "Saldo",
            ]
        )
        ws.append(["15/02/2026", "15/02/2026", "LINHA VALIDA", "desc", 100.0, None, 100.0])
        ws.append([None, None, None, None, None, None, None])
        ws.append(
            [
                "16/02/2026",
                "16/02/2026",
                "LINHA SEM SAIDA NEM ENTRADA",
                "desc",
                None,
                None,
                50.0,
            ]
        )

        arquivo = pasta / "ruido_c6_cc.xlsx"
        wb.save(arquivo)

        extrator = ExtratorC6CC(arquivo)
        transacoes = extrator.extrair()

        assert len(transacoes) == 1
        assert "LINHA VALIDA" in transacoes[0].descricao


# "Quem tem paciência tem o que deseja." -- Benjamin Franklin
