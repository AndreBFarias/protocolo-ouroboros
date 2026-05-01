"""Entry point CLI: ``python -m src.mobile_cache``.

Gera ambos os caches Mobile (humor-heatmap.json, financas-cache.json)
no Vault em ``$HOME/Protocolo-Ouroboros/.ouroboros/cache/``.

Uso:

    python -m src.mobile_cache               # vault padrao $HOME/Protocolo-Ouroboros
    python -m src.mobile_cache --vault PATH  # vault customizado
    python -m src.mobile_cache --xlsx PATH   # XLSX consolidado alternativo
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from src.mobile_cache import gerar_todos
from src.utils.logger import configurar_logger

logger = configurar_logger("mobile_cache.cli")

VAULT_PADRAO = Path(os.environ.get("OUROBOROS_VAULT", str(Path.home() / "Protocolo-Ouroboros")))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.mobile_cache",
        description="Gera caches JSON readonly consumidos pelo app Mobile.",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=VAULT_PADRAO,
        help="raiz do vault Mobile (default: $OUROBOROS_VAULT ou ~/Protocolo-Ouroboros)",
    )
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=None,
        help="XLSX consolidado (default: <repo>/data/output/ouroboros_2026.xlsx)",
    )
    parser.add_argument(
        "--periodo-dias",
        type=int,
        default=90,
        help="cobertura do humor-heatmap em dias (default 90)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.vault.exists():
        logger.warning(
            "vault inexistente em %s; gerador criara estrutura .ouroboros/cache/",
            args.vault,
        )
    paths = gerar_todos(
        vault_root=args.vault,
        xlsx_path=args.xlsx,
        periodo_dias=args.periodo_dias,
    )
    for p in paths:
        logger.info("cache gravado: %s", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "O caminho se faz ao caminhar." -- Antonio Machado
