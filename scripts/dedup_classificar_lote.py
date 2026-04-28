"""Sprint INFRA-DEDUP-CLASSIFICAR -- CLI para dedup retroativo de
data/raw/_classificar/.

Uso:
    .venv/bin/python scripts/dedup_classificar_lote.py             # dry-run (default)
    .venv/bin/python scripts/dedup_classificar_lote.py --executar  # apaga fósseis
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.intake.dedup_classificar import deduplicar_classificar  # noqa: E402

_PASTA_DEFAULT = _RAIZ / "data" / "raw" / "_classificar"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dedup automático de PDFs bit-a-bit em data/raw/_classificar/.",
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Aplica remoção (sem flag, só reporta em modo dry-run).",
    )
    parser.add_argument(
        "--pasta",
        type=Path,
        default=_PASTA_DEFAULT,
        help=f"Pasta-alvo (default: {_PASTA_DEFAULT}).",
    )
    args = parser.parse_args(argv)

    relatorio = deduplicar_classificar(args.pasta, dry_run=not args.executar)
    modo = "EXECUTAR" if args.executar else "DRY-RUN"
    print(f"\n[Dedup _classificar -- {modo}]")
    print(f"  Preservados: {relatorio['preservados']}")
    print(f"  Removidos:   {relatorio['removidos']}")
    if relatorio["grupos"]:
        print(f"  Grupos com duplicatas: {len(relatorio['grupos'])}")
        for g in relatorio["grupos"]:
            canonico_nome = Path(g["canonico"]).name
            print(f"    - canonico: {canonico_nome}")
            for d in g["descartados"]:
                print(f"        descartado: {Path(d).name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
