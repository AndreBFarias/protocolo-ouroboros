"""Extrator de cupom fiscal térmico fotografado (Sprint 45).

Cupom térmico é a fonte granular de consumo diário. O usuário fotografa
no celular e joga na inbox. Este extrator:

  1. Carrega a foto respeitando rotação EXIF (A45-3 cobre inversão 180°).
  2. Roda OCR via tesseract (`lang=por`) com confidence agregada.
  3. Cacheia o texto em `data/cache/ocr/<hash_do_conteudo>.txt` (A45-6).
  4. Detecta o emissor via identificador no texto e escolhe o regex
     apropriado de `mappings/ocr_cupom_regex.yaml`.
  5. Faz pós-processamento numérico nos trechos "R$ X,XX" (A45-1).
  6. Parseia cabeçalho (CNPJ, razão social, data) e itens.
  7. Calcula recall = soma(itens) / total e, se confidence < 70% ou
     recall < 70%, move a foto para `data/raw/_conferir/<uuid>/` e
     registra proposta em `docs/propostas/extracao_cupom/<uuid>.md`.
  8. Caso contrário, ingere no grafo via `ingerir_documento_fiscal`.

O extrator NÃO devolve `base.Transacao` -- a despesa já aparece no
extrato bancário do cartão/PIX usado no pagamento. O efeito colateral
é o grafo de consumo.

Fixtures `.txt` em `tests/fixtures/cupons/` reproduzem a saída OCR para
testes determinísticos via parâmetro `texto_override`.

Não confunde com:
  - `energia_ocr.py` (contas de energia, screenshot app Neoenergia)
  - `nfce_pdf.py` (NFC-e PDF nativo, Sprint 44b)
  - `cupom_garantia_estendida_pdf.py` (apólice de garantia, Sprint 47c)
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from src.extractors._ocr_comum import (
    cache_key,
    carregar_imagem_normalizada,
    ler_ou_gerar_cache,
    normalizar_digitos_valor,
    ocr_com_confidence,
    rotacionar_180,
)
from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.transform.irpf_tagger import _REGEX_CNPJ
from src.utils.logger import configurar_logger
from src.utils.parse_br import parse_valor_br

logger = configurar_logger("cupom_termico_foto")


EXTENSOES_ACEITAS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".heic", ".heif")

# Limiar do acceptance: abaixo disto, cupom vai para conferência supervisor.
LIMIAR_CONFIDENCE_OK: float = 70.0
LIMIAR_RECALL_OK: float = 0.70


# ============================================================================
# Configuração de regex por emissor
# ============================================================================


_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_MAPPING_PADRAO: Path = _RAIZ_REPO / "mappings" / "ocr_cupom_regex.yaml"
_DIR_CACHE_OCR_PADRAO: Path = _RAIZ_REPO / "data" / "cache" / "ocr"
_DIR_CONFERIR_PADRAO: Path = _RAIZ_REPO / "data" / "raw" / "_conferir"
_DIR_PROPOSTAS_PADRAO: Path = (
    _RAIZ_REPO / "docs" / "propostas" / "extracao_cupom"
)


def _carregar_regex_emissores(
    caminho_yaml: Path = _PATH_MAPPING_PADRAO,
) -> list[dict[str, Any]]:
    """Carrega a lista de emissores com regex compilados.

    Devolve lista de dicts com:
      nome, identificador (regex compilada ou None), regex_item (compilada).
    Mantém a ordem do YAML; o detector usa a primeira regra cujo
    identificador bate, com `generico` como fallback no final.
    """
    if not caminho_yaml.exists():
        raise FileNotFoundError(f"mapping de regex não encontrado: {caminho_yaml}")
    dados = yaml.safe_load(caminho_yaml.read_text(encoding="utf-8")) or {}
    emissores_brutos: dict[str, dict[str, str]] = dados.get("emissores", {}) or {}

    resultado: list[dict[str, Any]] = []
    for nome, cfg in emissores_brutos.items():
        identificador_str: str = cfg.get("identificador", "") or ""
        regex_item_str: str = cfg.get("regex_item", "") or ""
        if not regex_item_str:
            logger.warning("emissor %s sem regex_item; ignorado", nome)
            continue
        identificador = (
            re.compile(identificador_str, re.IGNORECASE | re.UNICODE)
            if identificador_str
            else None
        )
        regex_item = re.compile(
            regex_item_str, re.MULTILINE | re.UNICODE | re.VERBOSE | re.IGNORECASE
        )
        resultado.append(
            {
                "nome": nome,
                "identificador": identificador,
                "regex_item": regex_item,
            }
        )
    return resultado


# ============================================================================
# Detecção de marca de cupom fiscal no texto OCR
# ============================================================================


_RE_CUPOM_FISCAL_MARCAS = re.compile(
    r"(CUPOM\s+FISCAL|"
    r"NFC-?e|"
    r"CNPJ\s*:?\s*\d|"
    r"EXTRATO\s+CUPOM|"
    r"DOCUMENTO\s+AUXILIAR\s+DA\s+NOTA\s+FISCAL|"
    r"COO\s*:?\s*\d|"
    r"CCF\s*:?\s*\d)",
    re.IGNORECASE | re.UNICODE,
)


def _parece_cupom_fiscal(texto: str) -> bool:
    """Heurística: texto OCR de cupom deve ter CNPJ + marca de cupom."""
    if not texto or len(texto) < 40:
        return False
    tem_cnpj = bool(_REGEX_CNPJ.search(texto))
    tem_marca = bool(_RE_CUPOM_FISCAL_MARCAS.search(texto))
    return tem_cnpj and tem_marca


# ============================================================================
# Parsing de cabeçalho
# ============================================================================


_RE_DATA_BR = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
_RE_RAZAO_SOCIAL = re.compile(
    r"^\s*(?P<razao>[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 &\./\-]{3,}?)\s*$",
    re.MULTILINE | re.UNICODE,
)
_RE_COO = re.compile(r"COO\s*:?\s*(\d{1,9})", re.IGNORECASE)
_RE_CCF = re.compile(r"CCF\s*:?\s*(\d{1,9})", re.IGNORECASE)
_RE_SAT = re.compile(r"SAT\s*:?\s*(\d{1,9})", re.IGNORECASE)
_RE_TOTAL_CUPOM = re.compile(
    r"(?:TOTAL|VALOR\s+TOTAL|VALOR\s+A\s+PAGAR|TOTAL\s+R\$)\s*R?\$?\s*"
    r"(\d{1,7}[.,]\d{2})",
    re.IGNORECASE,
)


def _parse_data(texto: str) -> str | None:
    """Retorna a primeira data `YYYY-MM-DD` encontrada, ou None."""
    match = _RE_DATA_BR.search(texto)
    if not match:
        return None
    dia, mes, ano = match.groups()
    try:
        dt = date(int(ano), int(mes), int(dia))
    except ValueError:
        return None
    return dt.isoformat()


def _parse_cnpj_primeiro(texto: str) -> str | None:
    """Primeiro CNPJ no cabeçalho (sem formato canônico garantido)."""
    match = _REGEX_CNPJ.search(texto)
    return match.group(0) if match else None


def _parse_razao_social(texto: str, cnpj: str | None) -> str | None:
    """Razão social: primeira linha em caixa alta antes ou depois do CNPJ.

    Prioriza a linha que contém o CNPJ (padrão "RAZAO SOCIAL CNPJ:
    XX.XXX.XXX/XXXX-XX"). Caso não bata, devolve a primeira linha
    alfabética do topo.
    """
    if cnpj:
        for linha in texto.splitlines():
            if cnpj in linha:
                sem_cnpj = linha.replace(cnpj, "").strip()
                sem_cnpj = re.sub(r"CNPJ\s*:?", "", sem_cnpj, flags=re.IGNORECASE)
                sem_cnpj = sem_cnpj.strip(" -:")
                if len(sem_cnpj) >= 4:
                    return sem_cnpj

    for linha in texto.splitlines()[:8]:
        limpa = linha.strip()
        if len(limpa) < 5:
            continue
        if _REGEX_CNPJ.search(limpa):
            continue
        if _RE_RAZAO_SOCIAL.match(limpa):
            return limpa
    return None


def _parse_total(texto: str) -> float | None:
    """Total do cupom em float. Prioriza `VALOR A PAGAR` > `TOTAL`."""
    melhor: float | None = None
    for match in _RE_TOTAL_CUPOM.finditer(texto):
        bruto = match.group(1).replace(".", "").replace(",", ".")
        try:
            valor = float(bruto)
        except ValueError:
            continue
        if melhor is None or valor > melhor:
            # Estratégia: pega o maior (total > subtotais).
            melhor = valor
    return melhor


def _parse_numero_cupom(texto: str) -> dict[str, str | None]:
    """Extrai COO / CCF / SAT quando presentes."""
    return {
        "coo": _RE_COO.search(texto).group(1) if _RE_COO.search(texto) else None,
        "ccf": _RE_CCF.search(texto).group(1) if _RE_CCF.search(texto) else None,
        "sat": _RE_SAT.search(texto).group(1) if _RE_SAT.search(texto) else None,
    }


def _parse_cabecalho_cupom(texto: str) -> dict[str, Any]:
    """Monta o dict `documento` esperado por `ingerir_documento_fiscal`.

    `chave_44` é sintetizada quando o cupom não tem chave SEFAZ impressa
    (cupom fiscal antigo). O formato é `CUPOM|<cnpj>|<data>|<coo_or_hash>`
    para manter a chave canônica única e legível no grafo.
    """
    cnpj = _parse_cnpj_primeiro(texto)
    data_iso = _parse_data(texto)
    razao = _parse_razao_social(texto, cnpj)
    total = _parse_total(texto)
    numeros = _parse_numero_cupom(texto)
    coo = numeros.get("coo")

    if not (cnpj and data_iso):
        return {}

    # Chave sintética determinística (idempotente por foto do mesmo cupom).
    identificador_numero = coo or "semnum"
    chave_sintetica = f"CUPOM|{cnpj}|{data_iso}|{identificador_numero}"

    documento: dict[str, Any] = {
        "chave_44": chave_sintetica,
        "cnpj_emitente": cnpj,
        "data_emissao": data_iso,
        "tipo_documento": "cupom_fiscal",
        "razao_social": razao,
        "total": total,
        "numero": coo,
        "serie": None,
        "forma_pagamento": None,
    }
    # Números internos do cupom vão para metadata sem poluir contrato.
    if any(numeros.values()):
        documento["numeros_internos"] = {
            k: v for k, v in numeros.items() if v is not None
        }
    return documento


# ============================================================================
# Parsing de itens por emissor
# ============================================================================


def _detectar_emissor(
    texto: str, emissores: list[dict[str, Any]]
) -> dict[str, Any]:
    """Escolhe a regra de emissor. Cai para `generico` se nenhuma bate."""
    for emissor in emissores:
        identificador = emissor.get("identificador")
        if identificador is None:
            continue  # `generico`: avaliado só no fallback
        if identificador.search(texto):
            return emissor
    for emissor in emissores:
        if emissor.get("nome") == "generico":
            return emissor
    raise RuntimeError("nenhum emissor definido em ocr_cupom_regex.yaml")


def _parse_itens_cupom(
    texto: str, emissor: dict[str, Any]
) -> list[dict[str, Any]]:
    """Aplica regex do emissor a cada linha do texto; devolve lista de itens.

    Cada item tem `codigo`, `descricao`, `qtde`, `unidade`, `valor_unit`,  # noqa: accent
    `valor_total` (todos podem ser None exceto `descricao` e                # noqa: accent
    `valor_total`). Itens com qtd*unit inconsistente com total (A45-2)
    ficam marcados com `_inconsistente=True` no metadata mas não são
    descartados.
    """
    regex_item: re.Pattern[str] = emissor["regex_item"]
    itens: list[dict[str, Any]] = []
    contador_sem_codigo = 0
    for match in regex_item.finditer(texto):
        grupos = match.groupdict()
        descricao = (grupos.get("descricao") or "").strip()
        if not descricao:
            continue
        codigo = grupos.get("codigo")
        if not codigo:
            contador_sem_codigo += 1
            codigo = f"SEMCOD{contador_sem_codigo:04d}"

        qtde = parse_valor_br(grupos.get("qtde")) or 1.0
        valor_unit = parse_valor_br(grupos.get("valor_unit"))
        valor_total = parse_valor_br(grupos.get("valor_total"))

        if valor_total is None:
            continue
        if valor_unit is None and qtde:
            valor_unit = valor_total / qtde if qtde else valor_total

        item = {
            "codigo": codigo,
            "descricao": descricao,
            "qtde": qtde,
            "unidade": (grupos.get("unidade") or "").strip() or None,
            "valor_unit": valor_unit,
            "valor_total": valor_total,
        }
        # A45-2: valida qtde*unit ~ total (tolerância 1 centavo)
        if valor_unit is not None and qtde:
            esperado = round(qtde * valor_unit, 2)
            if abs(esperado - valor_total) > 0.01:
                item["_inconsistente"] = True
        itens.append(item)
    return itens


# ============================================================================
# Recall (cobertura) dos itens em relação ao total
# ============================================================================


def calcular_recall(total: float | None, itens: list[dict[str, Any]]) -> float:
    """Devolve soma(item.valor_total) / total. 0.0 se `total` inválido."""
    if not total or total <= 0:
        return 0.0
    soma = sum(
        item.get("valor_total", 0.0) or 0.0
        for item in itens
    )
    return round(soma / total, 4)


# ============================================================================
# Fallback supervisor
# ============================================================================


def _registrar_fallback_supervisor(
    caminho_foto: Path,
    texto_ocr: str,
    confidence: float,
    recall: float,
    documento: dict[str, Any],
    itens: list[dict[str, Any]],
    diretorio_conferir: Path,
    diretorio_propostas: Path,
) -> Path:
    """Move a foto para `_conferir/<uuid>/` e cria proposta em MD.

    Devolve o caminho do novo diretório. Não levanta exceção se o
    arquivo de origem não existir mais (idempotência em reprocessamento).
    """
    identificador = uuid.uuid4().hex[:12]
    dir_alvo = diretorio_conferir / identificador
    dir_alvo.mkdir(parents=True, exist_ok=True)
    destino_foto = dir_alvo / caminho_foto.name
    if caminho_foto.exists() and caminho_foto.resolve() != destino_foto.resolve():
        try:
            destino_foto.write_bytes(caminho_foto.read_bytes())
        except OSError as erro:
            logger.warning(
                "falha ao copiar foto para conferência: %s", erro
            )

    diretorio_propostas.mkdir(parents=True, exist_ok=True)
    proposta = diretorio_propostas / f"{identificador}.md"
    conteudo = _montar_proposta_supervisor(
        caminho_foto=caminho_foto,
        texto_ocr=texto_ocr,
        confidence=confidence,
        recall=recall,
        documento=documento,
        itens=itens,
    )
    proposta.write_text(conteudo, encoding="utf-8")
    logger.info(
        "cupom %s enviado para conferência: %s (confidence=%.1f, recall=%.2f)",
        caminho_foto.name,
        identificador,
        confidence,
        recall,
    )
    return dir_alvo


def _montar_proposta_supervisor(
    caminho_foto: Path,
    texto_ocr: str,
    confidence: float,
    recall: float,
    documento: dict[str, Any],
    itens: list[dict[str, Any]],
) -> str:
    linhas: list[str] = [
        f"# Conferência manual de cupom fiscal -- {caminho_foto.name}",
        "",
        f"- Data: {datetime.now().isoformat(timespec='seconds')}",
        f"- Confidence OCR: {confidence:.1f}%",
        f"- Recall estimado: {recall * 100:.1f}%",
        "",
        "## Cabeçalho parseado",
        "",
        f"- CNPJ: {documento.get('cnpj_emitente') or '(não detectado)'}",
        f"- Razão: {documento.get('razao_social') or '(não detectada)'}",
        f"- Data: {documento.get('data_emissao') or '(não detectada)'}",
        f"- Total: {documento.get('total') or '(não detectado)'}",
        "",
        "## Itens parseados",
        "",
    ]
    if itens:
        linhas.append("| Código | Descrição | Qtde | Unit | Total |")
        linhas.append("|---|---|---|---|---|")
        for item in itens:
            linhas.append(
                f"| {item.get('codigo', '')} "
                f"| {item.get('descricao', '')} "
                f"| {item.get('qtde', '')} "
                f"| {item.get('valor_unit', '')} "
                f"| {item.get('valor_total', '')} |"
            )
    else:
        linhas.append("_Nenhum item parseado._")
    linhas.extend(
        [
            "",
            "## Texto OCR bruto",
            "",
            "```",
            texto_ocr,
            "```",
            "",
            "## Ação esperada",
            "",
            "1. Abrir a foto original (copiada para `data/raw/_conferir/`).",
            "2. Comparar itens acima com o que a foto mostra.",
            "3. Propor correções no regex de `mappings/ocr_cupom_regex.yaml` "
            "ou anotar substituições de OCR-pós.",
            "",
        ]
    )
    return "\n".join(linhas)


# ============================================================================
# Extrator principal
# ============================================================================


class ExtratorCupomTermicoFoto(ExtratorBase):
    """Extrai cupom fiscal fotografado (JPG/PNG/HEIC) via OCR tesseract.

    `pode_processar` aceita imagens em pastas relacionadas a nota
    fiscal/cupom ou com pistas no nome. Para imagens genéricas (ex:
    screenshot de energia), recusa para não colidir com `energia_ocr.py`.

    `extrair` devolve `[]` de `base.Transacao`. Efeito colateral:
    ingestão no grafo, OU registro de fallback supervisor quando
    confidence/recall abaixo do limiar.

    `extrair_cupom(caminho, texto_override=None)` é ponto de injeção
    para testes: quando `texto_override` é dado, pula o OCR real e
    processa direto o texto passado. Devolve (documento, itens,
    confidence, recall).
    """

    BANCO_ORIGEM: str = "Cupom Fiscal Térmico"

    def __init__(
        self,
        caminho: Path,
        grafo: GrafoDB | None = None,
        emissores: list[dict[str, Any]] | None = None,
        diretorio_cache: Path | None = None,
        diretorio_conferir: Path | None = None,
        diretorio_propostas: Path | None = None,
    ) -> None:
        super().__init__(caminho)
        self._grafo = grafo
        self._emissores = emissores or _carregar_regex_emissores()
        self._dir_cache = diretorio_cache or _DIR_CACHE_OCR_PADRAO
        self._dir_conferir = diretorio_conferir or _DIR_CONFERIR_PADRAO
        self._dir_propostas = diretorio_propostas or _DIR_PROPOSTAS_PADRAO

    # --------------------------------------------------------------------
    # Contrato ExtratorBase
    # --------------------------------------------------------------------

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False

        caminho_lower = str(caminho).lower()
        pastas_cupom = ("cupom", "nfs_fiscais", "nfce", "cupons", "_classificar")
        if any(p in caminho_lower for p in pastas_cupom):
            # Evita colidir com energia_ocr.py: imagens em dividas_luz/energia
            # são do outro extrator.
            if "dividas_luz" in caminho_lower or "energia" in caminho_lower:
                return False
            return True

        nome_lower = caminho.name.lower()
        pistas = ("cupom", "nfce", "nota_fiscal", "receipt")
        return any(p in nome_lower for p in pistas)

    def extrair(self) -> list[Transacao]:
        """OCR + parse + ingestão ou fallback. Devolve lista vazia de Transacao."""
        try:
            resultado = self.extrair_cupom(self.caminho)
        except Exception as erro:
            self.logger.error(
                "falha ao extrair cupom %s: %s", self.caminho.name, erro
            )
            return []

        documento = resultado["documento"]
        itens = resultado["itens"]
        confidence = resultado["confidence"]
        recall = resultado["recall"]

        precisa_conferencia = (
            confidence < LIMIAR_CONFIDENCE_OK or recall < LIMIAR_RECALL_OK
        )
        if not documento or precisa_conferencia:
            _registrar_fallback_supervisor(
                caminho_foto=self.caminho,
                texto_ocr=resultado["texto"],
                confidence=confidence,
                recall=recall,
                documento=documento or {},
                itens=itens,
                diretorio_conferir=self._dir_conferir,
                diretorio_propostas=self._dir_propostas,
            )
            return []

        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            ingerir_documento_fiscal(
                grafo, documento, itens, caminho_arquivo=self.caminho
            )
        except ValueError as erro:
            self.logger.warning(
                "cupom inválido em %s: %s", self.caminho.name, erro
            )
        finally:
            if criou_grafo_localmente:
                grafo.fechar()

        self.logger.info(
            "cupom ingerido: %s (%d itens, confidence=%.1f, recall=%.2f)",
            self.caminho.name,
            len(itens),
            confidence,
            recall,
        )
        return []

    # --------------------------------------------------------------------
    # API pública usável por testes
    # --------------------------------------------------------------------

    def extrair_cupom(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> dict[str, Any]:
        """Extrai cupom. Quando `texto_override` é dado, pula OCR real.

        Devolve dict com `documento`, `itens`, `texto`, `confidence`,
        `recall`, `emissor`. Quando nada parseia, `documento` vem `{}`.
        """
        if texto_override is not None:
            texto = texto_override
            confidence = 100.0  # texto confiável em teste
        else:
            texto, confidence = self._rodar_ocr_com_cache(caminho)

        texto_normalizado = normalizar_digitos_valor(texto)
        if not _parece_cupom_fiscal(texto_normalizado):
            return {
                "documento": {},
                "itens": [],
                "texto": texto,
                "confidence": confidence,
                "recall": 0.0,
                "emissor": None,
            }

        emissor = _detectar_emissor(texto_normalizado, self._emissores)
        documento = _parse_cabecalho_cupom(texto_normalizado)
        itens = _parse_itens_cupom(texto_normalizado, emissor)
        recall = calcular_recall(documento.get("total"), itens) if documento else 0.0
        return {
            "documento": documento,
            "itens": itens,
            "texto": texto,
            "confidence": confidence,
            "recall": recall,
            "emissor": emissor.get("nome"),
        }

    # --------------------------------------------------------------------
    # OCR + cache
    # --------------------------------------------------------------------

    def _rodar_ocr_com_cache(self, caminho: Path) -> tuple[str, float]:
        """Faz OCR com cache em `_dir_cache`. Retorna (texto, confidence)."""

        def _gerar() -> tuple[str, float]:
            img = carregar_imagem_normalizada(caminho)
            texto, confidence = ocr_com_confidence(img, lang="por")
            # A45-3: se texto muito curto OU confidence muito baixa,
            # tenta rotação 180°. Usa o melhor dos dois.
            if confidence < LIMIAR_CONFIDENCE_OK or len(texto.strip()) < 40:
                img_invertida = rotacionar_180(img)
                texto_inv, confidence_inv = ocr_com_confidence(
                    img_invertida, lang="por"
                )
                if confidence_inv > confidence:
                    return texto_inv, confidence_inv
            return texto, confidence

        return ler_ou_gerar_cache(
            caminho,
            _gerar,
            self._dir_cache,
        )

    def chave_cache(self, caminho: Path) -> str:
        """Exposta para testes -- hash do conteúdo."""
        return cache_key(caminho)


# "Um cupom fiscal é um diário de apetites. Ler é conhecer-se."
# -- princípio de consumidor consciente
