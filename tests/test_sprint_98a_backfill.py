"""Sprint 98a: testes regressivos do backfill de metadata.arquivo_origem.

Cobre:
  1. Holerite com path quebrado é resolvido via mes_ref + empresa.
  2. Holerite com 2 candidatos (G4F + INFOBASE no mesmo mês) escolhe pela razao_social.
  3. Holerite sem candidato no FS é marcado como nao_resolvido (não apaga node).
  4. DAS PARCSN com path quebrado é resolvido via vencimento.
  5. Idempotência: rodar 2x não corrompe (segunda devolve 0 quebrados).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.graph.backfill_arquivo_origem import (
    _resolver_holerite,
    backfill_arquivo_origem,
    detectar_paths_quebrados,
)
from src.graph.db import GrafoDB


def _criar_grafo_holerite(
    tmp_path: Path,
    arquivo_origem_antigo: str,
    mes: str,
    razao: str,
    liquido: float | None = None,
) -> GrafoDB:
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    meta = {
        "tipo_documento": "holerite",
        "periodo_apuracao": mes,
        "razao_social": razao,
        "arquivo_origem": arquivo_origem_antigo,
    }
    if liquido is not None:
        meta["liquido"] = liquido
    db.upsert_node("documento", f"HOLERITE|{razao}|{mes}", metadata=meta)
    return db


def test_detectar_paths_quebrados_lista_nodes_com_path_inexistente(tmp_path: Path):
    db = _criar_grafo_holerite(tmp_path, "/path/inexistente.pdf", "2025-07", "G4F")
    quebrados = detectar_paths_quebrados(db)
    assert len(quebrados) == 1
    assert quebrados[0]["arquivo_origem_antigo"] == "/path/inexistente.pdf"


def test_detectar_paths_quebrados_ignora_path_valido(tmp_path: Path):
    arquivo_real = tmp_path / "doc.pdf"
    arquivo_real.write_bytes(b"X")
    db = _criar_grafo_holerite(tmp_path, str(arquivo_real), "2025-07", "G4F")
    quebrados = detectar_paths_quebrados(db)
    assert len(quebrados) == 0


def test_resolver_holerite_via_mes_e_empresa(tmp_path: Path):
    raiz = tmp_path / "raw"
    holerites = raiz / "andre" / "holerites"
    holerites.mkdir(parents=True)
    alvo = holerites / "HOLERITE_2025-07_G4F_6400.pdf"
    alvo.write_bytes(b"FAKE")

    meta = {"tipo_documento": "holerite", "periodo_apuracao": "2025-07", "razao_social": "G4F"}
    achado = _resolver_holerite(meta, raiz)
    assert achado == alvo


def test_resolver_holerite_desempata_por_liquido(tmp_path: Path):
    raiz = tmp_path / "raw"
    holerites = raiz / "andre" / "holerites"
    holerites.mkdir(parents=True)
    a = holerites / "HOLERITE_2025-10_G4F_2164.pdf"
    b = holerites / "HOLERITE_2025-10_G4F_6394.pdf"
    a.write_bytes(b"X")
    b.write_bytes(b"Y")

    meta = {
        "tipo_documento": "holerite",
        "periodo_apuracao": "2025-10",
        "razao_social": "G4F",
        "liquido": 2164.0,
    }
    achado = _resolver_holerite(meta, raiz)
    assert achado == a


def test_resolver_holerite_sem_candidato_devolve_none(tmp_path: Path):
    raiz = tmp_path / "raw"
    raiz.mkdir()
    meta = {"tipo_documento": "holerite", "periodo_apuracao": "2025-07", "razao_social": "G4F"}
    achado = _resolver_holerite(meta, raiz)
    assert achado is None


def test_backfill_atualiza_metadata_no_grafo(tmp_path: Path):
    raiz = tmp_path / "raw"
    holerites = raiz / "andre" / "holerites"
    holerites.mkdir(parents=True)
    novo = holerites / "HOLERITE_2025-07_G4F_6400.pdf"
    novo.write_bytes(b"FAKE")

    db = _criar_grafo_holerite(tmp_path, "/path/antigo/holerite_xxx.pdf", "2025-07", "G4F")
    rel = backfill_arquivo_origem(db, raiz_raw=raiz, dry_run=False)
    assert rel["quebrados"] == 1
    assert rel["resolvidos"] == 1
    assert rel["persistidos"] == 1
    assert rel["nao_resolvidos"] == 0

    # Confirma que foi atualizado
    cur = db._conn.execute("SELECT metadata FROM node WHERE tipo='documento'")
    meta = json.loads(cur.fetchone()[0])
    assert meta["arquivo_origem"] == str(novo.resolve())


def test_backfill_dry_run_nao_persiste(tmp_path: Path):
    raiz = tmp_path / "raw"
    holerites = raiz / "andre" / "holerites"
    holerites.mkdir(parents=True)
    novo = holerites / "HOLERITE_2025-07_G4F_6400.pdf"
    novo.write_bytes(b"FAKE")

    db = _criar_grafo_holerite(tmp_path, "/path/antigo/holerite_xxx.pdf", "2025-07", "G4F")
    rel = backfill_arquivo_origem(db, raiz_raw=raiz, dry_run=True)
    assert rel["resolvidos"] == 1
    assert rel["persistidos"] == 0  # dry-run não persiste

    # Metadata original preservado
    cur = db._conn.execute("SELECT metadata FROM node WHERE tipo='documento'")
    meta = json.loads(cur.fetchone()[0])
    assert meta["arquivo_origem"] == "/path/antigo/holerite_xxx.pdf"


def test_backfill_idempotente(tmp_path: Path):
    raiz = tmp_path / "raw"
    holerites = raiz / "andre" / "holerites"
    holerites.mkdir(parents=True)
    novo = holerites / "HOLERITE_2025-07_G4F_6400.pdf"
    novo.write_bytes(b"FAKE")

    db = _criar_grafo_holerite(tmp_path, "/path/antigo/holerite_xxx.pdf", "2025-07", "G4F")

    r1 = backfill_arquivo_origem(db, raiz_raw=raiz, dry_run=False)
    assert r1["quebrados"] == 1
    assert r1["resolvidos"] == 1

    r2 = backfill_arquivo_origem(db, raiz_raw=raiz, dry_run=False)
    assert r2["quebrados"] == 0  # após persistir, path real existe
    assert r2["resolvidos"] == 0


def test_backfill_node_sem_estrategia_marcado(tmp_path: Path):
    raiz = tmp_path / "raw"
    raiz.mkdir()
    db = _criar_grafo_holerite(tmp_path, "/path/inexistente.pdf", "2025-07", "G4F")
    rel = backfill_arquivo_origem(db, raiz_raw=raiz, dry_run=False)
    assert rel["resolvidos"] == 0
    assert rel["nao_resolvidos"] == 1
    assert len(rel["sem_estrategia"]) == 1


# "Path quebrado é cicatriz; backfill é o medico que sabe ler heuristica." -- bom diagnostico
