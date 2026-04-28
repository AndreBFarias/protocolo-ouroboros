"""Testes do script `scripts/limpar_revisao_orfaos.py` -- Sprint AUDIT2-B4.

Cobre:
  - Detecta item_ids node_<id> orfaos (node não existe no grafo).
  - Preserva item_ids de paths (raw/...) e nodes ainda válidos.
  - Modo --dry-run não altera DB.
  - Modo --executar remove as marcacoes orfas e cria backup.
  - Idempotencia: 2a execução e no-op.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scripts import limpar_revisao_orfaos
from src.dashboard.paginas import revisor


@pytest.fixture()
def grafo_com_um_documento(tmp_path: Path) -> Path:
    """Grafo sintetico com node id=100 documento; ids 7383, 7490 NÃO existem."""
    destino = tmp_path / "grafo.sqlite"
    conn = sqlite3.connect(destino)
    conn.executescript(
        """
        CREATE TABLE node (
          id INTEGER PRIMARY KEY,
          tipo TEXT,
          nome_canonico TEXT,
          metadata TEXT DEFAULT '{}'
        );
        """
    )
    conn.execute("INSERT INTO node VALUES (100, 'documento', 'X', '{}')")
    conn.commit()
    conn.close()
    return destino


@pytest.fixture()
def revisao_com_orfaos(tmp_path: Path) -> Path:
    """DB com mix: 1 node válido (100), 2 orfaos (7383, 7490), 1 path raw."""
    caminho = tmp_path / "rev.sqlite"
    revisor.salvar_marcacao(caminho, "node_100", "data", ok=1, observacao="")
    revisor.salvar_marcacao(caminho, "node_7383", "data", ok=1, observacao="")
    revisor.salvar_marcacao(caminho, "node_7383", "valor", ok=1, observacao="")
    revisor.salvar_marcacao(caminho, "node_7490", "data", ok=1, observacao="")
    revisor.salvar_marcacao(caminho, "raw/_classificar/X.pdf", "data", ok=0, observacao="")
    return caminho


def test_listar_orfaos_detecta_node_inexistente(
    grafo_com_um_documento: Path, revisao_com_orfaos: Path
) -> None:
    orfaos = limpar_revisao_orfaos.listar_orfaos(grafo_com_um_documento, revisao_com_orfaos)
    ids = {item_id for item_id, _ in orfaos}
    assert ids == {"node_7383", "node_7490"}


def test_listar_orfaos_preserva_path_e_node_valido(
    grafo_com_um_documento: Path, revisao_com_orfaos: Path
) -> None:
    orfaos = limpar_revisao_orfaos.listar_orfaos(grafo_com_um_documento, revisao_com_orfaos)
    ids = {item_id for item_id, _ in orfaos}
    # node_100 válido não entra; raw/... também não.
    assert "node_100" not in ids
    assert "raw/_classificar/X.pdf" not in ids


def test_dry_run_nao_altera_db(
    grafo_com_um_documento: Path, revisao_com_orfaos: Path
) -> None:
    limpar_revisao_orfaos.main(
        [
            "--grafo-db",
            str(grafo_com_um_documento),
            "--revisao-db",
            str(revisao_com_orfaos),
        ]
    )
    m = revisor.carregar_marcacoes(revisao_com_orfaos)
    assert len(m) == 5  # nada removido


def test_executar_remove_orfaos_e_cria_backup(
    grafo_com_um_documento: Path, revisao_com_orfaos: Path
) -> None:
    backup = revisao_com_orfaos.with_suffix(revisao_com_orfaos.suffix + ".bak")
    assert not backup.exists()
    limpar_revisao_orfaos.main(
        [
            "--grafo-db",
            str(grafo_com_um_documento),
            "--revisao-db",
            str(revisao_com_orfaos),
            "--executar",
        ]
    )
    m = revisor.carregar_marcacoes(revisao_com_orfaos)
    item_ids = {x["item_id"] for x in m}
    assert "node_7383" not in item_ids
    assert "node_7490" not in item_ids
    assert "node_100" in item_ids  # válido preservado
    assert "raw/_classificar/X.pdf" in item_ids  # path preservado
    assert backup.exists()


def test_executar_idempotente(
    grafo_com_um_documento: Path, revisao_com_orfaos: Path
) -> None:
    args = [
        "--grafo-db",
        str(grafo_com_um_documento),
        "--revisao-db",
        str(revisao_com_orfaos),
        "--executar",
    ]
    limpar_revisao_orfaos.main(args)
    m1 = revisor.carregar_marcacoes(revisao_com_orfaos)
    limpar_revisao_orfaos.main(args)
    m2 = revisor.carregar_marcacoes(revisao_com_orfaos)
    assert len(m1) == len(m2)


# "Toda casa precisa de faxina depois da reforma." -- princípio do cleanup pos-reextracao
