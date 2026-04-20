"""Expansão de envelopes: PDF compilado, ZIP e EML, mais diagnóstico scan/nativo.

Os 2 PDFs reais da inbox observados em 2026-04-19 são compilações
heterogêneas (NFC-e + cupom de garantia no mesmo arquivo). O classifier
opera por PÁGINA, não por arquivo -- então a expansão é pré-requisito
obrigatório, não opcional. ZIP e EML existem por completude (cupons
chegam por e-mail, recibos chegam zipados).

Decisões arquiteturais (alinhadas no chat):

- Page-split via pikepdf (lida com fontes esquisitas que pypdf reclama).
- Limite de 100MB descompactado por envelope ZIP (anti zip bomb).
- EML aninhado: profundidade máxima 2 (anti-loop).
- Validação de path em ZIP/EML: nada de `..` nem caminho absoluto
  (anti-zip-slip).
- Diagnóstico scan/nativo é por página, threshold padrão 50 chars úteis.
- Cleanup: remove o diretório <sha8>/ se TODAS as páginas/membros foram
  classificadas e arquivadas; mantém para auditoria caso contrário.
"""

from __future__ import annotations

import email
import email.message
import email.policy
import re
import shutil
import zipfile
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Literal

import pdfplumber
import pikepdf

from src.intake import sha8_arquivo
from src.intake.glyph_tolerant import extrair_chave_nfe44
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.envelope")

# ============================================================================
# Constantes
# ============================================================================

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_ENVELOPES_BASE: Path = _RAIZ_REPO / "data" / "raw" / "_envelopes"

LIMITE_DESCOMPACTADO_BYTES: int = 100 * 1024 * 1024  # 100 MB
LIMITE_PROFUNDIDADE_EML: int = 2
LIMITE_CHARS_NATIVO: int = 50

DiagnosticoPagina = Literal["nativo", "scan", "misto"]


# ============================================================================
# Estruturas
# ============================================================================


@dataclass(frozen=True)
class PaginaPdf:
    """Uma página extraída de PDF compilado."""

    indice: int  # 1-based, espelha numeração humana
    caminho: Path  # data/raw/_envelopes/pdf_split/<sha8>/pgN.pdf
    diagnostico: DiagnosticoPagina
    texto_nativo: str  # vazio se diagnostico != "nativo"


@dataclass(frozen=True)
class ResultadoEnvelope:
    """Resultado canônico de qualquer expansão de envelope.

    `artefatos` lista os arquivos que devem ser classificados em seguida
    (páginas-pdf, anexos-eml, membros-zip). Vazio se a extração inteira
    falhou. `erros` registra warnings (zip slip, limite estourado, EML
    aninhado profundo demais) para o supervisor.

    `paginas` carrega metadados extras só quando a origem é PDF
    multipage (cada PaginaPdf tem diagnostico + texto_nativo do mesmo
    pass de leitura). Para ZIP/EML, `paginas` fica como tupla vazia.
    """

    sha8_envelope: str
    diretorio_envelope: Path
    artefatos: list[Path]
    erros: list[str]
    paginas: tuple[PaginaPdf, ...] = ()


# ============================================================================
# Page-split de PDF
# ============================================================================


def expandir_pdf_multipage(pdf_path: Path) -> ResultadoEnvelope:
    """Quebra PDF em N PDFs de 1 página em `data/raw/_envelopes/pdf_split/<sha8>/`,
    roda diagnóstico no MESMO pass e devolve metadados completos por página.

    Sempre roda para PDFs com >= 1 página -- mesmo um PDF de 1 página
    é "envelope" para fins de hash + diagnóstico, padroniza o pipeline.

    Devolve `ResultadoEnvelope` com:
      - `artefatos`: caminhos dos PDFs splittados (para o router)
      - `paginas`: tupla de PaginaPdf com indice + diagnostico + texto_nativo
        do MESMO pass de leitura (sem precisar reabrir o PDF no router)

    Em caso de erro irrecuperável (PDF corrompido), devolve
    `artefatos=[]`, `paginas=()`, `erros=[motivo]` -- não levanta.
    """
    sha8 = sha8_arquivo(pdf_path)
    diretorio = _ENVELOPES_BASE / "pdf_split" / sha8
    diretorio.mkdir(parents=True, exist_ok=True)
    erros: list[str] = []

    try:
        pdf_origem = pikepdf.open(pdf_path)
    except (pikepdf.PdfError, FileNotFoundError) as exc:
        erro = f"falha ao abrir PDF {pdf_path}: {exc}"
        logger.error(erro)
        return ResultadoEnvelope(
            sha8_envelope=sha8,
            diretorio_envelope=diretorio,
            artefatos=[],
            erros=[erro],
            paginas=(),
        )

    artefatos: list[Path] = []
    paginas_meta: list[PaginaPdf] = []
    with pdf_origem:
        for indice, _ in enumerate(pdf_origem.pages, start=1):
            destino = diretorio / f"pg{indice}.pdf"
            try:
                _gravar_pagina(pdf_origem, indice - 1, destino)
            except (pikepdf.PdfError, OSError) as exc:
                erros.append(f"pg{indice}: falha ao gravar split: {exc}")
                continue
            artefatos.append(destino)
            diagnostico, texto = diagnosticar_pagina(destino)
            paginas_meta.append(
                PaginaPdf(
                    indice=indice,
                    caminho=destino,
                    diagnostico=diagnostico,
                    texto_nativo=texto if diagnostico == "nativo" else "",
                )
            )

    logger.info(
        "expandir_pdf_multipage: %s -> %d páginas em %s (diagnósticos: %s)",
        pdf_path.name,
        len(artefatos),
        diretorio,
        ", ".join(f"pg{p.indice}={p.diagnostico}" for p in paginas_meta),
    )
    return ResultadoEnvelope(
        sha8_envelope=sha8,
        diretorio_envelope=diretorio,
        artefatos=artefatos,
        erros=erros,
        paginas=tuple(paginas_meta),
    )


