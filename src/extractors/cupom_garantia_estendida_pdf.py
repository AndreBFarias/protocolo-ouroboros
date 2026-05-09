"""Extrator de Cupom Bilhete de Seguro -- Garantia Estendida (Sprint 47c).

Processa bilhetes SUSEP emitidos no PDV (varejo varia; hoje MAPFRE/Cardif via
Americanas). Três fontes de entrada:

- PDF nativo com fonte boa (texto extraível via pdfplumber, sem corrupção)
- PDF nativo com fonte ToUnicode quebrada (texto extraível mas com glyphs
  trocados: `CNPJ` -> `CNP)`, `S.A.` -> `5.A.`, `O BILHETE` -> `Q BILHETE`)
- PDF escaneado ou imagem PNG/JPEG (via OCR com tesseract)

Diagnóstico texto-primeiro (Armadilha #21): quando pdfplumber extrai texto
útil, ignora presença de imagens; caso contrário, cai para OCR.

Glyph-tolerance (Armadilha #20): usa `src/intake/glyph_tolerant.py` para
todos os campos sensíveis (CNPJ, CPF, palavras-chave de cabeçalho).

Campos canônicos extraídos (obrigatórios marcados com *):

    numero_bilhete*, processo_susep*, cpf_segurado, bem_segurado,
    valor_bem, premio_liquido, iof, premio_total, forma_pagamento,
    vigencia_inicio, vigencia_fim, cobertura_inicio, cobertura_fim,
    seguradora_razao_social*, seguradora_cnpj*, seguradora_codigo_susep,
    varejo_razao_social*, varejo_cnpj*, varejo_endereco, data_emissao*

Efeitos colaterais: ao chamar `extrair()`, os bilhetes extraídos são ingeridos
no grafo via `src/graph/ingestor_documento.py:ingerir_apolice`. O retorno é
sempre uma lista VAZIA de base.Transacao -- o prêmio já aparece nas transações
bancárias; duplicar seria erro contábil.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_apolice, upsert_seguradora
from src.intake.glyph_tolerant import (
    GLYPH_A_ACENTO,
    GLYPH_B_MAIUSCULO,
    GLYPH_E_ACENTO,
    GLYPH_J,
    GLYPH_S_MAIUSCULO,
    compilar_regex_tolerante,
    extrair_cnpjs,
    extrair_cpf,
)
from src.utils.logger import configurar_logger
from src.utils.parse_br import parse_valor_br

logger = configurar_logger("cupom_garantia_estendida_pdf")

RAIZ = Path(__file__).resolve().parents[2]
PATH_SEGURADORAS = RAIZ / "mappings" / "seguradoras.yaml"
PATH_PROPOSTAS = RAIZ / "docs" / "propostas" / "seguradoras"

EXTENSOES_ACEITAS: tuple[str, ...] = (".pdf", ".png", ".jpg", ".jpeg")


# ============================================================================
# Padrões de detecção (glyph-tolerante)
# ============================================================================


RE_MARCA_CUPOM_BILHETE = compilar_regex_tolerante(
    r"CUPOM\s+" + GLYPH_B_MAIUSCULO + r"ILHETE\s+DE\s+SEGURO"
)
RE_MARCA_GARANTIA_ESTENDIDA = compilar_regex_tolerante(r"GARANTIA\s+ESTENDIDA")
RE_MARCA_SUSEP = compilar_regex_tolerante(r"Processo\s+" + GLYPH_S_MAIUSCULO + r"USEP")


# ============================================================================
# Padrões de campos (glyph-tolerante)
# ============================================================================


RE_BILHETE_INDIVIDUAL = compilar_regex_tolerante(
    r"" + GLYPH_B_MAIUSCULO + r"ILHETE\s+INDIVIDUAL\s*:?\s*(\d{12,18})"
)
RE_PROCESSO_SUSEP = compilar_regex_tolerante(
    GLYPH_S_MAIUSCULO + r"USEP\s+No?\.?\s*([\d][\d./\s\-]{10,25})"
)
RE_COD_SUSEP = compilar_regex_tolerante(
    r"C[ou]d\s+" + GLYPH_S_MAIUSCULO + r"USEP\s*:?\s*([\dD]{4,8})"
)
RE_BEM_SEGURADO = compilar_regex_tolerante(
    r"Descri[çc][ãa]o\s+do\s+bem\s+segurado[^\n]*\n+([^\n]+)"
)
RE_LIMITE = compilar_regex_tolerante(
    r"Limite\s+M[áa]ximo\s+de\s+Indeniza[çc][ãa]o[^:\n]*:\s*([\d.,]+)"
)
RE_PREMIO_LIQUIDO = compilar_regex_tolerante(
    r"PR" + GLYPH_E_ACENTO + r"MIO\s+L[ÍI]QUIDO\s*:?\s*([\d.,]+)"
)
RE_IOF = compilar_regex_tolerante(r"IOF\s*:?\s*([\d.,]+)")
RE_PREMIO_TOTAL = compilar_regex_tolerante(r"PR" + GLYPH_E_ACENTO + r"MIO\s+TOTAL\s*:?\s*([\d.,]+)")
RE_FORMA_PAGAMENTO = compilar_regex_tolerante(r"Forma\s+de\s+Pagamento\s*:?\s*\n+([^\n]+)")
RE_DATA_EMISSAO = compilar_regex_tolerante(
    r"DATA\s+DA\s+EMISS" + GLYPH_A_ACENTO + r"O\s*:?\s*(\d{2}/\d{2}/\d{4})"
)
RE_VIGENCIA_INICIO = compilar_regex_tolerante(
    r"In[íi]cio\s+de\s+Vig[êe]ncia[^:\n]*:?\s*(\d{2}/\d{2}/\d{4})"
)
RE_VIGENCIA_FIM = compilar_regex_tolerante(r"Fim\s+de\s+Vig[êe]ncia[^:\n]*:?\s*(\d{2}/\d{2}/\d{4})")
# `.{0,60}?` permite dígitos intermediários ("às 24h do dia") -- `[^\d]` cortaria
# em "24" e quebraria o match. Limite 60 chars evita devorar até próximo bilhete.
# `.{0,60}?` permite dígitos intermediários ("às 24h do dia") -- `[^\d]` cortaria
# em "24" e quebraria o match. Limite 60 chars evita devorar até próximo bilhete.
# `Ri[asz]co` cobre "Risco" (ok), "Rizco" (nativo glyph), "Riaco" (OCR quebrado).
RE_COBERTURA_INICIO = compilar_regex_tolerante(
    r"In[íi]cio\s+de\s+Cobertura\s+de\s+Ri[asz]co.{0,60}?(\d{2}/\d{2}/\d{4})"
)
RE_COBERTURA_FIM = compilar_regex_tolerante(
    r"Fim\s+de\s+Cobertura\s+de\s+Ri[asz]co.{0,60}?(\d{2}/\d{2}/\d{4})"
)

# Seguradora: bloco após "DADOS DA SEGURADORA"
RE_BLOCO_SEGURADORA = re.compile(
    r"DADOS\s+DA\s+SEGURADORA(.{0,400})(?:DISPOSI[ÇC]" + r"[ÕO]ES\s+GERAIS|$)",
    re.IGNORECASE | re.DOTALL | re.UNICODE,
)
# `Raz[ãa]o Social` costuma ser OCR'd como `Kazão Sacial` (K no R, a no o) -- aceitar
# ambos os caracteres na primeira letra de cada palavra.
RE_RAZAO_SEGURADORA = compilar_regex_tolerante(
    r"[RK]az[ãa]o\s+" + GLYPH_S_MAIUSCULO + r"[ao]cial\s*:?\s*([^\n]+)"
)

# Cabeçalho do varejo: linha com CNPJ onde NÃO aparece "SUSEP".
# Linhas da seguradora (ex.: `CNPJ: XX.XXX.XXX/XXXX-XX Cod SUSEP: NNNNN`) também
# têm CNPJ mas contém SUSEP -- negative lookahead `(?!.*SUSEP)` as exclui.
# Separadores tolerantes (`[.,\s]?`) porque OCR às vezes troca `.` por `,`.
RE_VAREJO_LINHA = compilar_regex_tolerante(
    r"^(?!.*SUSEP)\s*([^\n]*CNP"
    + GLYPH_J
    + r"+\s*:?\s*\d{2}[.,\s]?\d{3}[.,\s]?\d{3}\s*[/\\]\s*\d{4}\s*[-\s]\s*\d{2}[^\n]*)"
)
# `S[EC][CL]` cobre OCR'd `SEC` (scanner confunde C com E).
# QN*/EQN*/SHS/SHN/SQS/SQN cobrem endereços canônicos de Brasília.
RE_ENDERECO_VAREJO_LINHA = re.compile(
    r"(S[EC][CL]|QN[A-Z]?|EQN[A-Z]?|SHS|SHN|SQS|SQN)[^\n]*"
    r"(?:BRAS[IÍ]LIA|GAMA|TAGUATINGA|CEIL[ÂA]NDIA|PLANO)\b[^\n]*",
    re.IGNORECASE | re.UNICODE,
)


# ============================================================================
# ExtratorCupomGarantiaEstendida
# ============================================================================


class ExtratorCupomGarantiaEstendida(ExtratorBase):
    """Extrai bilhetes de seguro de garantia estendida e popula o grafo.

    `pode_processar` aceita PDF/PNG/JPEG em pastas `*/garantias_estendidas/*`
    ou arquivo cujo texto contenha a tríade de marcadores SUSEP.

    `extrair` devolve lista vazia de base.Transacao (nenhum lançamento financeiro
    adicional; o prêmio já está no extrato bancário). Efeito colateral: inclui
    nó `apolice` + `seguradora` + `fornecedor(varejo)` + `periodo` no grafo.
    """

    BANCO_ORIGEM: str = "Bilhete SUSEP"

    def __init__(
        self,
        caminho: Path,
        grafo: GrafoDB | None = None,
        seguradoras_cfg: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(caminho)
        self._grafo = grafo
        # Distinguir None de {} -- testes passam {} para forçar "seguradora
        # desconhecida"; `or` trataria dict vazio como falsy e recarregaria.
        self._seguradoras_por_cnpj = (
            seguradoras_cfg if seguradoras_cfg is not None else _carregar_seguradoras()
        )

    # --------------------------------------------------------------------
    # Contrato ExtratorBase
    # --------------------------------------------------------------------

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False
        if "garantias_estendidas" in str(caminho).lower():
            return True
        try:
            texto = self._extrair_texto_total(caminho)
        except Exception as erro:
            self.logger.debug("pode_processar: falha ao ler %s: %s", caminho, erro)
            return False
        return e_cupom_garantia_estendida(texto)

    def extrair(self) -> list[Transacao]:
        """Extrai todos os bilhetes do arquivo e os ingere no grafo.

        Retorna lista vazia de base.Transacao -- ver docstring do módulo.
        """
        bilhetes = self.extrair_bilhetes(self.caminho)
        if not bilhetes:
            return []
        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            for bilhete in bilhetes:
                try:
                    ingerir_apolice(grafo, bilhete, caminho_arquivo=self.caminho)
                except ValueError as erro:
                    self.logger.warning("bilhete inválido em %s: %s", self.caminho.name, erro)
        finally:
            if criou_grafo_localmente:
                grafo.fechar()
        self.logger.info(
            "%d bilhete(s) ingerido(s) a partir de %s",
            len(bilhetes),
            self.caminho.name,
        )
        return []

    # --------------------------------------------------------------------
    # API pública usável por testes / callers externos
    # --------------------------------------------------------------------

    def extrair_bilhetes(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extrai bilhetes de um arquivo. `texto_override` pula leitura real.

        Quando `texto_override` é dado, o método ignora `caminho` para efeitos
        de leitura -- útil em testes com fixtures .txt que simulam o output
        do pdfplumber/pytesseract sem depender de PDFs binários.

        Fallback Opus (Sprint INFRA-EXTRATORES-USAR-OPUS, 2026-05-08):
        quando ``texto_override is None`` e o parse local devolve lista
        vazia, registra tentativa via ``extrair_via_opus``. O schema
        canônico Opus atual cobre cupons fiscais de consumo, NÃO bilhetes
        de garantia estendida (campos: ``numero_bilhete``, ``processo_susep``,
        ``cpf_segurado``, ``premio_total``, ``vigencia_inicio``...). Por
        isso ``_mapear_schema_canonico_opus`` devolve sempre lista vazia
        nesta sprint -- log INFO documenta o gancho disponível para quando
        houver schema canônico próprio de garantia estendida.
        """
        bilhetes_local = self._extrair_bilhetes_local(caminho, texto_override)

        if texto_override is not None:
            return bilhetes_local

        if bilhetes_local:
            return bilhetes_local

        from src.extractors._opus_fallback_comum import tentar_fallback_opus

        payload_opus = tentar_fallback_opus(caminho)
        if payload_opus is None:
            return bilhetes_local

        bilhetes_opus = self._mapear_schema_canonico_opus(payload_opus)
        if not bilhetes_opus:
            return bilhetes_local

        return bilhetes_opus

    def _extrair_bilhetes_local(
        self,
        caminho: Path,
        texto_override: str | None,
    ) -> list[dict[str, Any]]:
        """Parse local (pdfplumber + regex). Retrocompat."""
        if texto_override is not None:
            paginas = _dividir_em_bilhetes(texto_override)
        else:
            paginas = self._ler_paginas(caminho)

        bilhetes: list[dict[str, Any]] = []
        for pagina in paginas:
            if not e_cupom_garantia_estendida(pagina):
                continue
            bilhete = _parse_bilhete(pagina)
            if bilhete is None:
                continue
            self._enriquecer_seguradora(bilhete)
            bilhetes.append(bilhete)
        return bilhetes

    def _mapear_schema_canonico_opus(
        self,
        payload: dict[str, Any],  # noqa: ARG002 -- gancho documentado
    ) -> list[dict[str, Any]]:
        """Schema Opus atual NÃO cobre bilhete de garantia estendida.

        Gancho registrado para quando houver schema canônico próprio
        (campos: numero_bilhete, processo_susep, premio_total,
        vigencia_inicio/fim etc). Hoje devolve lista vazia + log INFO.
        """
        self.logger.info(
            "fallback Opus invocado em %s mas schema canônico não cobre "
            "garantia estendida -- mantendo resultado local",
            self.caminho.name,
        )
        return []

    # --------------------------------------------------------------------
    # Internals
    # --------------------------------------------------------------------

    def _ler_paginas(self, caminho: Path) -> list[str]:
        sufixo = caminho.suffix.lower()
        if sufixo == ".pdf":
            paginas = _ler_paginas_pdf(caminho)
            if any(_tem_texto_util(pg) for pg in paginas):
                return paginas
            return _ler_paginas_pdf_via_ocr(caminho)
        if sufixo in {".png", ".jpg", ".jpeg"}:
            return [_ocr_imagem(caminho)]
        return []

    def _extrair_texto_total(self, caminho: Path) -> str:
        paginas = self._ler_paginas(caminho)
        return "\n".join(paginas)

    def _enriquecer_seguradora(self, bilhete: dict[str, Any]) -> None:
        cnpj = bilhete.get("seguradora_cnpj")
        if not cnpj:
            return
        cfg = self._seguradoras_por_cnpj.get(cnpj)
        if cfg is None:
            _registrar_proposta_seguradora(bilhete)
            return
        bilhete.setdefault("seguradora_razao_social", cfg["razao_social"])
        if cfg.get("codigo_susep") and not bilhete.get("seguradora_codigo_susep"):
            bilhete["seguradora_codigo_susep"] = cfg["codigo_susep"]
        # Sobrescreve código SUSEP se detectado com glyph quebrado (D no zero).
        codigo_detectado = bilhete.get("seguradora_codigo_susep", "")
        if "D" in str(codigo_detectado) and cfg.get("codigo_susep"):
            bilhete["seguradora_codigo_susep"] = cfg["codigo_susep"]


