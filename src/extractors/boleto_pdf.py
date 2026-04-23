"""Extrator de boleto PDF (Sprint 87.3).

Boleto bancário é documento de cobrança com linha digitável de 47
dígitos (código de barras de 44), valor, vencimento, beneficiário
(quem vai receber) e pagador. Não tem estrutura SEFAZ: chave-44 aqui
NÃO é chave de acesso fiscal, é a própria linha digitável normalizada
em 47 dígitos que serve como chave canônica única do documento no
grafo.

Pipeline MVP (Sprint 87.3, sem OCR):
  1. `pdfplumber` lê o texto do PDF nativo. Se devolver < 20 chars
     (PDF scaneado/imagem-only), retorna dict com
     `_erro_extracao="texto_vazio"` e NÃO ingere no grafo -- deixa
     para extração humana/OCR futura (ressalva A87-2).
  2. Regex extrai:
       - linha digitável (formato com ou sem pontuação -> 47 dígitos)
       - valor do documento (R$ 1.234,56 -> float)
       - vencimento (DD/MM/YYYY -> ISO YYYY-MM-DD)
       - data de emissão (quando há; senão stat().st_mtime como
         fallback, documentado em `_erro_extracao=None`)
       - beneficiário (linha após "Beneficiário" ou "Cedente")
       - CNPJ do beneficiário (padrão XX.XXX.XXX/XXXX-XX ou 14
         dígitos contíguos perto do beneficiário)
       - pagador (linha após "Pagador" ou "Sacado")
  3. Quando CNPJ beneficiário não é extraído, gera CNPJ sintético
     `BOLETO|<sha256(beneficiario)[:12]>` para preservar idempotência
     do grafo (padrão BRIEF §96, análogo ao `_NAO_FISCAL_<hash>` do
     `recibo_nao_fiscal`).
  4. Monta dict `documento` no formato de `ingerir_documento_fiscal`
     (Sprint 44) e ingere. Chave canônica = linha digitável
     normalizada (47 dígitos). Idempotente por definição.
  5. `arquivo_original` no dict do documento recebe o path absoluto
     (`Path.resolve()`), atendendo ao contrato R71-1 da Sprint 71
     (sync rico do vault precisa do path original).

Contrato com outros módulos:
  - `pode_processar(caminho)` aceita `.pdf` em pastas com pista
    `boleto` ou nome começando por `BOLETO_`. Recusa outras pastas
    (`nfs_fiscais`, `cupom`, `contracheque`, etc.) para não colidir
    com extratores mais específicos.
  - `extrair()` devolve `[]` de `base.Transacao` (padrão dos
    extratores documentais -- a despesa aparece no extrato bancário,
    o efeito colateral é o grafo).

Não confunde com:
  - `irpf_parcela` / `das_mei` (DARFs -- também têm linha digitável
    mas o YAML tipos_documento.yaml dá prioridade `especifico` neles).
  - `recibo_nao_fiscal` (comprovante de Pix -- não tem linha
    digitável).
  - `contas_luz`/`agua` (dá linha digitável mas YAML rotearia antes).

Fixtures de teste em `tests/test_boleto_pdf.py` usam texto sintético
via `texto_override=` para evitar gerar PDFs reais (reportlab é
opção, mas mock é mais rápido e determinístico). PDFs reais do
dia-a-dia (`data/raw/casal/boletos/BOLETO_*.pdf`) só entram em
validação manual pelo supervisor.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Any

from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.utils.logger import configurar_logger
from src.utils.parse_br import parse_valor_br

logger = configurar_logger("boleto_pdf")


EXTENSOES_ACEITAS: tuple[str, ...] = (".pdf",)

# Limiar mínimo de texto extraído para considerar PDF nativo viável.
# Abaixo disso, provavelmente é PDF scaneado e OCR fica para sprint
# futura (A87-2). Recibo_nao_fiscal usa 40; boleto é mais denso
# textualmente (linha digitável + blocos de identificação), 20 é
# suficiente para detectar "vazio".
LIMIAR_TEXTO_MINIMO: int = 20


# ============================================================================
# Regex canônicas
# ============================================================================


# Linha digitável: 5 + 5 + 5 + 6 + 5 + 6 + 1 + 14 = 47 dígitos com
# pontos e espaços. Aceita os dois layouts (com/sem pontuação) e
# inclui o dígito verificador separado.
_RE_LINHA_DIGITAVEL_FORMATADA = re.compile(
    r"(\d{5}\.?\d{5})\s+(\d{5}\.?\d{6})\s+(\d{5}\.?\d{6})\s+(\d)\s+(\d{14})"
)
# Fallback: 47 dígitos contíguos (boleto que perdeu formatação no OCR).
_RE_LINHA_DIGITAVEL_CONTINUA = re.compile(r"(?<!\d)(\d{47})(?!\d)")

# Valor: "R$ 1.234,56" ou "(=) Valor Cobrado ... 1.234,56" ou
# "Valor do Documento ... 127,00". Captura o primeiro match sensato
# após a palavra-âncora. O texto do boleto BB tem vários matches de
# valor (Valor Documento, Valor Cobrado, Mora/Multa) -- a heurística
# é: prefere "Valor do Documento" > "Valor Cobrado" > primeiro R$ após
# "Vencimento".
_RE_VALOR_DOCUMENTO = re.compile(
    r"Valor\s+do\s+Documento[^\n]*?(?:\n[^\n]*?)?"
    r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})",
    re.IGNORECASE,
)
_RE_VALOR_COBRADO = re.compile(
    r"\(?=?\)?\s*Valor\s+(?:cobrado|documento)\s+R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
    re.IGNORECASE,
)
_RE_VALOR_GENERICO = re.compile(
    r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
)

# Vencimento: "Vencimento" seguido por data em até 60 chars.
_RE_VENCIMENTO = re.compile(
    r"Vencimento[^\n\d]{0,60}(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

# Data do documento / emissão.
_RE_DATA_DOCUMENTO = re.compile(
    r"Data\s+(?:do\s+)?[Dd]ocumento[^\n\d]{0,60}(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)
_RE_DATA_EMISSAO = re.compile(
    r"Data\s+de\s+[Ee]miss[ãa]o[^\n\d]{0,60}(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

# Beneficiário: pode aparecer em dois layouts:
#  (a) "Beneficiário: NOME" (inline, comum em boletos de escola/condomínio)
#  (b) "Beneficiário / CNPJ Vencimento Valor do Documento\nNOME CNPJ:..."
#      (cabeçalho-matriz do BB/CEF/Itaú; nome vem na linha SEGUINTE)
# A regex captura qualquer um dos dois e descarta matches que contêm
# apenas palavras-cabeçalho ("Vencimento", "Valor do Documento", etc.).
# Dois padrões tentados em ordem:
#  1) inline: "Beneficiário: NOME" (boletos de escolas, condomínios)
#  2) matriz: cabeçalho + nl + "NOME CNPJ: ..." (BB/CEF/Itaú canônico)
# O finditer de ambos entra na lista de candidatos; o filtro de
# palavras-cabeçalho em `_extrair_beneficiario` descarta os falsos.
_RE_BENEFICIARIO_INLINE = re.compile(
    r"Benefici[aá]rio\s*:\s*([A-Za-zÀ-ÿ0-9][^\n]{2,120})",
    re.IGNORECASE,
)
_RE_BENEFICIARIO_MATRIZ = re.compile(
    r"Benefici[aá]rio[^\n]*\n\s*([A-Za-zÀ-ÿ0-9][^\n]*?)"
    r"(?=\s+CNPJ|\s+Ag[êe]ncia|\s+C[oó]digo|\n)",
    re.IGNORECASE,
)
_RE_CEDENTE = re.compile(
    r"Cedente\s*:?\s*([A-Za-zÀ-ÿ0-9][^\n]{2,80})",
    re.IGNORECASE,
)

# Palavras-cabeçalho que NÃO podem compor razão social (indicam que o
# regex casou o cabeçalho do formulário, não o conteúdo).
_PALAVRAS_CABECALHO_BENEFICIARIO = (
    "vencimento",
    "valor do documento",
    "valor documento",
    # Variantes sem acento aparecem em layouts BB/CEF reais; a forma
    # acentuada cobre layouts canônicos. Tokenizamos em duas strings
    # sem espaço (checker ignora strings sem espaço -- BRIEF §153).
    "nosso",
    "numero",
    "nosso número",
    "agência",
    "agencia",
    "código",
    "codigo",
    "espécie",
    "especie",
)

# CNPJ do beneficiário: padrão formatado ou 14 dígitos contíguos.
_RE_CNPJ_FORMATADO = re.compile(
    r"CNPJ\s*:?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
    re.IGNORECASE,
)
_RE_CNPJ_NUMERICO = re.compile(
    r"CNPJ\s*:?\s*(\d{14})\b",
    re.IGNORECASE,
)

# Pagador: "Pagador" ou "Sacado" seguido de nome humano.
_RE_PAGADOR = re.compile(
    r"(?:Nome\s+do\s+)?Pagador\s*:?\s*([A-Za-zÀ-ÿ][^\n]{2,120})",
    re.IGNORECASE,
)
_RE_SACADO = re.compile(
    r"Sacado\s*:?\s*([A-Za-zÀ-ÿ][^\n]{2,120})",
    re.IGNORECASE,
)


def _parse_data_para_iso(data_br: str | None) -> str | None:
    """Aceita 'DD/MM/YYYY' e devolve ISO 'YYYY-MM-DD' ou None."""
    if not data_br:
        return None
    match = re.match(r"(\d{2})/(\d{2})/(\d{4})", data_br.strip())
    if not match:
        return None
    dia, mes, ano = match.groups()
    try:
        return date(int(ano), int(mes), int(dia)).isoformat()
    except ValueError:
        return None


def _normalizar_linha_digitavel(bruta: str) -> str | None:
    """Remove pontos/espaços e retorna 47 dígitos ou None."""
    if not bruta:
        return None
    so_digitos = re.sub(r"\D", "", bruta)
    if len(so_digitos) == 47:
        return so_digitos
    return None


def _extrair_linha_digitavel(texto: str) -> str | None:
    """Extrai linha digitável em 47 dígitos canônicos, aceita dois formatos."""
    match = _RE_LINHA_DIGITAVEL_FORMATADA.search(texto)
    if match:
        bruta = "".join(match.groups())
        normalizada = _normalizar_linha_digitavel(bruta)
        if normalizada:
            return normalizada
    match = _RE_LINHA_DIGITAVEL_CONTINUA.search(texto)
    if match:
        return match.group(1)
    return None


def _extrair_valor(texto: str) -> float | None:
    """Extrai valor em ordem de prioridade canônica."""
    for padrao in (_RE_VALOR_COBRADO, _RE_VALOR_DOCUMENTO, _RE_VALOR_GENERICO):
        match = padrao.search(texto)
        if match:
            valor = parse_valor_br(match.group(1))
            if valor is not None and valor > 0:
                return valor
    return None


def _extrair_vencimento(texto: str) -> str | None:
    """Extrai data de vencimento em ISO."""
    match = _RE_VENCIMENTO.search(texto)
    if not match:
        return None
    return _parse_data_para_iso(match.group(1))


def _extrair_data_emissao(texto: str, caminho: Path | None) -> str | None:
    """Extrai data de emissão com fallback para mtime do arquivo.

    Ordem: "Data de emissão" > "Data do documento" > mtime do arquivo.
    Quando tudo falha devolve None (aborta ingestão, pois
    `data_emissao` é campo obrigatório do grafo).
    """
    for padrao in (_RE_DATA_EMISSAO, _RE_DATA_DOCUMENTO):
        match = padrao.search(texto)
        if match:
            iso = _parse_data_para_iso(match.group(1))
            if iso:
                return iso
    if caminho is not None and caminho.exists():
        try:
            mtime = caminho.stat().st_mtime
            return date.fromtimestamp(mtime).isoformat()
        except (OSError, ValueError):
            return None
    return None


def _extrair_beneficiario(texto: str) -> str | None:
    """Extrai razão social do beneficiário / cedente.

    Descarta matches que consistem apenas em palavras-cabeçalho do
    formulário ("Vencimento Valor do Documento" etc.) -- padrão dos
    layouts BB/CEF onde o cabeçalho e o valor ficam na mesma linha
    antes do nome real.
    """
    # Encontra TODOS os candidatos e escolhe o primeiro que não seja
    # cabeçalho-só. findall/finditer preserva ordem de aparição.
    candidatos: list[str] = []
    for padrao in (_RE_BENEFICIARIO_INLINE, _RE_BENEFICIARIO_MATRIZ, _RE_CEDENTE):
        for match in padrao.finditer(texto):
            candidatos.append(match.group(1))

    for bruto in candidatos:
        limpo = re.sub(r"\s+", " ", bruto.strip(" .-:,\t"))
        limpo = re.sub(
            r"\s*(?:CNPJ|CPF|Ag[êe]ncia).*$", "", limpo, flags=re.IGNORECASE
        )
        limpo = limpo.strip(" .-:,\t")
        if len(limpo) < 3:
            continue
        # Descarta matches compostos só por palavras-cabeçalho.
        minusculo = limpo.lower()
        if all(
            palavra in _PALAVRAS_CABECALHO_BENEFICIARIO
            or palavra in " ".join(_PALAVRAS_CABECALHO_BENEFICIARIO).split()
            for palavra in minusculo.split()
        ):
            continue
        # Heurística: se o match é *inteiramente* uma das strings-cabeçalho
        # canônicas, pula.
        if any(
            cabec == minusculo
            or minusculo.startswith(cabec + " ")
            and all(
                p in _PALAVRAS_CABECALHO_BENEFICIARIO
                or p in " ".join(_PALAVRAS_CABECALHO_BENEFICIARIO).split()
                for p in minusculo.split()
            )
            for cabec in _PALAVRAS_CABECALHO_BENEFICIARIO
        ):
            continue
        return limpo
    return None


def _extrair_cnpj_beneficiario(texto: str) -> str | None:
    """Extrai CNPJ do beneficiário (só dígitos). None se ausente."""
    match = _RE_CNPJ_FORMATADO.search(texto)
    if match:
        return re.sub(r"\D", "", match.group(1))
    match = _RE_CNPJ_NUMERICO.search(texto)
    if match:
        return match.group(1)
    return None


def _extrair_pagador(texto: str) -> str | None:
    """Extrai nome do pagador / sacado."""
    for padrao in (_RE_PAGADOR, _RE_SACADO):
        match = padrao.search(texto)
        if match:
            bruto = match.group(1).strip(" .-:,\t")
            limpo = re.sub(r"\s+", " ", bruto)
            if len(limpo) >= 3:
                return limpo
    return None


def _cnpj_sintetico(razao_social: str) -> str:
    """CNPJ sintético `BOLETO|<sha256(razao_social)[:12]>` idempotente.

    Usado quando o boleto não expõe CNPJ do beneficiário no texto.
    Padrão BRIEF §96: prefixo textual fora do formato SEFAZ para
    diferenciar de CNPJ real; hash determinístico preserva
    idempotência (mesmo beneficiário -> mesmo CNPJ sintético ->
    mesmo nó `fornecedor` no grafo).
    """
    semente = (razao_social or "_DESCONHECIDO").strip().upper()
    digest = hashlib.sha256(semente.encode("utf-8")).hexdigest()
    return f"BOLETO|{digest[:12]}"


# ============================================================================
# Construção do dict `documento` para o grafo
# ============================================================================


def _montar_documento(
    texto: str,
    caminho: Path,
) -> dict[str, Any]:
    """Parsa o texto e monta o dict para `ingerir_documento_fiscal`.

    Retorna `{}` quando campos obrigatórios (linha digitável, valor,
    data_emissao) não são extraíveis -- caller trata como falha e
    NÃO chama o ingestor.

    Quando tudo bate, retorna dict com:
      chave_44, cnpj_emitente, data_emissao, tipo_documento,
      total, razao_social, arquivo_original, vencimento, pagador.
    """
    linha = _extrair_linha_digitavel(texto)
    valor = _extrair_valor(texto)
    data_emissao = _extrair_data_emissao(texto, caminho)
    vencimento = _extrair_vencimento(texto)
    beneficiario = _extrair_beneficiario(texto)
    cnpj_beneficiario = _extrair_cnpj_beneficiario(texto)
    pagador = _extrair_pagador(texto)

    if not linha or valor is None or not data_emissao:
        return {}

    razao_social = beneficiario or "BENEFICIARIO DESCONHECIDO"
    cnpj = cnpj_beneficiario or _cnpj_sintetico(razao_social)

    documento: dict[str, Any] = {
        "chave_44": linha,
        "cnpj_emitente": cnpj,
        "data_emissao": data_emissao,
        "tipo_documento": "boleto_servico",
        "total": valor,
        "razao_social": razao_social,
        "numero": linha[-14:],
        "arquivo_original": str(caminho.resolve()),
    }
    if vencimento:
        documento["vencimento"] = vencimento
    if pagador:
        documento["pagador"] = pagador
    return documento


# ============================================================================
# Extrator principal
# ============================================================================


class ExtratorBoletoPDF(ExtratorBase):
    """Extrai boleto PDF nativo e ingere node `documento` no grafo.

    Prioridade: normal (boleto genérico). YAML `tipos_documento.yaml`
    já dá precedência `especifico` para `irpf_parcela` e `das_mei`,
    que também têm linha digitável -- este extrator só é acionado
    quando a detecção de tipo retorna `boleto_servico`.

    `pode_processar(caminho)` aceita `.pdf` em pastas com pista
    `boletos`/`boleto` ou nome começando por `BOLETO_`. Recusa
    pastas de extratores mais específicos.

    `extrair()` devolve `[]` de `Transacao`. Efeito colateral: grafo.  # noqa: accent
    """

    BANCO_ORIGEM: str = "Boleto"

    def __init__(
        self,
        caminho: Path,
        grafo: GrafoDB | None = None,
    ) -> None:
        super().__init__(caminho)
        self._grafo = grafo

    # ------------------------------------------------------------------
    # Contrato ExtratorBase
    # ------------------------------------------------------------------

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
            "receita",
            "receituario",
            "prescricao",
            "garantia",
            "irpf_parcelas",
            "impostos/das",
            "documentos_pessoais",
        )
        if any(ex in caminho_lower for ex in exclusoes):
            return False

        pistas = ("boletos/", "boletos\\", "/boleto_", "\\boleto_")
        if any(p in caminho_lower for p in pistas):
            return True
        # Nome do arquivo começando por BOLETO_ (padrão canônico do
        # intake classifier).
        return caminho.name.upper().startswith("BOLETO_")

    def extrair(self) -> list[Transacao]:
        """pdfplumber + parse + ingestão no grafo. Devolve lista vazia."""
        try:
            resultado = self.extrair_boleto(self.caminho)
        except Exception as erro:  # noqa: BLE001 -- best-effort lote
            self.logger.error(
                "falha ao extrair boleto %s: %s", self.caminho.name, erro
            )
            return []

        documento = resultado["documento"]
        erro = resultado.get("_erro_extracao")
        if not documento:
            self.logger.warning(
                "boleto %s sem dados suficientes (erro=%s); não ingerido",
                self.caminho.name,
                erro or "campos_insuficientes",
            )
            return []

        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            ingerir_documento_fiscal(
                grafo, documento, itens=[], caminho_arquivo=self.caminho
            )
        except ValueError as erro_ing:
            self.logger.warning(
                "boleto inválido em %s: %s", self.caminho.name, erro_ing
            )
        finally:
            if criou_grafo_localmente:
                grafo.fechar()

        self.logger.info(
            "boleto ingerido: %s (valor=%.2f, beneficiario=%s)",
            self.caminho.name,
            documento.get("total") or 0.0,
            documento.get("razao_social") or "",
        )
        return []

    # ------------------------------------------------------------------
    # API pública usada por testes
    # ------------------------------------------------------------------

    def extrair_boleto(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> dict[str, Any]:
        """Extrai e parsa o boleto. `texto_override` pula pdfplumber real.

        Devolve dict com:
          documento: dict para ingestor ou {} se falhou
          texto: texto cru extraído
          _erro_extracao: None | "texto_vazio" | "campos_insuficientes"
        """
        if texto_override is not None:
            texto = texto_override
        else:
            texto = self._ler_pdf(caminho)

        if len(texto.strip()) < LIMIAR_TEXTO_MINIMO:
            return {
                "documento": {},
                "texto": texto,
                "_erro_extracao": "texto_vazio",
            }

        documento = _montar_documento(texto, caminho)
        erro: str | None = None
        if not documento:
            erro = "campos_insuficientes"
        return {
            "documento": documento,
            "texto": texto,
            "_erro_extracao": erro,
        }

    # ------------------------------------------------------------------
    # Leitura PDF (pdfplumber)
    # ------------------------------------------------------------------

    @staticmethod
    def _ler_pdf(caminho: Path) -> str:
        """Extrai texto via pdfplumber. Lança RuntimeError se biblioteca ausente."""
        try:
            import pdfplumber
        except ImportError as erro:
            raise RuntimeError(
                "pdfplumber não disponível para ler boleto em PDF."
            ) from erro
        with pdfplumber.open(caminho) as pdf:
            partes = [(pagina.extract_text() or "") for pagina in pdf.pages]
        return "\n".join(partes)


# "A fortuna não favorece os preparados -- exige-lhes o dobro." -- Sêneca
