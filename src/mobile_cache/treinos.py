"""Parser do schema ``treinos`` para o cache Mobile.

Varre ``<vault_root>/treinos/**/*.md`` extraindo frontmatter com
``rotina``, ``duracao_min``, ``exercicios`` (lista de dicts com nome,
series, reps, carga_kg) e ``observacoes``.

Cache em ``.ouroboros/cache/treinos.json``. Sprint UX-RD-16.
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

SCHEMA = "treinos"
SUBPATHS = (("treinos",),)


def _normalizar_exercicios(valor: Any) -> list[dict[str, Any]]:
    if not isinstance(valor, list):
        return []
    saida: list[dict[str, Any]] = []
    for ex in valor:
        if not isinstance(ex, dict):
            continue
        nome = str(ex.get("nome") or "").strip()
        if not nome:
            continue
        saida.append(
            {
                "nome": nome,
                "series": _coerce_int(ex.get("series")),
                "reps": _coerce_int(ex.get("reps")),
                "carga_kg": _coerce_int(ex.get("carga_kg")),
                "observacao": str(ex.get("observacao") or "").strip(),
            }
        )
    return saida


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "treino_sessao":
        return None
    data_iso = _normalizar_data(fm.get("data"))
    if data_iso is None:
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    return {
        "data": data_iso,
        "autor": autor,
        "rotina": str(fm.get("rotina") or "").strip(),
        "duracao_min": _coerce_int(fm.get("duracao_min")),
        "exercicios": _normalizar_exercicios(fm.get("exercicios")),
        "observacoes": str(fm.get("observacoes") or "").strip(),
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
    return gerar_cache_schema(schema=SCHEMA, payload=payload, vault_root=vault_root, saida=saida)


def cli(argv: list[str] | None = None) -> int:
    return cli_schema(schema=SCHEMA, varrer=varrer, argv=argv)


if __name__ == "__main__":
    raise SystemExit(cli())


# "O corpo é o templo do espírito." -- adágio antigo, citado por Cícero
