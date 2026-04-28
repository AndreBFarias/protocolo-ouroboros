"""Sprint AUDIT2-METADATA-PESSOA-CANONICA -- backfill de metadata.pessoa em nodes existentes.

Itera nodes documento, prescricao, garantia e apolice no grafo; aplica
`_inferir_pessoa_canonica` (mesma logica do ingestor) e grava em
`metadata.pessoa`. Idempotente: não sobrescreve quando ja preenchido
(passe `--sobrescrever` para forcar).

Modo `--dry-run` por default. Encadeavel em `--reextrair-tudo` (Sprint 108).
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

from src.graph.ingestor_documento import _inferir_pessoa_canonica  # noqa: E402
from src.graph.path_canonico import to_absoluto  # noqa: E402

# Tipos de node que carregam pessoa (vinculados a um arquivo origem).
_TIPOS_COM_PESSOA: tuple[str, ...] = ("documento", "apolice", "prescricao", "garantia")


def backfill(
    grafo_db: Path,
    sobrescrever: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Aplica _inferir_pessoa_canonica em nodes existentes.

    Em `dry_run=True` apenas conta os nodes que seriam atualizados (sem
    UPDATE). Em modo aplicar (default deste helper, controlado pelo CLI),
    grava metadata atualizado e commita.

    Retorna {detectados, atualizados, ja_preenchidos, falhou}.
    """
    contagens = {"detectados": 0, "atualizados": 0, "ja_preenchidos": 0, "falhou": 0}
    if not grafo_db.exists():
        return contagens
    placeholders = ",".join("?" for _ in _TIPOS_COM_PESSOA)
    modo = "ro" if dry_run else "rwc"
    conn = sqlite3.connect(f"file:{grafo_db}?mode={modo}", uri=True)
    try:
        cur = conn.execute(
            f"SELECT id, metadata FROM node WHERE tipo IN ({placeholders})",
            list(_TIPOS_COM_PESSOA),
        )
        nodes = cur.fetchall()
        contagens["detectados"] = len(nodes)
        for node_id, meta_raw in nodes:
            try:
                meta = json.loads(meta_raw or "{}")
            except json.JSONDecodeError:
                contagens["falhou"] += 1
                continue
            pessoa_atual = meta.get("pessoa")
            if not sobrescrever and pessoa_atual in {"andre", "vitoria", "casal"}:
                contagens["ja_preenchidos"] += 1
                continue
            ao = meta.get("arquivo_origem")
            caminho = to_absoluto(ao) if ao else None
            pessoa = _inferir_pessoa_canonica(meta, caminho)
            meta["pessoa"] = pessoa
            if not dry_run:
                conn.execute(
                    "UPDATE node SET metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (json.dumps(meta, ensure_ascii=False), int(node_id)),
                )
            contagens["atualizados"] += 1
        if not dry_run:
            conn.commit()
        return contagens
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill de metadata.pessoa em nodes existentes do grafo "
            "(Sprint AUDIT2-METADATA-PESSOA-CANONICA). Default --dry-run."
        )
    )
    parser.add_argument("--grafo-db", type=Path, default=_GRAFO_DB)
    parser.add_argument("--executar", action="store_true")
    parser.add_argument(
        "--sobrescrever",
        action="store_true",
        help="Refaz inferencia mesmo quando metadata.pessoa ja preenchido.",
    )
    args = parser.parse_args(argv)

    contagens = backfill(
        args.grafo_db,
        sobrescrever=args.sobrescrever,
        dry_run=not args.executar,
    )
    prefix = "[DRY-RUN] " if not args.executar else ""
    print(
        f"{prefix}Detectados: {contagens['detectados']} nodes\n"
        f"{prefix}Atualizados: {contagens['atualizados']}\n"
        f"{prefix}Ja preenchidos (skip): {contagens['ja_preenchidos']}\n"
        f"{prefix}Falharam (JSON invalido): {contagens['falhou']}",
        file=sys.stderr,
    )
    if not args.executar:
        print(
            "\nPasse --executar para aplicar as atualizacoes.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
