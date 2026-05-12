"""Wrapper para o binário ``tesseract`` (sem pytesseract).

Sprint INFRA-OCR-CLI-NATIVO. Princípio: subprocess direto, parsing TSV
manual para confidence. Determinístico e sem dependência de lib Python
ML/wrapping.

Fluxo:
1. ``extrair_texto(caminho)`` chama ``tesseract <caminho> stdout -l por --psm 6``
   e devolve string.
2. ``extrair_com_confidence(caminho)`` chama com ``--tsv`` e parseia colunas
   ``conf`` + ``text`` + ``block_num`` + ``par_num`` + ``line_num``,
   reconstruindo texto + confidence média (escala 0-100).

Idioma padrão: ``por``. Tesseract-ocr-por já está instalado no sistema
(verificado via ``tesseract --list-langs``).
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Linguagens canônicas do projeto. O `por` cobre PT-BR e PT-PT.
LANG_PADRAO: str = "por"

# PSM 6 = "Assume a single uniform block of text" — bom para cupom térmico.
# PSM 11 = "Sparse text" — útil para layouts esparsos.
PSM_PADRAO: int = 6

# Confidence mínima por palavra (descartada do texto mas entra na média).
MIN_CONFIDENCE_PALAVRA: int = 30


def _localizar_binario() -> str:
    """Acha caminho do binário tesseract; falha cedo se ausente.

    Padrão (n) defesa em camadas: se o binário não está instalado,
    falhar com mensagem actionable em vez de subprocess silencioso.
    """
    caminho = shutil.which("tesseract")
    if not caminho:
        raise RuntimeError(
            "Binário `tesseract` não encontrado no PATH. Instale com "
            "`sudo apt-get install tesseract-ocr tesseract-ocr-por`."
        )
    return caminho


def extrair_texto(
    caminho: Path,
    *,
    lang: str = LANG_PADRAO,
    psm: int = PSM_PADRAO,
) -> str:
    """Executa ``tesseract <caminho> stdout`` e devolve texto puro.

    Args:
        caminho: caminho da imagem (PNG/JPEG/TIFF) ou PDF (uma página).
        lang: idioma do tesseract (``por`` por padrão).
        psm: page segmentation mode (6 por padrão).

    Returns:
        Texto extraído (pode ser vazio se OCR falhar silenciosamente).

    Raises:
        RuntimeError: binário tesseract ausente.
        subprocess.CalledProcessError: tesseract retornou código != 0.
    """
    binario = _localizar_binario()
    if not caminho.exists():
        raise FileNotFoundError(f"Imagem não existe: {caminho}")

    cmd = [
        binario,
        str(caminho),
        "stdout",
        "-l",
        lang,
        "--psm",
        str(psm),
    ]
    proc = subprocess.run(  # noqa: S603 -- comando fixo, sem injeção
        cmd, capture_output=True, text=True, check=True
    )
    return proc.stdout


def extrair_com_confidence(
    caminho: Path,
    *,
    lang: str = LANG_PADRAO,
    psm: int = PSM_PADRAO,
    min_confidence_palavra: int = MIN_CONFIDENCE_PALAVRA,
) -> tuple[str, float]:
    """Executa tesseract com TSV output e devolve (texto, confidence_media).

    Substitui ``pytesseract.image_to_data(... output_type=Output.DICT)``.

    Args:
        caminho: imagem para OCR.
        lang: idioma.
        psm: page segmentation mode.
        min_confidence_palavra: palavras com confidence < esse valor são
            descartadas do texto final (mas entram na estatística agregada).

    Returns:
        Tupla ``(texto, confidence_media)``. Confidence em escala 0-100.
        Texto preserva ordem de leitura via (block, par, line).
    """
    binario = _localizar_binario()
    if not caminho.exists():
        raise FileNotFoundError(f"Imagem não existe: {caminho}")

    cmd = [
        binario,
        str(caminho),
        "stdout",
        "-l",
        lang,
        "--psm",
        str(psm),
        "tsv",
    ]
    proc = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, check=True
    )
    return _parsear_tsv(proc.stdout, min_confidence_palavra)


def _parsear_tsv(
    tsv: str, min_confidence_palavra: int
) -> tuple[str, float]:
    """Parse manual do TSV do tesseract.

    Formato (12 colunas): level, page_num, block_num, par_num, line_num,
    word_num, left, top, width, height, conf, text.

    Reusa a lógica original de ``_ocr_comum.ocr_com_confidence`` que
    agrupa por (block, par, line) preservando ordem de leitura.
    """
    linhas = tsv.strip().split("\n")
    if not linhas or len(linhas) < 2:
        return "", 0.0

    cabecalho = linhas[0].split("\t")
    try:
        idx_block = cabecalho.index("block_num")
        idx_par = cabecalho.index("par_num")
        idx_line = cabecalho.index("line_num")
        idx_conf = cabecalho.index("conf")
        idx_text = cabecalho.index("text")
    except ValueError as erro:
        raise RuntimeError(
            f"Formato TSV tesseract inesperado: cabeçalho {cabecalho}"
        ) from erro

    confidences: list[int] = []
    texto_linhas: dict[tuple[int, int, int], list[str]] = {}
    chaves_na_ordem: list[tuple[int, int, int]] = []

    for linha in linhas[1:]:
        cols = linha.split("\t")
        if len(cols) <= idx_text:
            continue
        try:
            conf = int(float(cols[idx_conf]))
        except (ValueError, IndexError):
            continue
        if conf < 0:
            continue
        confidences.append(conf)
        texto_palavra = cols[idx_text].strip()
        if not texto_palavra or conf < min_confidence_palavra:
            continue
        try:
            chave = (
                int(cols[idx_block]),
                int(cols[idx_par]),
                int(cols[idx_line]),
            )
        except (ValueError, IndexError):
            continue
        if chave not in texto_linhas:
            texto_linhas[chave] = []
            chaves_na_ordem.append(chave)
        texto_linhas[chave].append(texto_palavra)

    media = sum(confidences) / len(confidences) if confidences else 0.0
    texto_final = "\n".join(
        " ".join(texto_linhas[chave]) for chave in chaves_na_ordem
    )
    return texto_final, media


# "Texto bem ordenado é metade do parser." -- princípio tesseract_cli
