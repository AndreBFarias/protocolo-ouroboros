"""Testes do enriquecimento runtime de prazos com valor estimado.

Sprint UX-V-2.2.A. A função ``enriquecer_prazos_com_valor`` adiciona
``valor_estimado`` e ``origem_valor`` ao DataFrame de prazos cruzando
com extrato. Cobre os 3 caminhos canônicos:

  - ``"última fatura"`` (boletos recorrentes >= 2 ocorrências);
  - ``"histórico 12m"``  (média absoluta das despesas/impostos);
  - ``"sem dado"``       (sem cruzamento, mantém R$ 0,00).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from src.dashboard.paginas.pagamentos_valores import (
    ORIGEM_HISTORICO,
    ORIGEM_SEM_DADO,
    ORIGEM_ULTIMA_FATURA,
    enriquecer_prazos_com_valor,
)


def _prazos_basicos() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"conta": "Internet", "dia_vencimento": 10},
            {"conta": "Natação", "dia_vencimento": 10},
            {"conta": "Aluguel", "dia_vencimento": 20},
            {"conta": "Nubank", "dia_vencimento": 10},
        ]
    )


def _extrato_sintetico(hoje: date) -> pd.DataFrame:
    """Extrato com 3 padrões: categoria, boletos recorrentes, fora janela."""
    base = pd.Timestamp(hoje) - pd.Timedelta(days=30)
    return pd.DataFrame(
        [
            # Internet -- categoria casa, 2 lançamentos -> média
            {"data": base, "valor": 200.0, "tipo": "Despesa",
             "categoria": "Internet", "local": "TG BRASIL",
             "forma_pagamento": "Pix"},
            {"data": base + pd.Timedelta(days=30), "valor": 180.0,
             "tipo": "Despesa", "categoria": "Internet",
             "local": "TG BRASIL", "forma_pagamento": "Pix"},
            # Natação -- categoria + 2 boletos -> última fatura
            {"data": base, "valor": 100.0, "tipo": "Despesa",
             "categoria": "Natação", "local": "SESC",
             "forma_pagamento": "Boleto"},
            {"data": base + pd.Timedelta(days=30), "valor": 105.0,
             "tipo": "Despesa", "categoria": "Natação",
             "local": "SESC", "forma_pagamento": "Boleto"},
            # Nubank -- só Pix para pessoa, deve cair em "sem dado"
            {"data": base, "valor": 50.0, "tipo": "Despesa",
             "categoria": "Pessoal",
             "local": "Joao - Nubank Agência: 1 Conta: 123",
             "forma_pagamento": "Pix"},
            # Lançamento muito antigo, fora da janela -- ignorar
            {"data": pd.Timestamp(hoje) - pd.Timedelta(days=400),
             "valor": 999.0, "tipo": "Despesa",
             "categoria": "Aluguel", "local": "ANTIGO",
             "forma_pagamento": "Pix"},
        ]
    )


def test_enriquecer_adiciona_colunas_esperadas() -> None:
    hoje = date(2026, 5, 8)
    enriquecido = enriquecer_prazos_com_valor(
        _prazos_basicos(), _extrato_sintetico(hoje), hoje=hoje
    )
    assert "valor_estimado" in enriquecido.columns
    assert "origem_valor" in enriquecido.columns
    # Ordem e quantidade de linhas preservadas
    assert len(enriquecido) == 4
    assert list(enriquecido["conta"]) == ["Internet", "Natação", "Aluguel", "Nubank"]


def test_categoria_match_usa_media_absoluta() -> None:
    hoje = date(2026, 5, 8)
    enriquecido = enriquecer_prazos_com_valor(
        _prazos_basicos(), _extrato_sintetico(hoje), hoje=hoje
    )
    internet = enriquecido[enriquecido["conta"] == "Internet"].iloc[0]
    assert internet["origem_valor"] == ORIGEM_HISTORICO
    assert internet["valor_estimado"] == 190.0  # (200 + 180)/2


def test_boletos_recorrentes_usam_ultima_fatura() -> None:
    hoje = date(2026, 5, 8)
    enriquecido = enriquecer_prazos_com_valor(
        _prazos_basicos(), _extrato_sintetico(hoje), hoje=hoje
    )
    natacao = enriquecido[enriquecido["conta"] == "Natação"].iloc[0]
    assert natacao["origem_valor"] == ORIGEM_ULTIMA_FATURA
    assert natacao["valor_estimado"] == 105.0  # último boleto


def test_cartao_sem_fatura_real_cai_em_sem_dado() -> None:
    """Padrão (k): nome cartão (Nubank) sem 'fatura' no local => sem dado."""
    hoje = date(2026, 5, 8)
    enriquecido = enriquecer_prazos_com_valor(
        _prazos_basicos(), _extrato_sintetico(hoje), hoje=hoje
    )
    nubank = enriquecido[enriquecido["conta"] == "Nubank"].iloc[0]
    assert nubank["origem_valor"] == ORIGEM_SEM_DADO
    assert nubank["valor_estimado"] == 0.0


def test_sem_match_mantem_zero_e_sem_dado() -> None:
    hoje = date(2026, 5, 8)
    enriquecido = enriquecer_prazos_com_valor(
        _prazos_basicos(), _extrato_sintetico(hoje), hoje=hoje
    )
    aluguel = enriquecido[enriquecido["conta"] == "Aluguel"].iloc[0]
    # Único lançamento de Aluguel está fora da janela de 365 dias
    assert aluguel["origem_valor"] == ORIGEM_SEM_DADO
    assert aluguel["valor_estimado"] == 0.0


def test_prazos_vazio_retorna_dataframe_vazio() -> None:
    enriquecido = enriquecer_prazos_com_valor(
        pd.DataFrame(), _extrato_sintetico(date(2026, 5, 8))
    )
    assert enriquecido.empty


def test_prazos_sem_coluna_conta_nao_quebra() -> None:
    df = pd.DataFrame([{"dia_vencimento": 10}])
    enriquecido = enriquecer_prazos_com_valor(
        df, _extrato_sintetico(date(2026, 5, 8))
    )
    assert "valor_estimado" in enriquecido.columns
    assert enriquecido.iloc[0]["valor_estimado"] == 0.0
    assert enriquecido.iloc[0]["origem_valor"] == ORIGEM_SEM_DADO


def test_extrato_vazio_resulta_em_sem_dado_para_tudo() -> None:
    enriquecido = enriquecer_prazos_com_valor(
        _prazos_basicos(), pd.DataFrame()
    )
    assert all(enriquecido["origem_valor"] == ORIGEM_SEM_DADO)
    assert (enriquecido["valor_estimado"] == 0.0).all()


# "A medida certa nasce da observação repetida, não do palpite." -- Aristóteles
