#!/usr/bin/env python3
"""Hook T1: bloqueia novos print() em src/ (exceto dashboard e CLI).

Regra CLAUDE.md seção 5: nunca print() em produção. Usar logger rotacionado.
Exceções:
    - src/dashboard/ (Streamlit usa st.write, mas print é tolerável em debug)
    - scripts/ (CLI outputs são legítimos)
    - run.sh e afins (entrypoints)
    - tests/ e fixtures
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BLOCKED_DIRS = {
    "src/extractors/",
    "src/transform/",
    "src/load/",
    "src/integrations/",
    "src/projections/",
    "src/obsidian/",
    "src/irpf/",
    "src/utils/",
    "src/pipeline.py",
    "src/inbox_processor.py",
}

EXEMPT_PATTERNS = {
    "/tests/",
    "/dashboard/",
    "cli.py",
    "cli_runner.py",
    "__main__",
    "check_new_prints.py",
    "doc_generator.py",
    "validator.py",
}

PRINT_PATTERN = re.compile(r"^\s*print\s*\(")


def _is_blocked(filepath: str) -> bool:
    """Retorna True se o arquivo está em diretório bloqueado."""
    for blocked in BLOCKED_DIRS:
        if filepath == blocked or filepath.startswith(blocked):
            return True
    return False


def _get_new_prints() -> list[tuple[str, int, str]]:
    """Retorna (filepath, line_number, line) de novos print() em dirs bloqueados."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            check=False,
        )
        files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip().endswith(".py")]
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    violations = []
    for filepath in files:
        if not _is_blocked(filepath):
            continue
        if any(exempt in filepath for exempt in EXEMPT_PATTERNS):
            continue

        try:
            diff = subprocess.run(
                ["git", "diff", "--cached", "-U0", filepath],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT),
                check=False,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            continue

        line_num = 0
        for line in diff.stdout.splitlines():
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    line_num = int(match.group(1)) - 1

            if line.startswith("+") and not line.startswith("+++"):
                line_num += 1
                content = line[1:]
                if PRINT_PATTERN.match(content):
                    violations.append((filepath, line_num, content.strip()))

    return violations


def main() -> int:
    """Bloqueia commits com novos print() em diretórios protegidos."""
    violations = _get_new_prints()

    if not violations:
        return 0

    print()
    print("=" * 60)
    print("  [T1] print() proibido em produção (src/ exceto dashboard/CLI)")
    print("=" * 60)
    print()
    print("  Novos print() detectados no diff. Usar logger:")
    print("    from src.utils.logger import get_logger")
    print("    logger = get_logger(__name__)")
    print()
    for filepath, line_num, content in violations:
        print(f"  {filepath}:{line_num}: {content}")
    print()
    print("=" * 60)

    return 1


if __name__ == "__main__":
    sys.exit(main())

# "O que não se registra, não se depura." -- observabilidade 101
