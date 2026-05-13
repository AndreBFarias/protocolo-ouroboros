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
Composição do Documento de Arrecadação
Código Denominação Principal Multa Juros Total
1004 COFINS - SIMPLES NACIONAL 31,56 6,31 3,70 41,57
02/2024
1002 CSLL - SIMPLES NACIONAL 8,62 1,72 1,01 11,35
02/2024
1006 INSS - SIMPLES NACIONAL 106,86 21,37 12,54 140,77
02/2024
1001 IRPJ - SIMPLES NACIONAL 9,85 1,97 1,15 12,97
02/2024
1010 ISS - SIMPLES NACIONAL 82,47 16,49 9,68 108,64
BRASILIA (DF) - 02/2024
1005 PIS - SIMPLES NACIONAL 6,84 1,37 0,80 9,01
02/2024
Totais 246,20 49,23 28,88 324,31
85830000003 3 24310328251 0 20071825105 1 72313828197 5
"""

# Amostra 2: parcela 17/25, "Diversos" cobrindo 06/2024 + 07/2024 (2 meses x 6
# tributos = 12 entradas). Para garantir aritmética exata, espelhamos a
# composição da amostra 1 nos dois meses -> total = 2 x 324,31 = 648,62.
DAS_TEXTO_DIVERSOS = """Documento de Arrecadação
do Simples Nacional
CNPJ Razão Social
45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS
Período de Apuração Data de Vencimento Número do Documento Pagar este documento até
Diversos 07.18.25105.7231399-1
31/03/2026
Observações
DAS de PARCSN (Versão: 2.0.0)
Valor Total do Documento
Número do Parcelamento: 1
648,62
Parcela: 17/25
Composição do Documento de Arrecadação
Código Denominação Principal Multa Juros Total
1004 COFINS - SIMPLES NACIONAL 31,56 6,31 3,70 41,57
06/2024
1002 CSLL - SIMPLES NACIONAL 8,62 1,72 1,01 11,35
06/2024
1006 INSS - SIMPLES NACIONAL 106,86 21,37 12,54 140,77
06/2024
1001 IRPJ - SIMPLES NACIONAL 9,85 1,97 1,15 12,97
06/2024
1010 ISS - SIMPLES NACIONAL 82,47 16,49 9,68 108,64
BRASILIA (DF) - 06/2024
1005 PIS - SIMPLES NACIONAL 6,84 1,37 0,80 9,01
06/2024
1004 COFINS - SIMPLES NACIONAL 31,56 6,31 3,70 41,57
07/2024
1002 CSLL - SIMPLES NACIONAL 8,62 1,72 1,01 11,35
07/2024
1006 INSS - SIMPLES NACIONAL 106,86 21,37 12,54 140,77
07/2024
1001 IRPJ - SIMPLES NACIONAL 9,85 1,97 1,15 12,97
07/2024
1010 ISS - SIMPLES NACIONAL 82,47 16,49 9,68 108,64
BRASILIA (DF) - 07/2024
1005 PIS - SIMPLES NACIONAL 6,84 1,37 0,80 9,01
07/2024
Totais 492,40 98,46 57,76 648,62
85830000003 6 34910328261 0 30071825105 1 72313839197 1
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