# ============================================================================
# Detector + parser (funções puras, testáveis isoladamente)
# ============================================================================


def e_cupom_garantia_estendida(texto: str) -> bool:
    """Devolve True se pelo menos 2 de 3 marcadores SUSEP casarem.

    Tolera glyphs (CUPOM BILHETE / Q BILHETE, SUSEP / 5USEP).
    """
    marcadores = (
        RE_MARCA_CUPOM_BILHETE,
        RE_MARCA_GARANTIA_ESTENDIDA,
        RE_MARCA_SUSEP,
    )
    acertos = sum(1 for pad in marcadores if pad.search(texto))
    return acertos >= 2


def _parse_bilhete(texto: str) -> dict[str, Any] | None:
    """Parse campos canônicos. Devolve None se campos críticos faltarem."""
    numero_bilhete = _match_grupo(RE_BILHETE_INDIVIDUAL, texto)
    if not numero_bilhete:
        return None

    bilhete: dict[str, Any] = {
        "numero_bilhete": numero_bilhete,
        "processo_susep": _normalizar_processo_susep(_match_grupo(RE_PROCESSO_SUSEP, texto)),
        "cpf_segurado": extrair_cpf(texto),
        "bem_segurado": _limpar_linha(_match_grupo(RE_BEM_SEGURADO, texto)),
        "valor_bem": parse_valor_br(_match_grupo(RE_LIMITE, texto)),
        "premio_liquido": parse_valor_br(_match_grupo(RE_PREMIO_LIQUIDO, texto)),
        "iof": parse_valor_br(_match_grupo(RE_IOF, texto)),
        "premio_total": parse_valor_br(_match_grupo(RE_PREMIO_TOTAL, texto)),
        "forma_pagamento": _limpar_linha(_match_grupo(RE_FORMA_PAGAMENTO, texto)),
        "vigencia_inicio": _br_para_iso(_match_grupo(RE_VIGENCIA_INICIO, texto)),
        "vigencia_fim": _br_para_iso(_match_grupo(RE_VIGENCIA_FIM, texto)),
        "cobertura_inicio": _br_para_iso(_match_grupo(RE_COBERTURA_INICIO, texto)),
        "cobertura_fim": _br_para_iso(_match_grupo(RE_COBERTURA_FIM, texto)),
        "data_emissao": _br_para_iso(_match_grupo(RE_DATA_EMISSAO, texto)),
    }

    _preencher_seguradora(bilhete, texto)
    _preencher_varejo(bilhete, texto)
    return bilhete


