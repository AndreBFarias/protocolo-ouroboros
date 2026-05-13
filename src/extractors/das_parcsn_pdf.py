"""Extrator de DAS PARCSN (Documento de Arrecadação do Simples Nacional -- Parcelamento).

DAS PARCSN é documento de pagamento de parcela do Simples Nacional em
regime de parcelamento. Emitido pela Receita Federal via SENDA/PORTAL SN
para contribuintes MEI/ME que aderiram a parcelamento de débitos.

Auditoria 2026-04-23 detectou 47 DAS fisicamente presentes
(19 em data/raw/casal/impostos/das_parcsn/ + 28 em data/raw/_envelopes/
originais/) sem catalogação no grafo -- ADR-20 declara tracking documental
como KPI de primeira linha, então DAS precisa virar node `documento`.

Pipeline:
  1. pdfplumber lê texto nativo (PDFs do SENDA sempre têm texto).
  2. Regex extrai: CNPJ, razão social, período de apuração, data de
     vencimento, valor total, número do documento, parcela N/M.
  3. Monta dict no formato de `ingerir_documento_fiscal` e ingere.
  4. Chave canônica: número do documento SENDA (formato
     NN.NN.NNNNN.NNNNNNN-N). Idempotente por re-ingestão.

Contrato:
  - pode_processar: .pdf em pastas com pista 'das_parcsn', 'impostos/das',
    '_envelopes/originais', ou nome começando por 'DAS_PARCSN_'.
  - extrair() devolve [] de Transacao. Efeito colateral: grafo.
  - Quando CNPJ é da pessoa_a (45.850.636), tipo_documento="das_parcsn_andre".
    Senão, "das_parcsn".
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.utils.logger import configurar_logger

logger = configurar_logger("das_parcsn_pdf")

EXTENSOES_ACEITAS: tuple[str, ...] = (".pdf",)
LIMIAR_TEXTO_MINIMO: int = 100

_MESES_PT: dict[str, int] = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
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

# Regex canônicas
_RE_CNPJ = re.compile(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})")
_RE_RAZAO_SOCIAL = re.compile(
    r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ ]+[A-ZÁÉÍÓÚÂÊÔÃÕÇ])",
)
# Período aceita acentuação portuguesa (Março, São, etc.). DAS PARCSN também
# emite período "Diversos" quando a parcela cobre múltiplos meses; nesse caso
# a regex de mês não casa e o campo periodo_apuracao fica ausente -- isso é
# intencional (Sprint 90b), o documento ainda é válido para o grafo.
_RE_PERIODO = re.compile(
    r"([A-Za-zÀ-ÿ]+)/(\d{4})\s+\d{2}/\d{2}/\d{4}",
)
_RE_PERIODO_DIVERSOS = re.compile(r"\bDiversos\b", re.IGNORECASE)
_RE_VENCIMENTO = re.compile(
    r"[A-Za-zÀ-ÿ]+/\d{4}\s+(\d{2}/\d{2}/\d{4})",
)
# Variante "Diversos": linha do header tem só "Diversos NUMERO_DOC" e a data
# de vencimento original cai na linha seguinte isolada.
_RE_VENCIMENTO_DIVERSOS = re.compile(
    r"Diversos\s+\d{2}\.\d{2}\.\d{5}\.\d{7}-\d\s*\n\s*(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)
# Estrutura do DAS PARCSN: header de 4 colunas (Período, Data Venc., Num Doc,
# Pagar até) seguido de valores em 2 linhas -- os 3 primeiros ficam na linha de
# valores (Período + Vencimento original + Número), a data "Pagar até" cai na
# linha seguinte isolada. Em variante "Diversos" só o número e a data caem
# em linhas separadas, sem data de vencimento original na linha do header.
# Fonte primária do vencimento: rodapé do voucher PIX que repete "Pagar até:
# DD/MM/YYYY" de forma estável em ambos os layouts. _RE_PAGAR_ATE_HEADER é
# fallback para arquivos que eventualmente percam o rodapé.
_RE_PAGAR_ATE = re.compile(
    r"Pagar\s+at[ée]:\s*(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)
_RE_PAGAR_ATE_HEADER = re.compile(
    r"Pagar\s+este\s+documento\s+at[ée]\b.*?\d{2}/\d{2}/\d{4}.*?(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE | re.DOTALL,
)
_RE_NUMERO_DOC = re.compile(
    r"(\d{2}\.\d{2}\.\d{5}\.\d{7}-\d)",
)
_RE_VALOR_TOTAL = re.compile(
    r"Valor\s+Total\s+do\s+Documento\s*(?:\n[^\n]*)?\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
    re.IGNORECASE,
)
_RE_PARCELA = re.compile(r"Parcela:\s*(\d+)/(\d+)")

# Sprint INFRA-DAS-EXTRAIR-COMPOSICAO 2026-05-12:
# Tabela "Composição do Documento de Arrecadação" tem cabeçalho
# "Código Denominação Principal Multa Juros Total" seguido de linhas:
#   "1004 COFINS - SIMPLES NACIONAL 31,56 6,31 3,70 41,57"
#   "02/2024"   <-- período do tributo na linha seguinte (pode ter prefixo cidade)
# E rodapé:
#   "Totais 246,20 49,23 28,88 324,31"
#
# A denominação canônica é "<NOME> - SIMPLES NACIONAL" e o período pode vir
# isolado ("02/2024") ou após nome de cidade ("BRASILIA (DF) - 02/2024").
_RE_LINHA_TRIBUTO = re.compile(
    r"^(\d{4})\s+([A-Z][A-Z ]*?)\s+-\s+SIMPLES\s+NACIONAL\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*$",
    re.MULTILINE,
)
_RE_PERIODO_TRIBUTO = re.compile(r"(\d{2}/\d{4})")
_RE_TOTAIS_COMPOSICAO = re.compile(
    r"^Totais\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
    r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*$",
    re.MULTILINE,
)
# Linha digitável: 47 dígitos no padrão "11d esp 1d esp 11d esp 1d esp 11d
# esp 1d esp 11d esp 1d" (com tolerância a espaços simples ou duplos entre
# blocos -- alguns PDFs renderizam com gaps adicionais).
_RE_CODIGO_BARRAS = re.compile(
    r"(\d{11}\s+\d\s+\d{11}\s+\d\s+\d{11}\s+\d\s+\d{11}\s+\d)"
)


def _parse_data_iso(data_br: str | None) -> str | None:
    if not data_br:
        return None
    try:
        dia, mes, ano = data_br.split("/")
        return f"{ano}-{int(mes):02d}-{int(dia):02d}"
    except ValueError:
        return None


def _parse_periodo(texto: str) -> str | None:
    """'Fevereiro/2025' -> '2025-02'."""
    m = _RE_PERIODO.search(texto)
    if not m:
        return None
    mes_txt = m.group(1).lower()
    mes_num = _MESES_PT.get(mes_txt)
    if mes_num is None:
        return None
    return f"{m.group(2)}-{mes_num:02d}"


def _parse_valor(texto: str) -> float | None:
    m = _RE_VALOR_TOTAL.search(texto)
    if not m:
        return None
    try:
        return float(m.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _br_para_float(s: str) -> float:
    """'1.234,56' -> 1234.56."""
    return float(s.replace(".", "").replace(",", "."))


def _parse_composicao(texto: str) -> list[dict[str, Any]]:
    """Extrai linhas da tabela "Composição do Documento de Arrecadação".

    Cada match de `_RE_LINHA_TRIBUTO` é seguido por uma linha com o período
    de apuração no formato `MM/YYYY` (eventualmente com prefixo de cidade,
    ex: `BRASILIA (DF) - 02/2024`). Pareamos uma linha de tributo com o
    primeiro `MM/YYYY` que aparece após o final do match, sem ultrapassar
    o início do próximo match.
    """
    entradas: list[dict[str, Any]] = []
    matches = list(_RE_LINHA_TRIBUTO.finditer(texto))
    for idx, m in enumerate(matches):
        fim = m.end()
        proximo_inicio = matches[idx + 1].start() if idx + 1 < len(matches) else len(texto)
        janela = texto[fim:proximo_inicio]
        periodo_match = _RE_PERIODO_TRIBUTO.search(janela)
        periodo = None
        if periodo_match:
            mes, ano = periodo_match.group(1).split("/")
            periodo = f"{ano}-{mes}"
        entradas.append(
            {
                "codigo": m.group(1),
                "denominacao": m.group(2).strip(),
                "principal": _br_para_float(m.group(3)),
                "multa": _br_para_float(m.group(4)),
                "juros": _br_para_float(m.group(5)),
                "total": _br_para_float(m.group(6)),
                "periodo": periodo,
            }
        )
    return entradas


def _parse_totais_composicao(texto: str) -> dict[str, float] | None:
    m = _RE_TOTAIS_COMPOSICAO.search(texto)
    if not m:
        return None
    return {
        "principal": _br_para_float(m.group(1)),
        "multa": _br_para_float(m.group(2)),
        "juros": _br_para_float(m.group(3)),
        "total": _br_para_float(m.group(4)),
    }


def _parse_codigo_barras(texto: str) -> str | None:
    m = _RE_CODIGO_BARRAS.search(texto)
    if not m:
        return None
    return m.group(1)


def _meses_distintos(composicao: list[dict[str, Any]]) -> list[str]:
    vistos: list[str] = []
    for entrada in composicao:
        p = entrada.get("periodo")
        if p and p not in vistos:
            vistos.append(p)
    return vistos


def _montar_documento(texto: str, caminho: Path) -> dict[str, Any]:
    cnpj_match = _RE_CNPJ.search(texto)
    razao_match = _RE_RAZAO_SOCIAL.search(texto)
    numero_match = _RE_NUMERO_DOC.search(texto)
    periodo = _parse_periodo(texto)
    eh_diversos = bool(_RE_PERIODO_DIVERSOS.search(texto))
    valor = _parse_valor(texto)
    pagar_match = _RE_PAGAR_ATE.search(texto) or _RE_PAGAR_ATE_HEADER.search(texto)
    venc_match = _RE_VENCIMENTO.search(texto)
    venc_diversos_match = _RE_VENCIMENTO_DIVERSOS.search(texto)
    parcela_match = _RE_PARCELA.search(texto)

    # Sprint 90b: campos canônicos para identificar o documento são
    # cnpj/numero/valor. periodo_apuracao é opcional -- quando o DAS cobre
    # parcela "Diversos" (múltiplos meses), o campo fica ausente sem
    # invalidar a ingestão.
    if not cnpj_match or not numero_match or valor is None:
        return {}

    cnpj = cnpj_match.group(1)
    numero = numero_match.group(1)
    razao = razao_match.group(1).strip() if razao_match else "CONTRIBUINTE DESCONHECIDO"

    # Vencimento (data-limite de pagamento). Fallback: vencimento original
    # da linha do header (formato "Mês/YYYY DD/MM/YYYY" ou variante "Diversos").
    venc_original_br: str | None = None
    if venc_match:
        venc_original_br = venc_match.group(1)
    elif venc_diversos_match:
        venc_original_br = venc_diversos_match.group(1)

    vencimento = _parse_data_iso(pagar_match.group(1) if pagar_match else None) or _parse_data_iso(
        venc_original_br
    )
    data_emissao = _parse_data_iso(venc_original_br)

    # tipo_documento discriminado por CNPJ canônico da pessoa_a (auditoria 2026-04-23).
    tipo_doc = "das_parcsn_andre" if cnpj.startswith("45.850.636") else "das_parcsn"

    documento: dict[str, Any] = {
        "chave_44": re.sub(r"\D", "", numero),
        "cnpj_emitente": cnpj,
        "data_emissao": data_emissao or vencimento or "",
        "tipo_documento": tipo_doc,
        "total": valor,
        "razao_social": razao,
        "numero": numero,
        "arquivo_original": str(caminho.resolve()),
    }
    if vencimento:
        documento["vencimento"] = vencimento
    if periodo:
        documento["periodo_apuracao"] = periodo
    elif eh_diversos:
        # Sinaliza explicitamente que o período cobre múltiplos meses.
        documento["periodo_apuracao"] = "diversos"
    if parcela_match:
        documento["parcela_atual"] = int(parcela_match.group(1))
        documento["parcela_total"] = int(parcela_match.group(2))

    # Sprint INFRA-DAS-EXTRAIR-COMPOSICAO: campos novos
    # (composição por tributo, totais da decomposição, código de barras).
    composicao = _parse_composicao(texto)
    if composicao:
        documento["composicao_por_tributo"] = composicao
        totais = _parse_totais_composicao(texto)
        if totais:
            documento["principal"] = totais["principal"]
            documento["multa"] = totais["multa"]
            documento["juros"] = totais["juros"]
        else:
            # Fallback: somar a coluna a partir das entradas (mantém o invariante
            # principal+multa+juros=total mesmo sem o rodapé "Totais").
            documento["principal"] = round(sum(e["principal"] for e in composicao), 2)
            documento["multa"] = round(sum(e["multa"] for e in composicao), 2)
            documento["juros"] = round(sum(e["juros"] for e in composicao), 2)

        # Quando periodo_apuracao=="diversos", expõe os meses distintos
        # parseados da composição (ex: ["2024-06", "2024-07"]).
        if documento.get("periodo_apuracao") == "diversos":
            meses = _meses_distintos(composicao)
            if meses:
                documento["meses_diversos"] = meses
                documento["quantidade_meses_diversos"] = len(meses)

    codigo_barras = _parse_codigo_barras(texto)
    if codigo_barras:
        documento["codigo_barras"] = codigo_barras

    return documento


class ExtratorDASPARCSNPDF(ExtratorBase):
    """Extrai DAS PARCSN PDF nativo e ingere node `documento` no grafo."""

    BANCO_ORIGEM: str = "DAS-PARCSN"

    def __init__(self, caminho: Path, grafo: GrafoDB | None = None) -> None:
        super().__init__(caminho)
        self._grafo = grafo

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False
        caminho_lower = str(caminho).lower()
        pistas = (
            "das_parcsn",
            "impostos/das",
            "impostos\\das",
            "/das_parcsn_",
            "\\das_parcsn_",
            "_envelopes/originais",
        )
        return any(p in caminho_lower for p in pistas)

    def extrair(self) -> list[Transacao]:
        try:
            resultado = self.extrair_das(self.caminho)
        except Exception as erro:  # noqa: BLE001
            self.logger.error("falha ao extrair DAS %s: %s", self.caminho.name, erro)
            return []

        documento = resultado["documento"]
        if not documento:
            self.logger.warning(
                "DAS %s sem dados suficientes (erro=%s); não ingerido",
                self.caminho.name,
                resultado.get("_erro_extracao") or "campos_insuficientes",
            )
            return []

        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            ingerir_documento_fiscal(grafo, documento, itens=[], caminho_arquivo=self.caminho)
        except ValueError as erro_ing:
            self.logger.warning("DAS inválido em %s: %s", self.caminho.name, erro_ing)
        finally:
            if criou_grafo_localmente:
                grafo.fechar()

        self.logger.info(
            "DAS ingerido: %s (valor=%.2f, CNPJ=%s, periodo=%s, parcela=%s/%s)",
            self.caminho.name,
            documento.get("total") or 0.0,
            documento.get("cnpj_emitente") or "",
            documento.get("periodo_apuracao") or "",
            documento.get("parcela_atual") or "-",
            documento.get("parcela_total") or "-",
        )
        return []

    def extrair_das(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> dict[str, Any]:
        if texto_override is not None:
            texto = texto_override
        else:
            texto = self._ler_pdf(caminho)

        if len(texto.strip()) < LIMIAR_TEXTO_MINIMO:
            return {"documento": {}, "texto": texto, "_erro_extracao": "texto_vazio"}

        documento = _montar_documento(texto, caminho)
        erro: str | None = None if documento else "campos_insuficientes"
        return {"documento": documento, "texto": texto, "_erro_extracao": erro}

    @staticmethod
    def _ler_pdf(caminho: Path) -> str:
        try:
            import pdfplumber
        except ImportError as erro:
            raise RuntimeError("pdfplumber não instalado -- uv sync") from erro
        with pdfplumber.open(caminho) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)


# "Quem paga em parcelas também merece ser catalogado." -- princípio de equidade documental
