"""Extrator de contracheques (holerites) em PDF.

Suporta duas fontes:
- G4F SOLUCOES CORPORATIVAS (PDF com texto nativo)
- INFOBASE CONSULTORIA E INFORMATICA (PDF nativo ou escaneado, com fallback para OCR)

A saída é uma lista de dicts compatível com a aba `renda` do XLSX final.
Cada PDF gera UMA entrada. Meses com 13º salário produzem entrada adicional
(tipo "13º Adiantamento" ou "13º Integral") em paralelo à folha mensal.
"""

import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pdfplumber
import pypdfium2 as pdfium
import pytesseract

from src.utils.logger import configurar_logger
from src.utils.parse_br import parse_valor_br_float

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
    for match in REGEX_G4F_PROVENTO.finditer(texto):
        descricao, valor = match.groups()
        bruto += parse_valor_br_float(valor)
        descricao_norm = descricao.strip()
        if "13" in descricao_norm and "Adiantado" in descricao_norm:
            tipo = "13º Adiantamento"
        elif "13" in descricao_norm and "Integral" in descricao_norm:
            tipo = "13º Integral"

    inss = irrf = vr_va = 0.0
    for match in REGEX_G4F_DESCONTO.finditer(texto):
        descricao, valor = match.groups()
        valor_num = parse_valor_br_float(valor)
        descricao_upper = descricao.upper()
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

    return {
        "mes_ref": mes_ref,
        "fonte": f"Infobase - {tipo}" if tipo != "Folha Mensal" else "Infobase",
        "bruto": round(bruto, 2),
        "inss": round(inss, 2),
        "irrf": round(irrf, 2),
        "vr_va": round(vr_va, 2),
        "liquido": round(liquido, 2),
        "banco": "",
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
    empregador = fonte.split(" - ")[0] if " - " in fonte else fonte
    cnpj_sintetico = f"HOLERITE|{hashlib.sha256(empregador.encode('utf-8')).hexdigest()[:12]}"
    chave = f"HOLERITE|{fonte}|{mes_ref}".replace(" ", "_")
    documento = {
        "chave_44": chave,
        "cnpj_emitente": cnpj_sintetico,
        "data_emissao": f"{mes_ref}-01",
        "tipo_documento": "holerite",
        "total": float(registro.get("bruto") or 0.0),
        "razao_social": empregador.upper(),
        "numero": chave,
        "arquivo_original": str(arquivo.resolve()),
        "periodo_apuracao": mes_ref,
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
