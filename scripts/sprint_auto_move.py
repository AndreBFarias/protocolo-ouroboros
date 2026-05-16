#!/usr/bin/env python3
"""Hook T3: move sprints com Status CONCLUÍDA de producao/ para concluidos/.

Rodar no pre-commit (após staging). Detecta arquivos staged em
docs/sprints/producao/ com `**Status:** CONCLUÍDA` e move
automaticamente para docs/sprints/concluidos/.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_PRODUCAO = RAIZ / "docs" / "sprints" / "producao"
DIR_CONCLUIDOS = RAIZ / "docs" / "sprints" / "concluidos"

STATUS_CONCLUÍDA = re.compile(
    r"\*\*Status:\*\*\s*(CONCLU[IÍ]DA|CONCLUÍDA)",
    re.IGNORECASE,
)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    if not DIR_PRODUCAO.exists():
        return 0

    DIR_CONCLUIDOS.mkdir(parents=True, exist_ok=True)
    movidas = 0

    for sprint_file in sorted(DIR_PRODUCAO.glob("sprint_*.md")):
        conteudo = sprint_file.read_text(encoding="utf-8")
        if not STATUS_CONCLUÍDA.search(conteudo):
            continue

        destino = DIR_CONCLUIDOS / sprint_file.name
        if destino.exists():
            continue

        shutil.move(str(sprint_file), str(destino))
        _git("add", str(destino))
        _git("rm", "--cached", str(sprint_file))
        sys.stdout.write(f"  [SPRINT-MOVE] {sprint_file.name} -> concluidos/\n")
        movidas += 1

    if movidas:
        sys.stdout.write(f"  [SPRINT-MOVE] {movidas} sprint(s) movida(s)\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Organização é liberdade." -- pragmático
