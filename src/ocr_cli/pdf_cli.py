"""Wrappers para binários do poppler-utils (pdftotext, pdftoppm, pdfimages, pdfinfo).

Sprint INFRA-OCR-CLI-NATIVO. Princípio: subprocess direto. Determinístico
e sem dependência de pdfplumber/pdfminer/fitz para extração estrutural.

API:
- ``extrair_pdf_texto_nativo(pdf)``: pdftotext -layout, retorna texto.
- ``pdf_para_imagens(pdf, dpi)``: pdftoppm, retorna lista de paths PNG.
- ``extrair_imagens_embutidas(pdf)``: pdfimages, retorna lista de paths.
- ``info_pdf(pdf)``: pdfinfo, retorna dict de metadados.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _localizar(binario: str) -> str:
    caminho = shutil.which(binario)
    if not caminho:
        raise RuntimeError(
            f"Binário `{binario}` não encontrado no PATH. Instale com "
            f"`sudo apt-get install poppler-utils`."
        )
    return caminho


def extrair_pdf_texto_nativo(caminho: Path, *, layout: bool = True, encoding: str = "UTF-8") -> str:
    """Executa ``pdftotext -layout <pdf> -`` e devolve texto.

    Para PDFs com texto nativo (NFCe, holerite, fatura): muito mais rápido
    e preciso que OCR. Para PDFs scan, retorna string vazia ou ruído.

    Args:
        caminho: arquivo PDF.
        layout: preserva layout original (texto multi-coluna).
        encoding: encoding de saída (UTF-8 padrão).

    Returns:
        Texto extraído.
    """
    binario = _localizar("pdftotext")
    if not caminho.exists():
        raise FileNotFoundError(f"PDF não existe: {caminho}")

    cmd = [binario]
    if layout:
        cmd.append("-layout")
    cmd.extend(["-enc", encoding, str(caminho), "-"])

    proc = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, check=True
    )
    return proc.stdout


def pdf_para_imagens(
    caminho: Path,
    *,
    dpi: int = 300,
    formato: str = "png",
    primeira_pagina: int | None = None,
    ultima_pagina: int | None = None,
    diretorio_saida: Path | None = None,
) -> list[Path]:
    """Converte PDF em imagens usando ``pdftoppm``.

    Args:
        caminho: PDF de entrada.
        dpi: resolução (300 padrão; suficiente para OCR).
        formato: ``png`` ou ``jpeg``.
        primeira_pagina/ultima_pagina: range opcional.
        diretorio_saida: se ``None``, usa ``tempfile.mkdtemp()``.

    Returns:
        Lista de paths das imagens geradas, ordenada por número de página.
    """
    binario = _localizar("pdftoppm")
    if not caminho.exists():
        raise FileNotFoundError(f"PDF não existe: {caminho}")

    if diretorio_saida is None:
        diretorio_saida = Path(tempfile.mkdtemp(prefix="ocr_pdf_"))
    else:
        diretorio_saida.mkdir(parents=True, exist_ok=True)

    prefixo = diretorio_saida / caminho.stem
    cmd = [binario, "-r", str(dpi)]
    if formato == "png":
        cmd.append("-png")
    elif formato == "jpeg":
        cmd.append("-jpeg")
    if primeira_pagina is not None:
        cmd.extend(["-f", str(primeira_pagina)])
    if ultima_pagina is not None:
        cmd.extend(["-l", str(ultima_pagina)])
    cmd.extend([str(caminho), str(prefixo)])

    subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603

    extensao = "png" if formato == "png" else "jpg"
    imagens = sorted(diretorio_saida.glob(f"{caminho.stem}-*.{extensao}"))
    return imagens


def extrair_imagens_embutidas(
    caminho: Path,
    *,
    diretorio_saida: Path | None = None,
) -> list[Path]:
    """Extrai imagens embutidas no PDF via ``pdfimages``.

    Útil para NFCe que tem QR code e logo embutidos como JPEG.
    """
    binario = _localizar("pdfimages")
    if not caminho.exists():
        raise FileNotFoundError(f"PDF não existe: {caminho}")

    if diretorio_saida is None:
        diretorio_saida = Path(tempfile.mkdtemp(prefix="pdf_imgs_"))
    else:
        diretorio_saida.mkdir(parents=True, exist_ok=True)

    prefixo = diretorio_saida / caminho.stem
    cmd = [binario, "-all", str(caminho), str(prefixo)]
    subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603

    return sorted(
        p for p in diretorio_saida.iterdir() if p.is_file() and p.stem.startswith(caminho.stem)
    )


def info_pdf(caminho: Path) -> dict[str, str]:
    """Retorna metadados do PDF via ``pdfinfo``.

    Chaves típicas: ``Pages``, ``Encrypted``, ``Page size``, ``PDF version``,
    ``Creator``, ``Producer``, ``CreationDate``.
    """
    binario = _localizar("pdfinfo")
    if not caminho.exists():
        raise FileNotFoundError(f"PDF não existe: {caminho}")

    cmd = [binario, str(caminho)]
    proc = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, check=True
    )

    info: dict[str, str] = {}
    for linha in proc.stdout.splitlines():
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        info[chave.strip()] = valor.strip()
    return info


# "PDF é o XML do desespero. CLI nativo é o diff que faz funcionar." -- pdf_cli
