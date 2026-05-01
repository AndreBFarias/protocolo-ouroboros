"""Fixtures e helpers compartilhados para os testes."""

from datetime import date
from typing import Any

import pytest


def _transacao(
    data_t: date = date(2026, 3, 15),
    valor: float = 50.0,
    local: str = "Padaria X",
    banco: str = "Itaú",
    tipo: str = "Despesa",
    quem: str = "pessoa_a",
    forma: str = "Débito",
    mes_ref: str | None = None,
    identificador: str | None = None,
    descricao_original: str | None = None,
    **extras: Any,
) -> dict:
    """Monta um dict no formato normalizado usado pelo pipeline."""
    base = {
        "data": data_t,
        "valor": valor,
        "forma_pagamento": forma,
        "local": local,
        "quem": quem,
        "categoria": None,
        "classificacao": None,
        "banco_origem": banco,
        "tipo": tipo,
        "mes_ref": mes_ref or data_t.strftime("%Y-%m"),
        "tag_irpf": None,
        "obs": None,
        "_identificador": identificador,
        "_descricao_original": descricao_original or local,
    }
    base.update(extras)
    return base


@pytest.fixture
def transacao():
    """Retorna uma factory de transações."""
    return _transacao


@pytest.fixture
def transacoes_basicas():
    """Conjunto mínimo com receita, despesa e transferência."""
    return [
        _transacao(valor=2000.0, tipo="Receita", local="Salário G4F", banco="Itaú"),
        _transacao(valor=50.0, local="Padaria X"),
        _transacao(valor=500.0, local="Aluguel XYZ", mes_ref="2026-03"),
    ]


# "Ao que sabe, cada princípio é uma porta para outros." -- Aristóteles
