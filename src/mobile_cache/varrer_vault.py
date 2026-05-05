"""Entrypoint orquestrador da varredura Bem-estar (Sprint UX-RD-16).

Invoca em sequência todos os parsers de cache Mobile do cluster
Bem-estar (9 schemas) mais o ``humor_heatmap`` herdado da MOB-bridge-2,
totalizando 10 caches JSON em ``<vault>/.ouroboros/cache/``.

CLI:

    python -m src.mobile_cache.varrer_vault [--vault-root <path>]

Se ``--vault-root`` não for fornecido, tenta a variável de ambiente
``OUROBOROS_VAULT`` e, em seguida, uma lista de candidatos canônicos.
Quando nenhum vault existe, cada parser produz cache vazio sem crash
(fallback graceful).
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.mobile_cache import (
    alarmes,
    ciclo,
    contadores,
    diario_emocional,
    eventos,
    marcos,
    medidas,
    tarefas,
    treinos,
)
from src.mobile_cache.humor_heatmap import gerar_humor_heatmap
from src.utils.logger import configurar_logger

logger = configurar_logger("mobile_cache.varrer_vault")

# Ordem de prioridade canônica para descoberta automática do vault.
CANDIDATOS_VAULT: tuple[Path, ...] = (
    Path.home() / "Protocolo-Ouroboros",
    Path.home() / "Controle de Bordo" / "Pessoal" / "Casal" / "Financeiro",
    Path.home() / "Ouroboros-Vault",
    Path.home() / "sync" / "Ouroboros",
)

# Parsers Bem-estar (9). Cada um expõe ``gerar_cache(vault_root, saida)``.
PARSERS: tuple[tuple[str, Callable[..., Path]], ...] = (
    ("diario-emocional", diario_emocional.gerar_cache),
    ("eventos", eventos.gerar_cache),
    ("treinos", treinos.gerar_cache),
    ("medidas", medidas.gerar_cache),
    ("marcos", marcos.gerar_cache),
    ("alarmes", alarmes.gerar_cache),
    ("contadores", contadores.gerar_cache),
    ("ciclo", ciclo.gerar_cache),
    ("tarefas", tarefas.gerar_cache),
)


def descobrir_vault_root() -> Path | None:
    """Resolve o vault Bem-estar via env var ou candidatos canônicos.

    Ordem:

    1. ``OUROBOROS_VAULT`` se setada e existente.
    2. Primeiro de ``CANDIDATOS_VAULT`` que existe no filesystem.
    3. ``None`` — caller deve respeitar o fallback graceful dos parsers.
    """
    env = os.environ.get("OUROBOROS_VAULT")
    if env:
        cand = Path(env).expanduser()
        if cand.exists():
            return cand
        logger.warning("OUROBOROS_VAULT setada mas não existe: %s", cand)
    for cand in CANDIDATOS_VAULT:
        if cand.exists():
            return cand
    return None


def varrer_tudo(
    vault_root: Path | None = None,
    *,
    gerado_em: datetime | None = None,
    incluir_humor: bool = True,
) -> dict[str, Path | None]:
    """Roda todos os parsers Bem-estar + humor_heatmap (opcional).

    Devolve dict ``{schema: path_do_cache | None}``. Quando
    ``vault_root`` é ``None`` ou inexistente, parsers Bem-estar geram
    cache vazio em ``./.ouroboros/cache/`` (graceful). Humor heatmap
    requer vault válido; se ausente, registra ``None``.
    """
    if vault_root is None:
        vault_root = descobrir_vault_root()
    if vault_root is not None:
        vault_root = Path(vault_root).expanduser().resolve()
        if not vault_root.exists():
            logger.warning("vault_root informado não existe: %s", vault_root)
            vault_root = None
    resultado: dict[str, Path | None] = {}
    for nome, parser in PARSERS:
        try:
            saida = parser(vault_root, gerado_em=gerado_em)
            resultado[nome] = saida
            logger.info("parser %s: cache em %s", nome, saida)
        except Exception as exc:  # noqa: BLE001 -- defesa em camadas
            logger.error("parser %s falhou: %s", nome, exc)
            resultado[nome] = None
    if incluir_humor:
        if vault_root is not None:
            try:
                resultado["humor-heatmap"] = gerar_humor_heatmap(
                    vault_root, gerado_em=gerado_em
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("humor_heatmap falhou: %s", exc)
                resultado["humor-heatmap"] = None
        else:
            logger.warning("humor-heatmap pulado: vault_root indisponível")
            resultado["humor-heatmap"] = None
    return resultado


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.mobile_cache.varrer_vault")
    parser.add_argument(
        "--vault-root",
        type=Path,
        default=None,
        help="Raiz do vault Bem-estar. Default: env OUROBOROS_VAULT ou candidatos canônicos.",
    )
    parser.add_argument(
        "--sem-humor",
        action="store_true",
        help="Pula o humor_heatmap (útil para isolar regressão Bem-estar).",
    )
    args = parser.parse_args(argv)
    resultado = varrer_tudo(args.vault_root, incluir_humor=not args.sem_humor)
    sucesso = sum(1 for p in resultado.values() if p is not None)
    total = len(resultado)
    print(f"[varrer_vault] {sucesso}/{total} caches gravados")
    for nome, path in resultado.items():
        marca = "OK" if path else "FALHA"
        print(f"  [{marca}] {nome}: {path}")
    return 0 if sucesso == total else 1


if __name__ == "__main__":
    raise SystemExit(cli())


# "O todo é maior que a soma das partes." -- Aristóteles
