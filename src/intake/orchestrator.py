"""Orquestrador do intake: junta classifier + envelope + preview + router num único
ponto de entrada por arquivo da inbox.

Função principal:

    relatorio = processar_arquivo_inbox(caminho_inbox, pessoa="andre")

Fluxo:

    1. Detecta MIME (magic bytes + extensão como fallback).
    2. Arquiva original em `_envelopes/originais/<sha8>.<ext>` (auditoria).
    3. Decide caminho de envelope:
         - PDF       -> expandir_pdf_multipage (page-split + diagnóstico)
         - ZIP       -> expandir_zip
         - EML       -> extrair_anexos_eml
         - single    -> cópia única em `_envelopes/single/<sha8>/<nome>`
    4. Para cada artefato do envelope:
         - obtém preview (texto_nativo da página, ou gerar_preview)
         - classifica (Decisao do classifier)
    5. rotear_lote: move artefatos para pasta canônica, faz cleanup.
    6. Devolve RelatorioRoteamento. Caller decide quando descartar a inbox.

Esta função é o ponto de entrada que `inbox_processor.py` chamará para cada
arquivo novo. Em Sprint 41 vive em módulo próprio para reuso por scripts
(prova de fogo, testes de integração, batch externo).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

from src.intake import sha8_arquivo
from src.intake.classifier import Decisao, classificar
from src.intake.extractors_envelope import (
    PaginaPdf,
    ResultadoEnvelope,
    expandir_pdf_multipage,
    expandir_zip,
    extrair_anexos_eml,
)
from src.intake.heterogeneidade import e_heterogeneo
from src.intake.preview import gerar_preview
from src.intake.router import RelatorioRoteamento, arquivar_original, rotear_lote
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.orchestrator")

# ============================================================================
# Detector de MIME minimalista (magic bytes + sufixo)
# ============================================================================

_MAGIC_BYTES: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"PK\x05\x06", "application/zip"),  # ZIP vazio
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),  # validar mais profundo opcionalmente
)
# HEIC: bytes 4-12 contém "ftypheic" ou "ftypmif1" -- exige slice
_HEIC_BRANDS: frozenset[bytes] = frozenset(
    {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis", b"hevm", b"hevs"}
)

_SUFIXO_PARA_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "zip": "application/zip",
    "eml": "message/rfc822",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "heic": "image/heic",
    "heif": "image/heif",
    "webp": "image/webp",
    "xml": "application/xml",
    "csv": "text/csv",
    "txt": "text/plain",
    "ofx": "application/x-ofx",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
}


def detectar_mime(caminho: Path) -> str:
    """Detecta MIME por magic bytes; fallback por extensão.

    Não usa `python-magic` (dep externa); 8 magic bytes cobrem 100% dos
    formatos esperados na Sprint 41. EML é detectado por sufixo (não tem
    magic distintivo).
    """
    try:
        with caminho.open("rb") as f:
            cabecalho = f.read(32)
    except OSError:
        cabecalho = b""

    # Magic bytes diretos
    for prefixo, mime in _MAGIC_BYTES:
        if cabecalho.startswith(prefixo):
            return mime

    # HEIC: precisa olhar bytes 4-12 (formato `ftyp<brand>`)
    if len(cabecalho) >= 12 and cabecalho[4:8] == b"ftyp":
        brand = cabecalho[8:12]
        if brand in _HEIC_BRANDS:
            return "image/heic"

    # XML: `<?xml` ou `<infNFe` no início
    if cabecalho.startswith(b"<?xml") or cabecalho.lstrip().startswith(b"<"):
        return "application/xml"

    # Fallback por sufixo
    suf = caminho.suffix.lstrip(".").lower()
    return _SUFIXO_PARA_MIME.get(suf, "application/octet-stream")


# ============================================================================
# Envelope para single-file
# ============================================================================


def _envelope_single_file(
    caminho_inbox: Path, sha8: str, base_envelopes: Path
) -> ResultadoEnvelope:
    """Envelope sintético para arquivos sem multipage (imagem, XML, single PDF).

    Copia o arquivo para `_envelopes/single/<sha8>/<nome_original>` e devolve
    como artefato. Mantém o invariante de que `rotear_artefato` SEMPRE move
    de `_envelopes/<tipo>/<sha8>/...`, nunca da inbox direto -- preserva a
    inbox até `descartar_da_inbox`.
    """
    diretorio = base_envelopes / "single" / sha8
    diretorio.mkdir(parents=True, exist_ok=True)
    destino = diretorio / caminho_inbox.name
    if not destino.exists():
        shutil.copy2(caminho_inbox, destino)
    return ResultadoEnvelope(
        sha8_envelope=sha8,
        diretorio_envelope=diretorio,
        artefatos=[destino],
        erros=[],
    )


# ============================================================================
# Pipeline para um único arquivo da inbox
# ============================================================================

TipoEnvelope = Literal["pdf", "zip", "eml", "single"]


def _decidir_tipo_envelope(mime: str) -> TipoEnvelope:
    if mime == "application/pdf":
        return "pdf"
    if mime == "application/zip":
        return "zip"
    if mime == "message/rfc822":
        return "eml"
    return "single"


def processar_arquivo_inbox(
    caminho_inbox: Path,
    pessoa: str = "_indefinida",
) -> RelatorioRoteamento:
    """Processa UM arquivo da inbox: arquivar original, expandir envelope,
    classificar cada artefato, rotear, devolver relatório.

    NÃO descarta o arquivo da inbox -- caller chama `descartar_da_inbox`
    após gravar evidências (ex.: no grafo da Sprint 42).
    """
    if not caminho_inbox.exists():
        raise FileNotFoundError(f"arquivo da inbox não existe: {caminho_inbox}")

    mime = detectar_mime(caminho_inbox)
    logger.info("processar_arquivo_inbox: %s (mime=%s)", caminho_inbox.name, mime)

    arquivar_original(caminho_inbox)
    sha8 = sha8_arquivo(caminho_inbox)

    tipo_envelope = _decidir_tipo_envelope(mime)
    resultado_envelope, paginas_meta = _expandir(caminho_inbox, tipo_envelope, sha8)

    pares: list[tuple[Path, Decisao]] = []
    for indice, artefato in enumerate(resultado_envelope.artefatos):
        sub_mime, preview_texto = _preview_para_artefato(
            artefato=artefato,
            indice_no_envelope=indice,
            tipo_envelope=tipo_envelope,
            paginas_meta=paginas_meta,
        )
        decisao = classificar(artefato, sub_mime, preview_texto or "", pessoa=pessoa)
        pares.append((artefato, decisao))

    return rotear_lote(
        arquivo_inbox=caminho_inbox,
        sha8_envelope=resultado_envelope.sha8_envelope,
        diretorio_envelope=resultado_envelope.diretorio_envelope,
        pares_artefato_decisao=pares,
        erros_envelope=resultado_envelope.erros,
    )


# ============================================================================
# Helpers internos
# ============================================================================


def _expandir(
    caminho_inbox: Path, tipo_envelope: TipoEnvelope, sha8: str
) -> tuple[ResultadoEnvelope, tuple[PaginaPdf, ...]]:
    """Despacha para o envelope correto; devolve (resultado, paginas_meta)."""
    from src.intake import extractors_envelope as env

    if tipo_envelope == "pdf":
        # Sprint 41d: page-split SÓ se >1 documento lógico distinto detectado.
        # Sem isso, extratos bancários multipage fragmentam (cabeçalho só na pg1).
        if e_heterogeneo(caminho_inbox):
            resultado = expandir_pdf_multipage(caminho_inbox)
            return resultado, resultado.paginas
        # PDF homogêneo: 1 artefato só, single envelope
        return _envelope_single_file(caminho_inbox, sha8, env._ENVELOPES_BASE), ()
    if tipo_envelope == "zip":
        return expandir_zip(caminho_inbox), ()
    if tipo_envelope == "eml":
        return extrair_anexos_eml(caminho_inbox), ()
    # single (não-PDF)
    resultado = _envelope_single_file(caminho_inbox, sha8, env._ENVELOPES_BASE)
    return resultado, ()


def _preview_para_artefato(
    artefato: Path,
    indice_no_envelope: int,
    tipo_envelope: TipoEnvelope,
    paginas_meta: tuple[PaginaPdf, ...],
) -> tuple[str, str | None]:
    """Devolve (mime_do_artefato, preview_texto_ou_None).

    Para PDF page-split, reusa `texto_nativo` já calculado pelo envelope
    (zero re-leitura). Para outros, detecta mime e roda gerar_preview.
    """
    if tipo_envelope == "pdf" and indice_no_envelope < len(paginas_meta):
        pagina = paginas_meta[indice_no_envelope]
        if pagina.diagnostico == "nativo":
            return "application/pdf", pagina.texto_nativo
        # scan ou misto: PDF de 1 página com imagem; preview = OCR via gerar_preview
        # (que vai abrir o PDF de novo, mas não tem como evitar -- texto não existe)
        return "application/pdf", gerar_preview(artefato, "application/pdf")

    sub_mime = detectar_mime(artefato)
    return sub_mime, gerar_preview(artefato, sub_mime)


# "Quem orquestra precisa conhecer a partitura de cada instrumento." -- princípio do regente
