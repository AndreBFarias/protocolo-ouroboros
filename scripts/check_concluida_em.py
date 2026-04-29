"""Verifica que toda spec em docs/sprints/concluidos/ tem frontmatter
`concluida_em: YYYY-MM-DD`. Sprint ANTI-MIGUE-12.

Sai com exit code != 0 se alguma spec estiver sem o campo. Sera invocado
por check_anti_migue.sh (Sprint ANTI-MIGUE-01) ou por hook pre-commit.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

CONCLUIDOS_DIR = Path("docs/sprints/concluidos")
RE_CONCLUIDA_EM = re.compile(r"^concluida_em:\s*\d{4}-\d{2}-\d{2}\s*$", re.MULTILINE)

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not CONCLUIDOS_DIR.is_dir():
        logger.error("Diretório %s não existe", CONCLUIDOS_DIR)
        return 2
    faltantes: list[Path] = []
    for spec in sorted(CONCLUIDOS_DIR.glob("*.md")):
        conteudo = spec.read_text(encoding="utf-8")
        if not RE_CONCLUIDA_EM.search(conteudo):
            faltantes.append(spec)
    total = sum(1 for _ in CONCLUIDOS_DIR.glob("*.md"))
    if faltantes:
        logger.error("[FAIL] %d/%d specs sem frontmatter concluida_em:", len(faltantes), total)
        for spec in faltantes[:10]:
            logger.error("  %s", spec.name)
        if len(faltantes) > 10:
            logger.error("  ... +%d outras", len(faltantes) - 10)
        return 1
    logger.info("[OK] %d/%d specs com frontmatter concluida_em", total, total)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Tudo o que não se mede com número, escapa." -- William Thomson, Lord Kelvin
