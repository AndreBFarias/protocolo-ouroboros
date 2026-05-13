"""Normaliza transações de diferentes extratores para schema único."""

import hashlib
import re
from datetime import date
from typing import Optional

from src.transform.canonicalizer_casal import (
    e_transferencia_do_casal,
    variantes_curtas,
)
from src.transform.canonicalizer_fornecedor import canonicalizar as canonicalizar_fornecedor
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


def inferir_tipo_transacao(
    valor: float,
    descricao: str,
    tipo_sugerido: Optional[str] = None,
    valor_com_sinal: Optional[float] = None,
    banco_origem: Optional[str] = None,
) -> str:
    """Infere se é Despesa, Receita, Transferência Interna ou Imposto.

    Ordem de prioridade:
        1. Matcher rigoroso do casal (sempre prevalece).
        2. Matcher de variantes curtas (Sprint 82) -- exige `banco_origem`
           para checar whitelist + marcadores; sem banco, é pulado.
        3. Regex de Transferência Interna operacional (pagamento fatura,
           resgate/aplicação CDB/RDB).
        4. Regex de Imposto (prevalece sobre `tipo_sugerido`).
        5. `tipo_sugerido` do extrator (respeita sinal original do CSV).
        6. Regex de Receita.
        7. Sinal de `valor_com_sinal` (se fornecido) ou `valor` (legado).
        8. Default: Despesa.

    `tipo_sugerido` aceita os valores: "Receita", "Despesa",
    "Transferência Interna", "Imposto". Qualquer outro é ignorado.
    """
    desc_upper = descricao.upper()

    if e_transferencia_do_casal(descricao):
        return "Transferência Interna"

    if banco_origem and variantes_curtas(descricao, banco_origem):
        return "Transferência Interna"

    padroes_transferencia_interna_operacional = [
        r"RESGATE RDB|APLICAÇÃO RDB|RESGATE CDB|APLICAÇÃO CDB",
        r"FATURA\s+DE\s+CART[ÃA]O",
        r"PAGAMENTO\s+DE\s+FATURA",
        r"PGTO\s+FAT\s+CARTAO",
    ]
    for padrao in padroes_transferencia_interna_operacional:
        if re.search(padrao, desc_upper):
            return "Transferência Interna"

    padroes_imposto = [
        r"RECEITA.FED|DARF|DAS.*SIMPLES|DAS.*MEI",
    ]
    for padrao in padroes_imposto:
        if re.search(padrao, desc_upper):
            return "Imposto"

    tipos_validos = {"Receita", "Despesa", "Transferência Interna", "Imposto"}
    if tipo_sugerido in tipos_validos:
        return tipo_sugerido

    padroes_receita = [
        r"SALARIO|PAGTO.*SALARIO",
        r"TRANSFERENCIA RECEBIDA.*PAIM",
        r"REEMBOLSO|ESTORNO",
    ]
    for padrao in padroes_receita:
        if re.search(padrao, desc_upper):
            return "Receita"

    padroes_despesa_forte = [
        r"JUROS\s+POR\s+FATURA",
        r"IOF\s+POR\s+FATURA",
        r"MULTA\s+POR\s+FATURA",
        r"TRANSF\s+ENVIADA",
        r"TRANSFER[EÊ]NCIA\s+ENVIADA",
    ]
    for padrao in padroes_despesa_forte:
        if re.search(padrao, desc_upper):
            return "Despesa"

    valor_ref = valor_com_sinal if valor_com_sinal is not None else valor
    if valor_ref > 0:
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
    """Infere quem fez a transação pelo banco de origem.

    Retorna identificador genérico canônico (Sprint MOB-bridge-1):
    ``pessoa_a`` / ``pessoa_b`` / ``casal``. O nome real para
    apresentação é resolvido em runtime via
    ``src.utils.pessoas.nome_de`` na camada de relatório/UI.
    """
    bancos_pessoa_a = {"Itaú", "C6", "Santander"}
    bancos_pessoa_b_pf = {"Nubank (PF)"}
    bancos_pessoa_b_pj = {"Nubank (PJ)"}

    if banco_origem in bancos_pessoa_a:
        return "pessoa_a"
    if banco_origem in bancos_pessoa_b_pf:
        return "pessoa_b"
    if banco_origem in bancos_pessoa_b_pj:
        return "pessoa_b"

    if subtipo == "pj":
        return "pessoa_b"
    if subtipo == "pf":
        return "pessoa_b"

    # Nubank genérico (sem subtipo) é da pessoa_a.
    if banco_origem == "Nubank" and subtipo is None:
        return "pessoa_a"

    return "casal"


