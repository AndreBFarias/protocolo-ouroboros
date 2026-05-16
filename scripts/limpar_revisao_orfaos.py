"""Sprint AUDIT2-REVISAO-LIMPEZA-OBSOLETOS -- limpa item_ids orfaos.

Marcacoes em `data/output/revisao_humana.sqlite` referenciando
`item_id = "node_<id>"` ficam orfas quando reextracao deleta o node
correspondente do grafo. Este script identifica e remove essas marcacoes.

Modo `--dry-run` (default) só reporta. `--executar` aplica DELETE.
Idempotente: rodar 2x apos `--executar` e no-op (orfaos ja removidos).

Encadeavel em `--full-cycle` / `--reextrair-tudo` (Sprint 108) via
`run_passo`. Backup automatico do DB antes de executar (preserva 1 copia
em `data/output/revisao_humana.sqlite.bak`).
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
_GRAFO_DB = _RAIZ / "data" / "output" / "grafo.sqlite"
_REVISAO_DB = _RAIZ / "data" / "output" / "revisao_humana.sqlite"


def listar_orfaos(grafo_db: Path, revisao_db: Path) -> list[tuple[str, int]]:
    """Devolve [(item_id, num_marcacoes), ...] para item_ids node_<id> que
    não existem mais como nodes documento no grafo.
    """
    if not grafo_db.exists() or not revisao_db.exists():
        return []
    conn_g = sqlite3.connect(f"file:{grafo_db}?mode=ro", uri=True)
    conn_r = sqlite3.connect(f"file:{revisao_db}?mode=ro", uri=True)
    try:
        ids_validos = {
            int(row[0]) for row in conn_g.execute("SELECT id FROM node WHERE tipo='documento'")
        }
        cur = conn_r.execute(
            "SELECT item_id, COUNT(*) FROM revisao WHERE item_id LIKE 'node_%' GROUP BY item_id"
        )
        orfaos: list[tuple[str, int]] = []
        for item_id, n in cur:
            try:
                node_id = int(str(item_id).split("_", 1)[1])
            except (ValueError, IndexError):
                continue
            if node_id not in ids_validos:
                orfaos.append((str(item_id), int(n)))
        return orfaos
    finally:
        conn_g.close()
        conn_r.close()


def aplicar_remocao(revisao_db: Path, orfaos: list[tuple[str, int]]) -> int:
    """Remove marcacoes orfaos. Retorna número de linhas removidas.

    Cria backup `revisao_humana.sqlite.bak` antes de executar (sobrescreve
    backup anterior — 1 nivel apenas, alinhado a politica simples).
    """
    if not orfaos:
        return 0
    backup = revisao_db.with_suffix(revisao_db.suffix + ".bak")
    shutil.copy2(revisao_db, backup)
    conn = sqlite3.connect(revisao_db)
    try:
        ids = [item_id for item_id, _ in orfaos]
        placeholders = ",".join("?" for _ in ids)
        cur = conn.execute(
            f"DELETE FROM revisao WHERE item_id IN ({placeholders})",
            ids,
        )
        conn.commit()
        return cur.rowcount or 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Limpa item_ids node_<id> orfaos em revisao_humana.sqlite. "
            "Default --dry-run; passe --executar para aplicar."
        )
    )
    parser.add_argument("--grafo-db", type=Path, default=_GRAFO_DB)
    parser.add_argument("--revisao-db", type=Path, default=_REVISAO_DB)
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Aplica DELETE (default e dry-run com backup automatico).",
    )
    args = parser.parse_args(argv)

    orfaos = listar_orfaos(args.grafo_db, args.revisao_db)
    print(
        f"Item_ids orfaos: {len(orfaos)} ({sum(n for _, n in orfaos)} marcacoes)",
        file=sys.stderr,
    )
    if not orfaos:
        print("Nada a remover.", file=sys.stderr)
        return 0
    if not args.executar:
        print("--- dry-run (passe --executar para aplicar) ---", file=sys.stderr)
        for item_id, n in sorted(orfaos):
            print(f"  {item_id} -> {n} marcacoes", file=sys.stderr)
        return 0

    n = aplicar_remocao(args.revisao_db, orfaos)
    print(f"Removidas {n} marcacoes orfas. Backup em .bak.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
