"""Pré-processamento de imagem via ImageMagick CLI (sem opencv/Pillow ML).

Sprint INFRA-PREPROCESS-IMAGEMAGICK. Princípio: subprocess para ``convert``,
zero lib Python de visão computacional. Pipeline canônico eleva confidence
do tesseract de ~30% para ≥70% em cupom térmico fotografado.

Pipeline canônico (universal):

    convert <in> -auto-orient -colorspace Gray -deskew 40% \\
        -despeckle -level 10%,90%,1.0 \\
        -unsharp 0x0.75+0.75+0.008 \\
        -threshold 50% <out>

Variante cupom térmico (mais agressiva):

    convert <in> -auto-orient -colorspace Gray -deskew 40% \\
        -despeckle -despeckle \\
        -level 5%,95%,1.2 \\
        -unsharp 0x1.0+1.0+0.01 \\
        -threshold 45% <out>
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _localizar_convert() -> str:
    caminho = shutil.which("convert")
    if not caminho:
        raise RuntimeError(
            "Binário `convert` (ImageMagick) não encontrado. Instale com "
            "`sudo apt-get install imagemagick`."
        )
    return caminho


def preprocessar_canonico(entrada: Path, saida: Path | None = None) -> Path:
    """Pipeline universal de pré-processamento OCR.

    Aplica: auto-orient → grayscale → deskew → despeckle → level/contrast →
    unsharp → threshold binário. Saída sempre PNG (lossless).

    Args:
        entrada: imagem a processar (JPEG/PNG/HEIC).
        saida: caminho de saída. Se ``None``, gera em ``tempfile``.

    Returns:
        Path da imagem processada.
    """
    binario = _localizar_convert()
    if not entrada.exists():
        raise FileNotFoundError(f"Imagem não existe: {entrada}")

    if saida is None:
        saida = Path(tempfile.mkstemp(prefix="ocr_pre_", suffix=".png")[1])

    cmd = [
        binario,
        str(entrada),
        "-auto-orient",
        "-colorspace",
        "Gray",
        "-deskew",
        "40%",
        "-despeckle",
        "-level",
        "10%,90%,1.0",
        "-unsharp",
        "0x0.75+0.75+0.008",
        "-threshold",
        "50%",
        str(saida),
    ]
    subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
    return saida


def preprocessar_cupom_termico(entrada: Path, saida: Path | None = None) -> Path:
    """Variante mais agressiva para papel térmico fotografado.

    Diferenças vs canônico:
    - Despeckle aplicado 2× (papel térmico tem ruído de granulação).
    - Level 5%,95% (esticar histograma mais).
    - Unsharp 0x1.0 (mais nítido).
    - Threshold 45% (limiar mais baixo, papel térmico tende a desbotar).
    """
    binario = _localizar_convert()
    if not entrada.exists():
        raise FileNotFoundError(f"Imagem não existe: {entrada}")

    if saida is None:
        saida = Path(tempfile.mkstemp(prefix="ocr_termico_", suffix=".png")[1])

    cmd = [
        binario,
        str(entrada),
        "-auto-orient",
        "-colorspace",
        "Gray",
        "-deskew",
        "40%",
        "-despeckle",
        "-despeckle",
        "-level",
        "5%,95%,1.2",
        "-unsharp",
        "0x1.0+1.0+0.01",
        "-threshold",
        "45%",
        str(saida),
    ]
    subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
    return saida


def preprocessar_pdf_pagina(
    pdf: Path,
    n_pagina: int,
    saida: Path | None = None,
    *,
    dpi: int = 300,
) -> Path:
    """Renderiza página do PDF + aplica preprocessamento canônico.

    Equivale a ``pdf_cli.pdf_para_imagens`` + ``preprocessar_canonico``.

    Args:
        pdf: PDF de entrada.
        n_pagina: número da página (1-indexed).
        saida: caminho final processado. ``None`` = tempfile.
        dpi: resolução do render (300 padrão).

    Returns:
        Path da imagem PNG processada.
    """
    from src.ocr_cli.pdf_cli import pdf_para_imagens

    if saida is None:
        saida = Path(tempfile.mkstemp(prefix="ocr_pdfpre_", suffix=".png")[1])

    imagens = pdf_para_imagens(
        pdf,
        dpi=dpi,
        formato="png",
        primeira_pagina=n_pagina,
        ultima_pagina=n_pagina,
    )
    if not imagens:
        raise RuntimeError(f"pdftoppm não gerou imagem para página {n_pagina} de {pdf}")

    return preprocessar_canonico(imagens[0], saida=saida)


# "Pré-processamento bom dispensa modelo grande." -- preprocess_cli
