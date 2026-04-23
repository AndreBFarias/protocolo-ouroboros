"""Backfill de metadata.arquivo_original em nodes documento (Sprint 87.5).

Resolve a ressalva R71-1 da Sprint 71 (sync rico): nodes documento criados
por extratores antigos gravam apenas `arquivo_origem` (sem L), enquanto o
sync rico lê `arquivo_original` (com L) para montar o wikilink em
`_Attachments/`. Quando o campo está vazio, o link gerado fica quebrado.

Este módulo é ADMINISTRATIVO e rodado via `pipeline.py --backfill-metadata`.
Não faz parte do pipeline regular. É idempotente: rodar duas vezes não
produz efeito adicional na segunda execução.

Estratégias de preenchimento (nesta ordem):
1. Nó já tem `arquivo_original` não-vazio -> skip.
2. Nó tem `arquivo_origem` (convenção antiga) -> copia para `arquivo_original`.
3. Heurística por sha256: se `metadata.sha256` existir, calcula o sha256
   completo de cada candidato em `data/raw/` e casa. Cache local evita
   recomputar o mesmo arquivo duas vezes.
4. Heurística por nome canônico: se `nome_canonico` tem pelo menos 6
   caracteres e é substring case-insensitive de algum `Path.stem`, casa.

Armadilha: extratores antigos re-gravam `arquivo_origem` em cada ingestão,
mas o merge raso de `upsert_node` (`meta_unificado = {**existente, **novo}`)
preserva `arquivo_original` desde que o novo dict não traga essa chave.
Confirmado em `src/graph/db.py:135`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from src.graph.db import GrafoDB
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.backfill_arquivo_original")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_RAIZ_RAW_PADRAO: Path = _RAIZ_REPO / "data" / "raw"

# Nome canônico muito curto gera falsos-positivos em substring match.
_TAMANHO_MIN_NOME = 6


def _calcular_sha256(caminho: Path, cache: dict[Path, str]) -> str:
    """sha256 do arquivo inteiro com cache local para evitar recomputo."""
    if caminho in cache:
        return cache[caminho]
    hasher = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(65536), b""):
            hasher.update(bloco)
    digest = hasher.hexdigest()
    cache[caminho] = digest
    return digest


def _localizar_por_sha256(
    sha_alvo: str, arquivos: list[Path], cache: dict[Path, str]
) -> Path | None:
    """Varre `arquivos` computando sha256 até achar match. Aceita match por
    prefixo quando `sha_alvo` tem menos de 64 caracteres (alguns extratores
    guardam apenas os 16 primeiros por motivo de compactação)."""
    sha_alvo = sha_alvo.lower().strip()
    if not sha_alvo:
        return None
    prefixo = len(sha_alvo) < 64
    for arquivo in arquivos:
        sha = _calcular_sha256(arquivo, cache)
        if prefixo:
            if sha.startswith(sha_alvo):
                return arquivo
        elif sha == sha_alvo:
            return arquivo
    return None


def _localizar_por_nome(nome_canonico: str, arquivos: list[Path]) -> Path | None:
    """Procura arquivo cujo `Path.stem` contém `nome_canonico` (case-insensitive).

    Retorna None se o nome for curto demais (evita falsos-positivos) ou se
    houver múltiplos matches (ambíguo demais para escolher automaticamente)."""
    chave = nome_canonico.strip().lower()
    if len(chave) < _TAMANHO_MIN_NOME:
        return None
    candidatos = [a for a in arquivos if chave in a.stem.lower()]
    if len(candidatos) == 1:
        return candidatos[0]
    return None


def _listar_arquivos_raw(raiz: Path) -> list[Path]:
    """Varre recursivamente `raiz` e devolve todos os arquivos regulares."""
    if not raiz.exists():
        return []
    return [p for p in raiz.rglob("*") if p.is_file()]


def backfill_arquivo_original(
    db: GrafoDB, raiz_raw: Path | None = None
) -> dict[str, Any]:
    """Backfill de `metadata.arquivo_original` em nodes documento.

    Idempotente: segunda execução devolve `ja_preenchidos == total` e
    zero nos demais contadores.

    Args:
        db: instância aberta de GrafoDB.
        raiz_raw: raiz da varredura heurística (default: `data/raw/` do repo).

    Returns:
        dict com contadores:
        - total: quantidade de nodes documento.
        - ja_preenchidos: nodes que já tinham `arquivo_original` válido.
        - backfill_por_origem: copiados de `arquivo_origem`.
        - backfill_por_sha256: achados via hash.
        - backfill_por_heuristica: achados via substring de nome canônico.
        - nao_encontrados: nenhuma estratégia funcionou.
    """
    raiz = raiz_raw if raiz_raw is not None else _RAIZ_RAW_PADRAO
    stats: dict[str, int] = {
        "total": 0,
        "ja_preenchidos": 0,
        "backfill_por_origem": 0,
        "backfill_por_sha256": 0,
        "backfill_por_heuristica": 0,
        "nao_encontrados": 0,
    }

    nodes = db.listar_nodes(tipo="documento")
    stats["total"] = len(nodes)
    if not nodes:
        logger.info("nenhum node documento no grafo; nada a fazer")
        return stats

    arquivos_raw: list[Path] | None = None
    cache_sha: dict[Path, str] = {}

    for node in nodes:
        meta: dict[str, Any] = dict(node.metadata or {})

        atual = meta.get("arquivo_original")
        if isinstance(atual, str) and atual.strip():
            stats["ja_preenchidos"] += 1
            continue

        origem = meta.get("arquivo_origem")
        if isinstance(origem, str) and origem.strip():
            meta["arquivo_original"] = origem
            db.upsert_node(
                tipo=node.tipo,
                nome_canonico=node.nome_canonico,
                metadata=meta,
                aliases=list(node.aliases or []),
            )
            stats["backfill_por_origem"] += 1
            continue

        if arquivos_raw is None:
            arquivos_raw = _listar_arquivos_raw(raiz)

        sha_alvo = meta.get("sha256")
        achado: Path | None = None
        estrategia: str | None = None
        if isinstance(sha_alvo, str) and sha_alvo.strip() and arquivos_raw:
            achado = _localizar_por_sha256(sha_alvo, arquivos_raw, cache_sha)
            if achado is not None:
                estrategia = "sha256"

        if achado is None and arquivos_raw:
            achado = _localizar_por_nome(node.nome_canonico, arquivos_raw)
            if achado is not None:
                estrategia = "heuristica"

        if achado is None:
            stats["nao_encontrados"] += 1
            logger.warning(
                "documento sem arquivo_original e sem pista: id=%s nome=%s",
                node.id,
                node.nome_canonico,
            )
            continue

        meta["arquivo_original"] = str(achado.resolve())
        db.upsert_node(
            tipo=node.tipo,
            nome_canonico=node.nome_canonico,
            metadata=meta,
            aliases=list(node.aliases or []),
        )
        if estrategia == "sha256":
            stats["backfill_por_sha256"] += 1
        else:
            stats["backfill_por_heuristica"] += 1

    logger.info("backfill concluído: %s", stats)
    return stats


# "O que não tem nome não pode ser procurado." -- Lao-Tsé
