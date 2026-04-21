"""Testes da função ``calcular_ritmos`` em ``src.projections.scenarios``.

Cobre as três janelas (histórico, 12 meses, 3 meses) e os casos-borda de
dados insuficientes, garantindo o contrato pedido pela Sprint 61.
"""

from __future__ import annotations

from src.projections.scenarios import calcular_ritmos


def _mes(indice: int) -> str:
    """Gera rótulo ``YYYY-MM`` determinístico a partir de um índice mensal."""
    ano = 2023 + (indice - 1) // 12
    mes = ((indice - 1) % 12) + 1
    return f"{ano:04d}-{mes:02d}"


def _fabricar_transacoes(
    num_meses: int,
    receita_por_mes: float,
    despesa_por_mes: float,
) -> list[dict]:
    """Monta uma lista de transações sintéticas com um par receita/despesa por mês."""
    transacoes: list[dict] = []
    for i in range(1, num_meses + 1):
        mes_ref = _mes(i)
        transacoes.append(
            {"mes_ref": mes_ref, "tipo": "Receita", "valor": receita_por_mes}
        )
        transacoes.append(
            {"mes_ref": mes_ref, "tipo": "Despesa", "valor": despesa_por_mes}
        )
    return transacoes


def test_calcular_ritmos_com_36_meses_retorna_tres_janelas_validas() -> None:
    """Com 36 meses de dados, as três janelas existem e refletem o saldo médio."""
    transacoes = _fabricar_transacoes(36, receita_por_mes=10000.0, despesa_por_mes=7000.0)

    ritmos = calcular_ritmos(transacoes)

    assert ritmos["historico"] is not None
    assert ritmos["12_meses"] is not None
    assert ritmos["3_meses"] is not None
    # Receita - despesa constante = 3000 em todas as janelas
    assert abs(ritmos["historico"] - 3000.0) < 0.01
    assert abs(ritmos["12_meses"] - 3000.0) < 0.01
    assert abs(ritmos["3_meses"] - 3000.0) < 0.01


def test_janela_3m_reflete_apenas_ultimos_tres_meses() -> None:
    """Ritmo 3m deve capturar só os últimos 3 meses; 12m e histórico pegam mais."""
    transacoes: list[dict] = []
    # 9 meses antigos com saldo baixo (1000/mes)
    for i in range(1, 10):
        mes_ref = _mes(i)
        transacoes.append({"mes_ref": mes_ref, "tipo": "Receita", "valor": 5000.0})
        transacoes.append({"mes_ref": mes_ref, "tipo": "Despesa", "valor": 4000.0})
    # 3 meses mais recentes com saldo alto (5000/mes)
    for i in range(10, 13):
        mes_ref = _mes(i)
        transacoes.append({"mes_ref": mes_ref, "tipo": "Receita", "valor": 10000.0})
        transacoes.append({"mes_ref": mes_ref, "tipo": "Despesa", "valor": 5000.0})

    ritmos = calcular_ritmos(transacoes)

    assert ritmos["3_meses"] is not None
    assert abs(ritmos["3_meses"] - 5000.0) < 0.01
    assert ritmos["12_meses"] is not None
    # histórico com 12 meses = (9*1000 + 3*5000) / 12 = 2000
    assert abs(ritmos["12_meses"] - 2000.0) < 0.01
    assert ritmos["historico"] is not None
    assert abs(ritmos["historico"] - 2000.0) < 0.01


def test_menos_de_tres_meses_retorna_none_para_janelas_maiores() -> None:
    """Com 2 meses de dados, 3_meses e 12_meses ficam ``None``; histórico calcula."""
    transacoes = _fabricar_transacoes(2, receita_por_mes=8000.0, despesa_por_mes=6000.0)

    ritmos = calcular_ritmos(transacoes)

    assert ritmos["3_meses"] is None
    assert ritmos["12_meses"] is None
    assert ritmos["historico"] is not None
    assert abs(ritmos["historico"] - 2000.0) < 0.01


def test_lista_vazia_retorna_todas_none() -> None:
    """Sem transações, todas as três janelas retornam ``None``."""
    ritmos = calcular_ritmos([])

    assert ritmos["historico"] is None
    assert ritmos["12_meses"] is None
    assert ritmos["3_meses"] is None


def test_transferencia_interna_nao_conta_no_saldo() -> None:
    """Transferências internas devem ser ignoradas no cálculo do ritmo."""
    transacoes: list[dict] = []
    for i in range(1, 13):
        mes_ref = _mes(i)
        transacoes.append({"mes_ref": mes_ref, "tipo": "Receita", "valor": 5000.0})
        transacoes.append({"mes_ref": mes_ref, "tipo": "Despesa", "valor": 3000.0})
        # Ruído: transferências internas de valor alto não devem afetar o ritmo
        transacoes.append(
            {"mes_ref": mes_ref, "tipo": "Transferência Interna", "valor": 50000.0}
        )

    ritmos = calcular_ritmos(transacoes)

    assert ritmos["12_meses"] is not None
    assert abs(ritmos["12_meses"] - 2000.0) < 0.01


# "Quem mede, melhora; quem compara períodos, entende." -- princípio estatístico
