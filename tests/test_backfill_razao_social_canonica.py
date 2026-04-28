"""Testes Sprint AUDIT2-RAZAO-SOCIAL-HOLERITE.

Cobre:
  - resolver_razao_social_canonica devolve oficial para G4F/INFOBASE.
  - Sigla não mapeada cai para upper() sem CNPJ.
  - backfill atualiza node holerite + node fornecedor associado.
  - Idempotencia: 2a execução é no-op.
  - Dry-run não altera DB.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts import backfill_razao_social_canonica
from src.extractors.contracheque_pdf import resolver_razao_social_canonica


class TestResolverRazaoSocialCanonica:
    def test_g4f_devolve_canonico(self) -> None:
        razao, cnpj = resolver_razao_social_canonica("G4F")
        assert razao == "G4F SOLUCOES CORPORATIVAS LTDA"
        assert cnpj == "06146852000118"

    def test_infobase_devolve_canonico_sem_cnpj(self) -> None:
        razao, cnpj = resolver_razao_social_canonica("INFOBASE")
        assert razao == "INFOBASE CONSULTORIA E INFORMATICA LTDA"
        assert cnpj == ""

    def test_sigla_nao_mapeada_devolve_upper_sem_cnpj(self) -> None:
        razao, cnpj = resolver_razao_social_canonica("Empresa Nova")
        assert razao == "EMPRESA NOVA"
        assert cnpj == ""

    def test_sigla_vazia_devolve_vazio(self) -> None:
        razao, cnpj = resolver_razao_social_canonica("")
        assert razao == ""
        assert cnpj == ""


@pytest.fixture()
def grafo_holerites(tmp_path: Path) -> Path:
    """Grafo com 2 holerites apontando para 2 fornecedores siglas curtas."""
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
        CREATE TABLE edge (
          id INTEGER PRIMARY KEY,
          src_id INTEGER NOT NULL,
          dst_id INTEGER NOT NULL,
          tipo TEXT NOT NULL
        );
        """
    )
    # Holerite G4F (sigla curta)
    conn.execute(
        "INSERT INTO node VALUES (1, 'documento', 'H1', ?, CURRENT_TIMESTAMP)",
        (json.dumps({"tipo_documento": "holerite", "razao_social": "G4F"}),),
    )
    # Fornecedor G4F
    conn.execute(
        "INSERT INTO node VALUES (10, 'fornecedor', 'F-G4F', ?, CURRENT_TIMESTAMP)",
        (json.dumps({"razao_social": "G4F"}),),
    )
    conn.execute("INSERT INTO edge (src_id, dst_id, tipo) VALUES (1, 10, 'fornecido_por')")

    # Holerite INFOBASE
    conn.execute(
        "INSERT INTO node VALUES (2, 'documento', 'H2', ?, CURRENT_TIMESTAMP)",
        (json.dumps({"tipo_documento": "holerite", "razao_social": "INFOBASE"}),),
    )
    conn.execute(
        "INSERT INTO node VALUES (20, 'fornecedor', 'F-INFOBASE', ?, CURRENT_TIMESTAMP)",
        (json.dumps({"razao_social": "INFOBASE"}),),
    )
    conn.execute("INSERT INTO edge (src_id, dst_id, tipo) VALUES (2, 20, 'fornecido_por')")
    conn.commit()
    conn.close()
    return destino


def test_backfill_atualiza_holerites(grafo_holerites: Path) -> None:
    contagens = backfill_razao_social_canonica.backfill(grafo_holerites, dry_run=False)
    assert contagens["atualizados"] == 2
    assert contagens["fornecedores_atualizados"] == 2

    conn = sqlite3.connect(grafo_holerites)
    try:
        for nid, esperado in [
            (1, "G4F SOLUCOES CORPORATIVAS LTDA"),
            (2, "INFOBASE CONSULTORIA E INFORMATICA LTDA"),
            (10, "G4F SOLUCOES CORPORATIVAS LTDA"),
            (20, "INFOBASE CONSULTORIA E INFORMATICA LTDA"),
        ]:
            r = conn.execute(
                "SELECT json_extract(metadata, '$.razao_social') FROM node WHERE id=?",
                (nid,),
            ).fetchone()
            assert r[0] == esperado
    finally:
        conn.close()


def test_backfill_idempotente(grafo_holerites: Path) -> None:
    backfill_razao_social_canonica.backfill(grafo_holerites, dry_run=False)
    c2 = backfill_razao_social_canonica.backfill(grafo_holerites, dry_run=False)
    assert c2["atualizados"] == 0
    assert c2["fornecedores_atualizados"] == 0


def test_backfill_dry_run_nao_altera(grafo_holerites: Path) -> None:
    backfill_razao_social_canonica.backfill(grafo_holerites, dry_run=True)
    conn = sqlite3.connect(grafo_holerites)
    try:
        r = conn.execute(
            "SELECT json_extract(metadata, '$.razao_social') FROM node WHERE id=1"
        ).fetchone()
    finally:
        conn.close()
    assert r[0] == "G4F"  # ainda sigla curta


# "Razao social canonica casa o linker; sigla so serve display." -- princípio AUDIT2-A4
