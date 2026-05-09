"""Extrator de receita médica / prescrição (Sprint 47a).

Processa receitas que chegam como foto do celular no consultório ou PDF
vindo de telemedicina. O artefato NÃO gera transação financeira (o gasto
de farmácia já está no extrato bancário); o efeito colateral é popular
o grafo com:

    - nó `prescricao` (chave sintética derivada de data + CRM + hash)
    - nó `fornecedor` com categoria `medico` (chave `CRM|UF|NUM`)
    - nó(s) `item` com `categoria_item=medicamento` (chave `MED|<DCB>`)
    - arestas `emitida_por`, `ocorre_em`, `prescreve`
    - aresta opcional `prescreve_cobre` quando casa com item de farmácia
      já no grafo (ingestão de NFC-e/cupom anterior)

LGPD: guarda apenas o nome do paciente. Nunca CPF, diagnóstico ou CID --
a acceptance da Sprint 47a explicita "NÃO extrair dados do paciente além
do nome".

Contrato com outros módulos:

    `pode_processar(caminho)` aceita `.pdf`, `.jpg`, `.jpeg`, `.png`,
    `.heic`, `.heif` quando o caminho traz pista textual
    (`receita`, `receituario`, `prescricao`, `saude/receita`). Deliberadamente
    NÃO aceita outras pastas de documentos médicos (holerite, contracheque)
    nem pastas de extratores fiscais.

    `extrair()` devolve `[]` de `base.Transacao` -- a prescrição não é
    lançamento contábil. Efeito colateral: grafo.

    `extrair_receitas(caminho, texto_override=None)` é ponto de injeção
    de teste; passa `texto_override` e pula OCR/pdfplumber real.

Fixtures `.txt` em `tests/fixtures/receitas/` reproduzem texto já decodificado.

Armadilhas conhecidas (A47a-1..5):
    - OCR de receita manuscrita é ruim: usar `_ocr_comum` com cache por
      hash do conteúdo, nunca pelo nome.
    - Nome comercial vs princípio ativo: `mappings/medicamentos_dedutiveis.yaml`
      unifica via `nomes_comerciais`.
    - Tarja preta (controlada) altera `validade_meses` para 1.
    - "USO CONTÍNUO" é flag de elegibilidade fiscal, não dedução automática.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from src.extractors._ocr_comum import (
    carregar_imagem_normalizada,
    ocr_com_confidence,
)
from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_prescricao
from src.utils.logger import configurar_logger

logger = configurar_logger("receita_medica")


EXTENSOES_ACEITAS: tuple[str, ...] = (
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
)


# Validade padrão de receita comum no Brasil é 180 dias (6 meses) para
# tarja vermelha simples; controlada tem prazo menor (30 dias).
VALIDADE_DEFAULT_MESES: int = 6
VALIDADE_CONTROLADA_MESES: int = 1


_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_MEDICAMENTOS_DEDUTIVEIS: Path = _RAIZ_REPO / "mappings" / "medicamentos_dedutiveis.yaml"


# ============================================================================
# Regex canônicas da receita (acentuação PT-BR tolerada)
# ============================================================================


RE_CRM = re.compile(
    r"CRM\s*[-/\\]?\s*([A-Z]{2})\s*[-:.]?\s*(\d{3,7})",
    re.IGNORECASE | re.UNICODE,
)
RE_MEDICO_LINHA = re.compile(
    r"(?:Dr\.|Dra\.|Dr\s|Dra\s|Prof\.)\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,80})",
    re.IGNORECASE | re.UNICODE,
)
RE_PACIENTE = re.compile(
    r"Paciente\s*:?\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,80})",
    re.IGNORECASE | re.UNICODE,
)
RE_ESPECIALIDADE = re.compile(
    r"Especialidade\s*:?\s*([^\n]{3,40})",
    re.IGNORECASE | re.UNICODE,
)
RE_DATA_NUMERICA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_MESES_PT: dict[str, int] = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
RE_DATA_EXTENSA = re.compile(
    r"(\d{1,2})\s+de\s+([a-zçãéó]+)\s+de\s+(\d{4})",
    re.IGNORECASE | re.UNICODE,
)
RE_USO_CONTINUO = re.compile(r"uso\s+cont[íi]nuo", re.IGNORECASE | re.UNICODE)
RE_TARJA_PRETA = re.compile(
    r"tarja\s+preta|controle\s+especial|retinada",
    re.IGNORECASE | re.UNICODE,
)
RE_VALIDADE_MESES = re.compile(
    r"validade[^\d]{1,30}(\d{1,2})\s+(?:mes|mês|meses)",
    re.IGNORECASE | re.UNICODE,
)

# Medicamento numerado: "1. Amoxicilina 500mg", "2) Losartana 50mg"
RE_MEDICAMENTO_NUMERADO = re.compile(
    r"(?m)^\s*(\d{1,2})[\.\)]\s+"
    r"([A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç][A-Za-záéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ\s\-]{2,60}?)"
    r"\s+(\d{1,4}(?:[.,]\d{1,3})?\s*(?:mg|g|mcg|ml|ui|%))\b",
    re.IGNORECASE | re.UNICODE,
)

# Marcadores de presença de receita (detecção heurística)
RE_MARCA_RECEITUARIO = re.compile(
    r"receitu[áa]rio|prescri[çc][ãa]o|receita\s+m[eé]dica",
    re.IGNORECASE | re.UNICODE,
)


# ============================================================================
# Parsing de campos
# ============================================================================


def _normalizar_linha(bruto: str | None) -> str | None:
    if not bruto:
        return None
    limpo = re.sub(r"\s+", " ", bruto).strip(" -.,:;")
    return limpo or None


def _parse_data_para_iso(texto: str) -> str | None:
    """Aceita 'DD/MM/YYYY' ou 'DD de mês de YYYY'. Devolve ISO ou None."""
    match = RE_DATA_NUMERICA.search(texto)
    if match:
        dia, mes, ano = match.groups()
        try:
            return date(int(ano), int(mes), int(dia)).isoformat()
        except ValueError:
            return None

    match = RE_DATA_EXTENSA.search(texto)
    if match:
        dia, mes_nome, ano = match.groups()
        mes_num = _MESES_PT.get(mes_nome.lower())
        if mes_num is None:
            return None
        try:
            return date(int(ano), mes_num, int(dia)).isoformat()
        except ValueError:
            return None
    return None


def _extrair_crm(texto: str) -> str | None:
    """Extrai CRM canônico como 'UF|NUMERO' (ex: 'DF|12345').

    Linha `CRM/DF 12345` ou `CRM-DF: 67890`. UF sempre 2 letras; número
    3-7 dígitos. None quando nenhum CRM legível é detectado.
    """
    match = RE_CRM.search(texto)
    if not match:
        return None
    uf, numero = match.groups()
    return f"{uf.upper()}|{numero}"


def _extrair_medico_nome(texto: str) -> str | None:
    """Extrai o nome do médico pela primeira linha após 'Dr./Dra./Prof.'.

    Corta em marcadores de linha seguinte (CRM, especialidade) para não
    absorver o número do conselho no nome.
    """
    match = RE_MEDICO_LINHA.search(texto)
    if not match:
        return None
    bruto = match.group(1).strip()
    # Corta no primeiro marcador de fim ("CRM", "--", "|").
    for separador in (" CRM", " --", " -- ", " | ", " --"):
        idx = bruto.find(separador)
        if idx > 0:
            bruto = bruto[:idx]
            break
    return _normalizar_linha(bruto)


def _extrair_paciente(texto: str) -> str | None:
    match = RE_PACIENTE.search(texto)
    if not match:
        return None
    return _normalizar_linha(match.group(1))


def _extrair_especialidade(texto: str) -> str | None:
    match = RE_ESPECIALIDADE.search(texto)
    if not match:
        return None
    return _normalizar_linha(match.group(1))


def _extrair_validade_meses(texto: str, medicamentos_controlados: bool) -> int:
    """Deriva validade em meses do texto ou usa default.

    Prioridade:
      1. Marcador "tarja preta / controle especial / retinada" -> 1 mês.
      2. Declaração explícita "validade: N meses" no texto.
      3. Default legal de 6 meses.
    """
    if medicamentos_controlados or RE_TARJA_PRETA.search(texto):
        return VALIDADE_CONTROLADA_MESES
    match = RE_VALIDADE_MESES.search(texto)
    if match:
        try:
            return max(1, int(match.group(1)))
        except ValueError:
            pass
    return VALIDADE_DEFAULT_MESES


# ============================================================================
# Parsing de medicamentos e enriquecimento via YAML
# ============================================================================


def _carregar_medicamentos_dedutiveis() -> list[dict[str, Any]]:
    """Carrega a lista do YAML. Devolve [] em caso de falha (defensivo)."""
    if not _PATH_MEDICAMENTOS_DEDUTIVEIS.exists():
        logger.warning(
            "medicamentos_dedutiveis.yaml não encontrado em %s",
            _PATH_MEDICAMENTOS_DEDUTIVEIS,
        )
        return []
    try:
        dados = yaml.safe_load(_PATH_MEDICAMENTOS_DEDUTIVEIS.read_text(encoding="utf-8"))
    except yaml.YAMLError as erro:
        logger.warning("medicamentos_dedutiveis.yaml inválido: %s", erro)
        return []
    if not isinstance(dados, dict):
        return []
    return dados.get("medicamentos", []) or []


def _identificar_principio_ativo(
    nome_medicamento: str,
    catalogo: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Casa o nome extraído com um princípio ativo do YAML.

    Ordem de tentativa:
      1. Match exato com `principio_ativo`.
      2. Match exato com algum `nomes_comerciais`.
      3. Match por substring (normalizado upper).

    Devolve o registro completo do YAML (princípio + classe + nomes comerciais
    + observacao legal) ou None.
    """
    alvo = nome_medicamento.upper().strip()
    if not alvo:
        return None

    for entrada in catalogo:
        principio = str(entrada.get("principio_ativo", "")).upper().strip()
        if principio and principio == alvo:
            return entrada
        for nome_comercial in entrada.get("nomes_comerciais", []) or []:
            nome_norm = str(nome_comercial).upper().strip()
            if nome_norm and nome_norm == alvo:
                return entrada

    # Substring (ex: "LOSARTANA POTASSICA" casa com principio "losartana").
    for entrada in catalogo:
        principio = str(entrada.get("principio_ativo", "")).upper().strip()
        if principio and principio in alvo:
            return entrada
        for nome_comercial in entrada.get("nomes_comerciais", []) or []:
            nome_norm = str(nome_comercial).upper().strip()
            if nome_norm and nome_norm in alvo:
                return entrada
    return None


