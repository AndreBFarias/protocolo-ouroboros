"""Testes UX-RD-07 — Contas e Pagamentos reescritos.

Cobertura mínima do spec:
1. Cards de contas renderizam com saldo (HTML contém banco + valor R$)
2. Utilização >=80% pinta com classe ``d7-regredindo``
3. Utilização >=100% pinta com classe ``accent-red``
4. Snapshot de data dinâmica (não hardcoded "2023") -- usa mtime do XLSX
5. Calendário de pagamentos tem 14 cells (CAL_DIAS)
6. Lista de vencimentos retorna ordenada por data ASC

Funções puras testáveis sem Streamlit.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.dashboard.paginas.contas import (
    BANCOS_CONTAS,
    LIMITE_ALERTA,
    LIMITE_REGREDINDO,
    _card_banco_html,
    _card_cartao_html,
    aviso_snapshot_html,
    calcular_data_snapshot,
    calcular_saldo_por_banco,
    calcular_utilizacao_cartoes,
    classe_utilizacao_d7,
    cor_utilizacao_d7,
)
from src.dashboard.paginas.pagamentos import (
    CAL_DIAS,
    calcular_kpis_pagamentos,
    construir_eventos_calendario,
    gerar_celulas_calendario,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def extrato_minimo() -> pd.DataFrame:
    """Extrato com 3 bancos + 1 cartão de crédito 100% utilizado."""
    hoje = pd.Timestamp.today().normalize()
    rows: list[dict[str, object]] = []
    # Itaú (corrente positivo)
    for d in range(1, 8):
        rows.append(
            {
                "data": hoje - pd.Timedelta(days=d),
                "valor": 500.0 if d % 2 == 0 else -120.0,
                "banco_origem": "Itaú",
                "forma_pagamento": "Pix",
                "categoria": "Misto",
                "classificacao": "N/A",
                "tipo": "Despesa",
                "quem": "André",
                "mes_ref": hoje.strftime("%Y-%m"),
                "local": "X",
            }
        )
    # Nubank (corrente)
    for d in range(1, 5):
        rows.append(
            {
                "data": hoje - pd.Timedelta(days=d * 2),
                "valor": 300.0,
                "banco_origem": "Nubank",
                "forma_pagamento": "Pix",
                "categoria": "Salário",
                "classificacao": "N/A",
                "tipo": "Receita",
                "quem": "André",
                "mes_ref": hoje.strftime("%Y-%m"),
                "local": "X",
            }
        )
    # C6 cartão crédito - várias compras no mês corrente
    inicio = hoje.replace(day=1)
    for d in range(0, 10):
        rows.append(
            {
                "data": inicio + pd.Timedelta(days=d),
                "valor": -150.0,
                "banco_origem": "C6",
                "forma_pagamento": "Crédito",
                "categoria": "Mercado",
                "classificacao": "Obrigatório",
                "tipo": "Despesa",
                "quem": "André",
                "mes_ref": hoje.strftime("%Y-%m"),
                "local": "X",
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def prazos_minimo() -> pd.DataFrame:
    """3 prazos recorrentes com dias_vencimento variados."""
    hoje = date.today()
    return pd.DataFrame(
        [
            {
                "conta": "Aluguel",
                "dia_vencimento": ((hoje + timedelta(days=2)).day),
                "banco_pagamento": "Itaú",
                "auto_debito": False,
            },
            {
                "conta": "Internet",
                "dia_vencimento": ((hoje + timedelta(days=5)).day),
                "banco_pagamento": "C6",
                "auto_debito": True,
            },
            {
                "conta": "Plano de saúde",
                "dia_vencimento": ((hoje + timedelta(days=10)).day),
                "banco_pagamento": "Itaú",
                "auto_debito": True,
            },
        ]
    )


# ---------------------------------------------------------------------------
# Testes Contas
# ---------------------------------------------------------------------------


def test_card_banco_renderiza_com_saldo(extrato_minimo: pd.DataFrame) -> None:
    """Teste #1 — cards de contas renderizam com saldo formatado em R$."""
    info = calcular_saldo_por_banco(
        extrato_minimo, [b[0] for b in BANCOS_CONTAS]
    )
    assert "Itaú" in info, "Itaú deve aparecer no resumo por banco"
    assert "Nubank" in info

    html = _card_banco_html(
        "Itaú", "IT", "destaque", "Corrente · CC", info["Itaú"]
    )
    assert "Itaú" in html
    assert "R$" in html, "Cards devem mostrar valores monetários em R$"
    assert "page-header" not in html, "Card é fragmento, não a página inteira"


def test_utilizacao_acima_de_80_pct_pinta_d7_regredindo() -> None:
    """Teste #2 — utilização >=80% mapeia para classe ``d7-regredindo``."""
    assert classe_utilizacao_d7(LIMITE_REGREDINDO) == "d7-regredindo"
    assert classe_utilizacao_d7(0.85) == "d7-regredindo"
    assert classe_utilizacao_d7(0.99) == "d7-regredindo"

    cartao = {
        "banco": "C6",
        "limite": 1000.0,
        "usado": 850.0,
        "disponivel": 150.0,
        "percentual": 0.85,
        "classe_d7": "d7-regredindo",
    }
    html = _card_cartao_html(cartao)
    assert "d7-regredindo" in html, "Classe CSS D7 regredindo presente no HTML"
    assert cor_utilizacao_d7(0.85).lower() in html.lower()


