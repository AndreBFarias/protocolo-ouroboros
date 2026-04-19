"""Módulo de projeção financeira com cenários baseados em dados reais."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("projecoes")

LIQUIDO_INFOBASE: float = 7442.0
MESES_PROJECAO: int = 12
CAMINHO_METAS: Path = Path(__file__).resolve().parents[2] / "mappings" / "metas.yaml"

_FALLBACK_RESERVA: float = 27000.0
_FALLBACK_APE: float = 50000.0


def _carregar_valores_metas() -> tuple[float, float]:
    """Carrega valores alvo de metas do YAML. Retorna (reserva, apê) com fallback."""
    try:
        if CAMINHO_METAS.exists():
            with CAMINHO_METAS.open("r", encoding="utf-8") as f:
                dados = yaml.safe_load(f)
            metas = dados.get("metas", [])
            reserva = _FALLBACK_RESERVA
            ape = _FALLBACK_APE
            for meta in metas:
                nome = meta.get("nome", "").lower()
                if "reserva" in nome and "emergência" in nome:
                    reserva = float(meta.get("valor_alvo", _FALLBACK_RESERVA))
                elif "apartamento" in nome or "entrada" in nome:
                    ape = float(meta.get("valor_alvo", _FALLBACK_APE))
            return reserva, ape
    except Exception as err:
        logger.warning("Erro ao carregar metas: %s. Usando fallback.", err)
    return _FALLBACK_RESERVA, _FALLBACK_APE


VALOR_RESERVA_EMERGENCIA, VALOR_ENTRADA_APE = _carregar_valores_metas()


def _ultimos_n_meses(transacoes: list[dict], n: int = 3) -> list[dict]:
    """Filtra transações dos últimos N meses com dados disponíveis."""
    meses_disponiveis: set[str] = set()
    for t in transacoes:
        mes = t.get("mes_ref", "")
        if mes:
            meses_disponiveis.add(mes)

    meses_ordenados = sorted(meses_disponiveis, reverse=True)
    meses_selecionados = meses_ordenados[:n]

    return [t for t in transacoes if t.get("mes_ref") in meses_selecionados]


def _calcular_medias(transacoes: list[dict], n_meses: int = 3) -> dict[str, float]:
    """Calcula médias mensais de receita, despesa e saldo."""
    recentes = _ultimos_n_meses(transacoes, n_meses)

    if not recentes:
        return {"receita_media": 0.0, "despesa_media": 0.0, "saldo_medio": 0.0}

    meses_unicos = {t.get("mes_ref") for t in recentes if t.get("mes_ref")}
    n_real = len(meses_unicos) or 1

    receita_total: float = 0.0
    despesa_total: float = 0.0

    for t in recentes:
        tipo = t.get("tipo", "")
        if tipo == "Transferência Interna":
            continue
        valor = t.get("valor", 0.0)
        if tipo == "Receita":
            receita_total += valor
        elif tipo in ("Despesa", "Imposto"):
            despesa_total += valor

    receita_media = receita_total / n_real
    despesa_media = despesa_total / n_real
    saldo_medio = receita_media - despesa_media

    return {
        "receita_media": round(receita_media, 2),
        "despesa_media": round(despesa_media, 2),
        "saldo_medio": round(saldo_medio, 2),
    }


def meses_ate_objetivo(saldo_mensal: float, objetivo: float, atual: float = 0.0) -> int | None:
    """Calcula quantos meses até atingir um objetivo financeiro.

    Retorna None se saldo_mensal for <= 0 (inalcançável).
    """
    if saldo_mensal <= 0:
        return None

    faltante = objetivo - atual
    if faltante <= 0:
        return 0

    import math

    return math.ceil(faltante / saldo_mensal)


def _projecao_acumulada(
    saldo_mensal: float,
    patrimonio_atual: float,
    meses: int = MESES_PROJECAO,
) -> list[dict[str, Any]]:
    """Gera lista de saldos acumulados projetados mês a mês."""
    hoje = date.today()
    projecao: list[dict[str, Any]] = []
    acumulado = patrimonio_atual

    for i in range(1, meses + 1):
        mes_futuro = hoje + timedelta(days=30 * i)
        acumulado += saldo_mensal
        projecao.append(
            {
                "mes": mes_futuro.strftime("%Y-%m"),
                "indice": i,
                "acumulado": round(acumulado, 2),
            }
        )

    return projecao


def projetar_cenarios(transacoes: list[dict]) -> dict[str, Any]:
    """Calcula projeções financeiras baseadas nos dados reais.

    Retorna dicionário com três cenários e métricas derivadas:
    - Cenário Atual: mantém ritmo atual de receita/despesa.
    - Cenário Pós-Infobase: receita reduzida em R$ 7.442 (líquido).
    - Cenário Meta Apartamento: tempo até acumular R$ 50.000.
    """
    medias = _calcular_medias(transacoes)
    receita_media = medias["receita_media"]
    despesa_media = medias["despesa_media"]
    saldo_medio = medias["saldo_medio"]

    saldo_pos_infobase = (receita_media - LIQUIDO_INFOBASE) - despesa_media

    meses_reserva = meses_ate_objetivo(saldo_medio, VALOR_RESERVA_EMERGENCIA)
    meses_ape = meses_ate_objetivo(saldo_medio, VALOR_ENTRADA_APE)

    meses_reserva_pos = meses_ate_objetivo(saldo_pos_infobase, VALOR_RESERVA_EMERGENCIA)
    meses_ape_pos = meses_ate_objetivo(saldo_pos_infobase, VALOR_ENTRADA_APE)

    projecao_atual = _projecao_acumulada(saldo_medio, 0.0)
    projecao_pos = _projecao_acumulada(saldo_pos_infobase, 0.0)

    resultado: dict[str, Any] = {
        "receita_media": receita_media,
        "despesa_media": despesa_media,
        "saldo_medio": saldo_medio,
        "cenario_atual": {
            "nome": "Ritmo Atual",
            "saldo_mensal": saldo_medio,
            "meses_ate_reserva_emergencia": meses_reserva,
            "meses_ate_entrada_ape": meses_ape,
            "projecao_12_meses": projecao_atual,
        },
        "cenario_pos_infobase": {
            "nome": "Pós-Infobase",
            "saldo_mensal": round(saldo_pos_infobase, 2),
            "meses_ate_reserva_emergencia": meses_reserva_pos,
            "meses_ate_entrada_ape": meses_ape_pos,
            "projecao_12_meses": projecao_pos,
        },
        "cenario_meta_ape": {
            "nome": "Meta Apartamento",
            "valor_alvo": VALOR_ENTRADA_APE,
            "meses_ate_entrada_ape": meses_ape,
            "economia_necessaria_12m": round(VALOR_ENTRADA_APE / 12, 2),
            "economia_necessaria_24m": round(VALOR_ENTRADA_APE / 24, 2),
        },
        "projecao_12_meses": projecao_atual,
    }

    logger.info(
        "Projeções calculadas: saldo médio R$ %.2f, reserva em %s meses",
        saldo_medio,
        meses_reserva if meses_reserva is not None else "N/A",
    )

    return resultado


def projetar_com_economia(
    transacoes: list[dict],
    economia_extra: float,
) -> list[dict[str, Any]]:
    """Recalcula projeção com economia mensal adicional definida pelo usuário."""
    medias = _calcular_medias(transacoes)
    saldo_ajustado = medias["saldo_medio"] + economia_extra
    return _projecao_acumulada(saldo_ajustado, 0.0)


# "O dinheiro é um servo excelente, mas um mestre terrível." -- P.T. Barnum
