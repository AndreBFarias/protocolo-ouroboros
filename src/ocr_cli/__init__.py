"""Fronteira pública do OCR via CLI nativo (sem libs Python ML).

Sprint INFRA-OCR-CLI-NATIVO (2026-05-09) — substitui pytesseract por
subprocess `tesseract` direto. Princípio canônico do projeto:
ZERO lib Python para OCR; apenas binários CLI (apt-get installable).

Stack:
- ``tesseract`` (CRNN clássico português) via ``tesseract_cli``.
- ``pdftotext``/``pdftoppm``/``pdfimages``/``pdfinfo`` via ``pdf_cli``.
- ImageMagick ``convert`` via ``preprocess_cli``.

Uso típico::

    from src.ocr_cli import (
        extrair_texto, extrair_com_confidence,
        extrair_pdf_texto_nativo, pdf_para_imagens,
        preprocessar_canonico, preprocessar_cupom_termico,
    )

Padrões VALIDATOR_BRIEF: (a) edit incremental, (b) acentuação PT-BR,
(g) citação filosófica no rodapé, (e) sem `pip install` para OCR.
"""

from src.ocr_cli.pdf_cli import (
    extrair_imagens_embutidas,
    extrair_pdf_texto_nativo,
    info_pdf,
    pdf_para_imagens,
)
from src.ocr_cli.preprocess_cli import (
    preprocessar_canonico,
    preprocessar_cupom_termico,
    preprocessar_pdf_pagina,
)
from src.ocr_cli.tesseract_cli import (
    extrair_com_confidence,
    extrair_texto,
)

__all__ = [
    "extrair_texto",
    "extrair_com_confidence",
    "extrair_pdf_texto_nativo",
    "pdf_para_imagens",
    "extrair_imagens_embutidas",
    "info_pdf",
    "preprocessar_canonico",
    "preprocessar_cupom_termico",
    "preprocessar_pdf_pagina",
]

# "Determinismo é o que separa ferramenta de oráculo." -- INFRA-OCR-CLI-NATIVO