def test_utilizacao_100_pct_ou_mais_pinta_accent_red() -> None:
    """Teste #3 — utilização >=100% mapeia para classe ``accent-red``."""
    assert classe_utilizacao_d7(LIMITE_ALERTA) == "accent-red"
    assert classe_utilizacao_d7(1.20) == "accent-red"

    cartao = {
        "banco": "Nubank",
        "limite": 1000.0,
        "usado": 1100.0,
        "disponivel": 0.0,
        "percentual": 1.10,
        "classe_d7": "accent-red",
    }
    html = _card_cartao_html(cartao)
    assert "accent-red" in html


def test_snapshot_data_dinamica_via_mtime(tmp_path: Path) -> None:
    """Teste #4 — aviso de snapshot mostra DD/MM/YYYY do mtime, sem 2023."""
    fake_xlsx = tmp_path / "ouroboros_2026.xlsx"
    fake_xlsx.write_text("dummy")
    # Setamos mtime para 15/03/2024 12:00 (meio-dia local, longe de bordas
    # de fuso para qualquer TZ entre UTC-12 e UTC+12).
    from datetime import datetime as _dt

    alvo = _dt(2024, 3, 15, 12, 0, 0)
    ts = alvo.timestamp()
    os.utime(fake_xlsx, (ts, ts))

    data_str = calcular_data_snapshot(fake_xlsx)
    assert data_str == "15/03/2024", f"esperava 15/03/2024, got {data_str}"

    aviso = aviso_snapshot_html(fake_xlsx)
    assert "15/03/2024" in aviso
    assert "2023" not in aviso, "Aviso não pode mais ser hardcoded em 2023"

    # Caso XLSX inexistente: fallback gracioso, sem mentir data
    aviso_vazio = aviso_snapshot_html(tmp_path / "nao-existe.xlsx").lower()
    fallback_ok = (
        "vazio" in aviso_vazio
        or "indisponível" in aviso_vazio
        or "atualização manual" in aviso_vazio
    )
    assert fallback_ok


def test_calculo_utilizacao_cartoes_inclui_classe_d7(
    extrato_minimo: pd.DataFrame,
) -> None:
    """Teste extra — calcular_utilizacao_cartoes anota classe D7 por linha."""
    cartoes = calcular_utilizacao_cartoes(extrato_minimo)
    assert cartoes, "C6 cartão deveria aparecer"
    c6 = next((c for c in cartoes if c["banco"] == "C6"), None)
    assert c6 is not None
    assert "classe_d7" in c6
    assert c6["classe_d7"] in {
        "d7-graduado",
        "d7-calibracao",
        "d7-regredindo",
        "accent-red",
    }


# ---------------------------------------------------------------------------
# Testes Pagamentos
# ---------------------------------------------------------------------------


def test_calendario_tem_14_cells(prazos_minimo: pd.DataFrame) -> None:
    """Teste #5 — gerar_celulas_calendario retorna exatamente 14 cells."""
    eventos = construir_eventos_calendario(
        prazos_minimo, pd.DataFrame(), hoje=date(2026, 5, 1)
    )
    celulas = gerar_celulas_calendario(eventos, hoje=date(2026, 5, 1))
    assert len(celulas) == CAL_DIAS == 14
    # Primeira cell é hoje
    assert celulas[0]["is_today"] is True
    assert celulas[0]["data"] == date(2026, 5, 1)
    # Última cell é hoje + 13 dias
    assert celulas[-1]["data"] == date(2026, 5, 14)


def test_lista_vencimentos_ordenada_por_data_asc(
    prazos_minimo: pd.DataFrame,
) -> None:
    """Teste #6 — eventos retornados em ordem crescente de data."""
    hoje = date(2026, 5, 1)
    # forçamos prazos com dias específicos: dia 3, 6, 11
    prazos = pd.DataFrame(
        [
            {
                "conta": "C",
                "dia_vencimento": 11,
                "banco_pagamento": "Itaú",
                "auto_debito": False,
            },
            {
                "conta": "A",
                "dia_vencimento": 3,
                "banco_pagamento": "Itaú",
                "auto_debito": False,
            },
            {
                "conta": "B",
                "dia_vencimento": 6,
                "banco_pagamento": "C6",
                "auto_debito": True,
            },
        ]
    )
    eventos = construir_eventos_calendario(prazos, pd.DataFrame(), hoje=hoje)
    datas = [ev["data"] for ev in eventos]
    assert datas == sorted(datas), f"esperado ordenado, got {datas}"
    assert [ev["conta"] for ev in eventos] == ["A", "B", "C"]


def test_kpis_pagamentos_em_atraso_acumula_valor() -> None:
    """KPI ``em_atraso`` soma valor de eventos marcados ``atraso=True``."""
    eventos: list[dict[str, object]] = [
        {
            "data": date(2026, 5, 1),
            "valor": 148.0,
            "tipo": "late",
            "atraso": True,
            "auto_debito": False,
        },
        {
            "data": date(2026, 5, 5),
            "valor": 1280.0,
            "tipo": "fix",
            "atraso": False,
            "auto_debito": False,
        },
    ]
    kpis = calcular_kpis_pagamentos(eventos, hoje=date(2026, 5, 1))
    assert kpis["em_atraso"] == 148.0
    assert kpis["a_pagar_mes"] == 148.0 + 1280.0
    assert kpis["fixos"] == 1


# "A medida do tempo se faz contra a parede." -- adaptado de Drummond
