"""Extrator de recibo não-fiscal (Sprint 47).

Recibo não-fiscal é qualquer evidência de pagamento sem estrutura de
nota fiscal: comprovante de Pix impresso/screenshot (Nubank, Itaú,
Santander), voucher de serviço (iFood, 99, Uber) e recibos manuscritos
digitalizados. Nunca traz CNPJ do emitente no padrão SEFAZ -- quando
há CNPJ/CPF, é da contraparte (quem recebeu), não do emitente.

Pipeline:
  1. Obter texto: pdfplumber para PDF nativo; `_ocr_comum` para foto.
  2. Detectar layout por identificador textual (Pix Nubank vs Itaú vs
     voucher iFood vs voucher 99).
  3. Aplicar regex do layout para extrair `valor`, `data`, `contraparte`
     e opcionalmente `descricao` (ID do pedido/corrida).  # noqa: accent
  4. Calcular `confianca` 0.0..1.0 proporcional aos campos obrigatórios
     casados (valor, data, layout).
  5. Se `confianca < LIMIAR_CONFIDENCE_OK` ou layout None: registra
     fallback supervisor em `data/raw/_conferir/<hash>/` + proposta MD
     em `docs/propostas/extracao_recibo/<hash>.md`. Hash derivado de
     `cache_key(conteudo)` (lição da Sprint 45: nunca `uuid.uuid4()`,
     para idempotência em reprocessamento).
  6. Caso contrário: ingere no grafo via `ingerir_documento_fiscal` com
     CNPJ placeholder `_NAO_FISCAL_<hash12>` (permite documento genérico
     ocupar o slot fiscal; o metadata `tipo_documento=recibo_nao_fiscal`
     distingue downstream). Sem itens granulares: recibo não é tabular.

Contrato com outros módulos:
  - `pode_processar(caminho)` aceita `.pdf`, `.jpg`, `.jpeg`, `.png`,
    `.heic`, `.heif` em pastas com pista `recibo`/`comprovante`/`pix`/
    `voucher`/`_classificar` ou com nome que carregue as mesmas pistas.
    Deliberadamente NÃO aceita pastas que pertencem a outros extratores
    (`dividas_luz`, `energia`, `nfs_fiscais`, `cupom`, `danfe`, `nfce`).
  - `extrair()` devolve `[]` de `base.Transacao`: a despesa já aparece
    no extrato bancário da transação. O efeito colateral é o grafo
    (nó `documento` + `fornecedor` por contraparte quando há).

Fixtures `.txt` em `tests/fixtures/recibos/` reproduzem o texto OCR
pré-decodificado. `extrair_recibo(caminho, texto_override=...)` é o
ponto de injeção para testes determinísticos sem tesseract real.

Não confunde com:
  - `cupom_termico_foto.py` (cupom fiscal térmico, tem CNPJ + COO)
  - `nfce_pdf.py` (NFC-e 65 PDF nativo)
  - `energia_ocr.py` (conta de energia)
"""

from __future__ import annotations

import re
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
from src.utils.logger import configurar_logger

logger = configurar_logger("recibo_nao_fiscal")


EXTENSOES_ACEITAS: tuple[str, ...] = (
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
)

# Limiar acima do qual o recibo é ingerido direto. Abaixo: supervisor.
# Spec da Sprint 47 declara "confidence < 60% manda para supervisor".
LIMIAR_CONFIDENCE_OK: float = 60.0


# ============================================================================
# Caminhos canônicos
# ============================================================================


_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_MAPPING_PADRAO: Path = _RAIZ_REPO / "mappings" / "layouts_recibo.yaml"
_DIR_CACHE_OCR_PADRAO: Path = _RAIZ_REPO / "data" / "cache" / "ocr"
_DIR_CONFERIR_PADRAO: Path = _RAIZ_REPO / "data" / "raw" / "_conferir"
_DIR_PROPOSTAS_PADRAO: Path = (
    _RAIZ_REPO / "docs" / "propostas" / "extracao_recibo"
)


