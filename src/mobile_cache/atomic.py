"""Helper de escrita atômica de JSON para os caches do Mobile.

Implementa o padrão `path.tmp` + `os.replace(path.tmp, path)` para
garantir que o leitor (app Mobile via SAF) jamais observe arquivo
parcial enquanto o backend desktop reescreve o cache.

ADR cruzada: ``Protocolo-Mob-Ouroboros/docs/ADRs/0012-cache-mobile-readonly.md``.

A função cria diretórios pais quando ausentes (idempotente). Em caso
de falha durante a escrita do `.tmp`, o arquivo final permanece
intacto e o `.tmp` parcial é removido para não poluir o diretório.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Escreve ``payload`` como JSON em ``path`` de forma atômica.

    Sequência:

    1. ``path.parent.mkdir(parents=True, exist_ok=True)`` -- garante
       diretório pai (cria ``.ouroboros/cache/`` quando ausente).
    2. Serializa ``payload`` via ``json.dumps`` com
       ``ensure_ascii=False`` e ``indent=2`` (UTF-8, pretty).
    3. Grava em ``<path>.tmp`` (mesmo diretório do destino, condição
       necessária para ``os.replace`` ser atômico no mesmo
       filesystem).
    4. ``os.replace(tmp, path)`` -- rename atômico no POSIX. Mesmo se
       outro processo estiver lendo ``path``, não vê arquivo parcial.

    Em caso de exceção durante a escrita do ``.tmp``, remove o
    ``.tmp`` parcial e re-levanta a exceção sem tocar em ``path``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        tmp.write_text(data, encoding="utf-8")
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass  # noqa: BLE001 -- limpeza tmp best-effort; raise propaga erro original
        raise
    os.replace(tmp, path)


# "A natureza não dá saltos." -- Gottfried Wilhelm Leibniz
