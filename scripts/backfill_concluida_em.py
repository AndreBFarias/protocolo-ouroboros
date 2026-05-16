"""Backfill de frontmatter `concluida_em: YYYY-MM-DD` em sprints concluidas.

Sprint ANTI-MIGUE-12 -- plan pure-swinging-mitten (auditoria honesta 2026-04-29).

Para cada spec em docs/sprints/concluidos/*.md, infere a data de conclusao
a partir do primeiro commit que adicionou ou renomeou o arquivo para esse
path (git log --diff-filter=AR -- <path> | tail -1). Aplica frontmatter
no topo se ainda não houver. Idempotente: rodar duas vezes não duplica.

Uso:
    python scripts/backfill_concluida_em.py            # dry-run, lista alvos
    python scripts/backfill_concluida_em.py --executar # aplica frontmatter
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

CONCLUIDOS_DIR = Path("docs/sprints/concluidos")
RE_FRONTMATTER_INICIO = re.compile(r"^---\s*$", re.MULTILINE)
RE_CONCLUIDA_EM = re.compile(r"^concluida_em:\s*\d{4}-\d{2}-\d{2}\s*$", re.MULTILINE)

logger = logging.getLogger(__name__)


def data_de_conclusao_via_git(path: Path) -> str | None:
    """Retorna ISO date YYYY-MM-DD do primeiro commit que adicionou ou
    renomeou o arquivo para o path concluido. None se não achou."""
    cmd = [
        "git",
        "log",
        "--diff-filter=AR",
        "--format=%aI",
        "--",
        str(path),
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if resultado.returncode != 0 or not resultado.stdout.strip():
        return None
    linhas = [linha.strip() for linha in resultado.stdout.splitlines() if linha.strip()]
    if not linhas:
        return None
    iso_completo = linhas[-1]
    return iso_completo[:10]


def ja_tem_frontmatter_concluida(conteudo: str) -> bool:
    return bool(RE_CONCLUIDA_EM.search(conteudo))


def aplicar_frontmatter(conteudo: str, data_iso: str) -> str:
    """Insere frontmatter no topo. Se ja existe frontmatter sem
    concluida_em, adiciona o campo dentro dele."""
    matches = list(RE_FRONTMATTER_INICIO.finditer(conteudo))
    if len(matches) >= 2 and matches[0].start() == 0:
        primeiro_fim = matches[1].start()
        bloco_frontmatter = conteudo[:primeiro_fim]
        resto = conteudo[primeiro_fim:]
        if "concluida_em:" in bloco_frontmatter:
            return conteudo
        novo_bloco = bloco_frontmatter.rstrip() + f"\nconcluida_em: {data_iso}\n"
        return novo_bloco + resto
    novo_frontmatter = f"---\nconcluida_em: {data_iso}\n---\n\n"
    return novo_frontmatter + conteudo


def processar_spec(path: Path, executar: bool) -> str:
    conteudo = path.read_text(encoding="utf-8")
    if ja_tem_frontmatter_concluida(conteudo):
        return "SKIP_JA_TEM"
    data_iso = data_de_conclusao_via_git(path)
    if data_iso is None:
        return "SKIP_SEM_HISTORICO_GIT"
    novo = aplicar_frontmatter(conteudo, data_iso)
    if novo == conteudo:
        return "SKIP_SEM_MUDANCA"
    if executar:
        path.write_text(novo, encoding="utf-8")
        return f"APLICADO_{data_iso}"
    return f"DRY_RUN_{data_iso}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Aplica frontmatter (sem flag, apenas dry-run).",
    )
    parser.add_argument(
        "--diretorio",
        type=Path,
        default=CONCLUIDOS_DIR,
        help=f"Diretório com specs concluidas (default: {CONCLUIDOS_DIR}).",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.diretorio.is_dir():
        logger.error("Diretório não existe: %s", args.diretorio)
        return 2

    contagem: dict[str, int] = {}
    aplicados = 0
    for spec in sorted(args.diretorio.glob("*.md")):
        resultado = processar_spec(spec, args.executar)
        if resultado.startswith("APLICADO") or resultado.startswith("DRY"):
            chave = resultado.split("_")[0]
        else:
            chave = resultado
        contagem[chave] = contagem.get(chave, 0) + 1
        if args.executar and resultado.startswith("APLICADO"):
            aplicados += 1
            logger.info("[OK] %s -> %s", spec.name, resultado)
        elif resultado.startswith("DRY_RUN"):
            logger.info("[DRY] %s -> %s", spec.name, resultado)
        elif resultado == "SKIP_SEM_HISTORICO_GIT":
            logger.warning("[WARN] %s sem historico git", spec.name)

    logger.info("=== Resumo ===")
    for chave, qtd in sorted(contagem.items()):
        logger.info("  %s: %d", chave, qtd)
    if args.executar:
        logger.info("Total aplicado: %d", aplicados)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "O passado não e um lugar onde se pode chegar, mas um lugar de onde se vem." -- Walter Benjamin