def normalizar_transacao(
    data_transacao: date,
    valor: float,
    descricao: str,
    banco_origem: str,
    tipo_extrato: str = "cc",
    identificador: Optional[str] = None,
    subtipo: Optional[str] = None,
    arquivo_origem: Optional[str] = None,
    tipo_sugerido: Optional[str] = None,
    valor_original_com_sinal: Optional[float] = None,
    virtual: bool = False,
) -> dict:
    """Normaliza uma transação para o schema padrão do XLSX.

    Retorna dict com as 12 colunas do schema:
    data, valor, forma_pagamento, local, quem, categoria, classificação,
    banco_origem, tipo, mes_ref, tag_irpf, obs

    Parâmetros novos (Sprint 55):
        tipo_sugerido: tipo ("Receita"/"Despesa"/"Transferência Interna"/
            "Imposto") vindo do extrator. Respeitado exceto quando regex
            de Transferência Interna ou Imposto prevalece.
        valor_original_com_sinal: valor com sinal preservado do CSV bruto,
            usado como fallback quando `tipo_sugerido` não é fornecido.

    Parâmetro novo (Sprint 82b):
        virtual: flag interna que sinaliza linha sintética emitida por
            extrator de cartão como contraparte espelho de pagamento de
            fatura. Preserva-se em ``_virtual`` no dict retornado; quando
            True, o tipo é forçado a "Transferência Interna" (contraparte
            nunca entra em somatório de receita/despesa).
    """
    descricao_limpa = descricao.replace("&amp;", "&").strip()

    pessoa = inferir_pessoa(banco_origem, subtipo, descricao_limpa)
    forma = inferir_forma_pagamento(descricao_limpa, banco_origem, tipo_extrato)
    if virtual:
        # Sprint 82b: contraparte espelho de pagamento de fatura. Flag
        # vence a inferência -- a linha existe por simetria com a saída
        # real e nunca deve virar Despesa/Receita.
        tipo = "Transferência Interna"
    else:
        tipo = inferir_tipo_transacao(
            valor,
            descricao_limpa,
            tipo_sugerido=tipo_sugerido,
            valor_com_sinal=valor_original_com_sinal,
        )
    local = extrair_local(descricao_limpa)
    local = canonicalizar_fornecedor(local)

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
        # Sprint DASH-PAGAMENTOS-CRUZADOS-CASAL: campos opcionais para
        # reconhecer pagamentos cruzados do casal (Vitória paga DAS do MEI
        # Andre, etc.). ``pessoa_pagadora`` derivado do banco origem
        # (espelha ``quem``). ``pessoa_devedora`` populado por
        # ``src.transform.pagamentos_cruzados.inferir_pessoa_devedora``
        # quando há match com documento (DAS, IPVA, IRPF) no grafo.
        # Default None: retrocompat (padrão (o)).
        "pessoa_pagadora": pessoa,
        "pessoa_devedora": None,
        "_identificador": identificador,
        "_descricao_original": descricao_limpa,
        "_arquivo_origem": arquivo_origem,
        "_virtual": virtual,
    }


# "Conhece-te a ti mesmo." -- Sócrates