# ============================================================================
# Configuração de layouts
# ============================================================================


def _compilar_regex(padrao: str | None) -> re.Pattern[str] | None:
    """Compila regex com flags padrão (IGNORECASE | UNICODE). None passa adiante."""
    if not padrao:
        return None
    return re.compile(padrao, re.IGNORECASE | re.UNICODE)


def _carregar_layouts(
    caminho_yaml: Path = _PATH_MAPPING_PADRAO,
) -> list[dict[str, Any]]:
    """Carrega a lista de layouts com regex compilados.

    Devolve dicts com:
      id, identificadores (lista de regex compiladas), regex_valor,
      regex_data, regex_contraparte, regex_descricao (ou None), sinal.

    Ordem do YAML é preservada. O detector usa o PRIMEIRO layout cujo
    identificador casa; sem isso, devolve None.
    """
    if not caminho_yaml.exists():
        raise FileNotFoundError(f"mapping de layouts não encontrado: {caminho_yaml}")
    dados = yaml.safe_load(caminho_yaml.read_text(encoding="utf-8")) or {}
    brutos: list[dict[str, Any]] = dados.get("layouts", []) or []

    resultado: list[dict[str, Any]] = []
    for cfg in brutos:
        identificador = cfg.get("id") or ""
        if not identificador:
            logger.warning("layout sem 'id' em %s; ignorado", caminho_yaml.name)
            continue
        regex_valor = _compilar_regex(cfg.get("regex_valor"))
        regex_data = _compilar_regex(cfg.get("regex_data"))
        if regex_valor is None or regex_data is None:
            logger.warning(
                "layout %s sem regex_valor/regex_data; ignorado", identificador
            )
            continue
        identificadores = [
            _compilar_regex(pista) for pista in (cfg.get("identificadores") or [])
        ]
        identificadores = [r for r in identificadores if r is not None]
        resultado.append(
            {
                "id": identificador,
                "identificadores": identificadores,
                "regex_valor": regex_valor,
                "regex_data": regex_data,
                "regex_contraparte": _compilar_regex(cfg.get("regex_contraparte")),
                "regex_descricao": _compilar_regex(cfg.get("regex_descricao")),
                "sinal": cfg.get("sinal") or "despesa",
            }
        )
    return resultado


# ============================================================================
# Detecção de layout
# ============================================================================


