"""Fase 6 do gauntlet: testa cálculos de projeções financeiras."""

import time
from datetime import date

from scripts.gauntlet.config import ResultadoFase, ResultadoTeste
from src.projections.scenarios import (
    _calcular_medias,
    _meses_ate_objetivo,
    _projecao_acumulada,
    projetar_cenarios,
)
from src.utils.logger import configurar_logger

logger = configurar_logger("gauntlet.projecoes")


def _gerar_transacoes_teste() -> list[dict]:
    """Gera transações sintéticas para teste de projeções."""
    transacoes: list[dict] = []

    for mes in ["2026-02", "2026-03", "2026-04"]:
        transacoes.append({
            "data": date(2026, int(mes[-2:]), 1),
            "valor": 15000.0,
            "tipo": "Receita",
            "categoria": "Salário",
            "mes_ref": mes,
        })
        transacoes.append({
            "data": date(2026, int(mes[-2:]), 5),
            "valor": 3700.0,
            "tipo": "Receita",
            "categoria": "Renda PJ",
            "mes_ref": mes,
        })
        transacoes.append({
            "data": date(2026, int(mes[-2:]), 10),
            "valor": 8000.0,
            "tipo": "Despesa",
            "categoria": "Diversos",
            "mes_ref": mes,
        })
        transacoes.append({
            "data": date(2026, int(mes[-2:]), 15),
            "valor": 1200.0,
            "tipo": "Transferência Interna",
            "categoria": "Transferência",
            "mes_ref": mes,
        })

    return transacoes


def _testar_medias() -> ResultadoTeste:
    """Testa cálculo de médias mensais."""
    inicio = time.time()
    transacoes = _gerar_transacoes_teste()

    medias = _calcular_medias(transacoes)
    receita = medias["receita_media"]
    despesa = medias["despesa_media"]
    saldo = medias["saldo_medio"]

    receita_esperada = 18700.0
    despesa_esperada = 8000.0
    saldo_esperado = 10700.0

    tolerancia = 0.01
    passou = (
        abs(receita - receita_esperada) < tolerancia
        and abs(despesa - despesa_esperada) < tolerancia
        and abs(saldo - saldo_esperado) < tolerancia
    )

    detalhe = (
        f"Receita: {receita:.2f} (esperado: {receita_esperada:.2f}), "
        f"Despesa: {despesa:.2f} (esperado: {despesa_esperada:.2f}), "
        f"Saldo: {saldo:.2f} (esperado: {saldo_esperado:.2f})"
    )

    return ResultadoTeste(
        nome="medias_mensais",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
    )


def _testar_meses_ate_objetivo() -> ResultadoTeste:
    """Testa cálculo de meses até atingir objetivo."""
    inicio = time.time()

    meses = _meses_ate_objetivo(5000.0, 27000.0)
    meses_impossivel = _meses_ate_objetivo(-1000.0, 27000.0)
    meses_zero = _meses_ate_objetivo(5000.0, 27000.0, atual=27000.0)

    passou = meses == 6 and meses_impossivel is None and meses_zero == 0

    detalhe = (
        f"R$ 5k/mês até R$ 27k: {meses} meses (esperado: 6), "
        f"Saldo negativo: {meses_impossivel} (esperado: None), "
        f"Já atingido: {meses_zero} (esperado: 0)"
    )

    return ResultadoTeste(
        nome="meses_ate_objetivo",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
    )


def _testar_projecao_acumulada() -> ResultadoTeste:
    """Testa geração de projeção acumulada 12 meses."""
    inicio = time.time()

    projecao = _projecao_acumulada(5000.0, 10000.0, meses=12)

    passou = (
        len(projecao) == 12
        and projecao[0]["acumulado"] == 15000.0
        and projecao[11]["acumulado"] == 70000.0
    )

    detalhe = (
        f"{len(projecao)} pontos, "
        f"mês 1: {projecao[0]['acumulado']:.0f} (esperado: 15000), "
        f"mês 12: {projecao[11]['acumulado']:.0f} (esperado: 70000)"
    )

    return ResultadoTeste(
        nome="projecao_acumulada",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
    )


def _testar_cenarios_completos() -> ResultadoTeste:
    """Testa projetar_cenarios com dados sintéticos."""
    inicio = time.time()
    transacoes = _gerar_transacoes_teste()

    try:
        resultado = projetar_cenarios(transacoes)

        tem_atual = "cenario_atual" in resultado
        tem_pos = "cenario_pos_infobase" in resultado
        tem_ape = "cenario_meta_ape" in resultado
        saldo_atual = resultado.get("saldo_medio", 0)
        saldo_pos = resultado.get("cenario_pos_infobase", {}).get("saldo_mensal", 0)

        passou = tem_atual and tem_pos and tem_ape and saldo_atual > 0
        detalhe = (
            f"Cenários: atual={tem_atual}, pós={tem_pos}, apê={tem_ape}. "
            f"Saldo atual: {saldo_atual:.2f}, Pós-Infobase: {saldo_pos:.2f}"
        )
        erro = ""
    except Exception as e:
        passou = False
        detalhe = ""
        erro = str(e)

    return ResultadoTeste(
        nome="cenarios_completos",
        passou=passou,
        tempo=time.time() - inicio,
        detalhe=detalhe,
        erro=erro,
    )


def executar() -> ResultadoFase:
    """Executa todos os testes de projeções."""
    fase = ResultadoFase(nome="projecoes")
    inicio = time.time()

    fase.testes.append(_testar_medias())
    fase.testes.append(_testar_meses_ate_objetivo())
    fase.testes.append(_testar_projecao_acumulada())
    fase.testes.append(_testar_cenarios_completos())

    fase.tempo_total = time.time() - inicio
    logger.info(
        "Fase projeções: %d/%d testes OK em %.2fs",
        fase.ok, fase.total, fase.tempo_total,
    )
    return fase


# "Um investimento em conhecimento paga os melhores juros." -- Benjamin Franklin
