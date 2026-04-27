#!/usr/bin/env python3
"""Hook de tamanho de arquivo -- limite de 800 linhas por .py.

Regra CLAUDE.md seção 6:
    Limite de 800 linhas por arquivo (exceções: config, testes, registries).
    Se ultrapassar: extrair para módulos separados, manter imports limpos.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MAX_LINES = 800
GROWTH_THRESHOLD = 80
SCRIPT_DIR = Path(__file__).parent


def get_line_count(filepath: Path) -> int:
    """Conta linhas do arquivo."""
    try:
        with open(filepath, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def get_git_line_count(filepath: str, revision: str = "HEAD") -> int:
    """Conta linhas da versão HEAD do arquivo."""
    try:
        result = subprocess.run(
            ["git", "show", f"{revision}:{filepath}"],
            capture_output=True,
            text=False,
            check=False,
        )
        if result.returncode != 0:
            return 0
        return len(result.stdout.splitlines())
    except (subprocess.SubprocessError, FileNotFoundError):
        return 0


def is_new_file(filepath: str) -> bool:
    """Retorna True se o arquivo é novo (adicionado no index)."""
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=A"],
            capture_output=True,
            text=True,
            check=False,
        )
        return filepath in res.stdout.splitlines()
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def main() -> int:
    """Verifica limite de 800 linhas por .py staged."""
    print("Verificando tamanho dos arquivos Python...")

    if len(sys.argv) > 1:
        files_to_check = [f for f in sys.argv[1:] if f.endswith(".py")]
    else:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
            capture_output=True,
            text=True,
            check=False,
        )
        files_to_check = [f for f in res.stdout.splitlines() if f.endswith(".py")]

    errors = 0

    for filepath in files_to_check:
        path = Path(filepath)
        if not path.exists():
            continue
        if "/tests/" in filepath or filepath.startswith("tests/"):
            continue
        if "test_" in path.name or path.name == "conftest.py":
            continue
        if path.name == "__init__.py":
            continue
        if "mappings/" in filepath:
            continue

        current_lines = get_line_count(path)

        if is_new_file(filepath):
            if current_lines > MAX_LINES:
                print(
                    f"ERRO: Novo arquivo {filepath} tem {current_lines} linhas (máx: {MAX_LINES})"
                )
                print("  -> Divida em módulos menores antes de commitar")
                errors += 1
        else:
            if current_lines > MAX_LINES:
                old_lines = get_git_line_count(filepath)
                if old_lines <= MAX_LINES:
                    print(
                        f"ERRO: {filepath} ultrapassou {MAX_LINES} linhas "
                        f"(era {old_lines}, agora {current_lines})"
                    )
                    print("  -> Divida o arquivo em módulos menores")
                    errors += 1
                elif (current_lines - old_lines) > GROWTH_THRESHOLD:
                    print(
                        f"AVISO: {filepath} cresceu {current_lines - old_lines} linhas "
                        f"(está em {current_lines})"
                    )

    if errors > 0:
        print(f"\nGod Mode detectado! {errors} erro(s).")
        print(f"Arquivos devem ter no máximo {MAX_LINES} linhas (CLAUDE.md seção 6).")
        return 1

    print("OK: Verificação de tamanho concluída")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# "Pequeno e simples, não grande e complicado." -- Ernst Schumacher