def _extrair_medicamentos(
    texto: str,
    catalogo: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extrai os medicamentos prescritos com posologia e flags derivadas.

    Estratégia: varrer linhas numeradas como "1. Nome dosagem" e buscar a
    posologia na próxima 1-2 linhas abaixo. A posologia cai em linha livre
    começando com verbos canônicos ("Tomar", "Usar", "Aplicar").
    """
    medicamentos: list[dict[str, Any]] = []

    for match in RE_MEDICAMENTO_NUMERADO.finditer(texto):
        nome_bruto = (match.group(2) or "").strip()
        dosagem = (match.group(3) or "").strip()
        nome_limpo = _normalizar_linha(nome_bruto)
        if not nome_limpo:
            continue

        # Procura posologia e forma nas 2 linhas após a linha do match.
        fim_linha = texto.find("\n", match.end())
        if fim_linha == -1:
            janela = texto[match.end() :]
        else:
            proxima2 = texto.find("\n", fim_linha + 1)
            janela_fim = proxima2 if proxima2 != -1 else len(texto)
            # Mais uma linha adiante
            proxima3 = texto.find("\n", janela_fim + 1)
            if proxima3 != -1:
                janela_fim = proxima3
            janela = texto[fim_linha:janela_fim]

        forma = _extrair_forma(janela)
        posologia = _extrair_posologia(janela)
        continuo = bool(RE_USO_CONTINUO.search(janela))
        catalogo_match = _identificar_principio_ativo(nome_limpo, catalogo)

        principio_ativo: str | None = None
        classe: str | None = None
        nomes_comerciais: list[str] = []
        elegivel = False
        if catalogo_match:
            principio_ativo = str(catalogo_match.get("principio_ativo") or "")
            classe = str(catalogo_match.get("classe") or "") or None
            nomes_comerciais = list(catalogo_match.get("nomes_comerciais") or [])
            # Elegibilidade só quando YAML sinaliza uso contínuo OU texto
            # declara "uso contínuo" para este item.
            elegivel = continuo

        # Chave canônica preferida: princípio ativo normalizado; fallback
        # para nome extraído.
        chave_bruta = principio_ativo.upper() if principio_ativo else nome_limpo.upper()
        chave_medicamento = f"MED|{chave_bruta}"

        medicamentos.append(
            {
                "chave_medicamento": chave_medicamento,
                "nome": nome_limpo,
                "dosagem": dosagem,
                "forma": forma,
                "posologia": posologia,
                "continuo": continuo,
                "principio_ativo": principio_ativo,
                "classe": classe,
                "nomes_comerciais": nomes_comerciais,
                "elegivel_dedutivel_irpf": elegivel,
            }
        )
    return medicamentos


def _extrair_forma(trecho: str) -> str | None:
    """Heurística simples para forma farmacêutica ('comprimido', 'solução'...)."""
    padrao = re.compile(
        r"\b(comprimido(?:s)?(?:\s+revestido(?:s)?)?|c[áa]psula(?:s)?|"
        r"solu[çc][ãa]o(?:\s+or[aá]l)?|xarope|gotas|suspens[ãa]o|pomada|"
        r"creme|inalador|spray)\b",
        re.IGNORECASE | re.UNICODE,
    )
    match = padrao.search(trecho)
    if not match:
        return None
    return _normalizar_linha(match.group(1))


def _extrair_posologia(trecho: str) -> str | None:
    """Captura a instrução de uso a partir de verbos canônicos.

    Aceita: 'Tomar 1 ... por N dias', 'Aplicar ...', 'Usar ...'.
    Cai no resumo textual da primeira sentença encontrada -- suficiente
    para registro; dose exata fica para o supervisor.
    """
    padrao = re.compile(
        r"(?:Tomar|Usar|Aplicar|Administrar|Ingerir)\s+([^\n\.]+)",
        re.IGNORECASE | re.UNICODE,
    )
    match = padrao.search(trecho)
    if match:
        return _normalizar_linha(match.group(0))
    return None


# ============================================================================
# Parse consolidado
# ============================================================================


def _parse_receita(
    texto: str,
    catalogo: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Parseia o texto da receita e devolve dict estruturado.

    Devolve None quando o texto não tem o mínimo para ingestão (CRM ou data
    ausentes). Validade é derivada; se texto indica controle especial ou
    lista medicamento de tarja preta, reduz para 1 mês.
    """
    cat = catalogo if catalogo is not None else _carregar_medicamentos_dedutiveis()

    crm = _extrair_crm(texto)
    data_iso = _parse_data_para_iso(texto)
    if not crm or not data_iso:
        logger.debug("receita sem CRM ou data extraíveis (crm=%s, data=%s)", crm, data_iso)
        return None

    medicamentos = _extrair_medicamentos(texto, cat)
    if not medicamentos:
        logger.debug("receita sem medicamento numerado detectado; parse descartado")
        return None

    controlados = any(
        m.get("classe") in ("benzodiazepinico", "psicoestimulante") for m in medicamentos
    )
    validade_meses = _extrair_validade_meses(texto, medicamentos_controlados=controlados)

    data_emissao_dt = date.fromisoformat(data_iso)
    data_expira = data_emissao_dt + timedelta(days=validade_meses * 30)
    expirada = data_expira < date.today()

    hash_conteudo = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8]
    chave_prescricao = f"PRESC|{data_iso}|{crm}|{hash_conteudo}"

    return {
        "chave_prescricao": chave_prescricao,
        "crm_completo": crm,
        "data_emissao": data_iso,
        "medico_nome": _extrair_medico_nome(texto),
        "medico_especialidade": _extrair_especialidade(texto),
        "paciente_nome": _extrair_paciente(texto),
        "validade_meses": validade_meses,
        "data_expira": data_expira.isoformat(),
        "expirada": expirada,
        "medicamentos": medicamentos,
    }


