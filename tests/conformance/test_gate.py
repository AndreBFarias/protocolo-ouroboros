"""Testes do gate 4-way conformance (Sprint ANTI-MIGUE-01).

Cobre:
  1. Schema criado idempotentemente.
  2. Gate negado quando 0 amostras.
  3. Gate negado quando 2 amostras (limiar = 3).
  4. Gate liberado quando 3 amostras 4-way verdes.
  5. Amostra com 1 dimensão falha NÃO conta como verde.
  6. Idempotência: re-registrar mesma amostra atualiza, não duplica.
  7. CLI exit code via main().
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conformance.gate import (
    LIMIAR_AMOSTRAS_4WAY,
    contar_amostras_verdes,
    inicializar_db,
    main,
    registrar_amostra,
    validar,
)


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "conformance.sqlite"


def test_inicializar_db_cria_tabela(db: Path):
    inicializar_db(db)
    assert db.exists()
    import sqlite3

    with sqlite3.connect(db) as conn:
        tabela = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conformance_amostras'"
        ).fetchone()
    assert tabela is not None


def test_inicializar_db_eh_idempotente(db: Path):
    inicializar_db(db)
    inicializar_db(db)


def test_gate_negado_sem_amostras(db: Path):
    inicializar_db(db)
    rc = validar(db, "cnh")
    assert rc == 1


def test_gate_negado_com_2_amostras(db: Path):
    for i in range(2):
        registrar_amostra(
            db,
            tipo="cnh",
            item_id=f"doc_{i}",
            etl_ok=True,
            opus_ok=True,
            grafo_ok=True,
            humano_ok=True,
        )
    rc = validar(db, "cnh")
    assert rc == 1
    assert contar_amostras_verdes(db, "cnh") == 2


def test_gate_liberado_com_3_amostras_4way_verdes(db: Path):
    for i in range(3):
        registrar_amostra(
            db,
            tipo="cnh",
            item_id=f"doc_{i}",
            etl_ok=True,
            opus_ok=True,
            grafo_ok=True,
            humano_ok=True,
        )
    rc = validar(db, "cnh")
    assert rc == 0
    assert contar_amostras_verdes(db, "cnh") == 3


def test_amostra_com_1_dimensao_falha_nao_conta(db: Path):
    registrar_amostra(
        db,
        tipo="cnh",
        item_id="doc_a",
        etl_ok=True,
        opus_ok=False,
        grafo_ok=True,
        humano_ok=True,
    )
    assert contar_amostras_verdes(db, "cnh") == 0
    rc = validar(db, "cnh")
    assert rc == 1


def test_registrar_amostra_eh_idempotente_via_unique(db: Path):
    registrar_amostra(
        db,
        tipo="cnh",
        item_id="doc_x",
        etl_ok=True,
        opus_ok=True,
        grafo_ok=True,
        humano_ok=True,
    )
    registrar_amostra(
        db,
        tipo="cnh",
        item_id="doc_x",
        etl_ok=False,
        opus_ok=True,
        grafo_ok=True,
        humano_ok=True,
    )
    assert contar_amostras_verdes(db, "cnh") == 0


def test_tipos_isolados(db: Path):
    for i in range(3):
        registrar_amostra(
            db,
            tipo="cnh",
            item_id=f"doc_{i}",
            etl_ok=True,
            opus_ok=True,
            grafo_ok=True,
            humano_ok=True,
        )
    assert validar(db, "cnh") == 0
    assert validar(db, "rg") == 1


def test_cli_main_retorna_exit_code(db: Path):
    for i in range(3):
        registrar_amostra(
            db,
            tipo="cnh",
            item_id=f"doc_{i}",
            etl_ok=True,
            opus_ok=True,
            grafo_ok=True,
            humano_ok=True,
        )
    rc_ok = main(["cnh", "--db", str(db)])
    assert rc_ok == 0
    rc_fail = main(["rg", "--db", str(db)])
    assert rc_fail == 1


def test_limiar_customizavel(db: Path):
    registrar_amostra(
        db,
        tipo="cnh",
        item_id="doc_1",
        etl_ok=True,
        opus_ok=True,
        grafo_ok=True,
        humano_ok=True,
    )
    assert validar(db, "cnh", limiar=1) == 0
    assert validar(db, "cnh", limiar=LIMIAR_AMOSTRAS_4WAY) == 1


# "A medida sem padrão é palpite com etiqueta." -- princípio do gate empírico
