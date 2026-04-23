"""Testes do src.extractors.das_parcsn_pdf (P1.1 2026-04-23).

Cobre parse de DAS PARCSN sintético e rejeição de documentos não-DAS.
Origem: auditoria 2026-04-23 encontrou 47 DAS fisicamente presentes,
zero catalogados no grafo (ADR-20 tracking quebrado).
"""

from __future__ import annotations

from pathlib import Path

from src.extractors.das_parcsn_pdf import ExtratorDASPARCSNPDF

DAS_TEXTO_ANDRE = """Documento de Arrecadação
do Simples Nacional
CNPJ Razão Social
45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS
Período de Apuração Data de Vencimento Número do Documento Pagar este documento até
Fevereiro/2025 28/02/2025 07.18.25105.7231382-8
30/04/2025
Observações
DAS de PARCSN (Versão: 2.0.0)
Valor Total do Documento
Número do Parcelamento: 1
324,31
Parcela: 4/25
"""

DAS_TEXTO_OUTRO_CNPJ = """Documento de Arrecadação
do Simples Nacional
CNPJ Razão Social
99.999.999/0001-99 EMPRESA DESCONHECIDA
Período de Apuração Data de Vencimento Número do Documento Pagar este documento até
Janeiro/2025 31/01/2025 07.18.99999.9999999-0
28/02/2025
Valor Total do Documento
Número do Parcelamento: 1
100,00
Parcela: 1/12
"""

NAO_DAS_TEXTO = """Comprovante de Situação Cadastral no CPF
Ministério da Fazenda
Secretaria da Receita Federal do Brasil
No do CPF: 051.273.731-22
Nome: ANDRE DA SILVA BATISTA DE FARIAS
"""


class TestExtratorDASPARCSN:
    def test_extrai_campos_essenciais(self, tmp_path: Path) -> None:
        arq = tmp_path / "das.pdf"
        arq.write_bytes(b"x")
        ext = ExtratorDASPARCSNPDF(arq)
        result = ext.extrair_das(arq, texto_override=DAS_TEXTO_ANDRE)
        doc = result["documento"]

        assert doc["cnpj_emitente"] == "45.850.636/0001-60"
        assert doc["razao_social"] == "ANDRE DA SILVA BATISTA DE FARIAS"
        assert doc["total"] == 324.31
        assert doc["periodo_apuracao"] == "2025-02"
        assert doc["vencimento"] == "2025-04-30"
        assert doc["numero"] == "07.18.25105.7231382-8"
        assert doc["parcela_atual"] == 4
        assert doc["parcela_total"] == 25
        assert doc["tipo_documento"] == "das_parcsn_andre"

    def test_cnpj_diferente_nao_vira_andre(self, tmp_path: Path) -> None:
        arq = tmp_path / "das.pdf"
        arq.write_bytes(b"x")
        ext = ExtratorDASPARCSNPDF(arq)
        result = ext.extrair_das(arq, texto_override=DAS_TEXTO_OUTRO_CNPJ)
        assert result["documento"]["tipo_documento"] == "das_parcsn"
        assert result["documento"]["cnpj_emitente"] == "99.999.999/0001-99"

    def test_documento_nao_das_retorna_vazio(self, tmp_path: Path) -> None:
        arq = tmp_path / "comprovante.pdf"
        arq.write_bytes(b"x")
        ext = ExtratorDASPARCSNPDF(arq)
        result = ext.extrair_das(arq, texto_override=NAO_DAS_TEXTO)
        assert result["documento"] == {}
        assert result["_erro_extracao"] == "campos_insuficientes"

    def test_texto_muito_curto_retorna_vazio(self, tmp_path: Path) -> None:
        arq = tmp_path / "vazio.pdf"
        arq.write_bytes(b"x")
        ext = ExtratorDASPARCSNPDF(arq)
        result = ext.extrair_das(arq, texto_override="abc")
        assert result["_erro_extracao"] == "texto_vazio"

    def test_pode_processar_pasta_das_parcsn(self, tmp_path: Path) -> None:
        arq = tmp_path / "data" / "raw" / "casal" / "impostos" / "das_parcsn" / "x.pdf"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"x")
        ext = ExtratorDASPARCSNPDF(arq)
        assert ext.pode_processar(arq) is True

    def test_nao_processa_outras_pastas(self, tmp_path: Path) -> None:
        arq = tmp_path / "data" / "raw" / "andre" / "nubank_cc" / "nubank.csv"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"x")
        ext = ExtratorDASPARCSNPDF(arq)
        assert ext.pode_processar(arq) is False
