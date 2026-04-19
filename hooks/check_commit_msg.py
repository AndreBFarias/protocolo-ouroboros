#!/usr/bin/env python3
"""Hook commit-msg T1: valida formato conventional commits em PT-BR.

Formato obrigatório: tipo: descrição imperativa
Tipos aceitos: feat, fix, refactor, docs, test, perf, chore, build, ci

Uso:
    python3 hooks/check_commit_msg.py <commit-msg-file>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VALID_TYPES = {
    "feat",
    "fix",
    "refactor",
    "docs",
    "test",
    "perf",
    "chore",
    "build",
    "ci",
}

COMMIT_PATTERN = re.compile(r"^(" + "|".join(VALID_TYPES) + r")(\([a-z0-9_-]+\))?: .{3,}$")

MERGE_PATTERN = re.compile(r"^Merge (branch|pull request|remote-tracking)")
REVERT_PATTERN = re.compile(r"^Revert ")


def main() -> int:
    """Valida a mensagem de commit conforme Conventional Commits PT-BR."""
    if len(sys.argv) < 2:
        return 0

    msg_file = Path(sys.argv[1])
    if not msg_file.exists():
        return 0

    lines = msg_file.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return 0

    first_line = lines[0].strip()

    if MERGE_PATTERN.match(first_line):
        return 0

    if REVERT_PATTERN.match(first_line):
        return 0

    if COMMIT_PATTERN.match(first_line):
        return 0

    print()
    print("=" * 60)
    print("  [T1] Formato de commit inválido")
    print("=" * 60)
    print()
    print(f"  Mensagem: {first_line}")
    print()
    print("  Formato obrigatório: tipo: descrição imperativa")
    print(f"  Tipos aceitos: {', '.join(sorted(VALID_TYPES))}")
    print()
    print("  Exemplos válidos:")
    print("    feat: adiciona extrator de energia via OCR")
    print("    fix: corrige deduplicação por UUID no Nubank CC")
    print("    docs: atualiza roadmap de sprints 26-29")
    print("    refactor(pipeline): extrai categorizer para módulo próprio")
    print()
    print("=" * 60)

    return 1


if __name__ == "__main__":
    sys.exit(main())

# "Quem não nomeia, não controla." -- taxonomia de commits
