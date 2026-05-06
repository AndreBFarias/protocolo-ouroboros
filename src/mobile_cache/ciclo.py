"""Parser do schema ``ciclo`` (ciclo menstrual) para o cache Mobile.

Varre ``<vault_root>/ciclo/**/*.md`` extraindo frontmatter com
``fase`` (menstrual/folicular/ovulacao/lutea), ``sintomas`` (lista) e
``observacoes``.

Cache em ``.ouroboros/cache/ciclo.json``. Sprint UX-RD-16. Apenas a
autora ``pessoa_b`` registra ciclo neste vault, mas o parser respeita
qualquer autor válido (pessoa_a/pessoa_b/casal) sem hardcodar gênero.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.mobile_cache._base import cli_schema, gerar_cache_schema, varrer_schema
from src.mobile_cache.humor_heatmap import _ler_frontmatter, _normalizar_data
from src.utils.pessoas import pessoa_id_de_legacy

SCHEMA = "ciclo"
SUBPATHS = (("ciclo",),)
FASES_VALIDAS = {"menstrual", "folicular", "ovulacao", "lutea"}


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "ciclo":
        return None
    data_iso = _normalizar_data(fm.get("data"))
    if data_iso is None:
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    fase = str(fm.get("fase") or "").strip().lower()
    if fase and fase not in FASES_VALIDAS:
        # Aceita registros sem fase declarada (acompanhamento solto).
        fase = ""
    sintomas_raw = fm.get("sintomas") or []
    if not isinstance(sintomas_raw, list):
        sintomas_raw = []
    return {
        "data": data_iso,
        "autor": autor,
        "fase": fase,
        "sintomas": [str(s).strip() for s in sintomas_raw if str(s).strip()],
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
    return gerar_cache_schema(
        schema=SCHEMA, payload=payload, vault_root=vault_root, saida=saida
    )


def cli(argv: list[str] | None = None) -> int:
    return cli_schema(schema=SCHEMA, varrer=varrer, argv=argv)


if __name__ == "__main__":
    raise SystemExit(cli())


# "Os ciclos da natureza são também os ciclos da vida." -- Hesíodo
