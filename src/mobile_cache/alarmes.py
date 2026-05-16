"""Parser do schema ``alarmes`` para o cache Mobile.

Varre ``<vault_root>/alarmes/**/*.md`` extraindo frontmatter com
``horário`` (HH:MM), ``recorrência`` (diária/semanal/lista de dias),
``categoria`` e ``som``.

Cache em ``.ouroboros/cache/alarmes.json``. Sprint UX-RD-16.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.mobile_cache._base import cli_schema, gerar_cache_schema, varrer_schema
from src.mobile_cache.humor_heatmap import _ler_frontmatter
from src.utils.pessoas import pessoa_id_de_legacy

SCHEMA = "alarmes"
SUBPATHS = (("alarmes",),)


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "alarme":
        return None
    horario = str(fm.get("horario") or "").strip()
    if not horario:
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    recorrencia_raw = fm.get("recorrencia")
    if isinstance(recorrencia_raw, list):
        recorrencia: Any = [str(r).strip() for r in recorrencia_raw if str(r).strip()]
    else:
        recorrencia = str(recorrencia_raw or "").strip()
    return {
        "id": md_path.stem,
        "autor": autor,
        "horario": horario,
        "recorrencia": recorrencia,
        "categoria": str(fm.get("categoria") or "").strip(),
        "som": str(fm.get("som") or "").strip(),
        "ativo": bool(fm.get("ativo", True)),
    }


def varrer(vault_root: Path | None, *, gerado_em: datetime | None = None) -> dict[str, Any]:
    return varrer_schema(
        schema=SCHEMA,
        subpaths=SUBPATHS,
        parse_item=_parse_item,
        sort_key=lambda i: (i["horario"], i["id"]),
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
    return gerar_cache_schema(schema=SCHEMA, payload=payload, vault_root=vault_root, saida=saida)


def cli(argv: list[str] | None = None) -> int:
    return cli_schema(schema=SCHEMA, varrer=varrer, argv=argv)


if __name__ == "__main__":
    raise SystemExit(cli())


# "O tempo é o que mais queremos, mas o que pior usamos." -- William Penn
