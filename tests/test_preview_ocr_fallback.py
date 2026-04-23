"""Testes do fallback OCR em src/intake/preview.py (P1.2 / Sprint 89).

Cobre:
- PDF-imagem (0 chars nativos) cai em OCR via pypdfium2 + tesseract.
- PDF nativo com texto suficiente não invoca OCR (performance).
- pypdfium2 ausente devolve None sem crashar.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.intake.preview import (
    MIN_CHARS_TEXTO_NATIVO,
    _preview_pdf,
    _preview_pdf_via_ocr,
)


class TestPreviewPDFFallbackOCR:
    def test_pdf_nativo_nao_aciona_ocr(self, tmp_path: Path) -> None:
        """pdfplumber retorna texto suficiente -> OCR não é chamado."""
        arq = tmp_path / "nativo.pdf"
        arq.write_bytes(b"%PDF-1.4\n")  # placeholder

        texto_nativo = "x" * (MIN_CHARS_TEXTO_NATIVO + 10)

        with patch("src.intake.preview.pdfplumber") as mock_pdfplumber:
            mock_pdf = mock_pdfplumber.open.return_value.__enter__.return_value
            mock_pdf.pages = [type("P", (), {"extract_text": lambda self: texto_nativo})()]

            with patch("src.intake.preview._preview_pdf_via_ocr") as mock_ocr:
                resultado = _preview_pdf(arq)
                assert resultado == texto_nativo
                mock_ocr.assert_not_called()

    def test_pdf_imagem_cai_em_ocr(self, tmp_path: Path) -> None:
        """pdfplumber retorna texto curto -> OCR é invocado."""
        arq = tmp_path / "imagem.pdf"
        arq.write_bytes(b"%PDF-1.4\n")

        with patch("src.intake.preview.pdfplumber") as mock_pdfplumber:
            mock_pdf = mock_pdfplumber.open.return_value.__enter__.return_value
            mock_pdf.pages = [type("P", (), {"extract_text": lambda self: ""})()]

            with patch(
                "src.intake.preview._preview_pdf_via_ocr",
                return_value="texto OCR extraido",
            ) as mock_ocr:
                resultado = _preview_pdf(arq)
                assert resultado == "texto OCR extraido"
                mock_ocr.assert_called_once_with(arq)

    def test_ocr_pypdfium_ausente_retorna_none(self, tmp_path: Path) -> None:
        """Sem pypdfium2 instalado, OCR devolve None sem crashar."""
        arq = tmp_path / "imagem.pdf"
        arq.write_bytes(b"%PDF-1.4\n")

        import builtins

        original_import = builtins.__import__

        def raise_on_pypdfium(name, *args, **kwargs):
            if name.startswith("pypdfium2"):
                raise ImportError("simulado")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=raise_on_pypdfium):
            resultado = _preview_pdf_via_ocr(arq)
            assert resultado is None

    def test_ocr_erro_interno_retorna_none(self, tmp_path: Path) -> None:
        """Erro no pypdfium ou tesseract é capturado."""
        arq = tmp_path / "corrompido.pdf"
        arq.write_bytes(b"nao-e-um-pdf-real")

        # pypdfium2 vai falhar ao abrir PDF corrompido, mas a função
        # captura a exceção e devolve None.
        resultado = _preview_pdf_via_ocr(arq)
        assert resultado is None
