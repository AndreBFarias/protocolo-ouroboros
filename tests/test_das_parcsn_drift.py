"""Testes regressivos do drift -47% do DAS PARCSN (Sprint 90b).

Origem: auditoria 2026-04-26 contou 19 PDFs únicos por SHA-256 em
`data/raw/andre/impostos/das_parcsn/` mas grafo tinha apenas 10 nodes
do tipo `das_parcsn_andre`. Drift -47%.

Causa raiz confirmada por diagnóstico empírico (não OCR, hipótese 2 da
spec foi descartada -- todos os 19 PDFs têm texto nativo de 1197-1547
chars):

  - 8/9 PDFs faltantes têm "Período de Apuração: Diversos" (parcela
    cobrindo múltiplos meses). A regex `_RE_PERIODO` antiga exigia
    `Mês/YYYY DD/MM/YYYY` no header; com "Diversos" não casava e o
    `_montar_documento` retornava `{}` (early-return).
  - 1/9 PDF faltante (Março/2025) tinha o mês acentuado (ç). A regex
    `[A-Za-z]+` falhava em `ç`; capturava apenas o sufixo `o/2025` e
    `_MESES_PT["o"]` retornava None, levando ao mesmo early-return.

Fix (src/extractors/das_parcsn_pdf.py):
  - `_RE_PERIODO`/`_RE_VENCIMENTO` ampliados para `[A-Za-zÀ-ÿ]+`.
  - `_RE_PERIODO_DIVERSOS` detecta variante "Diversos".
  - `_RE_VENCIMENTO_DIVERSOS` captura data isolada na linha seguinte.
  - `_RE_PAGAR_ATE` priorizado em literal "Pagar até: DD/MM/YYYY"
    (rodapé do voucher PIX, presente em ambos os layouts) com fallback
    para o padrão antigo do header.
  - `_montar_documento` removeu `periodo` da lista de campos
    obrigatórios. Quando "Diversos", grava `periodo_apuracao="diversos"`.

Acceptance: cada uma das 4 variações abaixo deve render um documento
canônico com chave/cnpj/valor/data_emissao preenchidos e ser idempotente
ao reprocessar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.extractors.das_parcsn_pdf import (
    ExtratorDASPARCSNPDF,
    _montar_documento,
)
from src.graph.db import GrafoDB

# ---------------------------------------------------------------------------
# Fixtures sintéticas: 4 variações de layout
# ---------------------------------------------------------------------------

# Variação 1 -- PDF nativo, período "Mês/YYYY" sem acentuação (caso original
# já coberto pelos testes pré-Sprint 90b; replicado aqui como controle).
DAS_TEXTO_PERIODO_MES_SIMPLES = """Documento de Arrecadação
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
SENDA (Versão:5.2.3) Página: 1/1 15/04/2025 15:02:06
Pague com o PIX
CNPJ: 45.850.636/0001-60
Número: 07.18.25105.7231382-8
Pagar até: 30/04/2025
Valor: 324,31
"""

# Variação 2 -- PDF nativo, período com cedilha (Março). Antes da Sprint 90b
# a regex `[A-Za-z]+` falhava no `ç` e o early-return retornava {}.
DAS_TEXTO_PERIODO_COM_CEDILHA = """Documento de Arrecadação
do Simples Nacional
CNPJ Razão Social
45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS
Período de Apuração Data de Vencimento Número do Documento Pagar este documento até
Março/2025 31/03/2025 07.18.25105.7231432-8
30/04/2025
Observações
DAS de PARCSN (Versão: 2.0.0)
Valor Total do Documento
Número do Parcelamento: 1
324,31
Parcela: 5/25
SENDA (Versão:5.2.3) Página: 1/1 15/04/2025 15:02:07
Pague com o PIX
CNPJ: 45.850.636/0001-60
Número: 07.18.25105.7231432-8
Pagar até: 30/04/2025
Valor: 324,31
"""

# Variação 3 -- PDF nativo, período "Diversos" (parcela cobrindo múltiplos
# meses). Layout muda: na linha do header só cabem "Diversos" + número, e
# a data de vencimento original cai isolada na linha seguinte. Era a causa
# de 8 dos 9 PDFs faltantes detectados pela auditoria.
DAS_TEXTO_PERIODO_DIVERSOS = """Documento de Arrecadação
do Simples Nacional
CNPJ Razão Social
45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS
Período de Apuração Data de Vencimento Número do Documento Pagar este documento até
Diversos 07.18.25052.0333142-0
28/02/2025
Observações
DAS de PARCSN (Versão: 2.0.0)
Valor Total do Documento
Número do Parcelamento: 1
318,29
Parcela: 3/25
Composição do Documento de Arrecadação
SENDA (Versão:5.2.0) Página: 1/1 21/02/2025 15:40:54
Pague com o PIX
CNPJ: 45.850.636/0001-60
Número: 07.18.25052.0333142-0
Pagar até: 28/02/2025
Valor: 318,29
"""

# Variação 4 -- PDF "scaneado" simulado (sem rodapé "Pagar até:" estável,
# apenas o cabeçalho "Pagar este documento até ..."). Garante que o
# fallback `_RE_PAGAR_ATE_HEADER` continua acessível para layouts onde o
# rodapé do voucher PIX foi cortado.
DAS_TEXTO_SEM_RODAPE_PIX = """Documento de Arrecadação
do Simples Nacional
CNPJ Razão Social
45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS
Período de Apuração Data de Vencimento Número do Documento Pagar este documento até
Junho/2025 30/06/2025 07.18.25163.0767045-5
31/08/2025
Observações
DAS de PARCSN (Versão: 2.0.0)
Valor Total do Documento
Número do Parcelamento: 1
332,18
Parcela: 8/25
"""


# ---------------------------------------------------------------------------
# Testes regressivos
# ---------------------------------------------------------------------------


class TestDASParcsnDriftFix:
    """Cada variação de layout deve render um documento ingerível."""

    def test_variante_periodo_mes_simples(self, tmp_path: Path) -> None:
        arq = tmp_path / "v1.pdf"
        arq.write_bytes(b"x")
        doc = _montar_documento(DAS_TEXTO_PERIODO_MES_SIMPLES, arq)
        assert doc, "variante mês simples não montou documento"
        assert doc["periodo_apuracao"] == "2025-02"
        assert doc["data_emissao"] == "2025-02-28"
        assert doc["vencimento"] == "2025-04-30"
        assert doc["total"] == 324.31
        assert doc["parcela_atual"] == 4
        assert doc["tipo_documento"] == "das_parcsn_andre"

    def test_variante_periodo_com_cedilha(self, tmp_path: Path) -> None:
        arq = tmp_path / "v2.pdf"
        arq.write_bytes(b"x")
        doc = _montar_documento(DAS_TEXTO_PERIODO_COM_CEDILHA, arq)
        assert doc, "variante com cedilha (Março) não montou documento"
        assert doc["periodo_apuracao"] == "2025-03"
        assert doc["data_emissao"] == "2025-03-31"
        assert doc["vencimento"] == "2025-04-30"
        assert doc["parcela_atual"] == 5

    def test_variante_periodo_diversos(self, tmp_path: Path) -> None:
        arq = tmp_path / "v3.pdf"
        arq.write_bytes(b"x")
        doc = _montar_documento(DAS_TEXTO_PERIODO_DIVERSOS, arq)
        assert doc, "variante 'Diversos' não montou documento"
        # Período fica como 'diversos' literal -- sinaliza explicitamente
        # que o documento cobre múltiplos meses, sem inventar mes_ref.
        assert doc["periodo_apuracao"] == "diversos"
        assert doc["data_emissao"] == "2025-02-28"
        assert doc["vencimento"] == "2025-02-28"
        assert doc["total"] == 318.29
        assert doc["parcela_atual"] == 3
        assert doc["tipo_documento"] == "das_parcsn_andre"
        assert doc["numero"] == "07.18.25052.0333142-0"

    def test_variante_sem_rodape_pix_usa_fallback(self, tmp_path: Path) -> None:
        arq = tmp_path / "v4.pdf"
        arq.write_bytes(b"x")
        doc = _montar_documento(DAS_TEXTO_SEM_RODAPE_PIX, arq)
        assert doc, "variante sem rodapé PIX não montou documento"
        # Sem rodapé o fallback _RE_PAGAR_ATE_HEADER captura a data-limite
        # da linha "Pagar este documento até ...".
        assert doc["periodo_apuracao"] == "2025-06"
        assert doc["data_emissao"] == "2025-06-30"
        assert doc["vencimento"] == "2025-08-31"
        assert doc["parcela_atual"] == 8


class TestDASParcsnDriftIngestaoIdempotente:
    """Re-ingerir o mesmo documento não duplica nodes (chave_44 canônica)."""

    def test_ingestao_idempotente_diversos(self, tmp_path: Path) -> None:
        # Pasta com pista 'das_parcsn' para que pode_processar() aceite.
        arq = tmp_path / "data" / "raw" / "andre" / "impostos" / "das_parcsn" / "v.pdf"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"x")

        grafo_path = tmp_path / "grafo.sqlite"
        grafo = GrafoDB(grafo_path)
        grafo.criar_schema()

        ext = ExtratorDASPARCSNPDF(arq, grafo=grafo)
        # Primeira ingestão.
        ext.extrair_das(arq, texto_override=DAS_TEXTO_PERIODO_DIVERSOS)
        documento = _montar_documento(DAS_TEXTO_PERIODO_DIVERSOS, arq)
        from src.graph.ingestor_documento import ingerir_documento_fiscal

        id1 = ingerir_documento_fiscal(grafo, documento, itens=[], caminho_arquivo=arq)
        # Segunda ingestão -- deve devolver o mesmo id (chave_44 idempotente).
        id2 = ingerir_documento_fiscal(grafo, documento, itens=[], caminho_arquivo=arq)
        assert id1 == id2

        cur = grafo._conn.execute(
            "SELECT COUNT(*) FROM node WHERE tipo='documento' "
            "AND json_extract(metadata, '$.tipo_documento')='das_parcsn_andre'"
        )
        assert cur.fetchone()[0] == 1
        grafo.fechar()


class TestDASParcsnDriftRegressaoNaoDAS:
    """Garante que o relaxamento de campos opcionais não engole documentos
    fora do escopo DAS PARCSN. Falta de CNPJ/numero/valor continua bloqueando."""

    def test_documento_sem_cnpj_continua_rejeitado(self, tmp_path: Path) -> None:
        arq = tmp_path / "x.pdf"
        arq.write_bytes(b"x")
        # Texto curto cai no early-return de texto_vazio em extrair_das,
        # então testamos _montar_documento direto com texto suficiente
        # mas sem CNPJ válido.
        texto_sem_cnpj = (
            "Documento de Arrecadação do Simples Nacional "
            * 5
            + "\nDiversos 07.18.25052.0333142-0\n28/02/2025\nValor Total do "
            "Documento\n100,00\n"
        )
        assert len(texto_sem_cnpj) > 100
        doc = _montar_documento(texto_sem_cnpj, arq)
        assert doc == {}, "documento sem CNPJ válido não deve passar"

    def test_documento_sem_numero_continua_rejeitado(self, tmp_path: Path) -> None:
        texto_sem_numero = (
            "Documento de Arrecadação do Simples Nacional\n"
            "CNPJ Razão Social\n"
            "45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS\n"
            "Período de Apuração\n"
            "Diversos\n"
            "28/02/2025\n"
            "Valor Total do Documento\n100,00\n"
        ) * 2
        arq = tmp_path / "x.pdf"
        arq.write_bytes(b"x")
        doc = _montar_documento(texto_sem_numero, arq)
        assert doc == {}, "documento sem número SENDA válido não deve passar"


# ---------------------------------------------------------------------------
# Teste opcional contra dados reais (fica skipado em CI sem `data/`)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not Path("data/raw/andre/impostos/das_parcsn").exists(),
    reason="pasta data/raw/andre/impostos/das_parcsn não existe (ambiente sem dados reais)",
)
def test_19_pdfs_reais_processam_sem_falha() -> None:
    """Sob o ambiente do supervisor, os 19 PDFs reais montam documento."""
    import pdfplumber

    pasta = Path("data/raw/andre/impostos/das_parcsn")
    pdfs = sorted(pasta.glob("*.pdf"))
    assert len(pdfs) == 19, f"esperado 19 PDFs, encontrei {len(pdfs)}"

    montados = 0
    for pdf in pdfs:
        with pdfplumber.open(pdf) as doc:
            texto = "\n".join(p.extract_text() or "" for p in doc.pages)
        if _montar_documento(texto, pdf):
            montados += 1
    assert montados == 19, f"apenas {montados}/19 PDFs montaram documento"


# "Quem mede mal o invisível, perde o visível também." -- Heráclito
