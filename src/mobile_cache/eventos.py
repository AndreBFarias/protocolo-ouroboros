"""Parser do schema ``eventos`` para o cache Mobile.

Varre ``<vault_root>/eventos/**/*.md`` extraindo frontmatter com
``modo`` (positivo/negativo), ``lugar``, ``bairro``, ``com``,
``categoria``, ``fotos`` e ``intensidade``.

Cache em ``.ouroboros/cache/eventos.json``. Sprint UX-RD-16.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.mobile_cache._base import cli_schema, gerar_cache_schema, varrer_schema
from src.mobile_cache.humor_heatmap import (
    _coerce_int,
    _ler_frontmatter,
    _normalizar_data,
)
from src.utils.pessoas import pessoa_id_de_legacy

SCHEMA = "eventos"
SUBPATHS = (("eventos",),)
MODOS_VALIDOS = {"positivo", "negativo"}


def _lista_str(valor: Any) -> list[str]:
    if not isinstance(valor, list):
        return []
    return [str(v).strip() for v in valor if str(v).strip()]


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "evento":
        return None
    data_iso = _normalizar_data(fm.get("data"))
    if data_iso is None:
        return None
    modo = str(fm.get("modo", "")).strip().lower()
    if modo not in MODOS_VALIDOS:
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    return {
        "data": data_iso,
        "autor": autor,
        "modo": modo,
        "lugar": str(fm.get("lugar") or "").strip(),
        "bairro": str(fm.get("bairro") or "").strip(),
        "com": _lista_str(fm.get("com")),
        "categoria": str(fm.get("categoria") or "").strip(),
        "fotos": _lista_str(fm.get("fotos")),
        "intensidade": _coerce_int(fm.get("intensidade")),
    }


def varrer(vault_root: Path | None, *, gerado_em: datetime | None = None) -> dict[str, Any]:
    return varrer_schema(
        schema=SCHEMA,
        subpaths=SUBPATHS,
        parse_item=_parse_item,
        sort_key=lambda i: (i["data"], i["autor"]),
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


# "O que não pode ser medido, não pode ser melhorado." -- Peter Drucker
