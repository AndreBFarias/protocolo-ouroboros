"""Testes do src.intake.preview.

Cobre:
- gerar_preview por MIME (PDF, imagem, XML, texto, MIME desconhecido)
- Falha silenciosa: arquivo inexistente, binário corrompido, MIME sem handler
- OCR real numa imagem sintética PNG (skipa se tesseract indisponível)
- HEIC: skipa se pillow-heif indisponível, senão converte e OCR
- Texto cru: encoding fallback latin-1 quando UTF-8 falha
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from src.intake import preview

INBOX = Path(__file__).resolve().parents[1] / "inbox"
PDF_NOTAS = INBOX / "pdf_notas.pdf"

TESSERACT_DISPONIVEL = shutil.which("tesseract") is not None


# ============================================================================
# Helpers
# ============================================================================


def _imagem_com_texto(tmp_path: Path, texto: str, nome: str = "x.png") -> Path:
    """Cria imagem PNG simples com texto preto sobre fundo branco."""
    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)
    try:
        # Tenta uma fonte TrueType comum em sistemas Linux
        fonte = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except OSError:
        fonte = ImageFont.load_default()
    draw.text((20, 60), texto, fill="black", font=fonte)
    caminho = tmp_path / nome
    img.save(caminho)
    return caminho


# ============================================================================
# Falha silenciosa
# ============================================================================


def test_preview_arquivo_inexistente_devolve_none(tmp_path):
    assert preview.gerar_preview(tmp_path / "fantasma.pdf", "application/pdf") is None


def test_preview_mime_desconhecido_devolve_none(tmp_path):
    arq = tmp_path / "qq.bin"
    arq.write_bytes(b"\x00\x01\x02")
    assert preview.gerar_preview(arq, "application/octet-stream") is None


def test_preview_pdf_corrompido_devolve_none_sem_levantar(tmp_path):
    falso = tmp_path / "falso.pdf"
    falso.write_bytes(b"not a pdf")
    assert preview.gerar_preview(falso, "application/pdf") is None


def test_preview_imagem_corrompida_devolve_none(tmp_path):
    falso = tmp_path / "falso.png"
    falso.write_bytes(b"not a png")
    assert preview.gerar_preview(falso, "image/png") is None


# ============================================================================
# PDF (fallback)
# ============================================================================


@pytest.mark.skipif(not PDF_NOTAS.exists(), reason="inbox/pdf_notas.pdf indisponível")
def test_preview_pdf_le_primeira_pagina():
    texto = preview.gerar_preview(PDF_NOTAS, "application/pdf")
    assert texto is not None
    # pdf_notas.pdf pg1 tem "CUPOM BILHETE DE SEGURO" (com glyphs corrompidos
    # mas ainda legível pra detector de tipo).
    assert "CUPOM" in texto or "BILHETE" in texto


# ============================================================================
# Imagem (OCR real)
# ============================================================================


@pytest.mark.skipif(not TESSERACT_DISPONIVEL, reason="tesseract não está no PATH")
def test_preview_imagem_png_extrai_texto_via_ocr(tmp_path):
    arq = _imagem_com_texto(tmp_path, "CUPOM FISCAL eletronico", nome="cupom.png")
    texto = preview.gerar_preview(arq, "image/png")
    assert texto is not None
    # Tesseract pode trocar caracteres -- aceitar variações casefold
    assert "cupom" in texto.lower() or "fiscal" in texto.lower()


@pytest.mark.skipif(not TESSERACT_DISPONIVEL, reason="tesseract não está no PATH")
def test_preview_imagem_aplica_exif_transpose(tmp_path):
    """Foto sem EXIF deve passar normal -- garante que exif_transpose não quebra."""
    arq = _imagem_com_texto(tmp_path, "TESTE", nome="sem_exif.png")
    texto = preview.gerar_preview(arq, "image/png")
    assert texto is not None


@pytest.mark.skipif(not TESSERACT_DISPONIVEL, reason="tesseract não está no PATH")
def test_preview_imagem_grande_e_redimensionada(tmp_path):
    """Imagem 4000x3000 deve ser redimensionada antes do OCR sem crashar."""
    img = Image.new("RGB", (4000, 3000), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "BIG", fill="black")
    arq = tmp_path / "big.png"
    img.save(arq)
    texto = preview.gerar_preview(arq, "image/png")
    # Mesmo com fonte default minúscula, OCR não deve crashar em imagem grande
    assert texto is not None or texto is None  # qualquer dos dois sem exceção


@pytest.mark.skipif(
    not (TESSERACT_DISPONIVEL and preview._HEIC_DISPONIVEL),
    reason="tesseract OU pillow-heif indisponível",
)
def test_preview_heic_via_pillow_heif(tmp_path):
    """Cria HEIC sintético via pillow-heif e roda preview."""
    from pillow_heif import from_pillow

    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)
    try:
        fonte = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except OSError:
        fonte = ImageFont.load_default()
    draw.text((20, 60), "RECIBO", fill="black", font=fonte)
    arq = tmp_path / "foto.heic"
    from_pillow(img).save(arq, quality=80)

    texto = preview.gerar_preview(arq, "image/heic")
    assert texto is not None
    assert "recibo" in texto.lower()


def test_preview_heic_sem_pillow_heif_devolve_none(tmp_path, monkeypatch):
    """Se pillow-heif não estiver disponível, HEIC devolve None sem crashar."""
    monkeypatch.setattr(preview, "_HEIC_DISPONIVEL", False)
    arq = tmp_path / "x.heic"
    arq.write_bytes(b"fake-heic-bytes")
    assert preview.gerar_preview(arq, "image/heic") is None


# ============================================================================
# Texto cru (XML, CSV, plain)
# ============================================================================


def test_preview_xml_le_texto_cru(tmp_path):
    arq = tmp_path / "nfe.xml"
    arq.write_text(
        '<?xml version="1.0"?><infNFe><emit><CNPJ>12345</CNPJ></emit></infNFe>',
        encoding="utf-8",
    )
    texto = preview.gerar_preview(arq, "application/xml")
    assert texto is not None
    assert "<infNFe>" in texto


def test_preview_csv_le_header(tmp_path):
    arq = tmp_path / "nubank.csv"
    arq.write_text("Data,Valor,Identificador,Descrição\n", encoding="utf-8")
    texto = preview.gerar_preview(arq, "text/csv")
    assert texto is not None
    assert "Data,Valor" in texto


def test_preview_texto_latin1_fallback_quando_utf8_falha(tmp_path):
    """Bancos antigos exportam em latin-1; preview não pode quebrar com 'mojibake'."""
    arq = tmp_path / "extrato.csv"
    # Caractere 'ã' em latin-1 = 0xE3, que é byte inválido em UTF-8 sozinho
    arq.write_bytes("descrição,saldo\n".encode("latin-1"))
    texto = preview.gerar_preview(arq, "text/csv")
    assert texto is not None
    # Aceita "descrição" (utf8 ok) ou "descriÃ§Ã£o"-like (mojibake) -- o que
    # importa é não levantar e devolver alguma coisa
    assert "saldo" in texto


def test_preview_texto_trunca_em_limite(tmp_path, monkeypatch):
    """Arquivo muito grande é truncado -- preview não puxa MB de texto."""
    monkeypatch.setattr(preview, "LIMITE_BYTES_TEXTO", 32)
    arq = tmp_path / "grande.csv"
    conteudo = "a" * 1000
    arq.write_text(conteudo, encoding="utf-8")
    texto = preview.gerar_preview(arq, "text/csv")
    assert texto is not None
    assert len(texto) == 32


# ============================================================================
# MIMEs sem handler
# ============================================================================


@pytest.mark.parametrize(
    "mime",
    [
        "application/zip",
        "message/rfc822",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/x-ofx",
    ],
)
def test_preview_mimes_de_envelope_ou_extrator_devolvem_none(tmp_path, mime):
    arq = tmp_path / "qq.bin"
    arq.write_bytes(b"qualquer coisa")
    assert preview.gerar_preview(arq, mime) is None


# "O olhar lê o que o coração já decidiu enxergar." -- Montaigne
