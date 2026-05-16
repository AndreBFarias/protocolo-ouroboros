"""Fixtures e helpers compartilhados para os testes."""

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# Raiz da fixture sintetica usada por testes do cluster Mobile/Bem-estar.
_FIXTURE_VAULT_SINTETICO = (
    Path(__file__).resolve().parent / "fixtures" / "vault_sintetico"
)


@pytest.fixture(autouse=True, scope="session")
def _regenerar_caches_vault_sintetico() -> None:
    """Regenera os 10 caches do vault_sintetico antes dos testes da sessao.

    Sprint META-FIXTURES-CACHE-IGNORE (2026-05-15): os caches em
    ``tests/fixtures/vault_sintetico/.ouroboros/cache/*.json`` (excluindo
    ``memorias.json``, que vem do app Mobile externo) são gitignored.
    Esta fixture regenera-os via ``varrer_tudo`` com ``gerado_em`` fixo
    para garantir reprodutibilidade em CI e working tree limpo.

    Vault inexistente ou estrutura incompleta não quebra: parsers têm
    fallback graceful que produz cache vazio sem crash.
    """
    if not _FIXTURE_VAULT_SINTETICO.exists():
        return
    # Import tardio: evita custo de import quando subset de testes não
    # toca caches Mobile (ex.: rodar apenas tests/test_xml_nfe.py).
    from src.mobile_cache.varrer_vault import varrer_tudo

    gerado_em_fixo = datetime(2026, 1, 1, tzinfo=timezone.utc)
    varrer_tudo(
        _FIXTURE_VAULT_SINTETICO,
        gerado_em=gerado_em_fixo,
        incluir_humor=True,
    )


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