def _preencher_seguradora(bilhete: dict[str, Any], texto: str) -> None:
    match_bloco = RE_BLOCO_SEGURADORA.search(texto)
    bloco = match_bloco.group(1) if match_bloco else texto
    razao = _match_grupo(RE_RAZAO_SEGURADORA, bloco)
    bilhete["seguradora_razao_social"] = _limpar_linha(razao) if razao else None
    cnpjs_bloco = extrair_cnpjs(bloco)
    bilhete["seguradora_cnpj"] = cnpjs_bloco[0] if cnpjs_bloco else None
    codigo = _match_grupo(RE_COD_SUSEP, bloco)
    bilhete["seguradora_codigo_susep"] = codigo.strip() if codigo else None


def _preencher_varejo(bilhete: dict[str, Any], texto: str) -> None:
    primeira_linha_varejo: str | None = None
    for linha in texto.splitlines():
        if RE_VAREJO_LINHA.search(linha):
            primeira_linha_varejo = linha.strip()
            break
    if primeira_linha_varejo is None:
        bilhete["varejo_razao_social"] = None
        bilhete["varejo_cnpj"] = None
        bilhete["varejo_endereco"] = None
        return

    cnpjs_linha = extrair_cnpjs(primeira_linha_varejo)
    bilhete["varejo_cnpj"] = cnpjs_linha[0] if cnpjs_linha else None
    razao = _limpar_razao_varejo(primeira_linha_varejo)
    bilhete["varejo_razao_social"] = razao
    bilhete["varejo_endereco"] = _extrair_endereco_varejo(texto)


