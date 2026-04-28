"""Testes de scripts/normalizar_path_relativo.py -- Sprint AUDIT2-B1.

Cobre:
  - Detecta nodes com `arquivo_origem` absoluto.
  - Aplica `to_relativo` quando dentro do _RAIZ_REPO.
  - Idempotente: 2a execução é no-op.
  - Invariante: depois de --executar, 0 nodes com path absoluto.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts import normalizar_path_relativo


@pytest.fixture()
def grafo_misto(tmp_path: Path) -> Path:
    """Grafo com 2 nodes: 1 com path absoluto, 1 com relativo."""
    destino = tmp_path / "grafo.sqlite"
    conn = sqlite3.connect(destino)
    conn.executescript(
        """
        CREATE TABLE node (
          id INTEGER PRIMARY KEY,
          tipo TEXT NOT NULL,
          nome_canonico TEXT NOT NULL,
          metadata TEXT DEFAULT '{}',
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    raiz = normalizar_path_relativo._RAIZ
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            1,
            "documento",
            "X",
            json.dumps(
                {
                    "tipo_documento": "das_parcsn_andre",
                    "arquivo_origem": str(raiz / "data" / "raw" / "fake.pdf"),
                }
            ),
        ),
    )
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            2,
            "documento",
            "Y",
            json.dumps(
                {
                    "tipo_documento": "holerite",
                    "arquivo_origem": "data/raw/holerite_existente.pdf",
                }
            ),
        ),
    )
    conn.commit()
    conn.close()
    return destino


def test_listar_detecta_so_absolutos(grafo_misto: Path) -> None:
    nodes = normalizar_path_relativo.listar_nodes_path_absoluto(grafo_misto)
    ids = {nid for nid, _, _ in nodes}
    assert ids == {1}  # so o absoluto


def test_normalizar_atualiza_absoluto_para_relativo(grafo_misto: Path) -> None:
    contagens = normalizar_path_relativo.normalizar(grafo_misto)
    assert contagens["atualizados"] == 1
    assert contagens["fora_repo"] == 0
    # Verifica que ficou relativo
    conn = sqlite3.connect(grafo_misto)
    try:
        row = conn.execute(
            "SELECT json_extract(metadata, '$.arquivo_origem') FROM node WHERE id=1"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "data/raw/fake.pdf"


def test_idempotente(grafo_misto: Path) -> None:
    normalizar_path_relativo.normalizar(grafo_misto)
    contagens = normalizar_path_relativo.normalizar(grafo_misto)
    assert contagens["detectados"] == 0  # nada mais a fazer
    assert contagens["atualizados"] == 0


def test_dry_run_nao_altera(grafo_misto: Path) -> None:
    normalizar_path_relativo.main(
        ["--grafo-db", str(grafo_misto)],
    )
    nodes_apos = normalizar_path_relativo.listar_nodes_path_absoluto(grafo_misto)
    assert len(nodes_apos) == 1  # ainda detectavel


def test_invariante_pos_executar(grafo_misto: Path) -> None:
    normalizar_path_relativo.main(
        ["--grafo-db", str(grafo_misto), "--executar"],
    )
    nodes_apos = normalizar_path_relativo.listar_nodes_path_absoluto(grafo_misto)
    assert nodes_apos == []  # invariante: 0 absolutos


# "Toda casa precisa de endereco no formato certo." -- princípio do path canonico
