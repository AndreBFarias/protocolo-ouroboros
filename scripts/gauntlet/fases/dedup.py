"""Fase 3 do gauntlet: testa deduplicação em 3 níveis."""

import time
from datetime import date

from scripts.gauntlet.config import ResultadoFase, ResultadoTeste
from src.transform.deduplicator import (
    deduplicar,
    deduplicar_por_hash_fuzzy,
    deduplicar_por_identificador,
    marcar_transferencias_internas,
)
from src.utils.logger import configurar_logger

logger = configurar_logger("gauntlet.dedup")


def _base_transacao(**kwargs: object) -> dict:
    """Cria transação base para testes."""
    t: dict = {
        "data": date(2026, 4, 15),
        "valor": 100.0,
        "local": "TESTE",
        "quem": "André",
        "categoria": "Outros",
        "classificacao": "Questionável",
        "banco_origem": "Nubank",
        "tipo": "Despesa",
        "mes_ref": "2026-04",
        "_identificador": None,
        "_descricao_original": "TESTE",
    }
    t.update(kwargs)
    return t


def _testar_nivel1_uuid() -> ResultadoTeste:
    """Nível 1: duplicatas com mesmo _identificador são removidas."""
    inicio = time.time()

    transacoes = [
        _base_transacao(_identificador="uuid-001", local="IFOOD A"),
        _base_transacao(_identificador="uuid-001", local="IFOOD A (1)"),
        _base_transacao(_identificador="uuid-002", local="UBER"),
        _base_transacao(_identificador="uuid-003", local="MERCADO"),
    ]

    resultado = deduplicar_por_identificador(transacoes)
    esperado = 3
    passou = len(resultado) == esperado

    return ResultadoTeste(
        nome="dedup_l1_uuid",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=f"{len(resultado)} restantes (esperado: {esperado})",
    )


def _testar_nivel2_fuzzy() -> ResultadoTeste:
    """Nível 2: transações com mesma data+valor são marcadas (não removidas)."""
    inicio = time.time()

    transacoes = [
        _base_transacao(data=date(2026, 4, 10), valor=50.0, local="PIX A", banco_origem="Itaú"),
        _base_transacao(data=date(2026, 4, 10), valor=50.0, local="PIX B", banco_origem="Nubank"),
        _base_transacao(data=date(2026, 4, 12), valor=200.0, local="OUTRO"),
    ]

    resultado = deduplicar_por_hash_fuzzy(transacoes)
    marcados = [t for t in resultado if t.get("_duplicata_fuzzy")]

    passou = len(resultado) == 3 and len(marcados) == 1

    return ResultadoTeste(
        nome="dedup_l2_fuzzy",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=(
            f"{len(resultado)} mantidas, {len(marcados)} marcadas como fuzzy "
            f"(esperado: 3 mantidas, 1 marcada)"
        ),
    )


def _testar_nivel3_transferencia() -> ResultadoTeste:
    """Nível 3: pares de transferência entre contas são identificados."""
    inicio = time.time()

    transacoes = [
        _base_transacao(
            data=date(2026, 4, 15), valor=-1200.0,
            quem="André", tipo="Despesa", local="TED VITORIA",
        ),
        _base_transacao(
            data=date(2026, 4, 15), valor=1200.0,
            quem="Vitória", tipo="Receita", local="TED RECEBIDA",
        ),
        _base_transacao(
            data=date(2026, 4, 20), valor=-50.0,
            quem="André", tipo="Despesa", local="IFOOD",
        ),
    ]

    resultado = marcar_transferencias_internas(transacoes)
    internas = [t for t in resultado if t["tipo"] == "Transferência Interna"]

    passou = len(internas) == 2

    return ResultadoTeste(
        nome="dedup_l3_transferencia",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=f"{len(internas)} transferências internas (esperado: 2)",
    )


def _testar_pipeline_completo() -> ResultadoTeste:
    """Testa os 3 níveis em sequência via deduplicar()."""
    inicio = time.time()

    transacoes = [
        _base_transacao(_identificador="uuid-a", valor=100.0, local="A"),
        _base_transacao(_identificador="uuid-a", valor=100.0, local="A (1)"),
        _base_transacao(_identificador="uuid-b", valor=200.0, local="B"),
        _base_transacao(valor=300.0, local="C", _identificador=None),
    ]

    resultado = deduplicar(transacoes)
    passou = len(resultado) == 3

    return ResultadoTeste(
        nome="dedup_pipeline_completo",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=f"{len(resultado)} finais (esperado: 3)",
    )


def executar() -> ResultadoFase:
    """Executa todos os testes de deduplicação."""
    fase = ResultadoFase(nome="dedup")
    inicio = time.time()

    fase.testes.append(_testar_nivel1_uuid())
    fase.testes.append(_testar_nivel2_fuzzy())
    fase.testes.append(_testar_nivel3_transferencia())
    fase.testes.append(_testar_pipeline_completo())

    fase.tempo_total = time.time() - inicio
    logger.info(
        "Fase dedup: %d/%d testes OK em %.2fs",
        fase.ok, fase.total, fase.tempo_total,
    )
    return fase


# "A repetição é a mãe da habilidade." -- Anthony Robbins
