"""Simulador de regimes tributários do IRPF."""

from pathlib import Path
from typing import Any

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("irpf_simulador")

TABELAS_PATH = Path(__file__).resolve().parents[2] / "mappings" / "tabelas_irpf.yaml"


def carregar_tabela(ano: int) -> dict[str, Any]:
    """Carrega tabela progressiva do ano."""
    with open(TABELAS_PATH, encoding="utf-8") as f:
        tabelas = yaml.safe_load(f)
    return tabelas.get(ano, tabelas.get(max(tabelas.keys())))


def calcular_imposto_progressivo(base_calculo: float, tabela: list[dict[str, float]]) -> float:
    """Calcula imposto pela tabela progressiva."""
    for faixa in tabela:
        if base_calculo <= faixa["limite"]:
            return max(0.0, base_calculo * faixa["aliquota"] - faixa["deducao"])
    return 0.0


def simular_regime_completo(
    rendimentos: float,
    inss: float,
    medicas: float,
    dependentes: int,
    tabela_ano: dict[str, Any],
) -> dict[str, Any]:
    """Simula regime completo (deduções reais)."""
    deducao_dep = dependentes * tabela_ano["deducao_dependente_anual"]
    inss_limitado = min(inss, tabela_ano["teto_inss_anual"])
    total_deducoes = inss_limitado + medicas + deducao_dep
    base = max(0.0, rendimentos - total_deducoes)
    imposto = calcular_imposto_progressivo(base, tabela_ano["tabela_anual"])
    return {
        "regime": "Completo",
        "rendimentos": rendimentos,
        "deducoes_inss": inss_limitado,
        "deducoes_medicas": medicas,
        "deducoes_dependentes": deducao_dep,
        "total_deducoes": total_deducoes,
        "base_calculo": base,
        "imposto_devido": imposto,
    }


def simular_regime_simplificado(
    rendimentos: float,
    tabela_ano: dict[str, Any],
) -> dict[str, Any]:
    """Simula regime simplificado (desconto padrão de 20%)."""
    desconto = min(
        rendimentos * tabela_ano["deducao_simplificada_pct"],
        tabela_ano["deducao_simplificada_limite"],
    )
    base = max(0.0, rendimentos - desconto)
    imposto = calcular_imposto_progressivo(base, tabela_ano["tabela_anual"])
    return {
        "regime": "Simplificado",
        "rendimentos": rendimentos,
        "desconto_padrao": desconto,
        "base_calculo": base,
        "imposto_devido": imposto,
    }


def simular(
    rendimentos: float,
    inss: float,
    medicas: float,
    impostos_pagos: float,
    dependentes: int = 0,
    ano: int = 2025,
) -> dict[str, Any]:
    """Simula ambos os regimes e recomenda o mais vantajoso."""
    tabela = carregar_tabela(ano)
    completo = simular_regime_completo(rendimentos, inss, medicas, dependentes, tabela)
    simplificado = simular_regime_simplificado(rendimentos, tabela)

    recomendado = (
        "Completo"
        if completo["imposto_devido"] <= simplificado["imposto_devido"]
        else "Simplificado"
    )
    economia = abs(completo["imposto_devido"] - simplificado["imposto_devido"])

    saldo_completo = completo["imposto_devido"] - impostos_pagos
    saldo_simplificado = simplificado["imposto_devido"] - impostos_pagos

    logger.info(
        "Simulação IRPF %d: recomendado=%s, economia=R$ %.2f",
        ano,
        recomendado,
        economia,
    )

    return {
        "completo": completo,
        "simplificado": simplificado,
        "recomendado": recomendado,
        "economia": economia,
        "impostos_pagos": impostos_pagos,
        "saldo_completo": saldo_completo,
        "saldo_simplificado": saldo_simplificado,
    }


# "O imposto é o preço que pagamos por uma sociedade civilizada." -- Oliver Wendell Holmes
