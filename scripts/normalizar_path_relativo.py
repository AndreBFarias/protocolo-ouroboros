"""Sprint AUDIT2-PATH-RELATIVO-COMPLETO -- normaliza paths absolutos -> relativos.

A Sprint AUDIT-PATH-RELATIVO ligou `to_relativo()` em
`src/graph/ingestor_documento.py`, mas DAS PARCSN, boletos e envelopes
ingeridos antes dessa sprint mantem path absoluto em
`metadata.arquivo_origem` (ex: `/home/andrefarias/.../data/raw/...`).

Este script percorre todos os nodes `documento` no grafo, detecta paths
absolutos e re-aplica `to_relativo`. Idempotente: 2a execução é no-op.

Modo `--dry-run` por default (CLAUDE.md operação destrutiva). Modo
`--executar` aplica UPDATE no grafo.

Encadeavel em `--full-cycle` / `--reextrair-tudo` (Sprint 108).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
_GRAFO_DB = _RAIZ / "data" / "output" / "grafo.sqlite"

if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.graph.path_canonico import to_relativo  # noqa: E402


def listar_nodes_path_absoluto(grafo_db: Path) -> list[tuple[int, str, dict]]:
    """Devolve [(node_id, arquivo_origem_absoluto, metadata), ...] para nodes
    documento com `metadata.arquivo_origem` comecando por '/' (absoluto).
    """
    if not grafo_db.exists():
        return []
    conn = sqlite3.connect(f"file:{grafo_db}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "SELECT id, metadata FROM node WHERE tipo='documento' "
            "AND json_extract(metadata, '$.arquivo_origem') LIKE '/%'"
        )
        resultado: list[tuple[int, str, dict]] = []
        for node_id, meta_raw in cur:
            try:
                meta = json.loads(meta_raw or "{}")
            except json.JSONDecodeError:
                continue
            ao = meta.get("arquivo_origem", "")
            if ao.startswith("/"):
                resultado.append((int(node_id), ao, meta))
        return resultado
    finally:
        conn.close()


def normalizar(grafo_db: Path) -> dict[str, int]:
    """Aplica `to_relativo` em nodes com path absoluto. Retorna contagens."""
    conn = sqlite3.connect(grafo_db)
    contagens = {"detectados": 0, "atualizados": 0, "fora_repo": 0}
    try:
        cur_sel = conn.execute(
            "SELECT id, metadata FROM node WHERE tipo='documento' "
            "AND json_extract(metadata, '$.arquivo_origem') LIKE '/%'"
        )
        nodes = cur_sel.fetchall()
        contagens["detectados"] = len(nodes)
        for node_id, meta_raw in nodes:
            try:
                meta = json.loads(meta_raw or "{}")
            except json.JSONDecodeError:
                continue
            ao_abs = meta.get("arquivo_origem", "")
            ao_rel = to_relativo(ao_abs)
            if ao_rel == ao_abs:
                # Path fora do repo (raro). Preserva.
                contagens["fora_repo"] += 1
                continue
            meta["arquivo_origem"] = ao_rel
            conn.execute(
                "UPDATE node SET metadata = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (json.dumps(meta, ensure_ascii=False), int(node_id)),
            )
            contagens["atualizados"] += 1
        conn.commit()
        return contagens
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normaliza metadata.arquivo_origem absoluto -> relativo "
            "(Sprint AUDIT2-PATH-RELATIVO-COMPLETO). Default --dry-run."
        )
    )
    parser.add_argument("--grafo-db", type=Path, default=_GRAFO_DB)
    parser.add_argument("--executar", action="store_true")
    args = parser.parse_args(argv)

    nodes = listar_nodes_path_absoluto(args.grafo_db)
    print(
        f"Nodes documento com path absoluto: {len(nodes)}",
        file=sys.stderr,
    )
    if not nodes:
        print("Nada a normalizar.", file=sys.stderr)
        return 0
    if not args.executar:
        print("--- dry-run (passe --executar para aplicar) ---", file=sys.stderr)
        for node_id, ao, _ in nodes[:10]:
            print(f"  node_{node_id}: {ao}", file=sys.stderr)
        if len(nodes) > 10:
            print(f"  ... e mais {len(nodes) - 10}", file=sys.stderr)
        return 0

    contagens = normalizar(args.grafo_db)
    print(
        f"Atualizados: {contagens['atualizados']} de {contagens['detectados']} "
        f"(fora do repo, preservados absolutos: {contagens['fora_repo']})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
