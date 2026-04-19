#!/usr/bin/env python3
"""Hook pre-commit: análise de diff contra padrões de burla.

Regra CLAUDE.md seção 3: nunca TODO/FIXME inline (criar issue), error
handling explícito, nunca código comentado.

Bloqueia commit se detectar em linhas NOVAS (adicionadas):
- TODO/FIXME/HACK/XXX inline
- Testes desabilitados (@pytest.mark.skip)
- Except vazio sem tratamento
- Workarounds explícitos
- Blocos de código comentado (3+ linhas consecutivas)

Isenções:
- Arquivos em hooks/ (patterns legítimos)
- Arquivos em docs/, .md, .yml (documentação)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXEMPT_PATHS = {
    "hooks/",
    "docs/",
    ".claude/",
    "scripts/",
}

EXEMPT_EXTENSIONS = {
    ".md",
    ".txt",
    ".csv",
    ".json",
    ".yml",
    ".yaml",
    ".html",
    ".css",
    ".toml",
}

BURLA_PATTERNS = [
    (
        re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE),
        "TODO/FIXME/HACK inline",
        "Criar issue no GitHub em vez de comentário inline (CLAUDE.md seção 3)",
    ),
    (
        re.compile(r"@pytest\.mark\.skip|pytest\.skip\("),
        "Teste desabilitado",
        "Corrigir o teste em vez de pular",
    ),
    (
        re.compile(r"#\s*(workaround|gambiarra|temporary|hack temporário)", re.IGNORECASE),
        "Workaround explícito",
        "Resolver a causa raiz, não contornar",
    ),
]

EXCEPT_PATTERN = re.compile(r"^\s*except\s*(?:Exception\s*)?:")
EXCEPT_HANDLER = re.compile(r"raise|logger\.|logging\.|log\.|print\(")


def is_exempt(filepath: str) -> bool:
    """Retorna True se o arquivo está em caminho isento."""
    for exempt in EXEMPT_PATHS:
        if filepath.startswith(exempt):
            return True
    ext = Path(filepath).suffix
    if ext in EXEMPT_EXTENSIONS:
        return True
    return False


def get_added_lines() -> dict[str, list[tuple[int, str]]]:
    """Retorna linhas adicionadas no diff staged, agrupadas por arquivo."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--unified=0", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return {}

    files: dict[str, list[tuple[int, str]]] = {}
    current_file = None
    line_num = 0

    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            files[current_file] = []
        elif line.startswith("@@ "):
            match = re.search(r"\+(\d+)", line)
            if match:
                line_num = int(match.group(1)) - 1
        elif line.startswith("+") and not line.startswith("+++"):
            line_num += 1
            if current_file:
                files[current_file].append((line_num, line[1:]))
        elif not line.startswith("-"):
            line_num += 1

    return files


def check_commented_blocks(lines: list[tuple[int, str]]) -> list[str]:
    """Detecta blocos de 3+ linhas comentadas consecutivas."""
    violations = []
    consecutive = 0
    block_start = 0

    for line_num, content in lines:
        stripped = content.strip()
        if stripped.startswith("#") and not stripped.startswith("#!") and len(stripped) > 2:
            if consecutive == 0:
                block_start = line_num
            consecutive += 1
        else:
            if consecutive >= 3:
                violations.append(
                    f"  Linha {block_start}-{block_start + consecutive - 1}:"
                    f" {consecutive} linhas comentadas consecutivas (deletar ou documentar no commit)"
                )
            consecutive = 0

    if consecutive >= 3:
        violations.append(
            f"  Linha {block_start}-{block_start + consecutive - 1}: "
            f"{consecutive} linhas comentadas consecutivas"
        )

    return violations


def check_silent_except(lines: list[tuple[int, str]]) -> list[str]:
    """Detecta except vazio sem tratamento em linhas novas."""
    violations = []
    for i, (line_num, content) in enumerate(lines):
        if EXCEPT_PATTERN.match(content):
            next_lines = [text for _, text in lines[i + 1 : i + 4]]
            has_handler = any(EXCEPT_HANDLER.search(line) for line in next_lines)
            if not has_handler:
                violations.append(
                    f"  Linha {line_num}: except vazio sem logger/raise "
                    f"(CLAUDE.md seção 3 -- error handling explícito)"
                )

    return violations


def main() -> int:
    """Analisa diff staged contra padrões de burla."""
    added_lines = get_added_lines()
    if not added_lines:
        return 0

    all_violations: dict[str, list[str]] = {}

    for filepath, lines in added_lines.items():
        if is_exempt(filepath):
            continue

        violations = []

        for line_num, content in lines:
            for pattern, name, fix in BURLA_PATTERNS:
                if pattern.search(content):
                    violations.append(f"  Linha {line_num}: {name} -- {fix}")

        violations.extend(check_commented_blocks(lines))
        violations.extend(check_silent_except(lines))

        if violations:
            all_violations[filepath] = violations

    if all_violations:
        print("[ANTI-BURLA] Padrões de burla detectados no diff:")
        for filepath, violations in all_violations.items():
            print(f"\n  {filepath}:")
            for v in violations:
                print(f"    {v}")
        print()
        print("COMO CORRIGIR:")
        print("  - TODO/FIXME -> criar issue: gh issue create --title '...'")
        print("  - Workaround -> resolver causa raiz ou abrir issue detalhada")
        print("  - Código comentado -> deletar ou documentar no commit")
        print("  - Except vazio -> adicionar logger.error() ou raise")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

# "A virtude não consiste em evitar o vício, mas em não desejá-lo." -- George Bernard Shaw