# Sprint INFRA-DAS-EXTRAIR-COMPOSICAO 2026-05-12:
# Bateria de testes da decomposicao, codigo de barras e composicao por tributo.
class TestComposicaoDAS:
    """Cobre os campos novos: principal/multa/juros/codigo_barras/composicao."""

    def _doc(self, tmp_path: Path, texto: str) -> dict:
        arq = tmp_path / "das.pdf"
        arq.write_bytes(b"x")
        ext = ExtratorDASPARCSNPDF(arq)
        return ext.extrair_das(arq, texto_override=texto)["documento"]

    def test_amostra_fev_2025_decomposicao_completa(self, tmp_path: Path) -> None:
        doc = self._doc(tmp_path, DAS_TEXTO_ANDRE)
        assert doc["principal"] == 246.20
        assert doc["multa"] == 49.23
        assert doc["juros"] == 28.88
        assert doc["total"] == 324.31

    def test_amostra_fev_2025_aritmetica_principal_multa_juros(self, tmp_path: Path) -> None:
        doc = self._doc(tmp_path, DAS_TEXTO_ANDRE)
        soma = round(doc["principal"] + doc["multa"] + doc["juros"], 2)
        assert soma == doc["total"], f"{soma} != {doc['total']}"

    def test_amostra_fev_2025_composicao_seis_tributos(self, tmp_path: Path) -> None:
        doc = self._doc(tmp_path, DAS_TEXTO_ANDRE)
        comp = doc["composicao_por_tributo"]
        assert len(comp) == 6
        codigos = [e["codigo"] for e in comp]
        assert codigos == ["1004", "1002", "1006", "1001", "1010", "1005"]
        # Período de cada entrada deve estar preenchido (inclusive a entrada
        # com prefixo de cidade na linha "BRASILIA (DF) - 02/2024").
        assert all(e["periodo"] == "2024-02" for e in comp)

    def test_amostra_fev_2025_soma_composicao_igual_total(self, tmp_path: Path) -> None:
        doc = self._doc(tmp_path, DAS_TEXTO_ANDRE)
        soma = round(sum(e["total"] for e in doc["composicao_por_tributo"]), 2)
        assert soma == doc["total"]

    def test_amostra_fev_2025_codigo_barras_48_digitos(self, tmp_path: Path) -> None:
        doc = self._doc(tmp_path, DAS_TEXTO_ANDRE)
        cb = doc["codigo_barras"]
        # Boleto de arrecadação tem 48 dígitos (4 blocos de 11+1) -- amostra
        # real da auditoria 2026-05-12 entrega 48 (não 47 como o boleto
        # bancário padrão). Validamos o formato presente nos PDFs reais.
        apenas_digitos = "".join(c for c in cb if c.isdigit())
        assert len(apenas_digitos) == 48, f"esperado 48, veio {len(apenas_digitos)}"
        # 4 blocos separados por espaco em branco.
        assert cb.count(" ") >= 7

    def test_amostra_diversos_doze_entradas_dois_meses(self, tmp_path: Path) -> None:
        doc = self._doc(tmp_path, DAS_TEXTO_DIVERSOS)
        comp = doc["composicao_por_tributo"]
        assert len(comp) == 12
        # 2 meses distintos.
        meses_unicos = {e["periodo"] for e in comp}
        assert meses_unicos == {"2024-06", "2024-07"}

    def test_amostra_diversos_meses_diversos_exposto(self, tmp_path: Path) -> None:
        doc = self._doc(tmp_path, DAS_TEXTO_DIVERSOS)
        assert doc["periodo_apuracao"] == "diversos"
        assert doc["quantidade_meses_diversos"] == 2
        assert set(doc["meses_diversos"]) == {"2024-06", "2024-07"}

    def test_amostra_diversos_aritmetica_total(self, tmp_path: Path) -> None:
        doc = self._doc(tmp_path, DAS_TEXTO_DIVERSOS)
        assert doc["total"] == 648.62
        assert doc["principal"] == 492.40
        assert doc["multa"] == 98.46
        assert doc["juros"] == 57.76
        soma_pmj = round(doc["principal"] + doc["multa"] + doc["juros"], 2)
        assert soma_pmj == doc["total"]
        soma_comp = round(sum(e["total"] for e in doc["composicao_por_tributo"]), 2)
        assert soma_comp == doc["total"]

    def test_documento_sem_composicao_nao_quebra(self, tmp_path: Path) -> None:
        """Garante backward compat: DAS antigo sem tabela ainda gera dict
        valido (sem os campos novos)."""
        texto_minimal = """Documento de Arrecadação
do Simples Nacional
CNPJ Razão Social
99.999.999/0001-99 EMPRESA X
Período de Apuração Data de Vencimento Número do Documento Pagar este documento até
Janeiro/2025 31/01/2025 07.18.99999.9999999-0
28/02/2025
Valor Total do Documento
100,00
Parcela: 1/12
"""
        doc = self._doc(tmp_path, texto_minimal)
        assert doc["total"] == 100.00
        assert "principal" not in doc
        assert "composicao_por_tributo" not in doc
        assert "codigo_barras" not in doc
