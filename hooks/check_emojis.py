#!/usr/bin/env python3
"""Hook de verificação de emojis -- impede emojis no código.

Regra ZERO EMOJIS do CLAUDE.md seção 2.
Cobertura: .py, .sh, .md, .txt, .yaml, .yml, .toml, .json.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

EMOJI_REGEX = re.compile(
    r"["
    r"\U0001F600-\U0001F64F"
    r"\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F700-\U0001F77F"
    r"\U0001F780-\U0001F7FF"
    r"\U0001F800-\U0001F8FF"
    r"\U0001F900-\U0001F9FF"
    r"\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF"
    r"\U00002702-\U000027B0"
    r"\U00002600-\U000026FF"
    r"\U0000231A-\U0000231B"
    r"\U00002328"
    r"\U000023CF"
    r"\U000023E9-\U000023F3"
    r"\U000023F8-\U000023FA"
    r"\U0000FE00-\U0000FE0F"
    r"]+"
)

EXCLUSIONS = [
    "check_emojis.py",
    ".git/",
    "__pycache__",
    "venv/",
    ".venv/",
    "node_modules/",
    ".svg",
    ".png",
    ".jpg",
    ".gif",
    ".ico",
    "data/",
]

VALID_EXTENSIONS = {
    ".py",
    ".sh",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".css",
    ".html",
    ".js",
}


def is_excluded(filepath: str) -> bool:
    """Retorna True se o arquivo está em caminho excluído."""
    return any(exc in filepath for exc in EXCLUSIONS)


def check_file(filepath: str) -> list[dict]:
    """Verifica arquivo em busca de emojis. Retorna lista de violações."""
    if is_excluded(filepath):
        return []

    path = Path(filepath)
    if not path.exists() or not path.is_file():
        return []

    if path.suffix not in VALID_EXTENSIONS:
        return []

    violations = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            matches = EMOJI_REGEX.findall(line)
            if matches:
                violations.append(
                    {
                        "line": i,
                        "emojis": matches,
                        "code": line.strip()[:100],
                    }
                )
    except OSError:
        pass

    return violations


def format_error(all_violations: dict[str, list]) -> str:
    """Formata mensagem de erro final."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("HOOK FALHOU: check_emojis")
    lines.append("=" * 70)
    lines.append("")
    lines.append("O QUE FAZ: Impede emojis no código (regra ZERO EMOJIS)")
    lines.append("")

    for filepath, violations in all_violations.items():
        lines.append(f"ARQUIVO: {filepath}")
        for v in violations:
            lines.append(f"  Linha {v['line']}: Emojis encontrados: {v['emojis']}")
            lines.append(f"    -> {v['code']}")
        lines.append("")

    lines.append("COMO CORRIGIR:")
    lines.append("  1. Substitua emojis por texto ou remova")
    lines.append("  2. Em logs, use texto descritivo em vez de ícones")
    lines.append("  3. Em markdown, prefira tabelas e listas sem ícones")
    lines.append("")
    lines.append("DOCUMENTAÇÃO: CLAUDE.md seção 2 (Zero Emojis)")
    lines.append("=" * 70)
    lines.append("")

    return "\n".join(lines)


def _get_staged_files() -> list[str]:
    """Retorna arquivos staged no git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=False,
        )
        return [f for f in result.stdout.strip().split("\n") if f]
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def main() -> int:
    """Ponto de entrada principal."""
    files = sys.argv[1:] if len(sys.argv) > 1 else _get_staged_files()
    all_violations: dict[str, list] = {}

    for f in files:
        violations = check_file(f)
        if violations:
            all_violations[f] = violations

    if all_violations:
        print(format_error(all_violations))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

# "A simplicidade é o último grau de sofisticação." -- Leonardo da Vinci
