"""Parser do schema ``diario_emocional`` para o cache Mobile.

Varre arquivos em ``<vault_root>/inbox/mente/diario/**/*.md`` extraindo
frontmatter YAML com campos ``modo`` (trigger/vitoria), ``emocoes``,
``intensidade`` (1-5), ``com`` e ``texto``.

Cache em ``.ouroboros/cache/diario-emocional.json``. Sprint UX-RD-16.
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

SCHEMA = "diario-emocional"
SUBPATHS = (("inbox", "mente", "diario"),)
MODOS_VALIDOS = {"trigger", "vitoria"}


def _parse_item(md_path: Path) -> dict[str, Any] | None:
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() != "diario_emocional":
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
    intensidade = _coerce_int(fm.get("intensidade"))
    emocoes_raw = fm.get("emocoes") or []
    if not isinstance(emocoes_raw, list):
        emocoes_raw = []
    emocoes = [str(e).strip() for e in emocoes_raw if str(e).strip()]
    com_raw = fm.get("com") or []
    if not isinstance(com_raw, list):
        com_raw = []
    com = [str(c).strip() for c in com_raw if str(c).strip()]
    texto = str(fm.get("texto") or "").strip()
    return {
        "data": data_iso,
        "autor": autor,
        "modo": modo,
        "emocoes": emocoes,
        "intensidade": intensidade,
        "com": com,
        "texto": texto,
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


# "A vida não examinada não vale a pena ser vivida." -- Sócrates
