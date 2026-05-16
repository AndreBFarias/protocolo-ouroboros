"""Wrapper fino sobre ``reprocessar_documentos.py`` com backup + log estruturado.

Sprint INFRA-PROCESSAR-INBOX-MASSA (revisada 2026-05-08).

A pipeline real está em ``scripts/reprocessar_documentos.py`` (Sprint 57).
Este wrapper adiciona:

1. Backup automático de ``data/output/grafo.sqlite`` antes de rodar
   (pulável via ``--sem-backup``).
2. Estado antes/depois do grafo (counts por tipo de node/edge).
3. Log estruturado em ``logs/inbox_massa_<timestamp>.log``.
4. Delta de cobertura impresso ao final.

Argumentos:

* ``--dry-run`` -- repassa ao reprocessar (apenas lista, sem alterar grafo).
* ``--forcar-reextracao`` -- repassa ao reprocessar (limpa nodes
  ``documento`` antes de reingerir; usar com cuidado).
* ``--sem-backup`` -- pula o backup.

Padrões: VALIDATOR_BRIEF (b) acentuação, (e) data/ no .gitignore, (f)
paths relativos via ``Path``, (u) proof-of-work runtime real.
"""

from __future__ import annotations

import argparse
import json  # noqa: F401  -- usado em json.dumps (linha 133)
import shutil
import sqlite3
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GRAFO_PATH = RAIZ / "data" / "output" / "grafo.sqlite"
LOGS_DIR = RAIZ / "logs"
REPROCESSAR_SCRIPT = RAIZ / "scripts" / "reprocessar_documentos.py"


def contar_grafo(grafo: Path) -> dict:
    """Retorna contagens de nodes/edges por tipo. Vazio se grafo não existe."""
    if not grafo.exists():
        return {"nodes": {}, "edges": {}}
    with sqlite3.connect(grafo) as con:
        nodes = OrderedDict()
        for tipo, n in con.execute("SELECT tipo, COUNT(*) FROM node GROUP BY tipo ORDER BY 2 DESC"):
            nodes[tipo] = n
        edges = OrderedDict()
        for tipo, n in con.execute("SELECT tipo, COUNT(*) FROM edge GROUP BY tipo ORDER BY 2 DESC"):
            edges[tipo] = n
    return {"nodes": dict(nodes), "edges": dict(edges)}


def fazer_backup(grafo: Path, ts: str) -> Path | None:
    """Copia ``grafo.sqlite`` para ``grafo.sqlite.bak.<ts>``."""
    if not grafo.exists():
        return None
    destino = grafo.with_suffix(grafo.suffix + f".bak.{ts}")
    shutil.copy2(grafo, destino)
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wrapper sobre reprocessar_documentos com backup + log."
    )
    parser.add_argument("--dry-run", action="store_true", help="Repassa --dry-run ao reprocessar.")
    parser.add_argument(
        "--forcar-reextracao",
        action="store_true",
        help="Repassa --forcar-reextracao (limpa documentos).",
    )
    parser.add_argument("--sem-backup", action="store_true", help="Não faz backup do grafo.")
    args = parser.parse_args()

    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    log_path = LOGS_DIR / f"inbox_massa_{ts}.log"

    # Antes
    antes = contar_grafo(GRAFO_PATH)

    # Backup
    backup_path = None
    if not args.sem_backup and not args.dry_run:
        backup_path = fazer_backup(GRAFO_PATH, ts)

    # Reprocessar
    cmd = [sys.executable, str(REPROCESSAR_SCRIPT)]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.forcar_reextracao:
        cmd.append("--forcar-reextracao")

    proc = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, check=False)

    # Depois
    depois = contar_grafo(GRAFO_PATH)

    # Delta
    delta_nodes = {}
    for tipo in set(antes["nodes"]) | set(depois["nodes"]):
        d = depois["nodes"].get(tipo, 0) - antes["nodes"].get(tipo, 0)
        if d != 0 or tipo in depois["nodes"]:
            delta_nodes[tipo] = d
    delta_edges = {}
    for tipo in set(antes["edges"]) | set(depois["edges"]):
        d = depois["edges"].get(tipo, 0) - antes["edges"].get(tipo, 0)
        if d != 0 or tipo in depois["edges"]:
            delta_edges[tipo] = d

    # Log estruturado
    log = {
        "timestamp": ts,
        "args": vars(args),
        "comando_reprocessar": " ".join(cmd),
        "exit_code": proc.returncode,
        "backup": str(backup_path) if backup_path else None,
        "antes": antes,
        "depois": depois,
        "delta_nodes": delta_nodes,
        "delta_edges": delta_edges,
        "stdout_resumo": proc.stdout[-2000:] if proc.stdout else "",
        "stderr_resumo": proc.stderr[-2000:] if proc.stderr else "",
    }
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")

    # Resumo no console
    print(f"\n{'=' * 60}")
    print(f"INBOX MASSA -- timestamp {ts}")
    print(f"{'=' * 60}")
    print(f"Backup: {backup_path or '(pulado)'}")
    print(f"Reprocessar exit: {proc.returncode}")
    print(f"\nAntes: {sum(antes['nodes'].values())} nodes, {sum(antes['edges'].values())} edges")
    print(f"Depois: {sum(depois['nodes'].values())} nodes, {sum(depois['edges'].values())} edges")
    if delta_nodes:
        print("\nDelta nodes:")
        for tipo, d in sorted(delta_nodes.items(), key=lambda x: -abs(x[1])):
            sinal = f"+{d}" if d > 0 else str(d) if d < 0 else "0"
            print(f"  {tipo:25s} {sinal:>6s}")
    if delta_edges:
        print("\nDelta edges:")
        for tipo, d in sorted(delta_edges.items(), key=lambda x: -abs(x[1])):
            sinal = f"+{d}" if d > 0 else str(d) if d < 0 else "0"
            print(f"  {tipo:25s} {sinal:>6s}")
    print(f"\nLog completo: {log_path}")

    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())

# "O que se mede, se gerencia. Wrapper honesto sobre o que mudou."
# -- princípio INFRA-PROCESSAR-INBOX-MASSA
