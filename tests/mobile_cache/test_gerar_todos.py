"""Testes do orquestrador `gerar_todos` e do entry point CLI."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.mobile_cache import gerar_todos


def test_gerar_todos_produz_dois_caches(
    vault_temporario: Path,
    xlsx_factory,
    daily_writer,
    hoje_referencia: date,
) -> None:
    daily_writer(vault_temporario / "daily", hoje_referencia, autor="pessoa_a")
    xlsx = xlsx_factory(
        [
            {
                "data": hoje_referencia,
                "valor": 50.0,
                "forma_pagamento": "Pix",
                "local": "mercado",
                "quem": "pessoa_a",
                "categoria": "mercado",
                "classificacao": "Obrigatório",
                "banco_origem": "Itaú",
                "tipo": "Despesa",
                "mes_ref": hoje_referencia.strftime("%Y-%m"),
                "tag_irpf": None,
                "obs": "",
                "identificador": "id-1",
            }
        ]
    )

    paths = gerar_todos(
        vault_temporario,
        xlsx_path=xlsx,
        referencia=hoje_referencia,
    )
    assert len(paths) == 2
    nomes = sorted(p.name for p in paths)
    assert nomes == ["financas-cache.json", "humor-heatmap.json"]
    for p in paths:
        assert p.exists()
        payload = json.loads(p.read_text(encoding="utf-8"))
        assert payload["schema_version"] == 1


def test_cli_main_gera_caches(
    vault_temporario: Path,
    xlsx_factory,
    daily_writer,
    hoje_referencia: date,
    monkeypatch,
) -> None:
    daily_writer(vault_temporario / "daily", hoje_referencia, autor="pessoa_a")
    xlsx = xlsx_factory([])

    from src.mobile_cache.__main__ import main

    rc = main(
        [
            "--vault",
            str(vault_temporario),
            "--xlsx",
            str(xlsx),
        ]
    )
    assert rc == 0
    assert (vault_temporario / ".ouroboros" / "cache" / "humor-heatmap.json").exists()
    assert (vault_temporario / ".ouroboros" / "cache" / "financas-cache.json").exists()