# ============================================================================
# Leitura de arquivo (PDF nativo, PDF escaneado, imagem)
# ============================================================================


def _ler_pdf(caminho: Path) -> str:
    """Tenta pdfplumber; fallback para OCR quando texto é vazio."""
    try:
        import pdfplumber
    except ImportError as erro:
        logger.error("pdfplumber indisponível: %s", erro)
        return ""
    try:
        with pdfplumber.open(caminho) as pdf:
            paginas: list[str] = []
            for pg in pdf.pages:
                extraido = pg.extract_text() or ""
                paginas.append(extraido)
        texto = "\n".join(paginas).strip()
        if texto and len(texto) >= 40:
            return texto
    except Exception as erro:
        logger.warning("pdfplumber falhou em %s: %s", caminho, erro)

    return _ocr_pdf(caminho)


def _ocr_pdf(caminho: Path) -> str:
    try:
        import pdfplumber
        import pytesseract
    except ImportError as erro:
        logger.error("OCR indisponível: %s", erro)
        return ""
    try:
        with pdfplumber.open(caminho) as pdf:
            textos: list[str] = []
            for pg in pdf.pages:
                imagem = pg.to_image(resolution=200).original
                textos.append(pytesseract.image_to_string(imagem, lang="por"))
        return "\n".join(textos)
    except Exception as erro:
        logger.warning("OCR PDF falhou em %s: %s", caminho, erro)
        return ""


