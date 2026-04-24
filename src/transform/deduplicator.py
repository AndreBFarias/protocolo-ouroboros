"""Deduplicação de transações em múltiplos níveis."""

from src.transform.canonicalizer_casal import e_transferencia_do_casal
from src.utils.logger import configurar_logger

logger = configurar_logger("deduplicator")


def deduplicar_por_identificador(transacoes: list[dict]) -> list[dict]:
    """Nível 1: Remove duplicatas exatas por _identificador (UUID ou hash).

    Mantém a primeira ocorrência, descarta as demais.
    """
    vistos: dict[str, int] = {}
    resultado: list[dict] = []
    duplicatas = 0

    for t in transacoes:
        ident = t.get("_identificador")
        if ident is None:
            resultado.append(t)
            continue

        if ident in vistos:
            duplicatas += 1
            continue

        vistos[ident] = len(resultado)
        resultado.append(t)

    if duplicatas > 0:
        logger.info("Dedup nível 1 (identificador): %d duplicatas removidas", duplicatas)

    return resultado


def deduplicar_por_hash_fuzzy(transacoes: list[dict]) -> list[dict]:
    """Nível 2: Remove duplicatas por combinação data + valor + local.

    Cobre três cenários reais:
    - Mesma transação em OFX e XLSX/CSV legacy do mesmo banco
    - Mesma transação no XLSX histórico (banco_origem="Histórico") e na
      re-extração atual do banco de origem
    - Transferência interna listada pelo OFX e pelo CSV do mesmo banco

    Quando múltiplas transações casam pela chave, mantém a que TEM
    `banco_origem != "Histórico"` (metadados melhores da fonte original).
    Pares LEGÍTIMOS de transferência interna (entre bancos diferentes) não
    colidem na chave, pois têm `local` distinto em cada ponta.
    """
    grupos: dict[str, list[int]] = {}

    for idx, t in enumerate(transacoes):
        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        valor_str = f"{abs(t['valor']):.2f}"
        local = str(t.get("local", "")).strip().lower()
        chave = f"{data_str}|{valor_str}|{local}"
        grupos.setdefault(chave, []).append(idx)

    indices_remover: set[int] = set()
    for ids in grupos.values():
        if len(ids) <= 1:
            continue
        # Sprint 82b: espelho virtual de cartão tem razão de existir como
        # contraparte; se colide com saída real, PRESERVA AMBOS (dedup
        # clássico não se aplica a pares conta-espelho).
        tem_virtual = any(transacoes[i].get("_virtual") for i in ids)
        if tem_virtual:
            continue
        nao_historicos = [i for i in ids if transacoes[i].get("banco_origem") != "Histórico"]
        preservar = nao_historicos[0] if nao_historicos else ids[0]
        for i in ids:
            if i != preservar:
                indices_remover.add(i)

    resultado: list[dict] = []
    for idx, t in enumerate(transacoes):
        if idx in indices_remover:
            continue
        resultado.append(t)

    if indices_remover:
        logger.info(
            "Dedup nível 2 (fuzzy por data+valor+local): %d duplicatas removidas",
            len(indices_remover),
        )

    return resultado


def _descricao_para_match(transacao: dict) -> str:
    """Extrai o melhor texto da transação para matching de identidade do casal.

    Prioriza `_descricao_original` (string crua do extrator) e cai para `local`
    quando a original não existe (histórico importado).
    """
    return str(transacao.get("_descricao_original") or transacao.get("local") or "")


