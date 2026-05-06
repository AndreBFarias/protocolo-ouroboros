"""Parser do schema ``medidas`` para o cache Mobile.

Varre ``<vault_root>/medidas/**/*.md`` extraindo frontmatter com
``peso`` (kg, float), ``cintura``, ``quadril``, ``peito``, ``braco``,
``coxa`` (cm, float) e ``fotos`` (lista de paths comparativos).

Cache em ``.ouroboros/cache/medidas.json``. Sprint UX-RD-16.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.mobile_cache._base import cli_schema, gerar_cache_schema, varrer_schema
from src.mobile_cache.humor_heatmap import _ler_frontmatter, _normalizar_data
from src.utils.pessoas import pessoa_id_de_legacy

SCHEMA = "medidas"
SUBPATHS = (("medidas",),)
CAMPOS_NUMERICOS = ("peso", "cintura", "quadril", "peito", "braco", "coxa")


def _coerce_float(valor: Any) -> float | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        try:
            return float(valor.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "medidas":
        return None
    data_iso = _normalizar_data(fm.get("data"))
    if data_iso is None:
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    item: dict[str, Any] = {"data": data_iso, "autor": autor}
    for campo in CAMPOS_NUMERICOS:
        item[campo] = _coerce_float(fm.get(campo))
    fotos = fm.get("fotos") or []
    if not isinstance(fotos, list):
        fotos = []
    item["fotos"] = [str(f).strip() for f in fotos if str(f).strip()]
    return item


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


# "Tudo flui, nada permanece." -- Heráclito
