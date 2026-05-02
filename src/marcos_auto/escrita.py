"""Escrita atômica de Markdown com frontmatter YAML (Sprint MOB-bridge-3).

Reaproveita o padrão ``path.tmp`` + ``os.replace`` consolidado em
``src/mobile_cache/atomic.py`` (MOB-bridge-2), adaptando a
serialização: em vez de JSON, gravamos Markdown com frontmatter
YAML conforme ``MarcoSchema`` Mobile.

Layout do arquivo gerado:

    ---
    tipo: marco
    data: <ISO>
    autor: <pessoa_a | pessoa_b | casal>
    descricao: <texto seco>  # noqa: accent
    tags: [auto, treino|humor|emocional]
    auto: true
    origem: backend
    hash: <12 chars>
    ---

    <body opcional, geralmente vazio>

ADR cruzada: Protocolo-Mob-Ouroboros/docs/ADRs/0012-cache-mobile-readonly.md
(estende padrão atômico para arquivos de marco gravados em
``marcos/`` no Vault, ainda fora do diretório de cache mas seguindo
a mesma disciplina anti-leitura-parcial).

Função pública:

    write_md_atomic(path, frontmatter, body) -> None
        Escreve ``path`` com frontmatter YAML serializado +
        body opcional. Diretório pai é criado se ausente.
        ``.tmp`` parcial removido em caso de falha; ``path``
        final permanece intacto até o ``os.replace`` final.

Idempotência: o caller é responsável por verificar se o arquivo
já existe antes de chamar (decisão de não sobrescrever marco
manual cabe ao orquestrador, não ao writer).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import yaml


def write_md_atomic(
    path: Path,
    frontmatter: Mapping[str, Any],
    body: str = "",
) -> None:
    """Grava ``path`` com frontmatter YAML + body de forma atômica.

    Sequência:

    1. ``path.parent.mkdir(parents=True, exist_ok=True)``.
    2. Serializa ``frontmatter`` via ``yaml.safe_dump`` com
       ``allow_unicode=True``, ``sort_keys=False``.
    3. Monta o conteúdo: ``"---\\n" + yaml + "---\\n\\n" + body``.
       Se ``body`` for vazio, fica ``"---\\n" + yaml + "---\\n"``.
    4. Grava em ``<path>.tmp``.
    5. ``os.replace(tmp, path)`` -- rename atômico no POSIX.

    Em caso de exceção durante a escrita do ``.tmp``, remove o
    ``.tmp`` parcial e re-levanta a exceção sem tocar em ``path``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    yaml_bloco = yaml.safe_dump(
        dict(frontmatter),
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    if body:
        conteudo = f"---\n{yaml_bloco}---\n\n{body}\n"
    else:
        conteudo = f"---\n{yaml_bloco}---\n"
    try:
        tmp.write_text(conteudo, encoding="utf-8")
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
    os.replace(tmp, path)


# "A escrita é o pensamento condensado." -- Vilém Flusser
