"""Extrator de termo de garantia de fabricante (Sprint 47b).

Processa termos de garantia NATIVA de produto (Electrolux, Samsung, Apple,
LG, Whirlpool) ou declaração de prazo de varejista (Americanas, Magalu,
Amazon, Mercado Livre). Chega ao sistema como:

    - Certificado em PDF anexo a e-mail de confirmação de pedido.
    - Foto do folheto impresso dentro da caixa do produto.
    - Print do pedido com linha "Garantia: 12 meses" do varejista.

Distinção importante: garantia de FABRICANTE é diferente de garantia
ESTENDIDA POR APÓLICE SUSEP (aquilo é Sprint 47c, com nó `apolice` e
seguradora envolvida). Aqui modelamos `garantia` nativa ou varejista,
sem figura de seguradora.

O artefato NÃO gera transação financeira (o gasto já está no extrato
bancário via NFC-e/DANFE/cupom); o efeito colateral é popular o grafo:

    - nó `garantia` (chave sintética `GAR|<cnpj>|<serial>|<data>`)
    - nó `fornecedor` (fabricante ou varejista) via `upsert_fornecedor`
    - nó `periodo` via `upsert_periodo`
    - aresta `emitida_por` (garantia -> fornecedor)
    - aresta `ocorre_em` (garantia -> periodo)
    - aresta opcional `cobre` (garantia -> item) quando casa com item
      já ingerido de NF de compra (via `localizar_item` heurístico)

Quando faltam <=30 dias para o fim da garantia, propriedade `expirando`
vira True e o ingestor loga warning (acceptance #3 do spec 47b).

Contrato com outros módulos:

    `pode_processar(caminho)` aceita `.pdf`, `.jpg`, `.jpeg`, `.png`,
    `.heic`, `.heif`, `.txt` quando o caminho traz pista textual
    (`garantia`, `termo_garantia`, `certificado_garantia`) E NÃO casa
    com extratores de apólice estendida (`garantias_estendidas/`,
    `apolice`, `bilhete`), receita médica ou outros documentos fiscais.

    `extrair()` devolve `[]` de `base.Transacao`. Efeito colateral: grafo.

    `extrair_garantias(caminho, texto_override=None)` é ponto de injeção
    de teste; passa `texto_override` e pula OCR/pdfplumber real.

Fixtures `.txt` em `tests/fixtures/garantias_fabricante/` reproduzem
texto já decodificado (diferente de `garantias_estendidas/` da 47c).

Armadilhas conhecidas (A47b-1..4):
    - Prazo escrito por extenso e em dígito: "Prazo: 12 (doze) meses".
      Regex captura só o dígito.
    - "Garantia legal" (90 dias CDC) vs "garantia contratual" (12+ meses):
      campo `tipo_garantia` discrimina.
    - E-mail HTML de confirmação (Magalu/Amazon) tem template denso:
      quando chegar como `.eml` a Sprint 49 trata; aqui trabalhamos com
      texto já extraído.
    - Garantia de serviço (instalação, suporte) sem produto físico:
      campo `produto` pode ser vazio -- aresta `cobre` não é criada.
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
from src.graph.ingestor_documento import ingerir_garantia
from src.utils.logger import configurar_logger

logger = configurar_logger("garantia_fabricante")


EXTENSOES_ACEITAS: tuple[str, ...] = (
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
    ".txt",
)


ALERTA_PROXIMIDADE_DIAS: int = 30


_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_PADROES: Path = _RAIZ_REPO / "mappings" / "garantia_padroes.yaml"


# ============================================================================
# Regex canônicas (acentuação PT-BR tolerada)
# ============================================================================


RE_MARCA_GARANTIA = re.compile(
    r"termo\s+de\s+garantia|certificado\s+de\s+garantia|"
    r"garantia\s+do\s+fabricante|prazo\s+de\s+garantia|"
    r"garantia\s+contratual|registro\s+de\s+produto|"
    # Padrão varejista (pedido Amazon/Magalu/Americanas): "Garantia: N meses"
    # em início de linha é suficiente para considerar o arquivo termo elegível.
    r"^\s*garantia\s*:\s*\d",
    re.IGNORECASE | re.UNICODE | re.MULTILINE,
)

RE_PRODUTO = re.compile(
    r"(?:Produto|Modelo|Item|Descri[çc][ãa]o)\s*:?\s*"
    r"(?P<produto>[A-Z0-9ÁÉÍÓÚÂÊÔÃÕÇ][^\n]{3,80})",
    re.IGNORECASE | re.UNICODE,
)

RE_SERIAL = re.compile(
    r"(?:S/?N|S[ée]rie|Serial|N[uú]mero\s+de\s+s[ée]rie)\s*[:#]?\s*"
    r"(?P<serial>[A-Z0-9][A-Z0-9\-]{5,24})",
    re.IGNORECASE | re.UNICODE,
)

RE_IMEI = re.compile(
    r"IMEI\s*[:#]?\s*(?P<imei>\d{14,15})",
    re.IGNORECASE | re.UNICODE,
)

RE_DATA_COMPRA = re.compile(
    r"(?:Data\s+(?:de\s+)?(?:compra|emiss[ãa]o|registro|aquisi[çc][ãa]o))"
    r"\s*:?\s*(?P<dia>\d{2})/(?P<mes>\d{2})/(?P<ano>\d{4})",
    re.IGNORECASE | re.UNICODE,
)

RE_DATA_NUMERICA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

RE_PRAZO_MESES = re.compile(
    r"(?:Prazo|Garantia|Validade)(?:\s+(?:de|total|do\s+fabricante))?\s*[:#]?\s*"
    r"(?P<valor>\d{1,3})\s*(?:\([^)]+\)\s*)?(?P<unidade>meses?|anos?|dias?)",
    re.IGNORECASE | re.UNICODE,
)

RE_CNPJ = re.compile(
    r"(?:CNPJ)\s*:?\s*"
    r"(?P<cnpj>\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})",
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


def _normalizar_cnpj(bruto: str | None) -> str | None:
    """Devolve CNPJ canônico XX.XXX.XXX/XXXX-XX a partir de qualquer formato."""
    if not bruto:
        return None
    digitos = re.sub(r"\D", "", bruto)
    if len(digitos) != 14:
        return None
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def _parse_data_iso(texto: str) -> str | None:
    """Extrai data de compra. Tenta RE_DATA_COMPRA primeiro; senão data numérica."""
    match = RE_DATA_COMPRA.search(texto)
    if match:
        try:
            return date(
                int(match.group("ano")),
                int(match.group("mes")),
                int(match.group("dia")),
            ).isoformat()
        except ValueError:
            return None
    match = RE_DATA_NUMERICA.search(texto)
    if match:
        dia, mes, ano = match.groups()
        try:
            return date(int(ano), int(mes), int(dia)).isoformat()
        except ValueError:
            return None
    return None


def _extrair_produto(texto: str) -> str | None:
    match = RE_PRODUTO.search(texto)
    if not match:
        return None
    bruto = match.group("produto").strip()
    # Corta no primeiro separador de campo seguinte (S/N, IMEI, CNPJ).
    for sep in (" S/N", " Serial", " IMEI", " CNPJ", " Data"):
        idx = bruto.find(sep)
        if idx > 0:
            bruto = bruto[:idx]
            break
    return _normalizar_linha(bruto)


def _extrair_serial(texto: str) -> str | None:
    """Extrai serial/IMEI/S-N. IMEI tem prioridade (mais específico)."""
    match = RE_IMEI.search(texto)
    if match:
        return match.group("imei")
    match = RE_SERIAL.search(texto)
    if match:
        return match.group("serial").upper()
    return None


def _extrair_cnpj(texto: str) -> str | None:
    match = RE_CNPJ.search(texto)
    if not match:
        return None
    return _normalizar_cnpj(match.group("cnpj"))


def _extrair_prazo_meses(texto: str) -> int | None:
    """Devolve prazo em MESES. Converte anos e dias se preciso.

    Armadilha A47b-1: regex descarta texto entre parênteses (ex:
    "12 (doze) meses"). O grupo `valor` captura só o dígito.
    Armadilha A47b-2: "90 dias" é garantia legal CDC -- aceita, mas
    extrator flaga via tipo_garantia quando possível (quando declarado).
    """
    match = RE_PRAZO_MESES.search(texto)
    if not match:
        return None
    try:
        valor = int(match.group("valor"))
    except ValueError:
        return None
    unidade = match.group("unidade").lower()
    if unidade.startswith("ano"):
        return valor * 12
    if unidade.startswith("dia"):
        # Arredonda para baixo (90 dias ~3 meses; 180 dias ~6 meses).
        return max(1, valor // 30)
    return valor


# ============================================================================
# Carregamento do YAML de padrões conhecidos
# ============================================================================


def _carregar_padroes() -> dict[str, Any]:
    """Carrega `garantia_padroes.yaml`. Devolve dict vazio em falha (defensivo)."""
    if not _PATH_PADROES.exists():
        logger.warning("garantia_padroes.yaml não encontrado em %s", _PATH_PADROES)
        return {"fabricantes": [], "varejistas": [], "fallback": {}}
    try:
        dados = yaml.safe_load(_PATH_PADROES.read_text(encoding="utf-8"))
    except yaml.YAMLError as erro:
        logger.warning("garantia_padroes.yaml inválido: %s", erro)
        return {"fabricantes": [], "varejistas": [], "fallback": {}}
    if not isinstance(dados, dict):
        return {"fabricantes": [], "varejistas": [], "fallback": {}}
    return dados


def _identificar_fornecedor_conhecido(
    texto: str,
    padroes: dict[str, Any],
) -> dict[str, Any] | None:
    """Tenta casar o texto com fabricante ou varejista conhecido.

    Ordem: fabricantes (match mais específico, determina categoria_produto)
    depois varejistas. Casamento por nome canonical ou alias (case-insensitive).
    Devolve o registro completo do YAML ou None.
    """
    texto_norm = texto.upper()

    for fabricante in padroes.get("fabricantes", []) or []:
        candidatos = [fabricante.get("nome", "")] + list(
            fabricante.get("aliases", []) or []
        )
        for cand in candidatos:
            if cand and cand.upper() in texto_norm:
                return {**fabricante, "_kind": "fabricante"}

    for varejista in padroes.get("varejistas", []) or []:
        candidatos = [varejista.get("nome", "")] + list(
            varejista.get("aliases", []) or []
        )
        for cand in candidatos:
            if cand and cand.upper() in texto_norm:
                return {**varejista, "_kind": "varejista"}

    return None


# ============================================================================
# Parse consolidado
# ============================================================================


def _parse_garantia(
    texto: str,
    padroes: dict[str, Any] | None = None,
    hoje: date | None = None,
) -> dict[str, Any] | None:
    """Parseia termo de garantia e devolve dict estruturado.

    Devolve None quando falta mínimo (CNPJ + data + prazo). Produto e
    serial podem ser vazios (garantia de serviço, A47b-4).

    O parâmetro `hoje` permite congelar a data de referência em testes
    (evita flakiness quando fixture usa prazo próximo). Em runtime real,
    passar None para usar `date.today()`.
    """
    pad = padroes if padroes is not None else _carregar_padroes()

    cnpj = _extrair_cnpj(texto)
    data_iso = _parse_data_iso(texto)
    prazo_meses = _extrair_prazo_meses(texto)

    # Se CNPJ não está explícito no texto, tenta herdar do fornecedor
    # conhecido identificado por nome/alias no YAML.
    match_conhecido = _identificar_fornecedor_conhecido(texto, pad)
    if not cnpj and match_conhecido:
        cnpj_bruto = match_conhecido.get("cnpj")
        cnpj = _normalizar_cnpj(cnpj_bruto) if cnpj_bruto else None

    # Se prazo não foi extraído mas fornecedor conhecido tem padrão default,
    # usa como fallback (último recurso).
    if prazo_meses is None and match_conhecido:
        prazo_default = match_conhecido.get("prazo_padrao_meses")
        if isinstance(prazo_default, int) and prazo_default > 0:
            prazo_meses = prazo_default

    if not cnpj or not data_iso or not prazo_meses:
        logger.debug(
            "garantia sem CNPJ/data/prazo extraíveis "
            "(cnpj=%s, data=%s, prazo=%s)",
            cnpj, data_iso, prazo_meses,
        )
        return None

    produto = _extrair_produto(texto)
    serial = _extrair_serial(texto)

    # Chave canônica: CNPJ + serial + data de início. Serial vazio usa hash
    # dos primeiros 80 chars do texto (suficiente para idempotência sem
    # colidir entre termos distintos do mesmo fornecedor na mesma data).
    if serial:
        chave_serial = serial
    else:
        chave_serial = "NOSERIAL-" + hashlib.sha256(
            texto[:80].encode("utf-8")
        ).hexdigest()[:8]
    chave_garantia = f"GAR|{cnpj}|{chave_serial}|{data_iso}"

    data_inicio_dt = date.fromisoformat(data_iso)
    data_fim_dt = data_inicio_dt + timedelta(days=prazo_meses * 30)
    data_hoje = hoje if hoje is not None else date.today()
    dias_restantes = (data_fim_dt - data_hoje).days
    expirando = 0 <= dias_restantes <= ALERTA_PROXIMIDADE_DIAS
    expirada = dias_restantes < 0

    fornecedor_nome = match_conhecido.get("nome") if match_conhecido else None
    categoria_produto = (
        match_conhecido.get("categoria_produto") if match_conhecido else None
    )
    tipo_garantia = (
        "fabricante"
        if match_conhecido and match_conhecido.get("_kind") == "fabricante"
        else "varejista"
        if match_conhecido
        else "fabricante"
    )
    # Garantia legal de 90 dias (CDC art. 26) quando prazo curto e categoria
    # é servico ou quando texto menciona "garantia legal" explicitamente.
    if prazo_meses <= 3 or re.search(
        r"garantia\s+legal", texto, re.IGNORECASE | re.UNICODE
    ):
        tipo_garantia = "legal_cdc"

    return {
        "chave_garantia": chave_garantia,
        "fornecedor_cnpj": cnpj,
        "fornecedor_nome": fornecedor_nome,
        "data_inicio": data_iso,
        "data_fim": data_fim_dt.isoformat(),
        "prazo_meses": prazo_meses,
        "produto": produto,
        "numero_serie": serial,
        "categoria_produto": categoria_produto,
        "tipo_garantia": tipo_garantia,
        "expirando": expirando,
        "expirada": expirada,
    }


# ============================================================================
# Leitura de arquivo (PDF nativo, PDF escaneado, imagem, .txt)
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


class ExtratorGarantiaFabricante(ExtratorBase):
    """Extrai termo de garantia de fabricante (foto/PDF/texto) e popula o grafo.

    Prioridade: baixa. Registrado em `_descobrir_extratores` DEPOIS dos
    extratores fiscais (DANFE/NFC-e/cupom térmico), DEPOIS do extrator de
    apólice estendida (47c), DEPOIS da receita médica (47a) e ANTES do
    catch-all `recibo_nao_fiscal`.

    `pode_processar(caminho)` aceita quando o caminho carrega pista
    (`garantia_fabricante`, `termo_garantia`, `certificado_garantia`) E o
    arquivo NÃO está em pasta de apólice estendida (`garantias_estendidas`)
    ou de outro extrator específico.

    `extrair()` devolve `[]` de `base.Transacao`. Efeito colateral: grafo.

    `extrair_garantias(caminho, texto_override=None)` é ponto de injeção
    de teste; passa `texto_override` e pula OCR/pdfplumber real.
    """

    BANCO_ORIGEM: str = "Garantia Fabricante"

    def __init__(
        self,
        caminho: Path,
        grafo: GrafoDB | None = None,
        padroes: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(caminho)
        self._grafo = grafo
        self._padroes = padroes if padroes is not None else _carregar_padroes()

    # ------------------------------------------------------------------
    # Contrato ExtratorBase
    # ------------------------------------------------------------------

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False
        caminho_lower = str(caminho).lower()

        # Evita colisão com extratores mais específicos.
        exclusoes = (
            "garantias_estendidas",
            "apolice",
            "bilhete",
            "holerite",
            "contracheque",
            "energia",
            "dividas_luz",
            "nfce",
            "danfe",
            "cupom",
            "nfs_fiscais",
            "comprovante",
            "pix",
            "voucher",
            "receita",
            "receituario",
            "prescricao",
        )
        if any(ex in caminho_lower for ex in exclusoes):
            return False

        pistas = (
            "garantia_fabricante",
            "garantias_fabricante",
            "termo_garantia",
            "certificado_garantia",
            "garantia/",
            "/garantias/",
        )
        return any(p in caminho_lower for p in pistas)

    def extrair(self) -> list[Transacao]:
        """Lê termo, parseia, ingere no grafo. Devolve lista vazia."""
        try:
            self.extrair_garantias(self.caminho)
        except Exception as erro:
            self.logger.error(
                "falha ao extrair garantia %s: %s", self.caminho.name, erro
            )
        return []

    # ------------------------------------------------------------------
    # API pública para testes e callers externos
    # ------------------------------------------------------------------

    def extrair_garantias(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extrai garantia do arquivo. `texto_override` pula leitura real.

        Uma garantia por arquivo é o caso comum. Devolve a lista de
        garantias parseadas (em geral 0 ou 1) para teste e inspeção.
        """
        if texto_override is not None:
            texto = texto_override
        else:
            texto = self._ler_texto(caminho)

        if not texto:
            return []

        if not RE_MARCA_GARANTIA.search(texto):
            self.logger.debug(
                "texto sem marcador de garantia em %s -- ignorado", caminho.name
            )
            return []

        parsed = _parse_garantia(texto, padroes=self._padroes)
        if parsed is None:
            return []

        self._ingerir(parsed, caminho)
        return [parsed]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ler_texto(self, caminho: Path) -> str:
        sufixo = caminho.suffix.lower()
        if sufixo == ".pdf":
            return _ler_pdf(caminho)
        if sufixo == ".txt":
            try:
                return caminho.read_text(encoding="utf-8")
            except OSError as erro:
                self.logger.warning("falha lendo %s: %s", caminho, erro)
                return ""
        if sufixo in {".jpg", ".jpeg", ".png", ".heic", ".heif"}:
            return _ler_imagem(caminho)
        return ""

    def _ingerir(self, parsed: dict[str, Any], caminho: Path) -> None:
        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            ingerir_garantia(grafo, parsed, caminho_arquivo=caminho)
        except ValueError as erro:
            self.logger.warning(
                "garantia inválida em %s: %s", caminho.name, erro
            )
        finally:
            if criou_grafo_localmente:
                grafo.fechar()

        if parsed.get("expirada"):
            self.logger.warning(
                "garantia %s (produto %s) EXPIRADA em %s -- não cobrável",
                caminho.name,
                parsed.get("produto") or "?",
                parsed.get("data_fim"),
            )


# ============================================================================
# Facade sem estado
# ============================================================================


def ingerir_garantia_manualmente(
    grafo: GrafoDB,
    caminho: Path,
    texto_override: str | None = None,
) -> list[dict[str, Any]]:
    """Facade para scripts de backfill ou conferência manual."""
    extrator = ExtratorGarantiaFabricante(caminho, grafo=grafo)
    return extrator.extrair_garantias(caminho, texto_override=texto_override)


__all__ = [
    "ExtratorGarantiaFabricante",
    "EXTENSOES_ACEITAS",
    "ALERTA_PROXIMIDADE_DIAS",
    "_parse_garantia",
    "_extrair_cnpj",
    "_extrair_prazo_meses",
    "_extrair_serial",
    "_extrair_produto",
    "_identificar_fornecedor_conhecido",
    "_carregar_padroes",
    "ingerir_garantia_manualmente",
]


# "O que vale comprar vale lembrar." -- princípio do consumidor cauteloso
