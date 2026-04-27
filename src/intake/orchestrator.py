"""Orquestrador do intake: junta classifier + envelope + preview + router num único
ponto de entrada por arquivo da inbox.

Função principal:

    relatorio = processar_arquivo_inbox(caminho_inbox, pessoa="andre")  # noqa: accent

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
from src.intake.classifier import Decisao
from src.intake.extractors_envelope import (
    PaginaPdf,
    ResultadoEnvelope,
    expandir_pdf_multipage,
    expandir_zip,
    extrair_anexos_eml,
)
from src.intake.heterogeneidade import e_heterogeneo, e_heterogeneo_por_classificacao
from src.intake.pessoa_detector import detectar_pessoa
from src.intake.preview import gerar_preview
from src.intake.registry import detectar_tipo
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

    Quando `pessoa == "_indefinida"`, dispara auto-detect (Sprint 41b):
    extrai CPF do primeiro preview disponível, consulta
    `mappings/cpfs_pessoas.yaml`; fallback para path; fallback para `casal`.

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
    # Sprint 97: lembramos se o split foi forçado (e_heterogeneo True) ou
    # tentativo (PDF multipage sem identificadores únicos -- caller decide
    # depois de classificar).
    split_forcado = tipo_envelope == "pdf" and e_heterogeneo(caminho_inbox)
    resultado_envelope, paginas_meta = _expandir(caminho_inbox, tipo_envelope, sha8)

    # Sprint 41b: auto-detect de pessoa antes do loop de classificação.
    # Decide UMA vez por arquivo da inbox -- todos os artefatos do mesmo PDF
    # compartilham a mesma pessoa (segurado/destinatário do documento).
    pessoa_resolvida = pessoa
    if pessoa_resolvida == "_indefinida":
        preview_para_pessoa = _primeiro_preview_disponivel(
            resultado_envelope.artefatos, paginas_meta, tipo_envelope
        )
        pessoa_resolvida, fonte = detectar_pessoa(caminho_inbox, preview_para_pessoa)
        logger.info(
            "pessoa auto-detectada para %s: %s (fonte: %s)",
            caminho_inbox.name,
            pessoa_resolvida,
            fonte,
        )

    pares: list[tuple[Path, Decisao]] = []
    for indice, artefato in enumerate(resultado_envelope.artefatos):
        sub_mime, preview_texto = _preview_para_artefato(
            artefato=artefato,
            indice_no_envelope=indice,
            tipo_envelope=tipo_envelope,
            paginas_meta=paginas_meta,
        )
        # Sprint 41c: usa registry (legado + YAML) em vez de classifier direto
        decisao = detectar_tipo(artefato, sub_mime, preview_texto, pessoa=pessoa_resolvida)
        pares.append((artefato, decisao))

    # Sprint 97: reversão de split-tentativo. Se o split não foi forçado
    # por identificadores únicos (Sprint 41d) e a classificação por página
    # não detectou heterogeneidade (≤ 1 tipo canônico distinto entre as
    # páginas), reverter para single envelope -- evita fragmentar extratos
    # bancários scaneados que caem em pesquisa de identificadores vazia.
    if tipo_envelope == "pdf" and not split_forcado and len(resultado_envelope.artefatos) >= 2:
        tipos_paginas = [d.tipo for _, d in pares]
        if not e_heterogeneo_por_classificacao(tipos_paginas):
            logger.info(
                "Sprint 97: reverter para single (split tentativo não confirmou "
                "heterogeneidade) -- %s, tipos=%s",
                caminho_inbox.name,
                tipos_paginas,
            )
            from src.intake import extractors_envelope as env

            # Limpa as páginas do split tentativo antes de criar o single envelope
            _descartar_split_tentativo(resultado_envelope)
            resultado_envelope = _envelope_single_file(caminho_inbox, sha8, env._ENVELOPES_BASE)
            paginas_meta = ()
            # Re-classifica o PDF inteiro como artefato único
            pares = []
            for indice, artefato in enumerate(resultado_envelope.artefatos):
                sub_mime, preview_texto = _preview_para_artefato(
                    artefato=artefato,
                    indice_no_envelope=indice,
                    tipo_envelope=tipo_envelope,
                    paginas_meta=paginas_meta,
                )
                decisao = detectar_tipo(artefato, sub_mime, preview_texto, pessoa=pessoa_resolvida)
                pares.append((artefato, decisao))
        else:
            logger.info(
                "Sprint 97: heterogeneidade por classificação confirmada -- %s, tipos=%s",
                caminho_inbox.name,
                tipos_paginas,
            )

    return rotear_lote(
        arquivo_inbox=caminho_inbox,
        sha8_envelope=resultado_envelope.sha8_envelope,
        diretorio_envelope=resultado_envelope.diretorio_envelope,
        pares_artefato_decisao=pares,
        erros_envelope=resultado_envelope.erros,
    )


def _descartar_split_tentativo(resultado_envelope: ResultadoEnvelope) -> None:
    """Remove páginas geradas por split tentativo quando vamos reverter para single.

    Sprint 97: usado apenas quando classificação por página confirmou que
    o PDF é homogêneo. Não levanta -- falha silenciosa, a auditoria fica
    com o original em `_envelopes/originais/<sha8>.pdf`.
    """
    for pagina in resultado_envelope.artefatos:
        try:
            if pagina.exists():
                pagina.unlink()
        except OSError as exc:
            logger.warning("falha ao descartar página tentativa %s: %s", pagina, exc)
    try:
        if resultado_envelope.diretorio_envelope.exists():
            shutil.rmtree(resultado_envelope.diretorio_envelope)
    except OSError as exc:
        logger.warning(
            "falha ao remover diretório de split tentativo %s: %s",
            resultado_envelope.diretorio_envelope,
            exc,
        )


# ============================================================================
# Helpers internos
# ============================================================================


def _expandir(
    caminho_inbox: Path, tipo_envelope: TipoEnvelope, sha8: str
) -> tuple[ResultadoEnvelope, tuple[PaginaPdf, ...]]:
    """Despacha para o envelope correto; devolve (resultado, paginas_meta).

    Sprint 97: a decisão final de page-split para PDFs pode acontecer em
    DUAS etapas. A primeira (Sprint 41d) examina identificadores únicos
    extraíveis de texto nativo. Quando ela retorna False, o orquestrador
    NÃO decide aqui se vai dividir -- expande tentativamente e o caller
    (`processar_arquivo_inbox`) reverte para single se a classificação
    por página confirmar que o PDF é homogêneo.
    """
    from src.intake import extractors_envelope as env

    if tipo_envelope == "pdf":
        # Sprint 41d: page-split direto quando identificadores únicos divergem.
        if e_heterogeneo(caminho_inbox):
            resultado = expandir_pdf_multipage(caminho_inbox)
            return resultado, resultado.paginas
        # Sprint 97: PDF onde identificadores não bastam (scan puro, ou
        # PDF compósito sem chave/bilhete legível por pdfplumber). O caller
        # vai classificar página-a-página e decidir se mantém o split.
        # Para PDFs claramente single-page, vai direto para single envelope.
        if _e_pdf_multipage(caminho_inbox):
            resultado = expandir_pdf_multipage(caminho_inbox)
            return resultado, resultado.paginas
        # PDF de 1 página: single envelope, comportamento original.
        return _envelope_single_file(caminho_inbox, sha8, env._ENVELOPES_BASE), ()
    if tipo_envelope == "zip":
        return expandir_zip(caminho_inbox), ()
    if tipo_envelope == "eml":
        return extrair_anexos_eml(caminho_inbox), ()
    # single (não-PDF)
    resultado = _envelope_single_file(caminho_inbox, sha8, env._ENVELOPES_BASE)
    return resultado, ()


def _e_pdf_multipage(caminho: Path) -> bool:
    """Devolve True se PDF tem >= 2 páginas. Falha silenciosa = False."""
    try:
        import pdfplumber

        with pdfplumber.open(caminho) as pdf:
            return len(pdf.pages) >= 2
    except Exception as exc:  # noqa: BLE001 -- defensivo
        logger.warning("_e_pdf_multipage(%s) falhou: %s", caminho, exc)
        return False


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


def _primeiro_preview_disponivel(
    artefatos: list[Path],
    paginas_meta: tuple[PaginaPdf, ...],
    tipo_envelope: TipoEnvelope,
) -> str | None:
    """Devolve preview do primeiro artefato (para auto-detect de pessoa).

    Reusa `texto_nativo` quando disponível (PDF heterogêneo splittado);
    senão chama gerar_preview no primeiro artefato. None se vazio/falhou.
    """
    if not artefatos:
        return None
    if tipo_envelope == "pdf" and paginas_meta:
        primeira = paginas_meta[0]
        if primeira.diagnostico == "nativo" and primeira.texto_nativo:
            return primeira.texto_nativo
    primeiro_artefato = artefatos[0]
    sub_mime = detectar_mime(primeiro_artefato)
    return gerar_preview(primeiro_artefato, sub_mime)


# "Quem orquestra precisa conhecer a partitura de cada instrumento." -- princípio do regente