def _gravar_pagina(pdf_origem: pikepdf.Pdf, indice_zero_based: int, destino: Path) -> None:
    saida = pikepdf.Pdf.new()
    with saida:
        saida.pages.append(pdf_origem.pages[indice_zero_based])
        saida.save(destino)


# ============================================================================
# Diagnóstico scan/nativo (por página)
# ============================================================================


def diagnosticar_pagina(
    pdf_pagina_path: Path,
    limite_chars: int = LIMITE_CHARS_NATIVO,
) -> tuple[DiagnosticoPagina, str]:
    """Devolve (diagnostico, texto_extraido).

    Critério:
      - "nativo": texto extraído >= limite_chars úteis
      - "scan":   texto < limite E pelo menos 1 imagem cobrindo > 80% da página
      - "misto":  qualquer outro caso (página vazia, rodapé só com QR sem imagem grande)

    "misto" é o sinal para o orquestrador mandar a página para
    `data/raw/_classificar/_aguardando_ocr/` e pedir intervenção humana
    ou OCR pesado posterior.
    """
    try:
        with pdfplumber.open(pdf_pagina_path) as pdf:
            if not pdf.pages:
                return "misto", ""
            pagina = pdf.pages[0]
            texto = pagina.extract_text() or ""
            chars_uteis = len(re.sub(r"\s+", "", texto))
            if chars_uteis >= limite_chars:
                return "nativo", texto
            tem_imagem_grande = _tem_imagem_grande(pagina)
            if tem_imagem_grande:
                return "scan", ""
            return "misto", texto
    except Exception as exc:  # pikepdf/pdfplumber podem levantar variedade
        logger.warning("diagnosticar_pagina %s falhou: %s", pdf_pagina_path, exc)
        return "misto", ""


def _tem_imagem_grande(pagina) -> bool:  # type: pdfplumber.Page
    """Devolve True se houver pelo menos 1 imagem cobrindo > 80% da página."""
    if not pagina.images:
        return False
    area_pagina = pagina.width * pagina.height
    if area_pagina <= 0:
        return False
    for img in pagina.images:
        largura = img.get("width", 0) or 0
        altura = img.get("height", 0) or 0
        if (largura * altura) / area_pagina > 0.80:
            return True
    return False


# ============================================================================
# Identificador natural por tipo (dedup intra-arquivo)
# ============================================================================

# Regex de identificador único por tipo de documento.
# Ampliar conforme novos tipos pedirem dedup intra-PDF.
_REGEX_BILHETE_INDIVIDUAL: re.Pattern[str] = re.compile(
    r"BILHETE\s+INDIVIDUAL[:\s]+(\d{12,18})", re.IGNORECASE
)


def hash_identificador_natural(texto: str, tipo: str | None) -> str | None:
    """Devolve identificador natural extraído do conteúdo, ou None.

    Usado para dedup intra-PDF antes do classifier comprometer a página
    para a pasta canônica. Exemplos:
      - cupom_garantia_estendida: número do bilhete (15 dígitos)
      - nfce_consumidor_eletronica / danfe_nfe55 / xml_nfe: chave 44
    Quando `tipo` é None ou desconhecido, devolve None -- a dedup global
    fica a cargo do grafo (Sprint 42).
    """
    if not tipo:
        return None
    if tipo in {"nfce_consumidor_eletronica", "danfe_nfe55", "xml_nfe"}:
        return extrair_chave_nfe44(texto)
    if tipo == "cupom_garantia_estendida":
        match = _REGEX_BILHETE_INDIVIDUAL.search(texto)
        return match.group(1) if match else None
    return None


