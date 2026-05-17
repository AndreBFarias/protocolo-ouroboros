"""Testes do migrador retroativo de tipo_documento no grafo.

Sprint META-NORMALIZAR-TIPO-DOCUMENTO-ETL (2026-05-16). Cobre:
auditoria de candidatos, idempotência, metadata extras para
das_parcsn, reversibilidade.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "normalizar_tipo_documento_grafo",
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "normalizar_tipo_documento_grafo.py",
)
assert _SPEC and _SPEC.loader
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def _criar_grafo_sintetico(path: Path, nodes: list[dict]) -> None:
    """Cria grafo SQLite mínimo com schema canônico e nodes pré-definidos."""
    con = sqlite3.connect(str(path))
    con.executescript(
        """
        CREATE TABLE node (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nome_canonico TEXT NOT NULL,
            aliases TEXT NOT NULL DEFAULT '[]',
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (tipo, nome_canonico)
        );
        """
    )
    for n in nodes:
        con.execute(
            "INSERT INTO node (tipo, nome_canonico, metadata) VALUES (?, ?, ?)",
            (n["tipo"], n["nome_canonico"], json.dumps(n.get("metadata", {}))),
        )
    con.commit()
    con.close()


def test_coleta_candidatos_apenas_divergentes(tmp_path: Path) -> None:
    """Apenas nodes com tipo_documento no MAPA aparecem como candidatos."""
    grafo = tmp_path / "g.sqlite"
    nodes = [
        ("documento", "A", {"tipo_documento": "cupom_fiscal"}),
        ("documento", "B", {"tipo_documento": "holerite"}),
        ("documento", "C", {"tipo_documento": "das_parcsn_andre"}),
        ("documento", "D", {"tipo_documento": "nfce_modelo_65"}),
    ]
    _criar_grafo_sintetico(
        grafo,
        [{"tipo": t, "nome_canonico": n, "metadata": m} for t, n, m in nodes],
    )
    resultado = mod.executar(grafo=grafo, apply=False)
    assert resultado["n_candidatos"] == 3
    tipos = {c["tipo_atual"] for c in resultado["candidatos"]}
    assert tipos == {"cupom_fiscal", "das_parcsn_andre", "nfce_modelo_65"}


def test_apply_atualiza_tipo_e_grava_extras(tmp_path: Path) -> None:
    """`--apply` muda tipo_documento e grava metadata.pessoa para das_parcsn."""
    grafo = tmp_path / "g.sqlite"
    _criar_grafo_sintetico(
        grafo,
        [
            {
                "tipo": "documento",
                "nome_canonico": "das_a",
                "metadata": {"tipo_documento": "das_parcsn_andre"},
            },
            {
                "tipo": "documento",
                "nome_canonico": "das_v",
                "metadata": {"tipo_documento": "das_parcsn_vitoria"},
            },
        ],
    )
    resultado = mod.executar(grafo=grafo, apply=True, log=tmp_path / "log.json")
    assert resultado["n_aplicados"] == 2
    # Verifica metadata pós-migração:
    con = sqlite3.connect(str(grafo))
    rows = con.execute("SELECT nome_canonico, metadata FROM node").fetchall()
    con.close()
    por_nome = {nome: json.loads(meta) for nome, meta in rows}
    assert por_nome["das_a"]["tipo_documento"] == "das_parcsn"
    assert por_nome["das_a"]["pessoa"] == "pessoa_a"
    assert por_nome["das_a"]["_tipo_anterior"] == "das_parcsn_andre"
    assert por_nome["das_v"]["pessoa"] == "pessoa_b"


def test_apply_idempotente(tmp_path: Path) -> None:
    """Rodar 2× consecutivas: segunda não acha mais candidatos."""
    grafo = tmp_path / "g.sqlite"
    _criar_grafo_sintetico(
        grafo,
        [
            {
                "tipo": "documento",
                "nome_canonico": "x",
                "metadata": {"tipo_documento": "cupom_fiscal"},
            }
        ],
    )
    r1 = mod.executar(grafo=grafo, apply=True, log=tmp_path / "l1.json")
    r2 = mod.executar(grafo=grafo, apply=True, log=tmp_path / "l2.json")
    assert r1["n_aplicados"] == 1
    assert r2["n_aplicados"] == 0


def test_reverter_volta_para_tipo_anterior(tmp_path: Path) -> None:
    """`--reverter` usa _tipo_anterior gravado em runs anteriores."""
    grafo = tmp_path / "g.sqlite"
    _criar_grafo_sintetico(
        grafo,
        [
            {
                "tipo": "documento",
                "nome_canonico": "x",
                "metadata": {"tipo_documento": "cupom_fiscal"},
            }
        ],
    )
    mod.executar(grafo=grafo, apply=True, log=tmp_path / "l1.json")
    r = mod.executar(grafo=grafo, reverter=True, log=tmp_path / "l2.json")
    assert r["n_revertidos"] == 1
    # Confirma reversão:
    con = sqlite3.connect(str(grafo))
    row = con.execute("SELECT metadata FROM node WHERE nome_canonico='x'").fetchone()
    meta = json.loads(row[0])
    con.close()
    assert meta["tipo_documento"] == "cupom_fiscal"
    assert "_tipo_anterior" not in meta


def test_grafo_ausente_devolve_erro_estruturado(tmp_path: Path) -> None:
    """Grafo inexistente não crasha; devolve dict com erro."""
    resultado = mod.executar(grafo=tmp_path / "nao_existe.sqlite", apply=False)
    assert "erro" in resultado


def test_log_estruturado_gravado_em_apply(tmp_path: Path) -> None:
    """`--apply` grava JSON estruturado com mapa + candidatos + aplicados."""
    grafo = tmp_path / "g.sqlite"
    log = tmp_path / "log.json"
    _criar_grafo_sintetico(
        grafo,
        [
            {
                "tipo": "documento",
                "nome_canonico": "x",
                "metadata": {"tipo_documento": "cupom_fiscal"},
            }
        ],
    )
    mod.executar(grafo=grafo, apply=True, log=log)
    assert log.exists()
    d = json.loads(log.read_text(encoding="utf-8"))
    assert d["modo"] == "apply"
    assert d["n_aplicados"] == 1
    assert "mapa_normalizacao" in d


# "Duas fontes de verdade são uma fonte e um boato." -- princípio
