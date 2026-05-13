"""Extrator de NFC-e modelo 65 (mini-cupom 80mm com QR SEFAZ) -- Sprint 44b.

NFC-e (Nota Fiscal Eletrônica de Consumidor) é a versão enxuta da NFe usada
no varejo direto ao consumidor. Distingue-se do DANFE NFe55 pelos dígitos
21-22 da chave 44 (`65` vs `55`), pelo layout 80mm (cupom térmico) e pela
ausência de bloco destinatário formal.

Este extrator assume PDF NATIVO (texto extraível via pdfplumber). Fotos de
cupom térmico são responsabilidade da Sprint 45 (OCR dedicado).

Campos canônicos extraídos:

    chave_44           -- 44 dígitos com DV válido, modelo 65
    numero, serie      -- identificadores SEFAZ  # noqa: accent
    data_emissao       -- YYYY-MM-DD
    cnpj_emitente      -- canônico XX.XXX.XXX/XXXX-XX
    razao_social       -- razão social do emissor
    endereco           -- endereço da loja (multilinha colapsada)
    total              -- R$ (obriga; usa VALOR TOTAL ou VALOR A PAGAR)
    forma_pagamento    -- canônica: PIX | Crédito | Débito | Dinheiro | Vale
    cpf_consumidor     -- opcional, canônico XXX.XXX.XXX-XX
    itens              -- list[dict] com codigo, descricao, qtde, unidade,  # noqa: accent
                          valor_unit, valor_total

Efeitos colaterais: `extrair()` ingere cada NFC-e no grafo via
`src/graph/ingestor_documento.py:ingerir_documento_fiscal` -- cria nó
`documento` + 1 nó `fornecedor` + N nós `item` + arestas
`fornecido_por`/`contem_item`/`ocorre_em`. Retorna lista VAZIA de
`base.Transacao` -- o total já aparece no extrato bancário.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.intake.glyph_tolerant import (
    GLYPH_J,
    compilar_regex_tolerante,
    extrair_cnpjs,
    extrair_cpf,
    normalizar_ps5_p55,
)
from src.load import validacao_csv as _validacao_csv
from src.utils.chave_nfe import (
    extrair_modelo,
    valida_digito_verificador,
)
from src.utils.chave_nfe import (
    normalizar as normalizar_chave,
)
from src.utils.logger import configurar_logger
from src.utils.parse_br import parse_valor_br

logger = configurar_logger("nfce_pdf")

EXTENSOES_ACEITAS: tuple[str, ...] = (".pdf",)


# ============================================================================
# Padrões de detecção (glyph-tolerante)
# ============================================================================


RE_MARCA_NFCE_CABECALHO = compilar_regex_tolerante(
    r"Documento\s+Auxiliar\s+da\s+Nota\s+Fiscal\s+de\s+Consumidor"
)
RE_MARCA_NFCE_NUMERO = compilar_regex_tolerante(r"NFC-?e\s*N[ºo°&]")
RE_MARCA_QR_SEFAZ = compilar_regex_tolerante(r"fazenda[\s.]+\w+[\s.]+gov[\s.]+br")


# ============================================================================
# Padrões de cabeçalho
# ============================================================================


RE_CHAVE_44_DIGITOS = re.compile(r"((?:\d{4}\s*){10}\d{4})", re.MULTILINE)
RE_NUMERO_SERIE = compilar_regex_tolerante(
    r"NFC-?e\s*N?[ºo°&]?\s*(\d{1,9})\s+[Ss][eé]rie\s+(\d{1,3})"
)
RE_DATA_HORA_EMISSAO = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}(?::\d{2})?)")
RE_TOTAL = compilar_regex_tolerante(r"VALOR\s+(?:TOTAL|[ÀA]\s+PAGAR)\s*R\$?\s*([\d.,]+)")
RE_CPF_CONSUMIDOR = compilar_regex_tolerante(r"CONSUMIDOR\s+CPF\s*:?\s*([\d.\s\-]{11,16})")
RE_FORMA_PAGAMENTO_BLOCO = compilar_regex_tolerante(r"FORMA\s+DE\s+PAGAMENTO[^\n]*\n+([^\n]+)")

# Cabeçalho do emitente: primeira linha com CNPJ (mesma abordagem da 47c)
# Exclui SUSEP (linha de seguradora, se por acaso aparecer) por consistência.
RE_LINHA_EMITENTE = compilar_regex_tolerante(
    r"^(?!.*SUSEP)\s*([^\n]*CNP"
    + GLYPH_J
    + r"+\s*:?\s*\d{2}[.,\s]?\d{3}[.,\s]?\d{3}\s*[/\\]\s*\d{4}\s*[-\s]\s*\d{2}[^\n]*)"
)

# Endereço do emitente: ruas canônicas de centros urbanos + bairro/cidade
RE_ENDERECO_EMITENTE_MULTI = re.compile(
    r"((?:S[EC][CL]|QN[A-Z]?|EQN[A-Z]?|SHS|SHN|SQS|SQN|AV\.?|R\.?|RUA|TRAV\.?|ROD\.?)[^\n]*\n?[^\n]*"
    r"(?:BRAS[IÍ]LIA|GAMA|TAGUATINGA|CEIL[ÂA]NDIA|PLANO|S[ÃA]O\s+PAULO|RIO\s+DE\s+JANEIRO)[^\n]*)",
    re.IGNORECASE | re.UNICODE,
)


# ============================================================================
# Padrões de itens (layout 80mm)
# ============================================================================


# Linha de item típica:
#   000004300823 CONTROLE P55 DUALSENSE ... 1 PCE x 449,99 449,99
# Tolerante a:
#   - código com dígito errado por OCR (aceita [\d][\dA-Z]{5,14})
#   - unidade 1-4 letras (PCE, UN, KG, CX, PC, L)
#   - `x` opcional entre qtde e valor unitário
#   - valores com vírgula ou ponto
RE_LINHA_ITEM = re.compile(
    r"^\s*(?P<codigo>[\d][\dA-Za-z]{5,14})\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<qtde>\d+(?:[.,]\d+)?)\s+"
    r"(?P<unidade>[A-Za-z]{1,4})\s*"
    r"x?\s*"
    r"(?P<valor_unit>[\d]{1,7}[.,]\d{2,3})\s+"
    r"(?P<valor_total>[\d]{1,7}[.,]\d{2,3})\s*$",
    re.MULTILINE | re.UNICODE,
)

RE_FIM_TABELA_ITENS = compilar_regex_tolerante(r"QTD\.?\s+TOTAL\s+DE\s+ITENS|VALOR\s+TOTAL\s+R\$")


# ============================================================================
# Normalização de forma de pagamento
# ============================================================================


# Ordem importa: matches mais específicos primeiro para evitar que "Cartão"
# absorva uma linha de débito antes de classificar como crédito.
_FLAGS_FP = re.IGNORECASE | re.UNICODE
_FORMA_PAGAMENTO_MAPA: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PIX", re.compile(r"\b(PIX|Pagamento\s+Instant[âa]n?g?o|QR\s+Pix)\b", _FLAGS_FP)),
    ("Crédito", re.compile(r"Cart[ãa]o\s+(?:de\s+)?Cr[ée]dito", _FLAGS_FP)),
    ("Débito", re.compile(r"Cart[ãa]o\s+(?:de\s+)?D[ée]bito", _FLAGS_FP)),
    ("Vale", re.compile(r"Vale\s+(?:Alimenta[çc][ãa]o|Refei[çc][ãa]o|Tic?ket)", _FLAGS_FP)),
    ("Dinheiro", re.compile(r"\b(Dinheiro|Esp[ée]cie)\b", _FLAGS_FP)),
)


def normalizar_forma_pagamento(bruto: str | None) -> str | None:
    """Mapeia string livre para valor canônico (`PIX`/`Crédito`/`Débito`/`Dinheiro`/`Vale`).

    Devolve None se nenhum padrão casar. Usa ordem de prioridade para evitar
    "Cartão" engolir genericamente débito antes de classificar crédito.
    """
    if not bruto:
        return None
    for canonico, padrao in _FORMA_PAGAMENTO_MAPA:
        if padrao.search(bruto):
            return canonico
    return None


# ============================================================================
# ExtratorNfcePDF
# ============================================================================


class ExtratorNfcePDF(ExtratorBase):
    """Extrai NFC-e modelo 65 em PDF nativo e popula o grafo.

    `pode_processar` aceita `.pdf` em pastas `*/nfs_fiscais/nfce/*` ou arquivo
    com cabeçalho "Documento Auxiliar da Nota Fiscal de Consumidor".

    `extrair` devolve `[]` de `base.Transacao` (total já está no extrato
    bancário). Efeito colateral: nó `documento` + fornecedor + N itens +
    arestas no grafo.
    """

    BANCO_ORIGEM: str = "NFC-e SEFAZ"

    def __init__(self, caminho: Path, grafo: GrafoDB | None = None) -> None:
        super().__init__(caminho)
        self._grafo = grafo

    # --------------------------------------------------------------------
    # Contrato ExtratorBase
    # --------------------------------------------------------------------

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False
        caminho_lower = str(caminho).lower()
        if "nfce" in caminho_lower or "nfs_fiscais" in caminho_lower:
            return True
        try:
            texto = self._extrair_texto_total(caminho)
        except Exception as erro:
            self.logger.debug("pode_processar: falha ao ler %s: %s", caminho, erro)
            return False
        return e_nfce(texto)

    def extrair(self) -> list[Transacao]:
        """Extrai NFC-e do arquivo e ingere no grafo. Retorna [] de Transacao."""
        nfces = self.extrair_nfces(self.caminho)
        if not nfces:
            return []
        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            for doc, itens in nfces:
                try:
                    ingerir_documento_fiscal(grafo, doc, itens, caminho_arquivo=self.caminho)
                except ValueError as erro:
                    self.logger.warning("NFC-e inválida em %s: %s", self.caminho.name, erro)
                    continue
                # Sprint VALIDAÇÃO-CSV-01: registrar campos extraídos para
                # validação humana posterior. Não bloqueia pipeline em caso
                # de falha (princípio D7: cobertura observável, não gate).
                try:
                    campos_canonicos = {
                        chave: doc.get(chave, "") for chave in (
                            "chave_44",
                            "cnpj_emitente",
                            "razao_social",
                            "data_emissao",
                            "total",
                            "forma_pagamento",
                            "cpf_consumidor",
                            "numero",
                            "serie",
                        )
                    }
                    campos_canonicos["numero_itens"] = len(itens)
                    _validacao_csv.registrar_extracao(
                        arquivo=self.caminho,
                        tipo_arquivo="nfce_modelo_65",
                        campos=campos_canonicos,
                    )
                except Exception as erro:  # noqa: BLE001
                    self.logger.warning(
                        "validacao_csv falhou em %s: %s", self.caminho.name, erro
                    )
        finally:
            if criou_grafo_localmente:
                grafo.fechar()
        self.logger.info("%d NFC-e ingerida(s) a partir de %s", len(nfces), self.caminho.name)
        return []

    # --------------------------------------------------------------------
    # API pública usável por testes
    # --------------------------------------------------------------------

    def extrair_nfces(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
        """Extrai todas as NFC-e do arquivo. Devolve lista de (documento, itens).

        Quando `texto_override` é dado, lê o texto direto em vez de abrir o
        arquivo via pdfplumber -- ponto de injeção para testes com fixtures
        .txt que reproduzem o output do pdfplumber sem depender de binários.

        Fallback Opus (Sprint INFRA-EXTRATORES-USAR-OPUS, 2026-05-08):
        quando ``texto_override is None`` e o parse local devolve lista
        vazia, registra tentativa via ``extrair_via_opus``. O schema
        canônico Opus atual cobre cupons de consumo (sem chave 44 SEFAZ,
        sem ``serie``/``numero`` estruturados). Por isso  # noqa: accent
        ``_mapear_schema_canonico_opus`` devolve lista vazia -- gancho
        documentado para quando houver schema próprio NFC-e modelo 65.
        """
        resultado_local = self._extrair_nfces_local(caminho, texto_override)

        if texto_override is not None:
            return resultado_local

        if resultado_local:
            return resultado_local

        from src.extractors._opus_fallback_comum import tentar_fallback_opus

        payload_opus = tentar_fallback_opus(caminho)
        if payload_opus is None:
            return resultado_local

        resultado_opus = self._mapear_schema_canonico_opus(payload_opus)
        if not resultado_opus:
            return resultado_local

        return resultado_opus

    def _extrair_nfces_local(
        self,
        caminho: Path,
        texto_override: str | None,
    ) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
        """Parse local (pdfplumber + regex). Retrocompat."""
        if texto_override is not None:
            paginas = _dividir_em_nfces(texto_override)
        else:
            paginas = self._ler_paginas(caminho)

        resultados: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
        for pagina in paginas:
            if not e_nfce(pagina):
                continue
            documento = _parse_cabecalho_nfce(pagina)
            if documento is None:
                continue
            itens = _parse_itens_nfce(pagina)
            documento["qtde_itens"] = len(itens)
            resultados.append((documento, itens))
        return resultados

    def _mapear_schema_canonico_opus(
        self,
        payload: dict[str, Any],  # noqa: ARG002 -- gancho documentado
    ) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
        """Schema Opus atual NÃO cobre NFC-e modelo 65.

        Gancho registrado para quando houver schema canônico próprio
        (chave 44 SEFAZ, série, número, CFOP por item). Hoje devolve
        lista vazia + log INFO.
        """
        self.logger.info(
            "fallback Opus invocado em %s mas schema canônico não cobre "
            "NFC-e modelo 65 -- mantendo resultado local",
            self.caminho.name,
        )
        return []

    # --------------------------------------------------------------------
    # Internals
    # --------------------------------------------------------------------

    def _ler_paginas(self, caminho: Path) -> list[str]:
        return _ler_paginas_pdf(caminho)

    def _extrair_texto_total(self, caminho: Path) -> str:
        return "\n".join(self._ler_paginas(caminho))


# ============================================================================
# Detector + parser (funções puras, testáveis isoladamente)
# ============================================================================


def e_nfce(texto: str) -> bool:
    """True se o texto tem pelo menos 2 de 3 marcadores canônicos de NFC-e.

    Se uma chave 44 estiver presente, exige também modelo 65.
    """
    marcadores = (RE_MARCA_NFCE_CABECALHO, RE_MARCA_NFCE_NUMERO, RE_MARCA_QR_SEFAZ)
    acertos = sum(1 for pad in marcadores if pad.search(texto))
    if acertos < 2:
        return False
    chave = _extrair_chave_44(texto)
    if chave and extrair_modelo(chave) != "65":
        return False
    return True


def _extrair_chave_44(texto: str) -> str | None:
    for match in RE_CHAVE_44_DIGITOS.finditer(texto):
        chave = normalizar_chave(match.group(1))
        if chave and valida_digito_verificador(chave):
            return chave
    return None


def _parse_cabecalho_nfce(texto: str) -> dict[str, Any] | None:
    """Parse de campos fiscais. Devolve None se chave 44 faltar ou for inválida."""
    chave = _extrair_chave_44(texto)
    if not chave:
        return None
    if extrair_modelo(chave) != "65":
        return None

    cnpj_emitente, razao_social = _extrair_cnpj_razao_emitente(texto)
    if not cnpj_emitente:
        return None

    numero, serie = _extrair_numero_serie(texto)
    data_emissao = _extrair_data_emissao(texto)
    total = parse_valor_br(_match_grupo(RE_TOTAL, texto))
    cpf_consumidor = extrair_cpf(texto) or _extrair_cpf_consumidor(texto)
    forma_pagamento = normalizar_forma_pagamento(_match_grupo(RE_FORMA_PAGAMENTO_BLOCO, texto))

    return {
        "chave_44": chave,
        "tipo_documento": "nfce_modelo_65",
        "cnpj_emitente": cnpj_emitente,
        "razao_social": razao_social,
        "endereco": _extrair_endereco(texto),
        "numero": numero,
        "serie": serie,
        "data_emissao": data_emissao,
        "total": total,
        "forma_pagamento": forma_pagamento,
        "cpf_consumidor": cpf_consumidor,
    }


def _parse_itens_nfce(texto: str) -> list[dict[str, Any]]:
    """Extrai itens da tabela NFC-e.

    Estratégia: delimita a região de tabela (entre cabeçalho de colunas e
    `QTD. TOTAL DE ITENS` / `VALOR TOTAL`), aplica regex linha-a-linha,
    e anexa linhas órfãs como continuação de descrição do item anterior.
    """
    regiao = _delimitar_regiao_itens(texto)
    if not regiao:
        return []

    itens: list[dict[str, Any]] = []
    for linha in regiao.split("\n"):
        linha_stripada = linha.strip()
        if not linha_stripada:
            continue
        match = RE_LINHA_ITEM.match(linha_stripada)
        if match:
            itens.append(_item_de_match(match))
            continue
        if itens and not _e_cabecalho_ou_ruido(linha_stripada):
            itens[-1]["descricao"] = normalizar_ps5_p55(
                _limpar_espacos(f"{itens[-1]['descricao']} {linha_stripada}")
            )
    return itens


def _delimitar_regiao_itens(texto: str) -> str:
    """Devolve o trecho do texto que vai do cabeçalho de itens até o total."""
    inicio_match = re.search(r"C[ÓO]DIGO\s+DESCRI[ÇC][ÃA]O", texto, re.IGNORECASE | re.UNICODE)
    if not inicio_match:
        return ""
    inicio = inicio_match.end()
    fim_match = RE_FIM_TABELA_ITENS.search(texto, inicio)
    fim = fim_match.start() if fim_match else len(texto)
    return texto[inicio:fim]


def _item_de_match(match: re.Match[str]) -> dict[str, Any]:
    return {
        "codigo": match.group("codigo"),
        "descricao": normalizar_ps5_p55(_limpar_espacos(match.group("descricao"))),
        "qtde": parse_valor_br(match.group("qtde")),
        "unidade": match.group("unidade").upper(),
        "valor_unit": parse_valor_br(match.group("valor_unit")),
        "valor_total": parse_valor_br(match.group("valor_total")),
    }


def _e_cabecalho_ou_ruido(linha: str) -> bool:
    """True se a linha é cabeçalho, separador ou ruído (não é continuação de descrição)."""
    if re.match(r"^[\s\-=_]{3,}$", linha):
        return True
    cabecalho = r"^(QTD|VALOR|FORMA|CONSUMIDOR|NFC|Trib|Loja|Protocolo|Data)\b"
    if re.match(cabecalho, linha, re.IGNORECASE):
        return True
    return False


# ============================================================================
# Helpers de extração dos campos de cabeçalho
# ============================================================================


def _extrair_cnpj_razao_emitente(texto: str) -> tuple[str | None, str | None]:
    """Primeira linha do documento que tenha CNPJ é a do emitente (padrão 47c)."""
    for linha in texto.splitlines():
        if RE_LINHA_EMITENTE.search(linha):
            cnpjs = extrair_cnpjs(linha)
            if not cnpjs:
                continue
            razao = _limpar_razao_emitente(linha)
            return cnpjs[0], razao
    cnpjs_texto_todo = extrair_cnpjs(texto)
    if cnpjs_texto_todo:
        return cnpjs_texto_todo[0], None
    return None, None


def _limpar_razao_emitente(linha: str) -> str | None:
    """Remove o bloco `CNP...XX.XXX.../XXXX-XX` da linha; sobra a razão."""
    limpa = re.sub(
        r"CNP[J\)\]]+\s*:?\s*\d{2}[.,\s]?\d{3}[.,\s]?\d{3}\s*[/\\]\s*\d{4}\s*[-\s]\s*\d{2}",
        "",
        linha,
        flags=re.IGNORECASE,
    )
    limpa = limpa.strip(" -\t")
    return limpa or None


def _extrair_endereco(texto: str) -> str | None:
    match = RE_ENDERECO_EMITENTE_MULTI.search(texto)
    if not match:
        return None
    return _limpar_espacos(match.group(1))


def _extrair_numero_serie(texto: str) -> tuple[str | None, str | None]:
    match = RE_NUMERO_SERIE.search(texto)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _extrair_data_emissao(texto: str) -> str | None:
    """Primeira data+hora DD/MM/AAAA HH:MM -- na NFC-e é a emissão (cabeçalho)."""
    match = RE_DATA_HORA_EMISSAO.search(texto)
    if not match:
        return None
    dia, mes, ano = match.group(1).split("/")
    return f"{ano}-{mes}-{dia}"


def _extrair_cpf_consumidor(texto: str) -> str | None:
    match = RE_CPF_CONSUMIDOR.search(texto)
    if not match:
        return None
    digitos = re.sub(r"\D", "", match.group(1))
    if len(digitos) != 11:
        return None
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


# ============================================================================
# Divisão multi-NFC-e (quando um PDF contém mais de uma nota)
# ============================================================================


def _dividir_em_nfces(texto: str) -> list[str]:
    """Divide texto multi-NFC-e pelo marcador 'Documento Auxiliar...'.

    Cada bloco começa pouco antes do marcador (inclui cabeçalho do varejo,
    que aparece na mesma página). Quando há só 1 ocorrência, devolve o texto
    inteiro (preserva contexto).
    """
    ocorrencias = [m.start() for m in RE_MARCA_NFCE_CABECALHO.finditer(texto)]
    if len(ocorrencias) <= 1:
        return [texto]
    blocos: list[str] = []
    for pos, inicio in enumerate(ocorrencias):
        ancora = _anchor_inicio_bloco(texto, inicio)
        fim = ocorrencias[pos + 1] if pos + 1 < len(ocorrencias) else len(texto)
        fim_ancora = _anchor_inicio_bloco(texto, fim) if pos + 1 < len(ocorrencias) else len(texto)
        bloco = texto[ancora:fim_ancora].strip()
        if bloco:
            blocos.append(bloco)
    return blocos or [texto]


def _anchor_inicio_bloco(texto: str, pos: int) -> int:
    """Recuar até a linha com CNPJ do emitente mais próxima acima de `pos`.

    Limite de ~15 linhas para evitar agarrar o bloco anterior.
    """
    anchor = max(0, texto.rfind("\n", 0, pos))
    linhas_acima = 0
    while anchor > 0 and linhas_acima < 15:
        inicio_linha = texto.rfind("\n", 0, anchor - 1) + 1
        linha = texto[inicio_linha:anchor]
        if RE_LINHA_EMITENTE.search(linha):
            return inicio_linha
        anchor = inicio_linha - 1
        linhas_acima += 1
    return 0


# ============================================================================
# Helpers de leitura de PDF
# ============================================================================


def _ler_paginas_pdf(caminho: Path) -> list[str]:
    """Lê páginas do PDF via pdfplumber com fallback OCR (A2 2026-04-23).

    Quando pdfplumber devolve texto insuficiente (PDF-imagem sem layer de
    texto, ex: "notas de garantia e compras.pdf" da auditoria), cai em
    pypdfium2 + tesseract página a página. Custo: ~1-3s por página; só é
    invocado quando o texto nativo é insuficiente.
    """
    try:
        import pdfplumber
    except ImportError as erro:
        logger.error("pdfplumber indisponível: %s", erro)
        return []
    paginas: list[str] = []
    try:
        with pdfplumber.open(caminho) as pdf:
            for pg in pdf.pages:
                paginas.append(pg.extract_text() or "")
    except Exception as erro:
        logger.warning("falha ao ler %s via pdfplumber: %s", caminho, erro)
        return []

    # Fallback OCR: PDF-imagem tem todas as páginas vazias ou com muito
    # pouco texto. Threshold conservador (soma de chars > 50) para
    # preservar performance em PDFs nativos legítimos.
    total_chars = sum(len(p.strip()) for p in paginas)
    if total_chars < 50 and paginas:
        paginas_ocr = _ler_paginas_pdf_via_ocr(caminho)
        if paginas_ocr:
            logger.info(
                "PDF-imagem detectado em %s; %d páginas via OCR fallback",
                caminho.name,
                len(paginas_ocr),
            )
            return paginas_ocr
    return paginas


def _ler_paginas_pdf_via_ocr(caminho: Path) -> list[str]:
    """Renderiza páginas do PDF com pypdfium2 e aplica tesseract (A2)."""
    try:
        import pypdfium2 as pdfium
        import pytesseract
    except ImportError:
        return []
    try:
        pdf = pdfium.PdfDocument(str(caminho))
        paginas: list[str] = []
        for i in range(len(pdf)):
            pagina = pdf[i]
            pil_img = pagina.render(scale=2).to_pil()
            texto = pytesseract.image_to_string(pil_img, lang="por+eng")
            paginas.append(texto or "")
        return paginas
    except Exception as erro:  # noqa: BLE001
        logger.warning("OCR falhou em %s: %s", caminho.name, erro)
        return []


# ============================================================================
# Helpers numéricos
# ============================================================================


def _match_grupo(padrao: re.Pattern[str], texto: str) -> str | None:
    match = padrao.search(texto)
    if not match:
        return None
    return match.group(1).strip()


def _limpar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


# "Quem despreza o pequeno cupom não merece a grande nota." -- adaptação de Provérbios