def _limpar_razao_varejo(linha: str) -> str | None:
    """Remove o bloco `CNP...XX.XXX.../XXXX-XX` da linha, sobra a razão social.

    Usa as mesmas tolerâncias de glyph+separador da RE_VAREJO_LINHA para evitar
    que a CNPJ sobreviva na razão social quando OCR trocou `.` por `,`.
    """
    limpa = re.sub(
        r"CNP[J\)\]]+\s*:?\s*\d{2}[.,\s]?\d{3}[.,\s]?\d{3}\s*[/\\]\s*\d{4}\s*[-\s]\s*\d{2}",
        "",
        linha,
        flags=re.IGNORECASE,
    )
    limpa = limpa.strip(" -\t")
    return limpa or None


def _extrair_endereco_varejo(texto: str) -> str | None:
    match = RE_ENDERECO_VAREJO_LINHA.search(texto)
    if not match:
        return None
    return match.group(0).strip()


def _dividir_em_bilhetes(texto: str) -> list[str]:
    """Divide texto multi-bilhete em blocos, preservando o cabeçalho do varejo.

    Cada bilhete no PDV começa com o cabeçalho do VAREJO (razão + CNPJ +
    endereço + data). O `CUPOM BILHETE DE SEGURO` vem DEPOIS. Se dividíssemos
    por `CUPOM BILHETE`, o primeiro bloco ficaria só com o cabeçalho (sem
    marcador SUSEP, descartado pelo detector) e os demais ficariam órfãos
    do cabeçalho -- `_preencher_varejo` cairia na linha CNPJ da SEGURADORA
    por acidente. Bug real observado no pdf_notas.pdf.

    Estratégia correta: dividir na linha com CNPJ do VAREJO (a mesma regex
    `RE_VAREJO_LINHA` que o parser usa). Cada bloco fica: [cabeçalho varejo
    + corpo do bilhete] até o próximo cabeçalho.
    """
    linhas = texto.splitlines(keepends=True)
    inicios = [i for i, ln in enumerate(linhas) if RE_VAREJO_LINHA.search(ln)]
    if len(inicios) <= 1:
        return [texto]
    blocos: list[str] = []
    for pos, inicio in enumerate(inicios):
        fim = inicios[pos + 1] if pos + 1 < len(inicios) else len(linhas)
        bloco = "".join(linhas[inicio:fim]).strip()
        if bloco:
            blocos.append(bloco)
    return blocos or [texto]


