"""Extrator de contracheques (holerites) em PDF.

Suporta duas fontes:
- G4F SOLUCOES CORPORATIVAS (PDF com texto nativo)
- INFOBASE CONSULTORIA E INFORMATICA (PDF nativo ou escaneado, com fallback para OCR)

A saída é uma lista de dicts compatível com a aba `renda` do XLSX final.
Cada PDF gera UMA entrada. Meses com 13º salário produzem entrada adicional
(tipo "13º Adiantamento" ou "13º Integral") em paralelo à folha mensal.
"""

import functools
import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pdfplumber
import pypdfium2 as pdfium
import pytesseract
import yaml

from src.utils.logger import configurar_logger
from src.utils.parse_br import parse_valor_br_float

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_RAZAO_CANONICA: Path = _RAIZ_REPO / "mappings" / "razao_social_canonica.yaml"


@functools.lru_cache(maxsize=1)
def _carregar_razao_canonica() -> dict[str, dict]:
    """Carrega `mappings/razao_social_canonica.yaml` (cache via lru_cache).

    Devolve dict {sigla_upper: {razao_social_canonica, cnpj, aliases}}.
    Falha-soft: se o YAML faltar, retorna dict vazio (extractor cai para
    upper() padrao).
    """
    if not _PATH_RAZAO_CANONICA.exists():
        return {}
    try:
        bruto = yaml.safe_load(_PATH_RAZAO_CANONICA.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    empresas = bruto.get("empresas", {}) or {}
    return {str(k).upper(): v for k, v in empresas.items() if isinstance(v, dict)}


def resolver_razao_social_canonica(sigla: str) -> tuple[str, str]:
    """Mapeia sigla -> (razao_social_canonica, cnpj_oficial_ou_vazio).

    Quando sigla não mapeada, devolve (sigla.upper(), "") -- comportamento
    pre-AUDIT2 preservado.
    """
    if not sigla:
        return "", ""
    chave = sigla.strip().upper()
    mapping = _carregar_razao_canonica()
    entrada = mapping.get(chave)
    if entrada is None:
        return chave, ""
    return (
        str(entrada.get("razao_social_canonica") or chave),
        str(entrada.get("cnpj") or ""),
    )

if TYPE_CHECKING:
    from src.graph.db import GrafoDB

logger = configurar_logger("ExtratorContrachequePDF")

MESES_PT: dict[str, str] = {
    "Janeiro": "01",
    "Fevereiro": "02",
    "Março": "03",
    "Abril": "04",
    "Maio": "05",
    "Junho": "06",
    "Julho": "07",
    "Agosto": "08",
    "Setembro": "09",
    "Outubro": "10",
    "Novembro": "11",
    "Dezembro": "12",
}

REGEX_G4F_REF = re.compile(r"Pagamento de Sal[aáÁ]rio:\s*(\d{2})/(\d{2,4})")
REGEX_G4F_PROVENTO = re.compile(r"\+\s+(.+?)\s+[\d.,]+\s+R\$\s*([\d.,]+)")
REGEX_G4F_DESCONTO = re.compile(r"-\s+(.+?)\s+[\d.,]+\s+\(R\$\s*([\d.,]+)\)")
REGEX_G4F_LIQUIDO = re.compile(r"Valor l[ií]quido a receber:\s*R\$\s*([\d.,]+)")

REGEX_INFOBASE_REF = re.compile(r"Mensalista\s+(\w+)\s+de\s+(\d{4})")
REGEX_INFOBASE_CODIGO = re.compile(r"^\s*(\d{3,4})[|\]\s]")
REGEX_INFOBASE_VALOR = re.compile(r"[\d.]+,\d{2}")

CODIGOS_INFOBASE: dict[str, str] = {
    "8781": "bruto",
    "998": "inss",
    "999": "irrf",
}


def _extrair_texto(caminho: Path) -> str:
    """Extrai texto do PDF com fallback para OCR se pdfplumber retornar vazio."""
    try:
        with pdfplumber.open(caminho) as pdf:
            texto = pdf.pages[0].extract_text() or ""
    except Exception as exc:
        logger.warning("pdfplumber falhou em %s: %s", caminho.name, exc)
        texto = ""

    if len(texto) >= 100:
        return texto

    try:
        doc = pdfium.PdfDocument(str(caminho))
        imagem = doc[0].render(scale=2).to_pil()
        return pytesseract.image_to_string(imagem, lang="por")
    except Exception as exc:
        logger.warning("OCR falhou em %s: %s", caminho.name, exc)
        return ""


def _detectar_fonte(texto: str) -> Optional[str]:
    """Identifica a fonte do holerite a partir do texto extraído."""
    if "G4F" in texto:
        return "G4F"
    if "INFOBASE" in texto.upper():
        return "Infobase"
    return None


def _parse_g4f(texto: str) -> Optional[dict]:
    """Parseia holerite G4F. Retorna dict da aba renda ou None se inválido."""
    m_ref = REGEX_G4F_REF.search(texto)
    if not m_ref:
        return None
    mes, ano_curto = m_ref.groups()
    ano = ano_curto if len(ano_curto) == 4 else f"20{ano_curto}"
    mes_ref = f"{ano}-{mes}"

    bruto = 0.0
    tipo = "Folha Mensal"
    # Sprint AUDIT2-METADATA-ITENS-LISTA: lista granular para metadata.itens.
    itens_holerite: list[dict] = []
    for match in REGEX_G4F_PROVENTO.finditer(texto):
        descricao, valor = match.groups()
        valor_num = parse_valor_br_float(valor)
        bruto += valor_num
        descricao_norm = descricao.strip()
        itens_holerite.append(
            {"descricao": descricao_norm, "valor": valor_num, "tipo": "provento"}
        )
        if "13" in descricao_norm and "Adiantado" in descricao_norm:
            tipo = "13º Adiantamento"
        elif "13" in descricao_norm and "Integral" in descricao_norm:
            tipo = "13º Integral"

    inss = irrf = vr_va = 0.0
    for match in REGEX_G4F_DESCONTO.finditer(texto):
        descricao, valor = match.groups()
        valor_num = parse_valor_br_float(valor)
        descricao_upper = descricao.upper()
        itens_holerite.append(
            {"descricao": descricao.strip(), "valor": valor_num, "tipo": "desconto"}
        )
        if "IRRF" in descricao_upper:
            irrf += valor_num
        elif "INSS" in descricao_upper:
            inss += valor_num
        elif "VALE ALIMENTA" in descricao_upper or "VALE REFEI" in descricao_upper:
            vr_va += valor_num

    m_liq = REGEX_G4F_LIQUIDO.search(texto)
    liquido = parse_valor_br_float(m_liq.group(1)) if m_liq else 0.0
    if liquido == 0.0 and bruto > 0:
        liquido = bruto - inss - irrf - vr_va

    return {
        "mes_ref": mes_ref,
        "fonte": f"G4F - {tipo}" if tipo != "Folha Mensal" else "G4F",
        "bruto": round(bruto, 2),
        "inss": round(inss, 2),
        "irrf": round(irrf, 2),
        "vr_va": round(vr_va, 2),
        "liquido": round(liquido, 2),
        "banco": "",
        "itens": itens_holerite,
    }


def _parse_infobase(texto: str) -> Optional[dict]:
    """Parseia holerite Infobase (nativo ou OCR). Retorna dict da aba renda ou None.

    Suporta folha mensal (DIAS NORMAIS + I.N.S.S. + IMPOSTO DE RENDA) e
    13º integral (SALARIO INTEGRAL + ADIANTAMENTO 13 + INSS 13 + IRRF 13).
    """
    m_ref = REGEX_INFOBASE_REF.search(texto)
    if not m_ref:
        return None
    mes_nome, ano = m_ref.groups()
    mes = MESES_PT.get(mes_nome)
    if not mes:
        logger.warning("Infobase: mês desconhecido '%s'", mes_nome)
        return None
    mes_ref = f"{ano}-{mes}"

    eh_13 = "13 SALARIO" in texto.upper() or "SALARIO INTEGRAL" in texto.upper()
    tipo = "13º Integral" if eh_13 else "Folha Mensal"

    bruto = inss = irrf = vr_va = liquido = adiantamento = 0.0
    for linha in texto.splitlines():
        numeros = REGEX_INFOBASE_VALOR.findall(linha)
        if not numeros:
            continue
        valor = parse_valor_br_float(numeros[-1])
        linha_upper = linha.upper()

        if eh_13:
            if "SALARIO INTEGRAL" in linha_upper:
                bruto = valor
            elif "ADIANTAMENTO" in linha_upper and "13" in linha_upper:
                adiantamento = valor
            elif "INSS" in linha_upper and ("13" in linha_upper or "130" in linha_upper):
                inss = valor
            elif "IRRF" in linha_upper and ("13" in linha_upper or "130" in linha_upper):
                irrf = valor
            elif "VALOR" in linha_upper and ("LIQUIDO" in linha_upper or "LÍQUIDO" in linha_upper):
                liquido = valor
            continue

        m_cod = REGEX_INFOBASE_CODIGO.match(linha)
        if m_cod and m_cod.group(1) in CODIGOS_INFOBASE:
            chave = CODIGOS_INFOBASE[m_cod.group(1)]
            if chave == "bruto":
                bruto = valor
            elif chave == "inss":
                inss = valor
            elif chave == "irrf":
                irrf = valor
            continue
        if "VALOR" in linha_upper and ("LIQUIDO" in linha_upper or "LÍQUIDO" in linha_upper):
            liquido = valor

    if liquido == 0.0 and bruto > 0:
        liquido = bruto - adiantamento - inss - irrf - vr_va

    # Sprint AUDIT2-METADATA-ITENS-LISTA: itens granulares (estrutura
    # mínima do que conseguimos extrair do INFOBASE; OCR não dá lista
    # completa de proventos individuais, então gravamos os agregados
    # principais como pseudo-itens).
    itens_infobase: list[dict] = []
    if bruto > 0:
        itens_infobase.append(
            {"descricao": "SALARIO BRUTO", "valor": bruto, "tipo": "provento"}
        )
    if adiantamento > 0:
        itens_infobase.append(
            {"descricao": "ADIANTAMENTO 13", "valor": adiantamento, "tipo": "provento"}
        )
    if inss > 0:
        itens_infobase.append(
            {"descricao": "INSS", "valor": inss, "tipo": "desconto"}
        )
    if irrf > 0:
        itens_infobase.append(
            {"descricao": "IRRF", "valor": irrf, "tipo": "desconto"}
        )

    return {
        "mes_ref": mes_ref,
        "fonte": f"Infobase - {tipo}" if tipo != "Folha Mensal" else "Infobase",
        "bruto": round(bruto, 2),
        "inss": round(inss, 2),
        "irrf": round(irrf, 2),
        "vr_va": round(vr_va, 2),
        "liquido": round(liquido, 2),
        "banco": "",
        "itens": itens_infobase,
    }


def _ingerir_holerite_no_grafo(
    grafo: "GrafoDB",
    registro: dict,
    arquivo: Path,
) -> None:
    """Insere node `documento` tipo `holerite` (P3.2 2026-04-23).

    Chave canônica: `HOLERITE|<fonte>|<mes_ref>` (idempotente por fonte+mês,
    sobrescreve mesmo se o arquivo físico mudar). CNPJ sintético derivado
    do nome da fonte (G4F/Infobase) via hash -- mesma estratégia do boleto.
    """
    from src.graph.ingestor_documento import ingerir_documento_fiscal

    fonte = registro.get("fonte") or "HOLERITE"
    mes_ref = registro["mes_ref"]
    sigla = fonte.split(" - ")[0] if " - " in fonte else fonte
    # Sprint AUDIT2-RAZAO-SOCIAL-HOLERITE: mapping declarativo sigla -> oficial.
    razao_social_oficial, cnpj_oficial = resolver_razao_social_canonica(sigla)
    # CNPJ sintético preservado como chave_44 estavel (compat Sprint 48). O
    # CNPJ oficial fica em metadata.cnpj_oficial para entity resolution.
    cnpj_sintetico = f"HOLERITE|{hashlib.sha256(sigla.encode('utf-8')).hexdigest()[:12]}"
    chave = f"HOLERITE|{fonte}|{mes_ref}".replace(" ", "_")
    documento = {
        "chave_44": chave,
        "cnpj_emitente": cnpj_sintetico,
        "data_emissao": f"{mes_ref}-01",
        "tipo_documento": "holerite",
        "total": float(registro.get("bruto") or 0.0),
        # Sprint 95a: persiste 'bruto' e 'liquido' separados em metadata.
        # 'total' continua como bruto por compat (Sprint 48 + Sprint 95).
        # 'liquido' permite linker apertar diff_valor de 0.30 para 0.05
        # quando match com tx PAGTO SALARIO (que carrega o liquido).
        "bruto": float(registro.get("bruto") or 0.0),
        "liquido": float(registro.get("liquido") or 0.0),
        "razao_social": razao_social_oficial,
        "razao_social_curta": sigla.upper(),
        "cnpj_oficial": cnpj_oficial,
        "numero": chave,
        "arquivo_original": str(arquivo.resolve()),
        "periodo_apuracao": mes_ref,
        # Sprint AUDIT2-METADATA-ITENS-LISTA: lista granular de proventos+
        # descontos. Vai pra metadata.itens via spread (sem upsert_item, pois
        # holerite não tem código de produto).
        "itens": [
            {
                "descricao": str(it.get("descricao", "")),
                "valor_total": float(it.get("valor") or 0.0),
                "qtde": 1.0,
                "codigo": "",
                "tipo": str(it.get("tipo", "")),
            }
            for it in (registro.get("itens") or [])
        ],
    }
    try:
        ingerir_documento_fiscal(grafo, documento, itens=[], caminho_arquivo=arquivo)
    except ValueError as exc:
        logger.warning("holerite %s não ingerido no grafo: %s", arquivo.name, exc)


def processar_holerites(
    diretorio: Path,
    grafo: "GrafoDB | None" = None,
) -> list[dict]:
    """Varre o diretório de holerites e retorna lista de dicts da aba renda.

    Ignora arquivos com sufixo ' (1)' ou ' (2)' — convenção do inbox processor
    para duplicatas de download. Se o diretório não existir, retorna lista vazia.

    Sprint P3.2 (2026-04-23): quando `grafo` é fornecido, cada holerite
    parseado também é ingerido como node `documento` no grafo (tipo
    holerite). Fecha o gap ADR-20 de tracking documental para folha de
    pagamento: +24 docs no grafo em runtime real.
    """
    if not diretorio.exists():
        logger.info("Diretório de holerites não encontrado: %s", diretorio)
        return []

    registros: list[dict] = []
    for arquivo in sorted(diretorio.glob("*.pdf")):
        if " (1)" in arquivo.stem or " (2)" in arquivo.stem:
            logger.debug("Ignorando duplicata: %s", arquivo.name)
            continue

        texto = _extrair_texto(arquivo)
        if not texto:
            logger.warning("Texto vazio em %s", arquivo.name)
            continue

        fonte = _detectar_fonte(texto)
        if fonte == "G4F":
            registro = _parse_g4f(texto)
        elif fonte == "Infobase":
            registro = _parse_infobase(texto)
        else:
            logger.warning("Fonte desconhecida em %s", arquivo.name)
            continue

        if registro is None:
            logger.warning("Parse retornou None para %s", arquivo.name)
            continue

        logger.info(
            "Holerite %s %s: bruto=%.2f líquido=%.2f",
            registro["fonte"],
            registro["mes_ref"],
            registro["bruto"],
            registro["liquido"],
        )
        if grafo is not None:
            _ingerir_holerite_no_grafo(grafo, registro, arquivo)
        registros.append(registro)

    registros.sort(key=lambda r: (r["mes_ref"], r["fonte"]))
    logger.info("Processados %d holerites em %s", len(registros), diretorio)
    return registros


# "O trabalho é a melhor maneira de se ganhar dinheiro sem pedir a ninguém." -- Machado de Assis
