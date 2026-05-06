"""Parser do schema ``contadores`` para o cache Mobile.

Varre ``<vault_root>/contadores/**/*.md`` extraindo frontmatter com
``nome`` (rótulo amigável), ``data_inicio`` e ``ultima_reset``. O
contador "Dias sem X" é calculado pelo Mobile a partir de
``ultima_reset``; aqui apenas exportamos os campos.

Cache em ``.ouroboros/cache/contadores.json``. Sprint UX-RD-16.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.mobile_cache._base import cli_schema, gerar_cache_schema, varrer_schema
from src.mobile_cache.humor_heatmap import _ler_frontmatter, _normalizar_data
from src.utils.pessoas import pessoa_id_de_legacy

SCHEMA = "contadores"
SUBPATHS = (("contadores",),)


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "contador":
        return None
    nome = str(fm.get("nome") or "").strip()
    if not nome:
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    return {
        "id": md_path.stem,
        "autor": autor,
        "nome": nome,
        "data_inicio": _normalizar_data(fm.get("data_inicio")),
        "ultima_reset": _normalizar_data(fm.get("ultima_reset")),
        "categoria": str(fm.get("categoria") or "").strip(),
    }


def varrer(vault_root: Path | None, *, gerado_em: datetime | None = None) -> dict[str, Any]:
    return varrer_schema(
        schema=SCHEMA,
        subpaths=SUBPATHS,
        parse_item=_parse_item,
        sort_key=lambda i: (i["nome"], i["id"]),
        vault_root=vault_root,
        gerado_em=gerado_em,
    )


def gerar_cache(
    vault_root: Path | None,
    saida: Path | None = None,
    *,
    gerado_em: datetime | None = None,
) -> Path:
    payload = varrer(vault_root, gerado_em=gerado_em)
    return gerar_cache_schema(
        schema=SCHEMA, payload=payload, vault_root=vault_root, saida=saida
    )


def cli(argv: list[str] | None = None) -> int:
    return cli_schema(schema=SCHEMA, varrer=varrer, argv=argv)


if __name__ == "__main__":
    raise SystemExit(cli())


# "Não conte os dias, faça os dias contarem." -- Muhammad Ali
