"""Pacote ``marcos_auto``: gerador de marcos automáticos (Sprint MOB-bridge-3).

Detecta marcos a partir de heurísticas que correm sobre ``treinos/``,
``daily/``, ``inbox/mente/diario/`` e ``eventos/`` no Vault Mobile.
Cada marco é gravado em ``marcos/<data>-auto-<hash>.md`` de forma
idempotente: rodar duas vezes não duplica arquivo, e marcos manuais
existentes nunca são sobrescritos (filename ``-auto-`` é distinto
do padrão manual ``<data>-<descricao-curta>.md``).  # noqa: accent

ADR cruzada: Protocolo-Mob-Ouroboros/docs/ADRs/0013-marcos-auto.md
(simétrica no client M11). Cooperação client/backend: o app Mobile
implementa heurísticas equivalentes com o MESMO algoritmo de hash.
Ambos podem rodar; arquivos nunca duplicam.

API pública:

    gerar_marcos_auto(vault_root) -> list[Path]
        Lista os eventos do Vault, aplica todas as heurísticas
        registradas em ``HEURISTICAS_DISPONIVEIS``, calcula hash
        de cada marco, escreve arquivos novos em ``marcos/`` e
        devolve a lista de paths gravados nesta execução.

Decisões da spec MOB-bridge-3:

    - Heurísticas são funções puras em ``heuristicas.py`` (sem I/O).
    - Hash dedup em ``dedup.py::hash_marco``.
    - Escrita atômica em ``escrita.py::write_md_atomic``.
    - Parser de frontmatter em ``parser.py``.
    - Marcos não sobrescritos: arquivo já existente é skip.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.marcos_auto.dedup import hash_marco
from src.marcos_auto.escrita import write_md_atomic
from src.marcos_auto.heuristicas import HEURISTICAS_DISPONIVEIS
from src.marcos_auto.parser import listar_frontmatters
from src.utils.logger import configurar_logger

logger = configurar_logger("marcos_auto")

__all__ = [
    "gerar_marcos_auto",
    "hash_marco",
    "write_md_atomic",
    "HEURISTICAS_DISPONIVEIS",
]


# Diretórios do Vault inspecionados pelas heurísticas. Ordem não
# importa (heurísticas filtram por ``tipo`` no dict).
_FONTES = (
    "treinos",
    "daily",
    "eventos",
    "inbox/mente/diario",
)


def _coletar_eventos(vault_root: Path) -> list[dict[str, Any]]:
    """Lista frontmatters de todas as fontes do Vault.

    Para cada diretório-fonte inexistente, simplesmente devolve lista
    vazia (Vault recém-criado não é erro). Eventos malformados são
    ignorados pelo parser silenciosamente.
    """
    eventos: list[dict[str, Any]] = []
    for relativo in _FONTES:
        diretorio = vault_root / relativo
        eventos.extend(listar_frontmatters(diretorio))
    return eventos


def _data_para_dia(valor: Any) -> str:
    """Converte ``data`` ISO (date ou datetime ou string) para ``YYYY-MM-DD``.

    Usado apenas para compor o filename ``<data>-auto-<hash>.md``.
    O campo ``data`` no frontmatter preserva o formato original
    devolvido pela heurística (já em ISO 8601 string).
    """
    s = str(valor)
    return s[:10]


def gerar_marcos_auto(vault_root: Path | str) -> list[Path]:
    """Gera marcos automáticos no Vault. Devolve paths gravados nesta execução.

    Pipeline:

    1. Coleta frontmatters de ``treinos/``, ``daily/``, ``eventos/``
       e ``inbox/mente/diario/``.
    2. Aplica cada heurística registrada em ``HEURISTICAS_DISPONIVEIS``.
    3. Para cada marco gerado: calcula hash, monta filename
       ``<data>-auto-<hash>.md``. Se arquivo já existe em
       ``marcos/``, pula (idempotência). Caso contrário, escreve
       via ``write_md_atomic``.
    4. Devolve a lista de paths efetivamente gravados.

    Marcos manuais existentes (com nome diferente) NUNCA são tocados:
    o filename ``-auto-`` é distintivo. Marcos auto pré-existentes
    com mesmo hash também são preservados (idempotência via filename).
    """
    vault = Path(vault_root).expanduser()
    eventos = _coletar_eventos(vault)
    logger.info("marcos_auto: %d eventos coletados de %s", len(eventos), vault)
    diretorio_marcos = vault / "marcos"
    diretorio_marcos.mkdir(parents=True, exist_ok=True)
    gravados: list[Path] = []
    for heuristica in HEURISTICAS_DISPONIVEIS:
        try:
            detectados = heuristica(eventos)
        except Exception as exc:
            # Heurística defeituosa não deve derrubar o pipeline inteiro.
            # Logamos e seguimos para a próxima.
            logger.warning(
                "heuristica %s falhou: %s",
                heuristica.__name__,
                exc,
            )
            continue
        for marco in detectados:
            h = hash_marco(marco)
            dia = _data_para_dia(marco["data"])
            destino = diretorio_marcos / f"{dia}-auto-{h}.md"
            if destino.exists():
                continue
            frontmatter = dict(marco)
            frontmatter["hash"] = h
            write_md_atomic(destino, frontmatter, body="")
            gravados.append(destino)
    logger.info(
        "marcos_auto: %d marcos novos gravados em %s",
        len(gravados),
        diretorio_marcos,
    )
    return gravados


# "O eterno retorno é a forma do sentido que se reconhece em si." -- Friedrich Nietzsche