def _ler_imagem(caminho: Path) -> str:
    """Foto de celular: `_ocr_comum` normaliza (EXIF + cinza + autocontraste)."""
    try:
        img = carregar_imagem_normalizada(caminho)
        texto, _ = ocr_com_confidence(img, lang="por")
        return texto
    except Exception as erro:
        logger.warning("OCR imagem falhou em %s: %s", caminho, erro)
        return ""


# ============================================================================
# Extrator principal
# ============================================================================


class ExtratorReceitaMedica(ExtratorBase):
    """Extrai receita médica (foto/PDF) e popula o grafo.

    Prioridade: média. Registrado em `_descobrir_extratores` DEPOIS dos
    extratores fiscais (DANFE/NFC-e/cupom térmico) e ANTES do catch-all
    `recibo_nao_fiscal` -- evita capturar PDFs/fotos que pertencem a outro
    extrator.

    `pode_processar(caminho)` aceita quando o caminho carrega pista textual
    (`receita`, `receituario`, `prescricao`, `saude/receita`) E o arquivo
    está em extensão suportada. Deliberadamente NÃO aceita arquivos em
    pastas de outros extratores (holerite, contracheque, energia, cupom,
    nfce, danfe).

    `extrair()` devolve `[]` de `base.Transacao`. Efeito colateral: grafo.

    `extrair_receitas(caminho, texto_override=None)` é ponto de injeção de
    teste; passa `texto_override` e pula OCR/pdfplumber real.
    """

    BANCO_ORIGEM: str = "Receita Médica"

    def __init__(
        self,
        caminho: Path,
        grafo: GrafoDB | None = None,
        catalogo_medicamentos: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(caminho)
        self._grafo = grafo
        self._catalogo = (
            catalogo_medicamentos
            if catalogo_medicamentos is not None
            else _carregar_medicamentos_dedutiveis()
        )

    # ------------------------------------------------------------------
    # Contrato ExtratorBase
    # ------------------------------------------------------------------

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False
        caminho_lower = str(caminho).lower()

        # Evita colisão com extratores mais específicos.
        exclusoes = (
            "holerite",
            "contracheque",
            "energia",
            "dividas_luz",
            "nfce",
            "danfe",
            "cupom",
            "nfs_fiscais",
            "garantias_estendidas",
            "comprovante",
            "pix",
            "voucher",
        )
        if any(ex in caminho_lower for ex in exclusoes):
            return False

        pistas = ("receita", "receituario", "prescricao", "saude/receita")
        return any(p in caminho_lower for p in pistas)

    def extrair(self) -> list[Transacao]:
        """Lê receita, parseia, ingere no grafo. Devolve lista vazia."""
        try:
            self.extrair_receitas(self.caminho)
        except Exception as erro:
            self.logger.error("falha ao extrair receita %s: %s", self.caminho.name, erro)
        return []

    # ------------------------------------------------------------------
    # API pública para testes e callers externos
    # ------------------------------------------------------------------

    def extrair_receitas(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extrai receitas do arquivo. `texto_override` pula leitura real.

        Uma receita por arquivo é o caso comum (foto única do celular).
        Devolve a lista de prescrições parseadas (em geral 0 ou 1) para
        teste e inspeção.

        Fallback Opus (Sprint INFRA-EXTRATORES-USAR-OPUS, 2026-05-08):
        quando ``texto_override is None`` e o parse local devolve lista
        vazia, registra tentativa via ``extrair_via_opus``. O schema
        canônico Opus atual cobre cupons de consumo, NÃO receituário
        médico (campos: ``crm``, ``medicamentos``, ``posologia``,
        ``validade``, ``prescritor``...). Hoje
        ``_mapear_schema_canonico_opus`` devolve lista vazia -- gancho
        documentado para quando houver schema próprio.
        """
        resultado_local = self._extrair_receitas_local(caminho, texto_override)

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

    def _extrair_receitas_local(
        self,
        caminho: Path,
        texto_override: str | None,
    ) -> list[dict[str, Any]]:
        """Parse local (pdfplumber/OCR + regex). Retrocompat."""
        if texto_override is not None:
            texto = texto_override
        else:
            texto = self._ler_texto(caminho)

        if not texto:
            return []

        if not RE_MARCA_RECEITUARIO.search(texto):
            self.logger.debug("texto sem marcador de receituário em %s -- ignorado", caminho.name)
            return []

        parsed = _parse_receita(texto, catalogo=self._catalogo)
        if parsed is None:
            return []

        self._ingerir(parsed, caminho)
        return [parsed]

    def _mapear_schema_canonico_opus(
        self,
        payload: dict[str, Any],  # noqa: ARG002 -- gancho documentado
    ) -> list[dict[str, Any]]:
        """Schema Opus atual NÃO cobre receituário médico.

        Gancho registrado para quando houver schema canônico próprio
        (CRM, princípios ativos, posologia, validade). Hoje devolve
        lista vazia + log INFO.
        """
        self.logger.info(
            "fallback Opus invocado em %s mas schema canônico não cobre "
            "receituário médico -- mantendo resultado local",
            self.caminho.name,
        )
        return []

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ler_texto(self, caminho: Path) -> str:
        sufixo = caminho.suffix.lower()
        if sufixo == ".pdf":
            return _ler_pdf(caminho)
        if sufixo in {".jpg", ".jpeg", ".png", ".heic", ".heif"}:
            return _ler_imagem(caminho)
        return ""

    def _ingerir(self, parsed: dict[str, Any], caminho: Path) -> None:
        medicamentos = parsed.pop("medicamentos", [])
        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            ingerir_prescricao(
                grafo,
                parsed,
                medicamentos,
                caminho_arquivo=caminho,
            )
        except ValueError as erro:
            self.logger.warning("prescricao inválida em %s: %s", caminho.name, erro)
        finally:
            if criou_grafo_localmente:
                grafo.fechar()

        if parsed.get("expirada"):
            self.logger.warning(
                "receita %s (emitida em %s) está com validade expirada -- "
                "não usar para dedução fiscal sem renovação",
                caminho.name,
                parsed.get("data_emissao"),
            )

        # Log informativo para supervisor humano.
        for med in medicamentos:
            if med.get("elegivel_dedutivel_irpf"):
                self.logger.info(
                    "medicamento elegível dedutível IRPF na receita %s: %s (princípio: %s)",
                    caminho.name,
                    med.get("nome"),
                    med.get("principio_ativo"),
                )


# ============================================================================
# Facade sem estado
# ============================================================================


def ingerir_receita_manualmente(
    grafo: GrafoDB,
    caminho: Path,
    texto_override: str | None = None,
) -> list[dict[str, Any]]:
    """Facade para scripts de backfill ou conferência manual."""
    extrator = ExtratorReceitaMedica(caminho, grafo=grafo)
    return extrator.extrair_receitas(caminho, texto_override=texto_override)


# Helpers públicos para interoperar com outros módulos e facilitar testes:
__all__ = [
    "ExtratorReceitaMedica",
    "EXTENSOES_ACEITAS",
    "VALIDADE_DEFAULT_MESES",
    "VALIDADE_CONTROLADA_MESES",
    "_parse_receita",
    "_extrair_crm",
    "_extrair_medicamentos",
    "_identificar_principio_ativo",
    "_carregar_medicamentos_dedutiveis",
    "ingerir_receita_manualmente",
]

# "A receita é palavra do médico em papel -- honra quem lê." -- princípio do paciente

# N-para-N com src/transform/irpf_tagger.py: a tag `dedutivel_medico` já
# existe no tagger para categorizar transações de farmácia. A Sprint 48
# fecha o laço quando cruza prescricao <-> transação via aresta
# `prescreve_cobre`; o campo `elegivel_dedutivel_irpf` aqui é o sinal
# upstream que alimenta esse cruzamento.
# Não toca irpf_tagger nesta sprint -- cruzamento vive no grafo, não no tag.