# ============================================================================
# Helpers de leitura de arquivo
# ============================================================================


def _ler_paginas_pdf(caminho: Path) -> list[str]:
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
    return paginas


def _ler_paginas_pdf_via_ocr(caminho: Path) -> list[str]:
    try:
        import pdfplumber
        import pytesseract
    except ImportError as erro:
        logger.error("OCR indisponível: %s", erro)
        return []
    paginas: list[str] = []
    try:
        with pdfplumber.open(caminho) as pdf:
            for pg in pdf.pages:
                imagem = pg.to_image(resolution=200).original
                paginas.append(pytesseract.image_to_string(imagem, lang="por"))
    except Exception as erro:
        logger.warning("falha OCR em %s: %s", caminho, erro)
        return []
    return paginas


def _ocr_imagem(caminho: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as erro:
        logger.error("OCR de imagem indisponível: %s", erro)
        return ""
    try:
        with Image.open(caminho) as im:
            return pytesseract.image_to_string(im, lang="por")
    except Exception as erro:
        logger.warning("falha OCR em %s: %s", caminho, erro)
        return ""


def _tem_texto_util(pagina: str) -> bool:
    return len(pagina.strip()) >= 50


# ============================================================================
# Normalizadores
# ============================================================================


def _match_grupo(padrao: re.Pattern[str], texto: str) -> str | None:
    match = padrao.search(texto)
    if not match:
        return None
    return match.group(1).strip()


def _normalizar_processo_susep(bruto: str | None) -> str | None:
    """Normaliza para `XXXXX.XXXXXX/XXXX-XX`.

    Bilhetes reais às vezes têm espaço entre os dois primeiros blocos
    (ex.: `15414 .900147/2014-11`).
    """
    if not bruto:
        return None
    digitos = re.sub(r"\s+", "", bruto)
    match = re.match(r"^(\d{5})\.?(\d{6})/(\d{4})-(\d{2})$", digitos)
    if not match:
        return digitos
    return f"{match.group(1)}.{match.group(2)}/{match.group(3)}-{match.group(4)}"


def _br_para_iso(data_br: str | None) -> str | None:
    if not data_br:
        return None
    match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", data_br)
    if not match:
        return None
    dia, mes, ano = match.groups()
    return f"{ano}-{mes}-{dia}"


def _limpar_linha(texto: str | None) -> str | None:
    if not texto:
        return None
    return re.sub(r"\s+", " ", texto).strip() or None


# ============================================================================
# Carregamento de seguradoras.yaml + propostas
# ============================================================================


def _carregar_seguradoras() -> dict[str, dict[str, Any]]:
    if not PATH_SEGURADORAS.exists():
        return {}
    try:
        dados = yaml.safe_load(PATH_SEGURADORAS.read_text(encoding="utf-8"))
    except yaml.YAMLError as erro:
        logger.warning("seguradoras.yaml inválido: %s", erro)
        return {}
    if not isinstance(dados, dict):
        return {}
    por_cnpj: dict[str, dict[str, Any]] = {}
    for registro in dados.get("seguradoras", []) or []:
        cnpj = registro.get("cnpj")
        if cnpj:
            por_cnpj[cnpj] = registro
    return por_cnpj


def _registrar_proposta_seguradora(bilhete: dict[str, Any]) -> None:
    """Grava proposta em docs/propostas/seguradoras/<cnpj>.md para cadastro manual."""
    cnpj = bilhete.get("seguradora_cnpj") or "desconhecido"
    razao = bilhete.get("seguradora_razao_social") or "(não extraída)"
    PATH_PROPOSTAS.mkdir(parents=True, exist_ok=True)
    arquivo = PATH_PROPOSTAS / f"{cnpj.replace('/', '-').replace('.', '')}.md"
    if arquivo.exists():
        return
    conteudo = (
        f"# Proposta de cadastro: {razao}\n\n"
        f"- CNPJ: {cnpj}\n"
        f"- Razão Social: {razao}\n"
        f"- Código SUSEP: {bilhete.get('seguradora_codigo_susep') or '(não extraído)'}\n"
        f"- Detectada em bilhete: {bilhete.get('numero_bilhete')}\n"
        f"- Data emissão: {bilhete.get('data_emissao')}\n\n"
        "Adicionar a `mappings/seguradoras.yaml` após conferência manual.\n"
    )
    arquivo.write_text(conteudo, encoding="utf-8")
    logger.info("proposta de seguradora registrada em %s", arquivo)


# ============================================================================
# Hook para pipeline.py (opcional)
# ============================================================================


def ingerir_bilhete_manualmente(
    grafo: GrafoDB,
    caminho: Path,
) -> list[dict[str, Any]]:
    """Facade sem estado -- útil para scripts de backfill ou conferência Opus."""
    extrator = ExtratorCupomGarantiaEstendida(caminho, grafo=grafo)
    bilhetes = extrator.extrair_bilhetes(caminho)
    for bilhete in bilhetes:
        try:
            ingerir_apolice(grafo, bilhete, caminho_arquivo=caminho)
        except ValueError as erro:
            logger.warning("bilhete inválido em %s: %s", caminho.name, erro)
    return bilhetes


def cadastrar_seguradoras_yaml(grafo: GrafoDB) -> int:
    """Pré-popula o grafo com as seguradoras do YAML. Uso opcional, idempotente."""
    total = 0
    for cnpj, registro in _carregar_seguradoras().items():
        upsert_seguradora(
            grafo,
            cnpj=cnpj,
            razao_social=registro.get("razao_social", ""),
            codigo_susep=registro.get("codigo_susep"),
            aliases=registro.get("aliases") or [],
        )
        total += 1
    return total


# "Quem promete cobertura assume o futuro alheio." -- princípio atuarial
