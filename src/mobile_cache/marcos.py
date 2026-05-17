"""Parser do schema ``marcos`` para o cache Mobile.

Varre ``<vault_root>/marcos/**/*.md`` extraindo frontmatter com
``descrição``, ``tags`` (lista) e ``auto`` (bool — manual vs gerado
por ``gerar_marcos_auto``). O título canônico vem do nome do arquivo
ou do campo ``titulo`` quando presente.

Cache em ``.ouroboros/cache/marcos.json``. Sprint UX-RD-16.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.mobile_cache._base import cli_schema, gerar_cache_schema, varrer_schema
from src.mobile_cache.humor_heatmap import _ler_frontmatter, _normalizar_data
from src.utils.pessoas import pessoa_id_de_legacy

SCHEMA = "marcos"
# H2 (ADR-0023 do Mobile): ``markdown/`` é o layout-por-tipo canônico
# pós-migração; ``marcos/`` é o legado pre-H2. Ambos varridos em união
# pelo ``_base.varrer_schema`` -- vault que tem só um deles funciona,
# vault em migração intermediária (raro) funciona somando os dois.
SUBPATHS = (("markdown",), ("marcos",))
FILENAME_PREFIXES_H2: tuple[str, ...] = ("marco-",)


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    # Em layout H2 (markdown/), arquivos compartilham a pasta entre tipos
    # diferentes. Filtra rapidamente por prefixo para evitar abrir YAML
    # de arquivos não-marco (eventos, humor, etc.). Layout legado
    # (marcos/<file>) não tem essa restrição -- discriminador é só
    # ``tipo:`` no frontmatter.
    if md_path.parent.name == "markdown" and not md_path.name.startswith(FILENAME_PREFIXES_H2):
        return None
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "marco":
        return None
    data_iso = _normalizar_data(fm.get("data"))
    if data_iso is None:
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    auto_raw = fm.get("auto")
    if isinstance(auto_raw, bool):
        auto = auto_raw
    elif isinstance(auto_raw, str):
        auto = auto_raw.strip().lower() in {"true", "1", "sim", "yes"}
    else:
        auto = False
    titulo = str(fm.get("titulo") or md_path.stem).strip()
    tags_raw = fm.get("tags") or []
    if not isinstance(tags_raw, list):
        tags_raw = []
    return {
        "data": data_iso,
        "autor": autor,
        "titulo": titulo,
        "descricao": str(fm.get("descricao") or "").strip(),
        "tags": [str(t).strip() for t in tags_raw if str(t).strip()],
        "auto": auto,
    }


def varrer(vault_root: Path | None, *, gerado_em: datetime | None = None) -> dict[str, Any]:
    return varrer_schema(
        schema=SCHEMA,
        subpaths=SUBPATHS,
        parse_item=_parse_item,
        sort_key=lambda i: (i["data"], i["titulo"]),
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


# "Memória é o tesouro e guardião de todas as coisas." -- Cícero
