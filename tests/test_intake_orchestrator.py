"""Testes do src.intake.orchestrator.

Cobre:
- detectar_mime: PDF, ZIP, JPEG, PNG, HEIC, XML, fallback por extensão
- processar_arquivo_inbox end-to-end com PDFs reais (pdf_notas, scan)
- processar_arquivo_inbox single-file (XML, imagem)
- processar_arquivo_inbox ZIP (múltiplos PDFs em subdiretórios)
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.intake import classifier as clf
from src.intake import extractors_envelope as env
from src.intake import orchestrator as orq
from src.intake import router

INBOX = Path(__file__).resolve().parents[1] / "inbox"
PDF_NOTAS = INBOX / "pdf_notas.pdf"
PDF_SCAN = INBOX / "notas de garantia e compras.pdf"

SOMENTE_SE_INBOX_EXISTE = pytest.mark.skipif(
    not (PDF_NOTAS.exists() and PDF_SCAN.exists()),
    reason="PDFs reais da inbox/ não disponíveis",
)


# ============================================================================
# Fixtures de isolamento
# ============================================================================


@pytest.fixture(autouse=True)
def isolar_caminhos(tmp_path, monkeypatch):
    """Redireciona TODAS as constantes de path para tmp_path."""
    raiz = tmp_path / "repo"
    raiz.mkdir()
    monkeypatch.setattr(env, "_ENVELOPES_BASE", raiz / "data" / "raw" / "_envelopes")
    monkeypatch.setattr(router, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(
        router, "_ORIGINAIS_BASE", raiz / "data" / "raw" / "_envelopes" / "originais"
    )
    monkeypatch.setattr(clf, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(clf, "_PATH_DATA_RAW", raiz / "data" / "raw")
    clf.recarregar_tipos()
    yield raiz


# ============================================================================
# detectar_mime
# ============================================================================


def test_detect_pdf_por_magic_bytes(tmp_path):
    arq = tmp_path / "qq.bin"
    arq.write_bytes(b"%PDF-1.7 conteudo")
    assert orq.detectar_mime(arq) == "application/pdf"


def test_detect_zip_por_magic_bytes(tmp_path):
    arq = tmp_path / "qq.bin"
    arq.write_bytes(b"PK\x03\x04 resto")
    assert orq.detectar_mime(arq) == "application/zip"


def test_detect_png_por_magic_bytes(tmp_path):
    arq = tmp_path / "qq.bin"
    arq.write_bytes(b"\x89PNG\r\n\x1a\n resto")
    assert orq.detectar_mime(arq) == "image/png"


def test_detect_jpeg_por_magic_bytes(tmp_path):
    arq = tmp_path / "qq.bin"
    arq.write_bytes(b"\xff\xd8\xff\xe0 resto")
    assert orq.detectar_mime(arq) == "image/jpeg"


def test_detect_heic_por_brand(tmp_path):
    """HEIC tem 'ftypheic' (ou variantes) nos bytes 4-12."""
    arq = tmp_path / "x.bin"
    arq.write_bytes(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic")
    assert orq.detectar_mime(arq) == "image/heic"


def test_detect_xml_por_conteudo(tmp_path):
    arq = tmp_path / "x.bin"
    arq.write_bytes(b'<?xml version="1.0"?><infNFe/>')
    assert orq.detectar_mime(arq) == "application/xml"


def test_detect_eml_por_extensao(tmp_path):
    arq = tmp_path / "carta.eml"
    arq.write_bytes(b"From: a@b.com\nSubject: x\n\n")
    assert orq.detectar_mime(arq) == "message/rfc822"


def test_detect_fallback_octet_stream(tmp_path):
    arq = tmp_path / "misterio.dat"
    arq.write_bytes(b"\x00\x01\x02\x03 nada conhecido")
    assert orq.detectar_mime(arq) == "application/octet-stream"


# ============================================================================
# processar_arquivo_inbox -- PDFs reais
# ============================================================================


@SOMENTE_SE_INBOX_EXISTE
def test_processar_pdf_notas_3_paginas_classifica_3_garantias(tmp_path, isolar_caminhos):
    """pdf_notas.pdf: 3 páginas nativas, todas cupom_garantia_estendida."""
    pseudo_inbox = tmp_path / "inbox"
    pseudo_inbox.mkdir()
    copia = pseudo_inbox / PDF_NOTAS.name
    copia.write_bytes(PDF_NOTAS.read_bytes())

    relatorio = orq.processar_arquivo_inbox(copia, pessoa="andre")

    assert len(relatorio.artefatos) == 3
    tipos = [a.decisao.tipo for a in relatorio.artefatos]
    assert tipos == ["cupom_garantia_estendida"] * 3
    assert relatorio.sucesso_total is True

    for a in relatorio.artefatos:
        assert a.caminho_final.exists()
        assert "garantias_estendidas" in str(a.caminho_final)
        assert a.caminho_final.name.startswith("GARANTIA_EST_2026-04-19_")


@SOMENTE_SE_INBOX_EXISTE
def test_processar_pdf_scan_4_paginas_vira_single_e_cai_em_classificar(
    tmp_path, isolar_caminhos
):
    """notas de garantia e compras.pdf: 4 pgs SCAN, sem texto extraível.
    Pós-Sprint 41d (heterogeneidade): scan sem identificadores legíveis
    é classificado como HOMOGÊNEO (conservador) -> envelope `single` ->
    1 artefato só em `_classificar/`. Quando a Sprint 45 (OCR de PDF)
    entrar, identificadores serão extraídos e o PDF passa a ser detectado
    como heterogêneo (2 chaves NFe + 2 bilhetes) -> page-split + 4 artefatos.
    """
    pseudo_inbox = tmp_path / "inbox"
    pseudo_inbox.mkdir()
    copia = pseudo_inbox / PDF_SCAN.name
    copia.write_bytes(PDF_SCAN.read_bytes())

    relatorio = orq.processar_arquivo_inbox(copia, pessoa="andre")

    assert len(relatorio.artefatos) == 1, (
        "scan sem texto -> homogêneo -> 1 artefato (single envelope)"
    )
    assert relatorio.artefatos[0].decisao.tipo is None
    assert relatorio.sucesso_total is False
    assert "_classificar" in str(relatorio.artefatos[0].caminho_final)


# ============================================================================
# processar_arquivo_inbox -- single-file
# ============================================================================


def test_processar_xml_nfe_single_file(tmp_path, isolar_caminhos):
    """XML chega como single-file; detector encontra <infNFe>; classifier roteia."""
    pseudo_inbox = tmp_path / "inbox"
    pseudo_inbox.mkdir()
    arq = pseudo_inbox / "nfe.xml"
    arq.write_text(
        '<?xml version="1.0"?><infNFe><emit><CNPJ>12345</CNPJ></emit></infNFe>',
        encoding="utf-8",
    )
    relatorio = orq.processar_arquivo_inbox(arq, pessoa="andre")
    assert len(relatorio.artefatos) == 1
    assert relatorio.artefatos[0].decisao.tipo == "xml_nfe"
    assert relatorio.sucesso_total is True


def test_processar_arquivo_desconhecido_vai_pra_classificar(tmp_path, isolar_caminhos):
    pseudo_inbox = tmp_path / "inbox"
    pseudo_inbox.mkdir()
    arq = pseudo_inbox / "misterio.dat"
    arq.write_bytes(b"conteudo qualquer sem assinatura")
    relatorio = orq.processar_arquivo_inbox(arq, pessoa="andre")
    assert len(relatorio.artefatos) == 1
    assert relatorio.artefatos[0].decisao.tipo is None
    assert relatorio.sucesso_total is False


# ============================================================================
# processar_arquivo_inbox -- ZIP
# ============================================================================


def test_processar_zip_de_xmls(tmp_path, isolar_caminhos):
    pseudo_inbox = tmp_path / "inbox"
    pseudo_inbox.mkdir()
    zip_path = pseudo_inbox / "nfes.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("janeiro/nfe1.xml", '<?xml version="1.0"?><infNFe id="1"/>')
        zf.writestr("fevereiro/nfe2.xml", '<?xml version="1.0"?><infNFe id="2"/>')
    relatorio = orq.processar_arquivo_inbox(zip_path, pessoa="andre")
    assert len(relatorio.artefatos) == 2
    tipos = [a.decisao.tipo for a in relatorio.artefatos]
    assert tipos == ["xml_nfe", "xml_nfe"]
    assert relatorio.sucesso_total is True


# ============================================================================
# Inexistente
# ============================================================================


def test_processar_arquivo_inexistente_levanta(tmp_path, isolar_caminhos):
    with pytest.raises(FileNotFoundError):
        orq.processar_arquivo_inbox(tmp_path / "fantasma.pdf", pessoa="andre")


# "Quem orquestra precisa conhecer a partitura de cada instrumento." -- princípio do regente