def _detectar_layout(
    texto: str, layouts: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Escolhe o primeiro layout cujo identificador bate com o texto.

    Devolve None quando nenhum layout conhecido casa -- o chamador
    decide se manda para o fallback supervisor. Não há layout
    `generico` aqui porque recibo genérico sem pista é quase sempre
    lixo OCR (diferente de cupom fiscal, onde "generico" é útil).
    """
    if not texto:
        return None
    for layout in layouts:
        for padrao in layout["identificadores"]:
            if padrao.search(texto):
                return layout
    return None


# ============================================================================
# Parsing
# ============================================================================


_RE_DATA_NUMERICA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_MESES_PT: dict[str, int] = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}
_RE_DATA_EXTENSO = re.compile(
    r"(\d{1,2})\s+de\s+([a-zçãé]+)\s+de\s+(\d{4})",
    re.IGNORECASE | re.UNICODE,
)


def _parse_valor(valor_cru: str | None) -> float | None:
    """Converte '1.234,56' em 1234.56. None em entrada inválida."""
    if valor_cru is None:
        return None
    limpo = valor_cru.replace(".", "").replace(",", ".").strip()
    try:
        return float(limpo)
    except (ValueError, TypeError):
        return None


def _parse_data_para_iso(data_cru: str | None) -> str | None:
    """Aceita 'DD/MM/YYYY' ou 'DD de mês de YYYY'. Devolve ISO ou None."""
    if not data_cru:
        return None
    bruto = data_cru.strip()

    match = _RE_DATA_NUMERICA.search(bruto)
    if match:
        dia, mes, ano = match.groups()
        try:
            return date(int(ano), int(mes), int(dia)).isoformat()
        except ValueError:
            return None

    match = _RE_DATA_EXTENSO.search(bruto)
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


def _aplicar_layout(layout: dict[str, Any], texto: str) -> dict[str, Any]:
    """Aplica os regex do layout ao texto e devolve o dict estruturado.

    A `confianca` é 1.0 quando valor + data + contraparte são extraídos;
    0.67 quando só valor + data; 0.33 quando só um deles; 0.0 quando
    nada. O caller decide fallback comparando com `LIMIAR_CONFIDENCE_OK`
    em escala 0..100.
    """
    match_valor = layout["regex_valor"].search(texto)
    valor = _parse_valor(match_valor.group(1)) if match_valor else None

    match_data = layout["regex_data"].search(texto)
    data_iso: str | None = None
    if match_data:
        # Primeiro grupo da regex é a data capturada; fallback: match total.
        data_cru = match_data.group(1) if match_data.groups() else match_data.group(0)
        data_iso = _parse_data_para_iso(data_cru)

    contraparte: str | None = None
    if layout["regex_contraparte"] is not None:
        match_cp = layout["regex_contraparte"].search(texto)
        if match_cp:
            contraparte = match_cp.group(1).strip(" .-:,")
            # Limpa quebras internas de OCR ("JOAO\n SILVA" -> "JOAO SILVA")
            contraparte = re.sub(r"\s+", " ", contraparte)

    descricao: str | None = None
    if layout["regex_descricao"] is not None:
        match_d = layout["regex_descricao"].search(texto)
        if match_d:
            descricao = match_d.group(1).strip()

    pontos = 0
    if valor is not None:
        pontos += 1
    if data_iso is not None:
        pontos += 1
    if contraparte:
        pontos += 1
    confianca = pontos / 3.0

    return {
        "valor": valor,
        "data": data_iso,
        "contraparte": contraparte,
        "descricao": descricao,
        "confianca": confianca,
        "sinal": layout["sinal"],
    }


# ============================================================================
# Construção do documento para o grafo
# ============================================================================


def _cnpj_placeholder(chave_hash: str) -> str:
    """Gera placeholder de CNPJ para recibo sem emitente identificado.

    `ingerir_documento_fiscal` exige `cnpj_emitente` não-vazio. Usamos
    prefixo `_NAO_FISCAL_` seguido de 12 chars do hash do conteúdo,
    garantindo:
      - unicidade por recibo;
      - idempotência (mesmo conteúdo -> mesmo placeholder);
      - diferenciação clara de CNPJ real (underscores fora do padrão
        SEFAZ XX.XXX.XXX/XXXX-XX).
    """
    return f"_NAO_FISCAL_{chave_hash[:12]}"


def _chave_documento(
    layout_id: str, chave_hash: str, data_iso: str | None
) -> str:
    """Chave sintética para o nó `documento` do recibo.

    Formato: `RECIBO|<layout>|<data>|<hash12>`. `data_iso` pode ser None
    (recibo sem data extraída não é ingerido, mas defensivamente
    usamos "semdata" para não quebrar a chave).
    """
    sufixo_data = (data_iso or "semdata")[:10]
    return f"RECIBO|{layout_id}|{sufixo_data}|{chave_hash[:12]}"


def _montar_documento_grafo(
    dados: dict[str, Any],
    layout_id: str,
    chave_hash: str,
    caminho: Path,
) -> dict[str, Any]:
    """Monta o dict `documento` esperado por `ingerir_documento_fiscal`.

    Devolve `{}` quando valor+data insuficientes (garante que o
    caller trata como fallback em vez de inserir lixo no grafo).
    """
    valor = dados.get("valor")
    data_iso = dados.get("data")
    if valor is None or data_iso is None:
        return {}

    cnpj = _cnpj_placeholder(chave_hash)
    contraparte = dados.get("contraparte") or layout_id.replace("_", " ").upper()

    documento: dict[str, Any] = {
        "chave_44": _chave_documento(layout_id, chave_hash, data_iso),
        "cnpj_emitente": cnpj,
        "data_emissao": data_iso,
        "tipo_documento": "recibo_nao_fiscal",
        "razao_social": contraparte,
        "total": valor,
        "numero": None,
        "serie": None,
        "forma_pagamento": None,
        "layout": layout_id,
        "sinal": dados.get("sinal") or "despesa",
    }
    if dados.get("descricao"):
        documento["descricao_servico"] = dados["descricao"]
    documento["arquivo_origem"] = str(caminho)
    return documento


# ============================================================================
# Fallback supervisor (idempotente via hash do conteúdo)
# ============================================================================


def _registrar_fallback_supervisor(
    caminho: Path,
    texto_cru: str,
    confidence_ocr: float,
    confianca_parse: float,
    layout_id: str | None,
    dados_parciais: dict[str, Any],
    chave_hash: str,
    diretorio_conferir: Path,
    diretorio_propostas: Path,
) -> Path:
    """Copia o recibo para `_conferir/<hash12>/` e grava proposta MD.

    Hash derivado de `cache_key(caminho)` (SHA-256 dos bytes do arquivo).
    Identificador estável: reprocessar o mesmo arquivo NÃO cria
    propostas novas, sobrescreve a mesma.
    """
    identificador = chave_hash[:12]
    dir_alvo = diretorio_conferir / identificador
    dir_alvo.mkdir(parents=True, exist_ok=True)
    destino = dir_alvo / caminho.name
    if (
        caminho.exists()
        and caminho.resolve() != destino.resolve()
    ):
        try:
            destino.write_bytes(caminho.read_bytes())
        except OSError as erro:
            logger.warning(
                "falha ao copiar recibo para conferência: %s", erro
            )

    diretorio_propostas.mkdir(parents=True, exist_ok=True)
    proposta = diretorio_propostas / f"{identificador}.md"
    proposta.write_text(
        _montar_proposta_supervisor(
            caminho=caminho,
            texto_cru=texto_cru,
            confidence_ocr=confidence_ocr,
            confianca_parse=confianca_parse,
            layout_id=layout_id,
            dados_parciais=dados_parciais,
        ),
        encoding="utf-8",
    )
    logger.info(
        "recibo %s enviado para conferência: %s (confidence_ocr=%.1f, confianca_parse=%.2f)",
        caminho.name,
        identificador,
        confidence_ocr,
        confianca_parse,
    )
    return dir_alvo


def _montar_proposta_supervisor(
    caminho: Path,
    texto_cru: str,
    confidence_ocr: float,
    confianca_parse: float,
    layout_id: str | None,
    dados_parciais: dict[str, Any],
) -> str:
    linhas: list[str] = [
        f"# Conferência manual de recibo não-fiscal -- {caminho.name}",
        "",
        f"- Data da conferência: {datetime.now().isoformat(timespec='seconds')}",
        f"- Confidence OCR: {confidence_ocr:.1f}%",
        f"- Confiança do parse: {confianca_parse * 100:.1f}%",
        f"- Layout detectado: {layout_id or '(nenhum)'}",
        "",
        "## Campos parseados parcialmente",
        "",
        f"- Valor: {dados_parciais.get('valor') or '(não detectado)'}",
        f"- Data: {dados_parciais.get('data') or '(não detectada)'}",
        f"- Contraparte: {dados_parciais.get('contraparte') or '(não detectada)'}",
        f"- Descrição do serviço: {dados_parciais.get('descricao') or '(não detectada)'}",
        "",
        "## Texto bruto",
        "",
        "```",
        texto_cru,
        "```",
        "",
        "## Ação esperada",
        "",
        "1. Abrir o recibo original (copiado para `data/raw/_conferir/`).",
        "2. Identificar qual layout cobriria (Pix Nubank, Pix Itaú, voucher, etc).",
        "3. Propor atualização em `mappings/layouts_recibo.yaml` ou",
        "   criar layout novo se a fonte ainda não é coberta.",
        "",
    ]
    return "\n".join(linhas)


# ============================================================================
# Extrator principal
# ============================================================================


class ExtratorReciboNaoFiscal(ExtratorBase):
    """Extrai recibo não-fiscal (Pix impresso, voucher, recibo manuscrito).

    Prioridade: baixa. Catch-all depois de extratores fiscais
    (cupom térmico, NFC-e, DANFE). Registrado por último em
    `_descobrir_extratores` para não capturar arquivo que pertence a
    outro extrator.

    `pode_processar(caminho)` só aceita quando o caminho carrega pista
    textual de recibo (`recibo`, `comprovante`, `pix`, `voucher`,
    `_classificar`) E o arquivo está em extensão suportada. Recusa
    pastas de outros extratores para não colidir (`nfs_fiscais`, `cupom`,
    `danfe`, `nfce`, `dividas_luz`, `energia`).

    `extrair()` devolve `[]` de `Transacao`. Efeito colateral: grafo  # noqa: accent
    (quando confiança >= limiar) ou proposta supervisor (caso
    contrário).

    `extrair_recibo(caminho, texto_override=None)` é ponto de injeção
    de teste; passa `texto_override` e pula OCR/pdfplumber real.
    """

    BANCO_ORIGEM: str = "Recibo Não-Fiscal"

    def __init__(
        self,
        caminho: Path,
        grafo: GrafoDB | None = None,
        layouts: list[dict[str, Any]] | None = None,
        diretorio_cache: Path | None = None,
        diretorio_conferir: Path | None = None,
        diretorio_propostas: Path | None = None,
    ) -> None:
        super().__init__(caminho)
        self._grafo = grafo
        self._layouts = layouts or _carregar_layouts()
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

        # Evita colisão com extratores mais específicos.
        exclusoes = (
            "dividas_luz",
            "energia",
            "nfs_fiscais",
            "nfce",
            "danfe",
            "cupom",
            "holerite",
            "contracheque",
        )
        if any(ex in caminho_lower for ex in exclusoes):
            return False

        # Pista em pasta ou nome.
        pistas = ("recibo", "comprovante", "pix", "voucher", "_classificar")
        return any(p in caminho_lower for p in pistas)

    def extrair(self) -> list[Transacao]:
        """OCR/pdfplumber + parse + ingestão OU fallback. Devolve lista vazia."""
        try:
            resultado = self.extrair_recibo(self.caminho)
        except Exception as erro:
            self.logger.error(
                "falha ao extrair recibo %s: %s", self.caminho.name, erro
            )
            return []

        layout_id = resultado["layout"]
        confianca = resultado["confianca"] * 100.0  # escala 0..100
        confidence_ocr = resultado["confidence_ocr"]
        documento = resultado["documento"]

        precisa_conferencia = (
            not documento
            or layout_id is None
            or confianca < LIMIAR_CONFIDENCE_OK
            or confidence_ocr < LIMIAR_CONFIDENCE_OK
        )
        if precisa_conferencia:
            _registrar_fallback_supervisor(
                caminho=self.caminho,
                texto_cru=resultado["texto"],
                confidence_ocr=confidence_ocr,
                confianca_parse=resultado["confianca"],
                layout_id=layout_id,
                dados_parciais=resultado["dados"],
                chave_hash=resultado["chave_hash"],
                diretorio_conferir=self._dir_conferir,
                diretorio_propostas=self._dir_propostas,
            )
            return []

        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            ingerir_documento_fiscal(
                grafo, documento, itens=[], caminho_arquivo=self.caminho
            )
        except ValueError as erro:
            self.logger.warning(
                "recibo inválido em %s: %s", self.caminho.name, erro
            )
        finally:
            if criou_grafo_localmente:
                grafo.fechar()

        self.logger.info(
            "recibo ingerido: %s (layout=%s, valor=%.2f, confianca=%.2f)",
            self.caminho.name,
            layout_id,
            documento.get("total") or 0.0,
            resultado["confianca"],
        )
        return []

    # --------------------------------------------------------------------
    # API pública usável por testes
    # --------------------------------------------------------------------

    def extrair_recibo(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> dict[str, Any]:
        """Extrai recibo. `texto_override` pula OCR/pdfplumber real.

        Devolve dict com: `documento` (dict para grafo ou {}), `dados`
        (campos parciais brutos: valor, data, contraparte, descricao),
        `layout` (id ou None), `texto` (texto cru), `confidence_ocr`
        (escala 0..100, só significativa em OCR real), `confianca`
        (0..1 do parse), `chave_hash` (identificador estável).
        """
        if texto_override is not None:
            texto = texto_override
            confidence_ocr = 100.0
            # Hash derivado do texto (estável entre chamadas de teste).
            import hashlib

            chave_hash = hashlib.sha256(
                texto.encode("utf-8")
            ).hexdigest()[:16]
        else:
            texto, confidence_ocr = self._obter_texto(caminho)
            chave_hash = cache_key(caminho) if caminho.exists() else "semarquivo"

        texto_normalizado = normalizar_digitos_valor(texto)

        layout = _detectar_layout(texto_normalizado, self._layouts)
        if layout is None:
            return {
                "documento": {},
                "dados": {},
                "layout": None,
                "texto": texto,
                "confidence_ocr": confidence_ocr,
                "confianca": 0.0,
                "chave_hash": chave_hash,
            }

        dados = _aplicar_layout(layout, texto_normalizado)
        documento = _montar_documento_grafo(
            dados, layout["id"], chave_hash, caminho
        )

        return {
            "documento": documento,
            "dados": dados,
            "layout": layout["id"],
            "texto": texto,
            "confidence_ocr": confidence_ocr,
            "confianca": dados["confianca"],
            "chave_hash": chave_hash,
        }

    # --------------------------------------------------------------------
    # Obtenção de texto (PDF nativo ou imagem via OCR)
    # --------------------------------------------------------------------

    def _obter_texto(self, caminho: Path) -> tuple[str, float]:
        """PDF -> pdfplumber; imagem -> OCR com cache.

        Devolve (texto, confidence). Para PDF nativo, confidence=100
        (texto direto, sem OCR); para imagem, vem do tesseract.
        """
        sufixo = caminho.suffix.lower()
        if sufixo == ".pdf":
            try:
                import pdfplumber
            except ImportError as erro:
                raise RuntimeError(
                    "pdfplumber não disponível para ler recibo em PDF."
                ) from erro
            with pdfplumber.open(caminho) as pdf:
                partes = [
                    (pagina.extract_text() or "") for pagina in pdf.pages
                ]
            return "\n".join(partes), 100.0

        return self._rodar_ocr_com_cache(caminho)

    def _rodar_ocr_com_cache(self, caminho: Path) -> tuple[str, float]:
        """OCR via tesseract com cache e retry 180° (padrão Sprint 45)."""

        def _gerar() -> tuple[str, float]:
            img = carregar_imagem_normalizada(caminho)
            texto, confidence = ocr_com_confidence(img, lang="por")
            if confidence < LIMIAR_CONFIDENCE_OK or len(texto.strip()) < 40:
                img_invertida = rotacionar_180(img)
                texto_inv, confidence_inv = ocr_com_confidence(
                    img_invertida, lang="por"
                )
                if confidence_inv > confidence:
                    return texto_inv, confidence_inv
            return texto, confidence

        return ler_ou_gerar_cache(caminho, _gerar, self._dir_cache)

    def chave_cache(self, caminho: Path) -> str:
        """Exposta para testes -- hash do conteúdo."""
        return cache_key(caminho)


# "A memória do recibo é maior que a do banco." -- princípio do registrador
