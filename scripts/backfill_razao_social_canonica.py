"""Sprint AUDIT2-RAZAO-SOCIAL-HOLERITE -- backfill razao_social oficial em holerites.

Itera nodes documento de tipo 'holerite' no grafo e atualiza
`metadata.razao_social` para a versao canonica de
`mappings/razao_social_canonica.yaml` (sigla curta preservada em
`metadata.razao_social_curta`). Atualiza o node fornecedor associado.

Modo `--dry-run` por default. Idempotente.
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

from src.extractors.contracheque_pdf import resolver_razao_social_canonica  # noqa: E402


def backfill(grafo_db: Path, dry_run: bool = False) -> dict[str, int]:
    """Atualiza metadata.razao_social para canonica em holerites.

    Atualiza também o node fornecedor ligado via `fornecido_por` para que
    seu metadata.razao_social fique alinhado.
    """
    contagens = {"detectados": 0, "atualizados": 0, "fornecedores_atualizados": 0}
    if not grafo_db.exists():
        return contagens
    modo = "ro" if dry_run else "rwc"
    conn = sqlite3.connect(f"file:{grafo_db}?mode={modo}", uri=True)
    try:
        cur = conn.execute(
            "SELECT id, metadata FROM node WHERE tipo='documento' "
            "AND json_extract(metadata, '$.tipo_documento')='holerite'"
        )
        nodes = cur.fetchall()
        contagens["detectados"] = len(nodes)
        for node_id, meta_raw in nodes:
            try:
                meta = json.loads(meta_raw or "{}")
            except json.JSONDecodeError:
                continue
            atual = str(meta.get("razao_social") or "")
            sigla = str(meta.get("razao_social_curta") or atual)
            canonica, cnpj_oficial = resolver_razao_social_canonica(sigla)
            if not canonica or canonica == atual:
                continue
            meta["razao_social"] = canonica
            meta["razao_social_curta"] = sigla.upper()
            if cnpj_oficial:
                meta["cnpj_oficial"] = cnpj_oficial
            if not dry_run:
                conn.execute(
                    "UPDATE node SET metadata = ?, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ?",
                    (json.dumps(meta, ensure_ascii=False), int(node_id)),
                )
            contagens["atualizados"] += 1

            # Atualiza fornecedor associado (aresta fornecido_por).
            cur_f = conn.execute(
                "SELECT n.id, n.metadata FROM edge e JOIN node n ON n.id=e.dst_id "
                "WHERE e.src_id=? AND e.tipo='fornecido_por' LIMIT 1",
                (int(node_id),),
            )
            row_f = cur_f.fetchone()
            if row_f is not None:
                f_id, f_meta_raw = row_f
                try:
                    f_meta = json.loads(f_meta_raw or "{}")
                except json.JSONDecodeError:
                    continue
                if f_meta.get("razao_social") != canonica:
                    f_meta["razao_social"] = canonica
                    if not dry_run:
                        conn.execute(
                            "UPDATE node SET metadata = ?, "
                            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (json.dumps(f_meta, ensure_ascii=False), int(f_id)),
                        )
                    contagens["fornecedores_atualizados"] += 1
        if not dry_run:
            conn.commit()
        return contagens
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill razao_social canonica em holerites "
            "(Sprint AUDIT2-RAZAO-SOCIAL-HOLERITE). Default --dry-run."
        )
    )
    parser.add_argument("--grafo-db", type=Path, default=_GRAFO_DB)
    parser.add_argument("--executar", action="store_true")
    args = parser.parse_args(argv)

    contagens = backfill(args.grafo_db, dry_run=not args.executar)
    prefix = "[DRY-RUN] " if not args.executar else ""
    print(
        f"{prefix}Holerites detectados: {contagens['detectados']}\n"
        f"{prefix}Atualizados: {contagens['atualizados']}\n"
        f"{prefix}Fornecedores atualizados: {contagens['fornecedores_atualizados']}",
        file=sys.stderr,
    )
    if not args.executar:
        print("\nPasse --executar para aplicar.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
