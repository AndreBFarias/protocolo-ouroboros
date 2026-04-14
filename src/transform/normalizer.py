"""Normaliza transações de diferentes extratores para schema único."""

import hashlib
import re
from datetime import date
from typing import Optional

from src.utils.logger import configurar_logger

logger = configurar_logger("normalizer")


def gerar_hash_transacao(data: date, descricao: str, valor: float) -> str:
    """Gera hash determinístico para identificação de transações sem UUID."""
    conteudo = f"{data.isoformat()}|{descricao.strip().lower()}|{valor:.2f}"
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:16]


def inferir_forma_pagamento(descricao: str, banco_origem: str, tipo_extrato: str) -> str:
    """Infere a forma de pagamento pela descrição e contexto."""
    desc_upper = descricao.upper()

    if tipo_extrato == "cartao":
        return "Crédito"

    if "PIX" in desc_upper or "PELO PIX" in desc_upper:
        return "Pix"
    if "DÉBITO" in desc_upper or "DEBITO" in desc_upper or "NO DÉBITO" in desc_upper:
        return "Débito"
    if "BOLETO" in desc_upper:
        return "Boleto"
    if "TED" in desc_upper or "DOC" in desc_upper:
        return "Transferência"
    if "COMPRA NO DÉBITO" in desc_upper:
        return "Débito"

    return "Débito" if tipo_extrato == "cc" else "Crédito"


def inferir_tipo_transacao(valor: float, descricao: str) -> str:
    """Infere se é Despesa, Receita, Transferência Interna ou Imposto."""
    desc_upper = descricao.upper()

    padroes_transferencia_interna = [
        r"TRANSFERENCIA\s+(RECEBIDA|ENVIADA).*ANDRE.*SILVA",
        r"TRANSFERENCIA\s+(RECEBIDA|ENVIADA).*VITORIA.*MARIA",
        r"NU.PAGAMENT.*BOLETO",
        r"PAGAMENTO DE BOLETO.*NU PAGAMENTOS",
        r"RESGATE RDB|APLICAÇÃO RDB|RESGATE CDB",
        r"VALOR ADICIONADO.*CRÉDITO",
    ]
    for padrao in padroes_transferencia_interna:
        if re.search(padrao, desc_upper):
            return "Transferência Interna"

    padroes_imposto = [
        r"RECEITA.FED|DARF|DAS.*SIMPLES|DAS.*MEI",
    ]
    for padrao in padroes_imposto:
        if re.search(padrao, desc_upper):
            return "Imposto"

    padroes_receita = [
        r"SALARIO|PAGTO.*SALARIO",
        r"TRANSFERENCIA RECEBIDA.*PAIM",
        r"REEMBOLSO|ESTORNO",
    ]
    for padrao in padroes_receita:
        if re.search(padrao, desc_upper):
            return "Receita"

    if valor > 0:
        return "Receita"

    return "Despesa"


def extrair_local(descricao: str) -> str:
    """Extrai o nome do estabelecimento/local da descrição."""
    desc = descricao.strip()

    # Nubank CC: "Transferência enviada pelo Pix - NOME - CPF/CNPJ - BANCO..."
    match = re.match(
        r"(?:Transferência enviada pelo Pix|Compra no débito|Pagamento de boleto efetuado)"
        r"\s*-\s*(.+?)(?:\s*-\s*\d|$)",
        desc,
    )
    if match:
        return match.group(1).strip()

    # Nubank CC: "Transferência Recebida - NOME CPF - CNPJ..."
    match = re.match(r"Transferência Recebida\s*-\s*(.+?)(?:\s+\d{5,}|\s*-\s*\d)", desc)
    if match:
        return match.group(1).strip()

    # Nubank cartão: título direto
    if " - Parcela " in desc:
        return desc.split(" - Parcela ")[0].strip()

    # Fallback: primeiros 60 caracteres
    return desc[:60].strip() if len(desc) > 60 else desc


def inferir_pessoa(
    banco_origem: str,
    subtipo: Optional[str] = None,
    descricao: str = "",
) -> str:
    """Infere quem fez a transação pelo banco de origem."""
    bancos_andre = {"Itaú", "C6", "Santander"}
    bancos_vitoria_pf = {"Nubank PF"}
    bancos_vitoria_pj = {"Nubank PJ"}

    if banco_origem in bancos_andre:
        return "André"
    if banco_origem in bancos_vitoria_pf:
        return "Vitória"
    if banco_origem in bancos_vitoria_pj:
        return "Vitória"

    if subtipo == "pj":
        return "Vitória"
    if subtipo == "pf":
        return "Vitória"

    # Nubank genérico do André
    if banco_origem == "Nubank" and subtipo is None:
        return "André"

    return "Casal"


def normalizar_transacao(
    data_transacao: date,
    valor: float,
    descricao: str,
    banco_origem: str,
    tipo_extrato: str = "cc",
    identificador: Optional[str] = None,
    subtipo: Optional[str] = None,
    arquivo_origem: Optional[str] = None,
) -> dict:
    """Normaliza uma transação para o schema padrão do XLSX.

    Retorna dict com as 12 colunas do schema:
    data, valor, forma_pagamento, local, quem, categoria, classificacao,
    banco_origem, tipo, mes_ref, tag_irpf, obs
    """
    descricao_limpa = descricao.replace("&amp;", "&").strip()

    pessoa = inferir_pessoa(banco_origem, subtipo, descricao_limpa)
    forma = inferir_forma_pagamento(descricao_limpa, banco_origem, tipo_extrato)
    tipo = inferir_tipo_transacao(valor, descricao_limpa)
    local = extrair_local(descricao_limpa)

    if identificador is None:
        identificador = gerar_hash_transacao(data_transacao, descricao_limpa, valor)

    return {
        "data": data_transacao,
        "valor": abs(valor),
        "forma_pagamento": forma,
        "local": local,
        "quem": pessoa,
        "categoria": None,  # Preenchido pelo categorizer
        "classificacao": None,  # Preenchido pelo categorizer
        "banco_origem": banco_origem,
        "tipo": tipo,
        "mes_ref": data_transacao.strftime("%Y-%m"),
        "tag_irpf": None,
        "obs": None,
        "_identificador": identificador,
        "_descricao_original": descricao_limpa,
        "_arquivo_origem": arquivo_origem,
    }


# "Conhece-te a ti mesmo." -- Sócrates
