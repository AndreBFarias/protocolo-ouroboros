"""Utilitários OCR compartilhados entre extratores de foto (Sprint 45).

Reutilizáveis por qualquer extrator baseado em imagem (cupom térmico,
contas de serviço fotografadas no futuro, etc.). Evita duplicar lógica
de rotação EXIF, binarização e cache de resultados OCR.

Contratos:

    carregar_imagem_normalizada(caminho)  -> PIL.Image em escala de cinza,
                                             com rotação EXIF aplicada e
                                             autocontraste. Suporta JPG/PNG
                                             e HEIC (com pillow-heif).

    ocr_com_confidence(img, lang="por")   -> tupla (texto, confidence_media).
                                             Confidence é média das
                                             confiabilidades por palavra
                                             devolvidas pelo tesseract,
                                             ignorando tokens inválidos
                                             (-1) e muito baixos (<30).

    cache_key(caminho)                    -> hash SHA-256 do conteúdo da
                                             foto (16 primeiros chars),
                                             usável como nome de arquivo
                                             de cache. Invariante: mesmo
                                             conteúdo → mesma chave,
                                             independente do nome.

    ler_ou_gerar_cache(caminho, gerador,  -> texto OCR. Se já existe cache
                       diretorio_cache)      em `<diretorio>/<hash>.txt`,  # noqa: accent
                                             lê direto; caso contrário
                                             chama `gerador()` e grava.
                                             Evita reprocessar a mesma
                                             foto repetidas vezes.

Pós-processamento numérico (A45-1):

    normalizar_digitos_valor(texto)       -> substitui confusões OCR
                                             típicas ("O" → "0", "l" → "1")
                                             APENAS em trechos que já
                                             parecem valor monetário
                                             ("R$ X,XX"). Nunca globalmente.

Rotação 180° como retry (A45-3) é exposta em:

    rotacionar_180(img)                   -> nova PIL.Image rotacionada.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

from src.utils.logger import configurar_logger

logger: logging.Logger = configurar_logger("extrator_ocr_comum")


# ============================================================================
# Carregamento e normalização de imagem
# ============================================================================


def _importar_pillow_heif_se_preciso(caminho: Path) -> None:
    """Registra pillow-heif no PIL quando a foto é HEIC (A45-7).

    Import condicional com erro explícito. Evita falha silenciosa quando
    o usuário joga foto HEIC na inbox e a biblioteca opcional não está
    instalada.
    """
    if caminho.suffix.lower() not in (".heic", ".heif"):
        return
    try:
        from pillow_heif import register_heif_opener  # type: ignore[import-not-found]
    except ImportError as erro:
        raise RuntimeError(
            f"Foto HEIC {caminho.name} exige 'pillow-heif' instalado. "
            "Rodar: pip install pillow-heif"
        ) from erro
    register_heif_opener()


def carregar_imagem_normalizada(caminho: Path) -> Image.Image:
    """Abre a foto, aplica rotação EXIF, converte para cinza e autocontrasta.

    Pipeline (ordem importa):
      1. HEIC: registra opener (erro explícito se faltar dep).
      2. Abre a imagem.
      3. `exif_transpose` respeita o tag de orientação gravado pela câmera
         (A45 acceptance: "EXIF rotation respeitado").
      4. Converte para escala de cinza ("L") -- OCR térmico pouco se
         beneficia de cor, e cinza estabiliza o contraste.
      5. `autocontrast` espalha o histograma -- compensa fotos com
         iluminação irregular.

    Não aplica binarização (threshold) porque o tesseract internamente
    faz isso de forma adaptativa; binarizar pré-OCR costuma PIORAR
    cupons térmicos com papel amassado.
    """
    _importar_pillow_heif_se_preciso(caminho)
    img = Image.open(caminho)
    img = ImageOps.exif_transpose(img)
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    return img


def rotacionar_180(img: Image.Image) -> Image.Image:
    """Rotaciona 180° -- retry quando foto chega de cabeça para baixo (A45-3)."""
    return img.rotate(180, expand=True)


# ============================================================================
# OCR com confidence
# ============================================================================


_MIN_CONFIDENCE_PALAVRA: int = 30


def ocr_com_confidence(
    img: Image.Image,
    lang: str = "por",
    min_confidence_palavra: int = _MIN_CONFIDENCE_PALAVRA,
) -> tuple[str, float]:
    """Executa tesseract e devolve (texto, confidence_media_percentual).

    - `lang="por"` sempre, conforme A45-5 (mistura lusitano/brasileiro
      é tolerada pelo modelo `por`).
    - Palavras com confidence < `min_confidence_palavra` são descartadas
      do texto mas entram na estatística agregada -- permite ao chamador
      decidir fallback quando a média cai.
    - Devolve confidence em escala 0-100 (tesseract devolve nessa faixa).
    """
    try:
        import pytesseract
    except ImportError as erro:
        raise RuntimeError(
            "pytesseract não disponível. Instalar pytesseract + tesseract-ocr."
        ) from erro

    dados = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    confidences: list[int] = []
    # Agrupa palavras válidas preservando a ordem do tesseract via chave
    # composta (block, par, line) -- o próprio PyTesseract garante ordem
    # de leitura do documento quando itera pela lista.
    texto_linhas: dict[tuple[int, int, int], list[str]] = {}
    chaves_na_ordem: list[tuple[int, int, int]] = []
    for i, bruto in enumerate(dados["conf"]):
        try:
            conf = int(float(bruto))
        except (ValueError, TypeError):
            continue
        if conf < 0:
            continue
        confidences.append(conf)
        texto_palavra = str(dados["text"][i]).strip()
        if not texto_palavra or conf < min_confidence_palavra:
            continue
        chave = (
            int(dados["block_num"][i]),
            int(dados["par_num"][i]),
            int(dados["line_num"][i]),
        )
        if chave not in texto_linhas:
            texto_linhas[chave] = []
            chaves_na_ordem.append(chave)
        texto_linhas[chave].append(texto_palavra)

    media: float = sum(confidences) / len(confidences) if confidences else 0.0
    texto_final = "\n".join(" ".join(texto_linhas[chave]) for chave in chaves_na_ordem)
    return texto_final, media


# ============================================================================
# Cache de OCR
# ============================================================================


def cache_key(caminho: Path) -> str:
    """Hash SHA-256 do CONTEÚDO da foto (A45-6: nunca do nome).

    Evita que o cache sirva resultado antigo quando o usuário re-tira a
    foto com o mesmo nome. Devolve os 16 primeiros caracteres do hex
    (colisão improvável para o volume esperado).
    """
    dados = caminho.read_bytes()
    return hashlib.sha256(dados).hexdigest()[:16]


def ler_ou_gerar_cache(
    caminho: Path,
    gerador: Callable[[], tuple[str, float]],
    diretorio_cache: Path,
) -> tuple[str, float]:
    """Lê o cache do OCR se existe; gera e grava caso contrário.

    Formato do arquivo de cache: primeira linha `#CONFIDENCE=XX.X`, resto
    é o texto OCR. Mantém o arquivo legível por humanos e cacheia a
    confidence também (evita ter que rodar tesseract de novo só para
    decidir fallback).

    Se `gerador()` lança exceção, o cache NÃO é escrito.
    """
    diretorio_cache.mkdir(parents=True, exist_ok=True)
    chave = cache_key(caminho)
    arquivo_cache = diretorio_cache / f"{chave}.txt"

    if arquivo_cache.exists():
        bruto = arquivo_cache.read_text(encoding="utf-8")
        primeira_linha, _, corpo = bruto.partition("\n")
        confidence = _parse_confidence_cabecalho(primeira_linha)
        logger.debug("cache OCR hit: %s", arquivo_cache.name)
        return corpo, confidence

    texto, confidence = gerador()
    conteudo = f"#CONFIDENCE={confidence:.1f}\n{texto}"
    arquivo_cache.write_text(conteudo, encoding="utf-8")
    logger.debug("cache OCR miss -> gravado: %s", arquivo_cache.name)
    return texto, confidence


def _parse_confidence_cabecalho(linha: str) -> float:
    match = re.match(r"#CONFIDENCE=([\d.]+)", linha)
    if not match:
        return 0.0
    try:
        return float(match.group(1))
    except ValueError:
        return 0.0


# ============================================================================
# Pós-processamento de dígitos em valores (A45-1)
# ============================================================================


_REGEX_VALOR_MONETARIO = re.compile(
    r"(R\$\s*)([0-9OoIlSBZ.,\s]+)",
    re.IGNORECASE,
)
_SUBSTITUICOES_DIGITO: dict[str, str] = {
    "O": "0",
    "o": "0",
    "I": "1",
    "l": "1",
    "S": "5",
    "B": "8",
    "Z": "2",
}


def normalizar_digitos_valor(texto: str) -> str:
    """Substitui confusões OCR típicas só em trechos que parecem R$ valor.

    A45-1: tesseract confunde `0`/`O`, `1`/`l`, `5`/`S`, `8`/`B`. Fazer
    substituição global corromperia palavras legítimas (ex: "LEITE 1L"
    viraria "LEITE 11"). A substituição SÓ acontece em trechos que
    casam "R$ <números e letras confundíveis>".
    """

    def _substituir(match: re.Match[str]) -> str:
        prefixo = match.group(1)
        bruto = match.group(2)
        corrigido = "".join(_SUBSTITUICOES_DIGITO.get(c, c) for c in bruto)
        return prefixo + corrigido

    return _REGEX_VALOR_MONETARIO.sub(_substituir, texto)


# "O olho que tudo vê sabe que 99% é legível e 1% é palpite." -- princípio do OCR pragmático
