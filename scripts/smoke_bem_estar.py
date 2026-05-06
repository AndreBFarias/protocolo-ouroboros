"""Smoke aritmético do cluster Bem-estar (Sprint UX-RD-16).

Compara, para cada um dos 9 schemas Bem-estar, ``count(items)`` no
cache JSON com ``count(*.md válidos)`` no filesystem do vault. Falha
com exit 1 se algum schema apresenta divergência.

Uso:
    python scripts/smoke_bem_estar.py                            # auto-detecta vault
    python scripts/smoke_bem_estar.py --vault-root <path>        # vault explícito
    python scripts/smoke_bem_estar.py --cache-dir <path>         # diretório de caches

Quando o vault é vazio (ou inexistente), o smoke passa com 0/0 em todos
os schemas — o invariante aqui é equivalência cache↔filesystem, não
presença de dados.

Saída literal:
    [SMOKE-BE] 9/9 schemas OK
    [SMOKE-BE] VIOLAÇÃO em <schema>: cache=N filesystem=M
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.mobile_cache.varrer_vault import descobrir_vault_root, varrer_tudo  # noqa: E402

SCHEMAS_SUBPATHS: dict[str, tuple[str, ...]] = {
    "diario-emocional": ("inbox", "mente", "diario"),
    "eventos": ("eventos",),
    "treinos": ("treinos",),
    "medidas": ("medidas",),
    "marcos": ("marcos",),
    "alarmes": ("alarmes",),
    "contadores": ("contadores",),
    "ciclo": ("ciclo",),
    "tarefas": ("tarefas",),
}


def contar_cache(cache_path: Path) -> int:
    if not cache_path.exists():
        return -1
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return -2
    items = payload.get("items")
    if not isinstance(items, list):
        return -3
    return len(items)


def contar_filesystem(vault_root: Path | None, subpath: tuple[str, ...]) -> int:
    if vault_root is None:
        return 0
    base = vault_root.joinpath(*subpath)
    if not base.exists():
        return 0
    return sum(1 for _ in base.rglob("*.md"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/smoke_bem_estar.py")
    parser.add_argument("--vault-root", type=Path, default=None)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Diretório dos caches. Default: <vault>/.ouroboros/cache/",
    )
    parser.add_argument(
        "--regenerar",
        action="store_true",
        help="Regenera caches antes de medir (usa varrer_tudo).",
    )
    args = parser.parse_args(argv)

    vault_root = args.vault_root
    if vault_root is None:
        vault_root = descobrir_vault_root()
    if vault_root is not None:
        vault_root = Path(vault_root).expanduser().resolve()
        if not vault_root.exists():
            print(f"[SMOKE-BE] aviso: vault_root inexistente ({vault_root}); seguindo com 0/0")
            vault_root = None

    if args.regenerar:
        varrer_tudo(vault_root, incluir_humor=False)

    if args.cache_dir is not None:
        cache_dir = args.cache_dir
    elif vault_root is not None:
        cache_dir = vault_root / ".ouroboros" / "cache"
    else:
        cache_dir = Path(".ouroboros") / "cache"

    violacoes: list[str] = []
    detalhes: list[str] = []
    for schema, subpath in SCHEMAS_SUBPATHS.items():
        cache_path = cache_dir / f"{schema}.json"
        cache_count = contar_cache(cache_path)
        fs_count = contar_filesystem(vault_root, subpath)
        if cache_count < 0:
            violacoes.append(f"{schema}: cache ausente/inválido ({cache_path})")
            continue
        if cache_count != fs_count:
            violacoes.append(
                f"{schema}: cache={cache_count} filesystem={fs_count}"
            )
        detalhes.append(f"  {schema}: cache={cache_count} fs={fs_count}")

    if violacoes:
        for v in violacoes:
            print(f"[SMOKE-BE] VIOLAÇÃO em {v}")
        return 1

    print(f"[SMOKE-BE] {len(SCHEMAS_SUBPATHS)}/{len(SCHEMAS_SUBPATHS)} schemas OK")
    for d in detalhes:
        print(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# "Contar é a mais antiga das ciências." -- Bertrand Russell
