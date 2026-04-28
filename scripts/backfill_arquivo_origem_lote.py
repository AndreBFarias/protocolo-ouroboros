"""Sprint 98a -- CLI para backfill retroativo de metadata.arquivo_origem.

Uso:
    .venv/bin/python scripts/backfill_arquivo_origem_lote.py             # dry-run
    .venv/bin/python scripts/backfill_arquivo_origem_lote.py --executar  # aplica
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.graph.backfill_arquivo_origem import backfill_arquivo_origem  # noqa: E402
from src.graph.db import GrafoDB, caminho_padrao  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill de metadata.arquivo_origem em nodes documento com path quebrado.",
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Aplica updates (default: dry-run).",
    )
    parser.add_argument("--grafo", type=Path, default=None, help="Caminho do grafo.sqlite.")
    args = parser.parse_args(argv)

    caminho_grafo = args.grafo or caminho_padrao()
    grafo = GrafoDB(caminho_grafo)
    try:
        rel = backfill_arquivo_origem(grafo, dry_run=not args.executar)
    finally:
        # GrafoDB não tem close() explicito; conn fecha no GC.
        pass

    modo = "EXECUTAR" if args.executar else "DRY-RUN"
    print(f"\n[Backfill arquivo_origem -- {modo}]")
    print(f"  Quebrados:      {rel['quebrados']}")
    print(f"  Resolvidos:     {rel['resolvidos']}")
    print(f"  Persistidos:    {rel['persistidos']}")
    print(f"  Não-resolvidos: {rel['nao_resolvidos']}")
    if rel["sem_estrategia"]:
        print(f"  Sem estrategia ({len(rel['sem_estrategia'])} primeiros):")
        for s in rel["sem_estrategia"][:10]:
            print(f"    - id={s['id']} nome={s['nome']} antigo={s['arquivo_antigo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
