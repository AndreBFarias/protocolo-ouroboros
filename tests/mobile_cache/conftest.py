"""Fixtures comuns para os testes do pacote ``mobile_cache``."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import openpyxl
import pytest


def _escrever_daily(
    daily_dir: Path,
    data_obj: date,
    autor: str = "pessoa_a",
    humor: int = 4,
    energia: int = 3,
    ansiedade: int = 2,
    foco: int = 4,
    tipo: str = "humor",
    extras: dict[str, Any] | None = None,
) -> Path:
    """Escreve um daily .md com frontmatter YAML completo."""
    daily_dir.mkdir(parents=True, exist_ok=True)
    nome = f"{data_obj.isoformat()}.md"
    caminho = daily_dir / nome
    bloco = [
        "---",
        f"tipo: {tipo}",
        f"data: {data_obj.isoformat()}",
        f"autor: {autor}",
        f"humor: {humor}",
        f"energia: {energia}",
        f"ansiedade: {ansiedade}",
        f"foco: {foco}",
    ]
    if extras:
        for chave, valor in extras.items():
            bloco.append(f"{chave}: {valor}")
    bloco.append("---")
    bloco.append("")
    bloco.append("corpo livre.")
    caminho.write_text("\n".join(bloco), encoding="utf-8")
    return caminho


@pytest.fixture
def vault_temporario(tmp_path: Path) -> Path:
    """Cria estrutura minima de vault Mobile."""
    raiz = tmp_path / "vault"
    (raiz / "daily").mkdir(parents=True)
    (raiz / "inbox" / "mente" / "humor").mkdir(parents=True)
    return raiz


@pytest.fixture
def hoje_referencia() -> date:
    """Data de referencia fixa para isolar testes do relogio do CI."""
    return date(2026, 4, 29)


@pytest.fixture
def gerado_em_referencia() -> datetime:
    """Timestamp fixo para idempotencia em testes."""
    from datetime import timezone as tz

    return datetime(2026, 4, 29, 18, 0, 0, tzinfo=tz(timedelta(hours=-3)))


@pytest.fixture
def vault_com_dailies(
    vault_temporario: Path,
    hoje_referencia: date,
) -> Path:
    """Vault com 5 dailies seguidos terminando em hoje_referencia."""
    daily_dir = vault_temporario / "daily"
    for i in range(5):
        d = hoje_referencia - timedelta(days=i)
        _escrever_daily(daily_dir, d, autor="pessoa_a", humor=3 + (i % 3))
    return vault_temporario


def _criar_xlsx(
    destino: Path,
    transacoes: list[dict[str, Any]],
) -> Path:
    """Cria um XLSX consolidado mínimo (apenas aba `extrato`)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "extrato"
    colunas = [
        "data",
        "valor",
        "forma_pagamento",
        "local",
        "quem",
        "categoria",
        "classificacao",
        "banco_origem",
        "tipo",
        "mes_ref",
        "tag_irpf",
        "obs",
        "identificador",
    ]
    ws.append(colunas)
    for tx in transacoes:
        ws.append([tx.get(c) for c in colunas])
    wb.save(destino)
    wb.close()
    return destino


@pytest.fixture
def xlsx_factory(tmp_path: Path):
    """Factory para criar XLSX sintético com transações arbitrárias."""

    def _factory(transacoes: list[dict[str, Any]], nome: str = "ouroboros_test.xlsx") -> Path:
        destino = tmp_path / nome
        return _criar_xlsx(destino, transacoes)

    return _factory


@pytest.fixture
def daily_writer():
    """Atalho para escrever dailies em testes que precisam de controle fino."""
    return _escrever_daily
