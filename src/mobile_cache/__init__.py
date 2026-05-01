"""Pacote ``mobile_cache``: geradores de cache JSON para o Mobile.

Sprint MOB-bridge-2. ADR cruzada:
``Protocolo-Mob-Ouroboros/docs/ADRs/0012-cache-mobile-readonly.md``.

Expoe ``gerar_todos(vault_root, xlsx_path)`` que dispara os dois
geradores em sequencia e devolve a lista de paths gravados:

    [<vault>/.ouroboros/cache/humor-heatmap.json,
     <vault>/.ouroboros/cache/financas-cache.json]

Layout de pacote: ``src.mobile_cache`` segue o padrao do codebase
(``src.pipeline``, ``src.inbox_processor``). A spec MOB-bridge-2
mencionava ``protocolo_ouroboros.mobile_cache``, mas o pacote
registrado em ``src/protocolo_ouroboros.egg-info/top_level.txt`` e
``src`` -- adotamos ``src.mobile_cache`` para coerencia com todos os
imports existentes (``from src.utils.pessoas import ...``).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from src.mobile_cache.atomic import write_json_atomic
from src.mobile_cache.financas_cache import gerar_financas_cache
from src.mobile_cache.humor_heatmap import gerar_humor_heatmap

__all__ = [
    "gerar_humor_heatmap",
    "gerar_financas_cache",
    "gerar_todos",
    "write_json_atomic",
]


def gerar_todos(
    vault_root: Path | str,
    xlsx_path: Path | str | None = None,
    *,
    periodo_dias: int = 90,
    referencia: date | None = None,
    gerado_em: datetime | None = None,
) -> list[Path]:
    """Gera ambos os caches JSON e devolve a lista de paths gravados.

    Parametros:
        vault_root: raiz do vault Mobile (ex.: ``~/Protocolo-Ouroboros``).
        xlsx_path: XLSX consolidado. Default
            ``<repo>/data/output/ouroboros_2026.xlsx``.
        periodo_dias: cobertura do humor-heatmap (default 90).
        referencia: data dentro da semana ISO para o financas-cache
            (default: hoje).
        gerado_em: timestamp ISO 8601 com TZ. Default: agora.

    Retorna lista com dois ``Path``: humor-heatmap, financas-cache.
    """
    vault = Path(vault_root).expanduser()
    paths: list[Path] = []
    paths.append(
        gerar_humor_heatmap(
            vault,
            periodo_dias=periodo_dias,
            gerado_em=gerado_em,
        )
    )
    paths.append(
        gerar_financas_cache(
            vault,
            xlsx_path=Path(xlsx_path) if xlsx_path is not None else None,
            referencia=referencia,
            gerado_em=gerado_em,
        )
    )
    return paths


# "Pluralitas non est ponenda sine necessitate." -- William of Ockham