# ============================================================================
# ZIP (anti zip-slip e zip-bomb)
# ============================================================================


def expandir_zip(zip_path: Path) -> ResultadoEnvelope:
    """Expande ZIP em `data/raw/_envelopes/zip/<sha8>/`.

    Defesas obrigatórias:
      - todo membro deve ter path RELATIVO sem `..` e sem absoluto
      - soma do tamanho descompactado <= LIMITE_DESCOMPACTADO_BYTES
      - tipos não-arquivo (links, devices) são recusados

    Falha de defesa: registra em `erros`, pula o membro e continua. Se
    falhar a abertura do ZIP em si, devolve `artefatos=[]`.
    """
    sha8 = sha8_arquivo(zip_path)
    diretorio = _ENVELOPES_BASE / "zip" / sha8
    diretorio.mkdir(parents=True, exist_ok=True)
    erros: list[str] = []
    artefatos: list[Path] = []

    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        erro = f"ZIP inválido {zip_path}: {exc}"
        logger.error(erro)
        return ResultadoEnvelope(
            sha8_envelope=sha8, diretorio_envelope=diretorio, artefatos=[], erros=[erro]
        )

    with zf:
        soma_descompactada = 0
        for membro in zf.infolist():
            if membro.is_dir():
                continue
            problema = _validar_membro_zip(membro)
            if problema:
                erros.append(problema)
                continue
            soma_descompactada += membro.file_size
            if soma_descompactada > LIMITE_DESCOMPACTADO_BYTES:
                erros.append(
                    f"limite descompactado excedido em {membro.filename} "
                    f"({soma_descompactada} > {LIMITE_DESCOMPACTADO_BYTES} bytes)"
                )
                break
            destino = _resolver_destino_sem_colisao(diretorio, Path(membro.filename).name)
            try:
                with zf.open(membro) as origem, destino.open("wb") as out:
                    shutil.copyfileobj(origem, out)
            except OSError as exc:
                erros.append(f"falha ao extrair {membro.filename}: {exc}")
                continue
            artefatos.append(destino)

    logger.info(
        "expandir_zip: %s -> %d arquivos (%d aviso(s)) em %s",
        zip_path.name,
        len(artefatos),
        len(erros),
        diretorio,
    )
    return ResultadoEnvelope(
        sha8_envelope=sha8, diretorio_envelope=diretorio, artefatos=artefatos, erros=erros
    )


def _resolver_destino_sem_colisao(diretorio: Path, nome_basico: str) -> Path:
    """Resolve `diretorio/nome_basico` evitando sobrescrita silenciosa.

    Se já existir, sufixa o stem com `_1`, `_2`, ... até achar slot livre.
    Mantém a extensão original.

    Caso real: ZIP bancário com `janeiro/extrato.pdf` + `fevereiro/extrato.pdf`.
    Achatar sem desambiguar perderia o segundo silenciosamente.
    """
    destino = diretorio / nome_basico
    if not destino.exists():
        return destino
    stem = destino.stem
    suffix = destino.suffix
    contador = 1
    while True:
        candidato = diretorio / f"{stem}_{contador}{suffix}"
        if not candidato.exists():
            return candidato
        contador += 1


def _validar_membro_zip(membro: zipfile.ZipInfo) -> str | None:
    """Devolve string de erro se o membro deve ser recusado, ou None."""
    nome = membro.filename
    if not nome:
        return "membro com nome vazio recusado"
    p = Path(nome)
    if p.is_absolute():
        return f"path absoluto recusado: {nome!r}"
    partes_normalizadas = p.parts
    if ".." in partes_normalizadas:
        return f"path com '..' recusado (zip-slip): {nome!r}"
    # Tipos não-arquivo: bit 0xA000 = symlink, 0x4000 = diretório (já filtramos)
    modo_externo = membro.external_attr >> 16
    if modo_externo and (modo_externo & 0xF000) == 0xA000:
        return f"symlink recusado: {nome!r}"
    return None


# ============================================================================
# EML (anti-loop por profundidade)
# ============================================================================


