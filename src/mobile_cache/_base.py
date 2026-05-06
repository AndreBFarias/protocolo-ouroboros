"""Base genérica dos parsers de schemas Bem-estar (Sprint UX-RD-16).

Cada schema (eventos, treinos, medidas, marcos, alarmes, contadores,
ciclo, tarefas, diario_emocional) reusa o boilerplate de varredura,
gravação atômica e CLI. O parser específico só precisa fornecer:

- nome do schema (str usada no nome do JSON e no logger)
- subpaths candidatos no vault (lista de tuplas; primeiro existente vence)
- callable ``parse_item(md_path) -> dict | None``

Todos os helpers de frontmatter (``_ler_frontmatter``,
``_normalizar_data``, ``_coerce_int``) vêm de ``humor_heatmap`` para
satisfazer o critério de reuso da Sprint UX-RD-16.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from src.mobile_cache.atomic import write_json_atomic
from src.mobile_cache.humor_heatmap import TZ_LOCAL
from src.utils.logger import configurar_logger


def gerado_em_iso(referencia: datetime | None = None) -> str:
    """Retorna ISO 8601 com timezone -03:00, microsegundos zerados."""
    momento = referencia or datetime.now(TZ_LOCAL)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=TZ_LOCAL)
    else:
        momento = momento.astimezone(TZ_LOCAL)
    return momento.replace(microsecond=0).isoformat()


def varrer_schema(
    *,
    schema: str,
    subpaths: tuple[tuple[str, ...], ...],
    parse_item: Callable[[Path], dict[str, Any] | None],
    sort_key: Callable[[dict[str, Any]], Any] | None = None,
    vault_root: Path | None,
    gerado_em: datetime | None = None,
) -> dict[str, Any]:
    """Varre o vault aplicando ``parse_item`` em cada .md das subárvores.

    Devolve payload canônico ``{schema_version, schema, gerado_em,
    vault_root, items}``. Se ``vault_root`` for ``None`` ou nenhuma
    sub-árvore existir, ``items`` é lista vazia (sem crash).
    """
    logger = configurar_logger(f"mobile_cache.{schema}")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "schema": schema,
        "gerado_em": gerado_em_iso(gerado_em),
        "vault_root": str(vault_root) if vault_root else None,
        "items": [],
    }
    if vault_root is None:
        logger.warning("vault_root ausente; cache %s vazio", schema)
        return payload
    base = Path(vault_root).expanduser().resolve()
    payload["vault_root"] = str(base)
    bases_existentes: list[Path] = []
    for sub in subpaths:
        cand = base.joinpath(*sub)
        if cand.exists():
            bases_existentes.append(cand)
    if not bases_existentes:
        logger.warning("nenhuma subpasta de %s existe sob %s", schema, base)
        return payload
    items: list[dict[str, Any]] = []
    for sub in bases_existentes:
        for md in sorted(sub.rglob("*.md")):
            item = parse_item(md)
            if item is None:
                continue
            items.append(item)
    if sort_key is not None:
        items.sort(key=sort_key)
    payload["items"] = items
    logger.info("%s: %d items", schema, len(items))
    return payload


def gerar_cache_schema(
    *,
    schema: str,
    payload: dict[str, Any],
    vault_root: Path | None,
    saida: Path | None,
) -> Path:
    """Persiste o payload em disco via ``write_json_atomic``."""
    if saida is None:
        if vault_root is not None:
            base = Path(vault_root).expanduser().resolve()
            saida = base / ".ouroboros" / "cache" / f"{schema}.json"
        else:
            saida = Path(".ouroboros") / "cache" / f"{schema}.json"
    write_json_atomic(saida, payload)
    return saida


def cli_schema(
    *,
    schema: str,
    varrer: Callable[..., dict[str, Any]],
    argv: list[str] | None = None,
) -> int:
    """CLI canônico ``--vault-root`` ``--cache``."""
    parser = argparse.ArgumentParser(
        prog=f"python -m src.mobile_cache.{schema.replace('-', '_')}",
    )
    parser.add_argument("--vault-root", type=Path, default=None)
    parser.add_argument("--cache", type=Path, default=None)
    args = parser.parse_args(argv)
    payload = varrer(args.vault_root)
    saida = gerar_cache_schema(
        schema=schema,
        payload=payload,
        vault_root=args.vault_root,
        saida=args.cache,
    )
    print(f"[{schema}] cache gravado em {saida} ({len(payload['items'])} items)")
    return 0


# "Frustra fit per plura quod potest fieri per pauciora." -- Ockham
