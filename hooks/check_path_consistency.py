#!/usr/bin/env python3
"""Hook pre-commit para bloquear paths obsoletos.

Bloqueia commits que referenciam paths antigos/removidos do Ouroboros:
  - "controle_de_bordo" (nome antigo antes do rebranding -- Sprint 12)
  - "financas.xlsx" (nome antigo do output)
  - "data/raw/pessoa/" raiz (deve ser data/raw/{andre,vitoria}/{banco}/)

Uso:
    python3 hooks/check_path_consistency.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

OBSOLETE_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Só casa quando 'controle_de_bordo' aparece num path/módulo Python
    # (evita falso-positivo em docs que citam outro projeto 'Controle_de_Bordo_OS')
    (
        re.compile(r"""(?:from|import)\s+controle_de_bordo|["']controle_de_bordo/"""),
        "protocolo-ouroboros",
        "Módulo antigo (antes do rebranding -- Sprint 12). Use 'src.' ou 'protocolo_ouroboros'",
    ),
    (
        re.compile(r"""["']?financas\.xlsx["']?"""),
        "ouroboros_YYYY.xlsx",
        "Nome antigo do output. Use 'ouroboros_2026.xlsx' ou equivalente",
    ),
    (
        re.compile(r"""["']data/raw/pessoa/"""),
        "data/raw/{andre|vitoria}/{banco}/",
        "Path inválido. Estrutura correta: data/raw/{pessoa}/{banco}/",
    ),
]

IGNORE_FILES = {
    ".gitignore",
    "CLAUDE.md",
    "GSD.md",
    "check_path_consistency.py",
    "check_acentuacao.py",
}


def get_staged_files() -> list[str]:
    """Retorna arquivos staged no git."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def get_staged_diff(filepath: str) -> str:
    """Retorna diff staged de um arquivo."""
    result = subprocess.run(
        ["git", "diff", "--cached", "-U0", filepath],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def check_file(filepath: str) -> list[str]:
    """Retorna violações detectadas no diff staged do arquivo."""
    if Path(filepath).name in IGNORE_FILES:
        return []
    if not filepath.endswith((".py", ".sh", ".md", ".yaml", ".yml")):
        return []

    diff = get_staged_diff(filepath)
    violations = []

    for line in diff.split("\n"):
        if not line.startswith("+") or line.startswith("+++"):
            continue

        for pattern, correct_path, message in OBSOLETE_PATTERNS:
            if pattern.search(line):
                violations.append(
                    f"  {filepath}: {message}\n    Encontrado: {line.strip()}\n    Use: {correct_path}"
                )

    return violations


def main() -> int:
    """Bloqueia commits com paths obsoletos nas linhas adicionadas."""
    files = get_staged_files()
    if not files:
        return 0

    all_violations = []
    for f in files:
        all_violations.extend(check_file(f))

    if all_violations:
        print("[BLOQUEADO] Paths obsoletos detectados:")
        print()
        for v in all_violations:
            print(v)
        print()
        print("Consulte: docs/sprints/sprint_12_rebranding.md")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

# "O caminho mais curto entre dois pontos é a linha reta -- mas só se o terreno for honesto." -- provérbio pragmático