def extrair_anexos_eml(
    eml_path: Path,
    profundidade_max: int = LIMITE_PROFUNDIDADE_EML,
) -> ResultadoEnvelope:
    """Extrai anexos de e-mail .eml em `data/raw/_envelopes/eml_anexos/<sha8>/`.

    Profundidade máxima protege contra EML que contém EML aninhado
    indefinidamente. Anexos `message/rfc822` consomem 1 nível; abaixo do
    limite, são extraídos como artefato bruto e o pipeline reprocessa.
    """
    sha8 = sha8_arquivo(eml_path)
    diretorio = _ENVELOPES_BASE / "eml_anexos" / sha8
    diretorio.mkdir(parents=True, exist_ok=True)
    erros: list[str] = []

    try:
        with eml_path.open("rb") as f:
            mensagem = email.message_from_binary_file(f, policy=email.policy.default)
    except (OSError, email.errors.MessageError) as exc:
        erro = f"EML inválido {eml_path}: {exc}"
        logger.error(erro)
        return ResultadoEnvelope(
            sha8_envelope=sha8, diretorio_envelope=diretorio, artefatos=[], erros=[erro]
        )

    artefatos: list[Path] = []
    _percorrer_eml(
        mensagem,
        diretorio=diretorio,
        artefatos=artefatos,
        erros=erros,
        profundidade_atual=0,
        profundidade_max=profundidade_max,
    )

    logger.info(
        "extrair_anexos_eml: %s -> %d anexos (%d aviso(s)) em %s",
        eml_path.name,
        len(artefatos),
        len(erros),
        diretorio,
    )
    return ResultadoEnvelope(
        sha8_envelope=sha8, diretorio_envelope=diretorio, artefatos=artefatos, erros=erros
    )


def _percorrer_eml(
    mensagem: EmailMessage,
    diretorio: Path,
    artefatos: list[Path],
    erros: list[str],
    profundidade_atual: int,
    profundidade_max: int,
) -> None:
    if profundidade_atual > profundidade_max:
        erros.append(f"profundidade EML > {profundidade_max} -- ignorado")
        return
    for parte in mensagem.iter_parts():
        # IMPORTANTE -- testar message/rfc822 ANTES de is_multipart().
        # Anexos message/rfc822 também respondem `is_multipart()=True`
        # (pelo wrapper MIMEMessage), e cairíamos no branch errado sem
        # incrementar profundidade -> recursão infinita até stack-overflow.
        content_type = parte.get_content_type()
        if content_type == "message/rfc822":
            payloads = parte.get_payload()
            interior = payloads[0] if isinstance(payloads, list) and payloads else payloads
            if interior is not None:
                _percorrer_eml(
                    interior,
                    diretorio=diretorio,
                    artefatos=artefatos,
                    erros=erros,
                    profundidade_atual=profundidade_atual + 1,
                    profundidade_max=profundidade_max,
                )
            continue
        if parte.is_multipart():
            _percorrer_eml(
                parte,
                diretorio=diretorio,
                artefatos=artefatos,
                erros=erros,
                profundidade_atual=profundidade_atual,
                profundidade_max=profundidade_max,
            )
            continue
        nome = parte.get_filename()
        if not nome:
            continue
        # Anti zip-slip também no EML
        nome_seguro = Path(nome).name
        destino = _resolver_destino_sem_colisao(diretorio, nome_seguro)
        try:
            payload = parte.get_payload(decode=True)
            if payload is None:
                continue
            destino.write_bytes(payload)
        except OSError as exc:
            erros.append(f"falha ao gravar anexo {nome!r}: {exc}")
            continue
        artefatos.append(destino)


# ============================================================================
# Cleanup pós-classificação
# ============================================================================


def cleanup_envelope(diretorio_envelope: Path, sucesso_total: bool) -> bool:
    """Remove o diretório <sha8>/ se sucesso_total; mantém para auditoria caso contrário.

    Devolve True se removeu, False se manteve. Não levanta -- envelopes
    intactos são preferíveis a crashes silenciosos no cleanup.

    Política definida na Sprint 41 (alinhada no chat): se TODAS as
    páginas/membros do envelope foram classificadas e arquivadas em
    pasta canônica, o split é descartável. Se qualquer um caiu em
    `_classificar/`, o envelope original fica para o supervisor
    reconstruir o contexto.
    """
    if not sucesso_total:
        logger.info("envelope mantido para auditoria: %s", diretorio_envelope)
        return False
    if not diretorio_envelope.exists():
        return False
    try:
        shutil.rmtree(diretorio_envelope)
        logger.info("envelope removido (sucesso total): %s", diretorio_envelope)
        return True
    except OSError as exc:
        logger.warning("falha ao remover envelope %s: %s", diretorio_envelope, exc)
        return False


# "Quem abre a caixa precisa estar pronto para o que sai dela." -- Pandora, paráfrase
