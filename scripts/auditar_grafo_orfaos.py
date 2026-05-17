"""Audita nodes órfãos no grafo (sem edges).

Sprint GRAFO-AUDIT-ORPHAN-NODES (2026-05-17). Detecta nodes que não
participam de nenhuma aresta (`src_id` ou `dst_id`). Reporta + opcional
remove com confirmação.

Hoje (2026-05-17): 3 nodes fornecedor órfãos detectados:
- `643` BIR COMERCIO (2026-04-20)
- `7426` 45.850.636/0001-60 (CNPJ MEI, 2026-04-23)
- `7463` DIRPF|E7536C39308A (2026-04-24)

Hipóteses para origem:
- Fragmento de migração antiga (sprint pre-tipo_documento canônico).
- Duplicata: pode ter sido absorvido por outro node com mesma razão social.
- Teste vazado: pytest criou e não cleanou.

Uso CLI::

    python scripts/auditar_grafo_orfaos.py             # dry-run (lista)
    python scripts/auditar_grafo_orfaos.py --apply     # DELETE órfãos
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
PATH_GRAFO = _RAIZ / "data" / "output" / "grafo.sqlite"
PATH_LOG = _RAIZ / "data" / "output" / "grafo_orfaos_log.json"

QUERY_ORFAOS = """
SELECT id, tipo, nome_canonico, metadata, created_at, updated_at
FROM node
WHERE id NOT IN (SELECT src_id FROM edge UNION SELECT dst_id FROM edge)
ORDER BY tipo, id
"""


def _listar_orfaos(grafo: Path) -> list[dict]:
    """Devolve lista de dicts com info de cada órfão."""
    if not grafo.exists():
        return []
    con = sqlite3.connect(str(grafo))
    try:
        out = []
        for row in con.execute(QUERY_ORFAOS):
            node_id, tipo, nome, meta_str, created, updated = row
            try:
                meta = json.loads(meta_str) if meta_str else {}
            except json.JSONDecodeError:
                meta = {}
            out.append(
                {
                    "id": node_id,
                    "tipo": tipo,
                    "nome_canonico": nome,
                    "created_at": str(created or ""),
                    "updated_at": str(updated or ""),
                    "metadata_resumo": {
                        k: v
                        for k, v in meta.items()
                        if k in ("razao_social", "cnpj", "alias", "tipo_documento")
                    },
                }
            )
        return out
    finally:
        con.close()


def _deletar_orfaos(grafo: Path, ids: list[int]) -> int:
    """Deleta nodes pelos IDs. Retorna count de removidos."""
    if not ids:
        return 0
    con = sqlite3.connect(str(grafo))
    try:
        placeholders = ",".join(["?"] * len(ids))
        cursor = con.execute(f"DELETE FROM node WHERE id IN ({placeholders})", ids)
        con.commit()
        return cursor.rowcount or 0
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audita nodes orfaos do grafo")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="DELETE nodes orfaos (default: dry-run lista)",
    )
    args = parser.parse_args(argv)

    orfaos = _listar_orfaos(PATH_GRAFO)
    sys.stdout.write(f"Total de nodes orfaos: {len(orfaos)}\n")
    if not orfaos:
        return 0

    sys.stdout.write("\nDetalhe:\n")
    for o in orfaos:
        sys.stdout.write(
            f"  [{o['id']}] tipo={o['tipo']:12s} "
            f"nome='{o['nome_canonico'][:60]}' "
            f"created={o['created_at'][:10]}\n"
        )
        if o["metadata_resumo"]:
            sys.stdout.write(f"    metadata: {o['metadata_resumo']}\n")

    if not args.apply:
        sys.stdout.write("\nDry-run: use --apply para deletar.\n")
        return 0

    ids = [o["id"] for o in orfaos]
    deletados = _deletar_orfaos(PATH_GRAFO, ids)

    # Log estruturado:
    PATH_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_data = {
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "modo": "apply",
        "total_orfaos_antes": len(orfaos),
        "deletados": deletados,
        "amostras": orfaos[:50],
    }
    # Apenda em modo histórico:
    historico: list = []
    if PATH_LOG.exists():
        try:
            historico = json.loads(PATH_LOG.read_text(encoding="utf-8"))
            if not isinstance(historico, list):
                historico = []
        except json.JSONDecodeError:
            historico = []
    historico.append(log_data)
    PATH_LOG.write_text(
        json.dumps(historico, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    sys.stdout.write(f"\nDeletados: {deletados} node(s).\n")
    sys.stdout.write(f"Log: {PATH_LOG}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Node sem edge eh fantasma do grafo." -- principio da consistencia relacional
