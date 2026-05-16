"""Parser do schema ``tarefas`` para o cache Mobile.

Varre ``<vault_root>/tarefas/**/*.md`` extraindo frontmatter com
``título``, ``prioridade`` (baixa/média/alta), ``prazo`` e
``concluída`` (bool).

Cache em ``.ouroboros/cache/tarefas.json``. Sprint UX-RD-16. Schema
leve, deliberadamente sem subtarefas (Mobile usa o cache como to-do
linear; gestão complexa fica no desktop).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.mobile_cache._base import cli_schema, gerar_cache_schema, varrer_schema
from src.mobile_cache.humor_heatmap import _ler_frontmatter, _normalizar_data
from src.utils.pessoas import pessoa_id_de_legacy

SCHEMA = "tarefas"
SUBPATHS = (("tarefas",),)
PRIORIDADES_VALIDAS = {"baixa", "media", "alta"}


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "tarefa":
        return None
    titulo = str(fm.get("titulo") or "").strip()
    if not titulo:
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    prioridade = str(fm.get("prioridade") or "media").strip().lower()
    if prioridade not in PRIORIDADES_VALIDAS:
        prioridade = "media"
    concluida_raw = fm.get("concluida", False)
    if isinstance(concluida_raw, bool):
        concluida = concluida_raw
    elif isinstance(concluida_raw, str):
        concluida = concluida_raw.strip().lower() in {"true", "1", "sim", "yes"}
    else:
        concluida = False
    return {
        "id": md_path.stem,
        "autor": autor,
        "titulo": titulo,
        "prioridade": prioridade,
        "prazo": _normalizar_data(fm.get("prazo")),
        "concluida": concluida,
    }


def varrer(vault_root: Path | None, *, gerado_em: datetime | None = None) -> dict[str, Any]:
    return varrer_schema(
        schema=SCHEMA,
        subpaths=SUBPATHS,
        parse_item=_parse_item,
        sort_key=lambda i: (i["concluida"], i["prazo"] or "9999-99-99", i["id"]),
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


# "A jornada de mil léguas começa com um único passo." -- Lao-Tsé
