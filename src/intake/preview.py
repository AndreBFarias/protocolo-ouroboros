"""Preview de conteúdo para alimentar o classifier.

API minimalista:

    texto = gerar_preview(caminho, mime)
    # texto: str se conseguiu extrair algo; None se vazio/falhou

Escopo (alinhado no chat):

- PDFs que vieram via `extractors_envelope.expandir_pdf_multipage` JÁ
  trazem o texto nativo no `PaginaPdf.texto_nativo` (mesmo pass de leitura).
  O orquestrador (`inbox_processor.py`) usa aquilo direto -- chamar
  `gerar_preview` para PDF é só fallback defensivo (PDF que entrou na
  pasta de uma decisão sem passar pelo envelope -- improvável, mas a
  função suporta).
- Imagens (JPG/PNG/HEIC): OCR via tesseract a 150 DPI. Lower-resolution
  é deliberado -- preview é para classificação, NÃO para extração final.
  HEIC do iPhone exige `pillow-heif` (registrado no pyproject).
- XML / texto: leitura crua, truncada a `LIMITE_BYTES_TEXTO`.
- Outros MIMEs (zip, eml, ofx, csv, xlsx, ofx, ...): None -- preview
  textual não faz sentido. Quem precisa do conteúdo é o envelope ou o
  extrator dedicado.

Política de erro: NUNCA levanta. Em qualquer falha (binário corrompido,
tesseract sem trained data, HEIC inválido, encoding bizarro), devolve
None. O classifier recebe None como "preview vazio" -> nada casa, vai
para `_classificar/` para revisão humana.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytesseract
from PIL import Image, ImageOps

from src.utils.logger import configurar_logger

logger = configurar_logger("intake.preview")

# pillow-heif registra suporte a HEIC/HEIF no PIL via side-effect do import
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    _HEIC_DISPONIVEL = True
except ImportError:
    _HEIC_DISPONIVEL = False
    logger.warning(
        "pillow-heif indisponível -- previews de HEIC vão devolver None. "
        "Instale com: pip install pillow-heif"
    )

# ============================================================================
# Constantes
# ============================================================================

DPI_OCR_PREVIEW: int = 150
LIMITE_BYTES_TEXTO: int = 64 * 1024  # 64KB de texto bruto basta para preview
TESSERACT_LANG: str = "por+eng"
# Abaixo deste threshold, assume PDF-imagem e aciona fallback OCR (Sprint 89).
MIN_CHARS_TEXTO_NATIVO: int = 50

_MIMES_IMAGEM: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"}
)
_MIMES_TEXTO_CRUO: frozenset[str] = frozenset(
    {"application/xml", "text/xml", "text/plain", "text/csv"}
)


# ============================================================================
# API pública
# ============================================================================


def gerar_preview(caminho: Path, mime: str) -> str | None:
    """Devolve preview textual do arquivo, ou None se não aplicável/falhou.

    Args:
        caminho: arquivo a ler. NÃO precisa existir -- se não existir,
                 devolve None sem levantar.
        mime:    MIME detectado pelo file_detector.

    Returns:
        str com texto extraído (PDF nativo, OCR de imagem, texto cru) ou
        None se o tipo não tem preview textual ou se a extração falhou.
    """
    if not caminho.exists():
        logger.debug("preview: arquivo inexistente %s", caminho)
        return None
    try:
        if mime == "application/pdf":
            return _preview_pdf(caminho)
        if mime in _MIMES_IMAGEM:
            return _preview_imagem(caminho)
        if mime in _MIMES_TEXTO_CRUO:
            return _preview_texto_cru(caminho)
    except Exception as exc:  # noqa: BLE001 -- defensivo, não queremos crashar
        logger.warning("preview falhou para %s (mime=%s): %s", caminho, mime, exc)
        return None
    logger.debug("preview: mime %s sem handler -- None", mime)
    return None


# ============================================================================
# Handlers por tipo
# ============================================================================


def _preview_pdf(caminho: Path) -> str | None:
    """Fallback para PDFs que NÃO vieram via expandir_pdf_multipage.

    Em produção, o orquestrador da Sprint 41 prefere o texto já extraído
    em `PaginaPdf.texto_nativo` (mesmo pass do page-split). Esta função
    existe para defesa em profundidade quando algum caller chamar
    `gerar_preview` diretamente sobre um PDF não-envelope.

    Lê APENAS a primeira página -- preview é para classificação, basta.
    Se pdfplumber devolver texto muito curto (< MIN_CHARS_TEXTO_NATIVO),
    tenta fallback OCR via pypdfium2 + tesseract (P1.2 / Sprint 89 --
    PDFs-imagem sem texto extraível).
    """
    with pdfplumber.open(caminho) as pdf:
        if not pdf.pages:
            return None
        texto = pdf.pages[0].extract_text() or ""
        texto_limpo = texto.strip()
        if len(texto_limpo) >= MIN_CHARS_TEXTO_NATIVO:
            return texto_limpo
    # Fallback OCR: PDF-imagem (notas de garantia, scans sem layer de texto).
    return _preview_pdf_via_ocr(caminho)


def _preview_pdf_via_ocr(caminho: Path, paginas: int = 1) -> str | None:
    """Renderiza as primeiras páginas com pypdfium2 e passa por tesseract.

    Custo: ~1-3s por página. Só é chamado como fallback quando pdfplumber
    retorna texto curto. Não aplica preprocessamento (deskew/threshold) --
    preview é para casar regex de classificação, não extração fina.
    """
    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.warning("preview OCR pulado (pypdfium2 ausente): %s", caminho.name)
        return None
    try:
        pdf = pdfium.PdfDocument(str(caminho))
        partes: list[str] = []
        for i in range(min(paginas, len(pdf))):
            pagina = pdf[i]
            pil_img = pagina.render(scale=2).to_pil()
            texto = pytesseract.image_to_string(pil_img, lang=TESSERACT_LANG)
            if texto:
                partes.append(texto)
        resultado = "\n".join(partes).strip()
        return resultado or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("preview OCR falhou em %s: %s", caminho.name, exc)
        return None


def _preview_imagem(caminho: Path) -> str | None:
    """OCR baixa-resolução para classificação. Aceita JPG/PNG/HEIC/WebP.

    Aplica `ImageOps.exif_transpose` para corrigir rotação de fotos do
    celular (Armadilha A41-2 da Sprint 41). HEIC só funciona se
    `pillow-heif` estiver instalado.
    """
    extensao = caminho.suffix.lower().lstrip(".")
    if extensao in {"heic", "heif"} and not _HEIC_DISPONIVEL:
        logger.info("preview HEIC ignorado (pillow-heif ausente): %s", caminho)
        return None

    with Image.open(caminho) as imagem:
        imagem = ImageOps.exif_transpose(imagem)
        # Redimensionar para DPI_OCR_PREVIEW se maior -- evita gastar CPU
        # com fotos 12MP do iPhone só pro preview classificar
        imagem = _normalizar_dpi(imagem, DPI_OCR_PREVIEW)
        texto = pytesseract.image_to_string(imagem, lang=TESSERACT_LANG)
    return texto.strip() or None


def _preview_texto_cru(caminho: Path) -> str | None:
    """Lê os primeiros LIMITE_BYTES_TEXTO bytes; tenta UTF-8 com fallback.

    XML/CSV/text-plain: o classifier precisa de pistas no início (tag
    <infNFe>, header `Data,Valor,...`, etc.). Truncar é seguro para
    classificação.
    """
    bruto = caminho.read_bytes()[:LIMITE_BYTES_TEXTO]
    try:
        return bruto.decode("utf-8")
    except UnicodeDecodeError:
        # Cupons antigos e exports bancários frequentemente vêm em latin-1
        return bruto.decode("latin-1", errors="replace")


# ============================================================================
# Internals
# ============================================================================


def _normalizar_dpi(imagem: Image.Image, dpi_alvo: int) -> Image.Image:
    """Reduz a imagem se a maior dimensão exceder dpi_alvo * fator_seguranca.

    Heurística simples -- assume página A4 ~210mm. Se a imagem tem largura
    > 1.500 px (suficiente para 150 DPI numa A4), redimensiona para 1.500 px
    de largura mantendo aspect ratio. Para preview-OCR, isso é abundante.
    """
    largura_alvo_max = int(dpi_alvo * 10)  # ~1500 px em 150 DPI
    largura, altura = imagem.size
    if largura <= largura_alvo_max:
        return imagem
    nova_altura = int(altura * largura_alvo_max / largura)
    return imagem.resize((largura_alvo_max, nova_altura), Image.LANCZOS)


def extrair_preview_completo(arquivo: Path, max_chars: int = 4000) -> str:
    """AUDIT-IMPORT-CAMADA: helper compartilhado para alimentar
    pessoa_detector/ocr_fallback. Diferente de `gerar_preview` (que recebe
    MIME e devolve None em falha), este aceita Path direto e devolve string
    vazia em qualquer falha.

    Estratégia em camadas para PDFs: pdfplumber primeiro (texto nativo),
    fallback OCR via pypdfium2 + tesseract.

    Para imagens (.jpg/.jpeg/.png/.webp): OCR direto.
    Para outros: leitura crua truncada.

    NUNCA levanta. Devolve string vazia em qualquer falha.
    """
    sufixo = arquivo.suffix.lower()

    if sufixo == ".pdf":
        try:
            with pdfplumber.open(arquivo) as pdf:
                pedacos: list[str] = []
                for pagina in pdf.pages[:3]:
                    t = pagina.extract_text() or ""
                    if t.strip():
                        pedacos.append(t)
                texto = "\n".join(pedacos)
                if len(texto) > 50:
                    return texto[:max_chars]
        except Exception as exc:  # noqa: BLE001
            logger.debug("pdfplumber falhou em %s: %s", arquivo.name, exc)

        # Fallback OCR
        try:
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(str(arquivo))
            pedacos = []
            for i in range(min(2, len(pdf))):
                pil = pdf[i].render(scale=2).to_pil()
                t = pytesseract.image_to_string(pil, lang="por") or ""
                if t.strip():
                    pedacos.append(t)
            return "\n".join(pedacos)[:max_chars]
        except Exception as exc:  # noqa: BLE001
            logger.debug("OCR falhou em %s: %s", arquivo.name, exc)
            return ""

    if sufixo in (".jpg", ".jpeg", ".png", ".webp"):
        try:
            img = Image.open(arquivo)
            return pytesseract.image_to_string(img, lang="por")[:max_chars]
        except Exception as exc:  # noqa: BLE001
            logger.debug("OCR imagem falhou em %s: %s", arquivo.name, exc)
            return ""

    try:
        return arquivo.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception:  # noqa: BLE001
        return ""


# "O olhar lê o que o coração já decidiu enxergar." -- Montaigne