def _parear_espelhos_virtuais(transacoes: list[dict]) -> int:
    """Sprint 82b: pareia espelho virtual (cartão) com saída real (CC).

    Extratores de cartão (c6_cartao, santander_pdf) emitem linha virtual
    com `_virtual=True` quando detectam pagamento de fatura recebido. A
    contraparte real é a saída no CC (mesma data, mesmo valor, outra
    conta) que já chega ao deduplicator com tipo="Transferência Interna"
    via regex operacional do extrator ou do pipeline. O pareamento clássico
    de `marcar_transferencias_internas` não cobre esse caso porque ambos
    os lados já são TI (nenhum é Despesa/None) e ambos têm pessoa="André".

    Esta função apenas GARANTE que ambos os lados permanecem como TI e
    conta os pares encontrados (pelo menos um dos dois com `_virtual=True`
    + mesma data + mesmo valor absoluto, ignorando a identidade). Idempotente:
    não remove nem duplica linhas; só acumula estatística para log.
    """
    virtuais_por_chave: dict[str, list[int]] = {}
    reais_por_chave: dict[str, list[int]] = {}

    for idx, t in enumerate(transacoes):
        if t.get("tipo") != "Transferência Interna":
            continue
        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        chave = f"{data_str}|{abs(t.get('valor', 0)):.2f}"
        if t.get("_virtual"):
            virtuais_por_chave.setdefault(chave, []).append(idx)
        else:
            reais_por_chave.setdefault(chave, []).append(idx)

    pares = 0
    for chave, idx_virtuais in virtuais_por_chave.items():
        idx_reais = reais_por_chave.get(chave)
        if not idx_reais:
            continue
        # Confirma que ambos os lados continuam TI -- ja deveriam estar.
        for i in idx_virtuais:
            transacoes[i]["tipo"] = "Transferência Interna"
        for i in idx_reais:
            transacoes[i]["tipo"] = "Transferência Interna"
        pares += min(len(idx_virtuais), len(idx_reais))

    return pares


def marcar_transferencias_internas(transacoes: list[dict]) -> list[dict]:
    """Nível 3: Identifica pares de transferência interna.

    Procura pares onde:
    - Saída de uma conta = Entrada em outra
    - Mesmo valor, mesma data
    - Entre contas do André e Vitória

    Para evitar falso-positivo (Sprint 68), exige que PELO MENOS UM lado
    do par contenha identidade do casal na descrição -- via
    `canonicalizer_casal.e_transferencia_do_casal`. Se nenhum dos dois
    lados bate com a whitelist, o par é ignorado (não vira TI).

    Marca ambos como Transferência Interna sem remover.

    Sprint 82b: pareia também espelhos virtuais de cartão (_virtual=True)
    com saídas reais no CC do mesmo valor/data -- via `_parear_espelhos_virtuais`.
    """
    pares_encontrados = 0

    entradas: dict[str, list[int]] = {}
    for i, t in enumerate(transacoes):
        if t.get("tipo") == "Receita" or (
            t.get("tipo") == "Transferência Interna" and t.get("valor", 0) > 0
        ):
            data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
            chave = f"{data_str}|{abs(t['valor']):.2f}"
            entradas.setdefault(chave, []).append(i)

    for t in transacoes:
        if t.get("tipo") not in ("Despesa", None):
            continue

        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        chave = f"{data_str}|{abs(t['valor']):.2f}"

        if chave not in entradas:
            continue

        for idx in entradas[chave]:
            entrada = transacoes[idx]
            if entrada.get("quem") == t.get("quem"):
                continue

            desc_saida = _descricao_para_match(t)
            desc_entrada = _descricao_para_match(entrada)
            if not (
                e_transferencia_do_casal(desc_saida)
                or e_transferencia_do_casal(desc_entrada)
            ):
                continue

            t["tipo"] = "Transferência Interna"
            entrada["tipo"] = "Transferência Interna"
            pares_encontrados += 1
            break

    if pares_encontrados > 0:
        logger.info(
            "Dedup nível 3: %d pares de transferência interna identificados",
            pares_encontrados,
        )

    pares_virtuais = _parear_espelhos_virtuais(transacoes)
    if pares_virtuais > 0:
        logger.info(
            "Dedup nível 3 (Sprint 82b): %d pares espelho-virtual + saída-real confirmados",
            pares_virtuais,
        )

    return transacoes


def deduplicar(transacoes: list[dict]) -> list[dict]:
    """Executa todos os níveis de deduplicação em sequência."""
    logger.info("Iniciando deduplicação de %d transações", len(transacoes))

    resultado = deduplicar_por_identificador(transacoes)
    resultado = marcar_transferencias_internas(resultado)
    resultado = deduplicar_por_hash_fuzzy(resultado)

    logger.info("Deduplicação concluída: %d transações restantes", len(resultado))
    return resultado


# "A repetição é a mãe do aprendizado." -- Plutarco
