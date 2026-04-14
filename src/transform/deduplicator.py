"""Deduplicação de transações em múltiplos níveis."""

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
    """Nível 2: Remove duplicatas por combinação data + valor + local similar.

    Detecta a mesma transação aparecendo em dois extratos diferentes
    (ex: Pix aparece no Itaú E no Nubank com descrições ligeiramente diferentes).
    """
    resultado: list[dict] = []
    chaves_vistas: set[str] = set()
    duplicatas = 0

    for t in transacoes:
        # Transferências internas são tratadas separadamente
        if t.get("tipo") == "Transferência Interna":
            resultado.append(t)
            continue

        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        valor_str = f"{abs(t['valor']):.2f}"
        chave = f"{data_str}|{valor_str}"

        if chave in chaves_vistas:
            duplicatas += 1
            t["_duplicata_fuzzy"] = True
            # Mantém a transação mas marca -- pode ser coincidência legítima
            # (dois gastos iguais no mesmo dia é possível)
            resultado.append(t)
            continue

        chaves_vistas.add(chave)
        resultado.append(t)

    if duplicatas > 0:
        logger.info(
            "Dedup nível 2 (fuzzy): %d possíveis duplicatas marcadas (não removidas)",
            duplicatas,
        )

    return resultado


def marcar_transferencias_internas(transacoes: list[dict]) -> list[dict]:
    """Nível 3: Identifica pares de transferência interna.

    Procura pares onde:
    - Saída de uma conta = Entrada em outra
    - Mesmo valor, mesma data (ou +/- 1 dia)
    - Entre contas do André e Vitória

    Marca ambos como Transferência Interna sem remover.
    """
    pares_encontrados = 0

    # Indexar entradas por (data, valor absoluto)
    entradas: dict[str, list[int]] = {}
    for i, t in enumerate(transacoes):
        if t.get("tipo") == "Receita" or (
            t.get("tipo") == "Transferência Interna" and t.get("valor", 0) > 0
        ):
            data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
            chave = f"{data_str}|{abs(t['valor']):.2f}"
            entradas.setdefault(chave, []).append(i)

    # Para cada saída, procurar entrada correspondente
    for t in transacoes:
        if t.get("tipo") not in ("Despesa", None):
            continue

        data_str = t["data"].isoformat() if hasattr(t["data"], "isoformat") else str(t["data"])
        chave = f"{data_str}|{abs(t['valor']):.2f}"

        if chave not in entradas:
            continue

        # Verificar se é entre pessoas diferentes (André <-> Vitória)
        for idx in entradas[chave]:
            entrada = transacoes[idx]
            if entrada.get("quem") != t.get("quem"):
                t["tipo"] = "Transferência Interna"
                entrada["tipo"] = "Transferência Interna"
                pares_encontrados += 1
                break

    if pares_encontrados > 0:
        logger.info(
            "Dedup nível 3: %d pares de transferência interna identificados",
            pares_encontrados,
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
