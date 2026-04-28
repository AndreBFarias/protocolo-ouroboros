"""Testes Sprint AUDIT2-METADATA-PESSOA-CANONICA.

Cobre:
  - `_inferir_pessoa_canonica` por contribuinte ANDRE/VITORIA, path,
    e fallback casal.
  - `backfill` aplica em nodes existentes, idempotente, dry-run não altera.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts import backfill_metadata_pessoa
from src.graph.ingestor_documento import _inferir_pessoa_canonica


class TestInferirPessoaCanonica:
    def test_contribuinte_andre_devolve_andre(self) -> None:
        doc = {"contribuinte": "ANDRE DA SILVA BATISTA DE FARIAS"}
        assert _inferir_pessoa_canonica(doc, None) == "andre"

    def test_contribuinte_vitoria_devolve_vitoria(self) -> None:
        doc = {"contribuinte": "VITORIA SOUZA"}
        assert _inferir_pessoa_canonica(doc, None) == "vitoria"

    def test_contribuinte_original_quando_sintetico_aplicado(self) -> None:
        # Sprint 107: quando sintético aplica, contribuinte real fica em
        # __contribuinte_original. _inferir_pessoa_canonica deve consultá-lo.
        doc = {
            "razao_social": "Receita Federal do Brasil",
            "__contribuinte_original": "ANDRE DA SILVA",
        }
        assert _inferir_pessoa_canonica(doc, None) == "andre"

    def test_path_andre_devolve_andre_quando_sem_contribuinte(self) -> None:
        caminho = Path("/repo/data/raw/andre/holerites/X.pdf")
        assert _inferir_pessoa_canonica({}, caminho) == "andre"

    def test_path_vitoria_devolve_vitoria(self) -> None:
        caminho = Path("/repo/data/raw/vitoria/nfs/X.pdf")
        assert _inferir_pessoa_canonica({}, caminho) == "vitoria"

    def test_fallback_casal_quando_sem_evidencia(self) -> None:
        assert _inferir_pessoa_canonica({}, None) == "casal"
        assert _inferir_pessoa_canonica({}, Path("/repo/data/raw/_envelopes/X.pdf")) == "casal"


@pytest.fixture()
def grafo_para_backfill(tmp_path: Path) -> Path:
    """Grafo com 3 nodes documento: 1 sem pessoa, 1 com 'andre', 1 com pessoa invalida."""
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
    # node 1: sem pessoa, contribuinte ANDRE
    conn.execute(
        "INSERT INTO node VALUES (1, 'documento', 'X', ?, CURRENT_TIMESTAMP)",
        (json.dumps({"contribuinte": "ANDRE DA SILVA", "tipo_documento": "das_parcsn_andre"}),),
    )
    # node 2: ja com pessoa='andre' valida
    conn.execute(
        "INSERT INTO node VALUES (2, 'documento', 'Y', ?, CURRENT_TIMESTAMP)",
        (json.dumps({"pessoa": "andre", "tipo_documento": "holerite"}),),
    )
    # node 3: pessoa invalida, deve ser corrigida
    conn.execute(
        "INSERT INTO node VALUES (3, 'documento', 'Z', ?, CURRENT_TIMESTAMP)",
        (json.dumps({"pessoa": "_indefinida"}),),
    )
    conn.commit()
    conn.close()
    return destino


def test_backfill_atualiza_sem_pessoa(grafo_para_backfill: Path) -> None:
    contagens = backfill_metadata_pessoa.backfill(grafo_para_backfill, dry_run=False)
    assert contagens["atualizados"] == 2  # nodes 1 e 3
    assert contagens["ja_preenchidos"] == 1  # node 2

    conn = sqlite3.connect(grafo_para_backfill)
    try:
        for nid in (1, 2, 3):
            r = conn.execute(
                "SELECT json_extract(metadata, '$.pessoa') FROM node WHERE id=?",
                (nid,),
            ).fetchone()
            assert r[0] in {"andre", "vitoria", "casal"}
    finally:
        conn.close()


def test_backfill_idempotente(grafo_para_backfill: Path) -> None:
    backfill_metadata_pessoa.backfill(grafo_para_backfill, dry_run=False)
    c2 = backfill_metadata_pessoa.backfill(grafo_para_backfill, dry_run=False)
    assert c2["atualizados"] == 0  # tudo ja preenchido
    assert c2["ja_preenchidos"] == 3


def test_backfill_dry_run_nao_altera(grafo_para_backfill: Path) -> None:
    backfill_metadata_pessoa.backfill(grafo_para_backfill, dry_run=True)
    conn = sqlite3.connect(grafo_para_backfill)
    try:
        r = conn.execute(
            "SELECT json_extract(metadata, '$.pessoa') FROM node WHERE id=1"
        ).fetchone()
    finally:
        conn.close()
    assert r[0] is None  # não foi gravado


def test_backfill_sobrescrever_recalcula(grafo_para_backfill: Path) -> None:
    contagens = backfill_metadata_pessoa.backfill(
        grafo_para_backfill, sobrescrever=True, dry_run=False
    )
    assert contagens["atualizados"] == 3  # todos


# "Pessoa canonica eh contrato, não inferencia ad-hoc por consumidor."
# -- princípio do metadata.pessoa
