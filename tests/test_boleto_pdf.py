"""Testes do extrator de boleto PDF (Sprint 87.3).

Estratégia: usa `extrair_boleto(caminho, texto_override=...)` para
injetar texto determinístico sem abrir PDF real. Fixtures textuais
minúsculas replicam os blocos canônicos dos boletos BB/Itaú/SESC
vistos em `data/raw/casal/boletos/`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.extractors.boleto_pdf import (
    ExtratorBoletoPDF,
    _cnpj_sintetico,
    _montar_documento,
    _normalizar_linha_digitavel,
)
from src.graph.db import GrafoDB
from src.utils.parse_br import parse_valor_br

# ---------------------------------------------------------------------------
# Fixtures textuais
# ---------------------------------------------------------------------------


TEXTO_BOLETO_SESC = """
Boleto Banco do Brasil
Beneficiário / CNPJ Vencimento Valor do Documento
SESC - Servico Social do Comercio do DF CNPJ: 03288908000130 11/05/2026 127,00
Data do Documento No documento Espécie Doc.
30/06/2025 335001250111306 RC
Nome do Pagador
ANDRE DA SILVA BATISTA DE FARIAS 05127373122
001-9 00190.00009 02819.325008 17390.074171 4 14430000012700
Local de pagamento Vencimento
PAGÁVEL EM QUALQUER BANCO ATÉ O VENCIMENTO. 11/05/2026
(=) Valor documento R$ 127,00
"""


TEXTO_BOLETO_SEM_CNPJ = """
Boleto bancário
Cedente: ESCOLINHA DE NATACAO SANTA MONICA
Vencimento: 19/03/2026
Valor do Documento R$ 103,93
Pagador: ANDRE FARIAS
Linha digitável
23793.38128 60012.345678 90123.456789 1 98260000010393
Data de emissão: 15/03/2026
"""


TEXTO_BOLETO_FORMATO_CONTINUO = """
BOLETO DE COBRANCA
Beneficiário: CONDOMINIO EDIFICIO TALENTOS
CNPJ: 12.345.678/0001-90
Vencimento 10/05/2026
Valor do Documento R$ 1.234,56
Pagador: ANDRE FARIAS
Linha digitavel:
03399876543210987654321098765432198765432101234
Data do documento 01/05/2026
"""


TEXTO_VAZIO_OCR = "  \n\n  "


# ---------------------------------------------------------------------------
# Testes unitários de helpers
# ---------------------------------------------------------------------------


def test_parse_valor_br_aceita_formatos_canonicos():
    # Contrato agora é garantido pelo helper canônico src.utils.parse_br
    # (Sprint INFRA-parse-br). Mantemos este teste para documentar o
    # contrato usado pelo extrator de boleto especificamente.
    assert parse_valor_br("127,00") == pytest.approx(127.00)
    assert parse_valor_br("1.234,56") == pytest.approx(1234.56)
    assert parse_valor_br("103,93") == pytest.approx(103.93)
    assert parse_valor_br(None) is None
    assert parse_valor_br("abc") is None


def test_normalizar_linha_digitavel_47_digitos():
    formatada = "00190.00009 02819.325008 17390.074171 4 14430000012700"
    normalizada = _normalizar_linha_digitavel(formatada)
    assert normalizada is not None
    assert len(normalizada) == 47
    assert normalizada.isdigit()

    continua = "00190000090281932500817390074171414430000012700"
    assert _normalizar_linha_digitavel(continua) == continua
    assert _normalizar_linha_digitavel("1234") is None


def test_cnpj_sintetico_eh_idempotente():
    a = _cnpj_sintetico("SESC - Servico Social do Comercio do DF")
    b = _cnpj_sintetico("SESC - Servico Social do Comercio do DF")
    c = _cnpj_sintetico("OUTRA RAZAO SOCIAL")
    assert a == b
    assert a != c
    assert a.startswith("BOLETO|")
    assert len(a) == len("BOLETO|") + 12


# ---------------------------------------------------------------------------
# Testes do parser completo (via extrair_boleto texto_override)
# ---------------------------------------------------------------------------


def test_extrai_linha_digitavel_47_digitos(tmp_path: Path):
    caminho_fake = tmp_path / "boleto_sesc.pdf"
    caminho_fake.write_bytes(b"%PDF-")  # só para existir

    extrator = ExtratorBoletoPDF(caminho_fake)
    resultado = extrator.extrair_boleto(caminho_fake, texto_override=TEXTO_BOLETO_SESC)

    documento = resultado["documento"]
    assert documento
    assert documento["chave_44"] == "00190000090281932500817390074171414430000012700"
    assert len(documento["chave_44"]) == 47


def test_extrai_valor_com_parse_br(tmp_path: Path):
    caminho = tmp_path / "boleto.pdf"
    caminho.write_bytes(b"%PDF-")

    extrator = ExtratorBoletoPDF(caminho)

    r1 = extrator.extrair_boleto(caminho, texto_override=TEXTO_BOLETO_SESC)
    assert r1["documento"]["total"] == pytest.approx(127.00)

    r2 = extrator.extrair_boleto(caminho, texto_override=TEXTO_BOLETO_FORMATO_CONTINUO)
    assert r2["documento"]["total"] == pytest.approx(1234.56)

    r3 = extrator.extrair_boleto(caminho, texto_override=TEXTO_BOLETO_SEM_CNPJ)
    assert r3["documento"]["total"] == pytest.approx(103.93)


def test_extrai_vencimento_iso(tmp_path: Path):
    caminho = tmp_path / "boleto.pdf"
    caminho.write_bytes(b"%PDF-")

    extrator = ExtratorBoletoPDF(caminho)
    resultado = extrator.extrair_boleto(
        caminho, texto_override=TEXTO_BOLETO_SEM_CNPJ
    )
    documento = resultado["documento"]
    assert documento["vencimento"] == "2026-03-19"
    # data_emissao vem de "Data de emissão" e tem prioridade sobre "Data do documento"
    assert documento["data_emissao"] == "2026-03-15"


def test_extrai_beneficiario_e_cnpj_real(tmp_path: Path):
    caminho = tmp_path / "boleto.pdf"
    caminho.write_bytes(b"%PDF-")

    extrator = ExtratorBoletoPDF(caminho)
    resultado = extrator.extrair_boleto(
        caminho, texto_override=TEXTO_BOLETO_FORMATO_CONTINUO
    )
    documento = resultado["documento"]
    # CNPJ formatado vira só dígitos
    assert documento["cnpj_emitente"] == "12345678000190"
    # Razão social extraída, sem o sufixo "CNPJ"
    assert "CONDOMINIO" in documento["razao_social"].upper()
    assert "CNPJ" not in documento["razao_social"]


def test_fallback_cnpj_sintetico_sem_cnpj_no_pdf(tmp_path: Path):
    caminho = tmp_path / "boleto_sem_cnpj.pdf"
    caminho.write_bytes(b"%PDF-")

    extrator = ExtratorBoletoPDF(caminho)
    resultado = extrator.extrair_boleto(caminho, texto_override=TEXTO_BOLETO_SEM_CNPJ)
    documento = resultado["documento"]
    assert documento
    cnpj = documento["cnpj_emitente"]
    assert cnpj.startswith("BOLETO|")
    assert len(cnpj) == len("BOLETO|") + 12
    # Razão social do cedente preservada
    assert "NATACAO" in documento["razao_social"].upper()


def test_pagador_extraido_ou_ausente(tmp_path: Path):
    caminho = tmp_path / "boleto.pdf"
    caminho.write_bytes(b"%PDF-")
    extrator = ExtratorBoletoPDF(caminho)

    r = extrator.extrair_boleto(caminho, texto_override=TEXTO_BOLETO_SESC)
    pagador = r["documento"].get("pagador")
    assert pagador is not None
    assert "ANDRE" in pagador.upper()


def test_texto_vazio_retorna_erro_sem_ingerir(tmp_path: Path):
    caminho = tmp_path / "scan.pdf"
    caminho.write_bytes(b"%PDF-")
    extrator = ExtratorBoletoPDF(caminho)
    resultado = extrator.extrair_boleto(caminho, texto_override=TEXTO_VAZIO_OCR)
    assert resultado["_erro_extracao"] == "texto_vazio"
    assert resultado["documento"] == {}


def test_arquivo_original_path_absoluto(tmp_path: Path):
    caminho = tmp_path / "BOLETO_teste.pdf"
    caminho.write_bytes(b"%PDF-")
    extrator = ExtratorBoletoPDF(caminho)
    resultado = extrator.extrair_boleto(caminho, texto_override=TEXTO_BOLETO_SESC)
    documento = resultado["documento"]
    assert documento["arquivo_original"] == str(caminho.resolve())
    assert Path(documento["arquivo_original"]).is_absolute()


# ---------------------------------------------------------------------------
# Idempotência e integração com ingestor
# ---------------------------------------------------------------------------


def test_idempotencia_reingesta_mesma_chave(tmp_path: Path):
    """Dois _montar_documento com o mesmo texto devolvem o mesmo dict (chave estável)."""
    caminho = tmp_path / "boleto.pdf"
    caminho.write_bytes(b"%PDF-")
    d1 = _montar_documento(TEXTO_BOLETO_SESC, caminho)
    d2 = _montar_documento(TEXTO_BOLETO_SESC, caminho)
    assert d1["chave_44"] == d2["chave_44"]
    assert d1["cnpj_emitente"] == d2["cnpj_emitente"]
    assert d1["total"] == d2["total"]
    assert d1["data_emissao"] == d2["data_emissao"]


def test_ingestao_real_no_grafo_nao_duplica(tmp_path: Path):
    """Roda extrair() duas vezes no mesmo PDF e confirma 1 documento no grafo."""
    caminho = tmp_path / "BOLETO_real.pdf"
    caminho.write_bytes(b"%PDF-")

    grafo = GrafoDB(tmp_path / "grafo_teste.sqlite")
    grafo.criar_schema()
    try:
        extrator = ExtratorBoletoPDF(caminho, grafo=grafo)
        # Monkey-patch o leitor de PDF para retornar texto canônico
        extrator._ler_pdf = lambda c: TEXTO_BOLETO_SESC  # type: ignore[method-assign]
        extrator.extrair()
        extrator.extrair()

        cur = grafo._conn.cursor()
        total = cur.execute(
            "SELECT COUNT(*) FROM node WHERE tipo='documento' "
            "AND json_extract(metadata, '$.tipo_documento')='boleto_servico'"
        ).fetchone()[0]
        assert total == 1

        # arquivo_original preenchido
        row = cur.execute(
            "SELECT json_extract(metadata, '$.arquivo_original') "
            "FROM node WHERE tipo='documento' "
            "AND json_extract(metadata, '$.tipo_documento')='boleto_servico'"
        ).fetchone()
        assert row[0] == str(caminho.resolve())
    finally:
        grafo.fechar()


def test_pode_processar_aceita_pasta_boletos(tmp_path: Path):
    pasta = tmp_path / "data" / "raw" / "casal" / "boletos"
    pasta.mkdir(parents=True)
    arquivo = pasta / "BOLETO_2026-04-21_abcd1234.pdf"
    arquivo.write_bytes(b"%PDF-")
    extrator = ExtratorBoletoPDF(arquivo)
    assert extrator.pode_processar(arquivo)


def test_pode_processar_recusa_outras_pastas(tmp_path: Path):
    # irpf_parcelas tem linha digitável, mas boleto não deve capturar
    pasta = tmp_path / "data" / "raw" / "andre" / "impostos" / "irpf_parcelas"
    pasta.mkdir(parents=True)
    arquivo = pasta / "IRPF_PARCELA_2026-03-15_abc.pdf"
    arquivo.write_bytes(b"%PDF-")
    extrator = ExtratorBoletoPDF(arquivo)
    assert not extrator.pode_processar(arquivo)


# "O boleto é só um papel; o pagamento é decisão." -- proverbio do pagador
