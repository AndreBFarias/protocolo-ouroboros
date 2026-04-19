#!/usr/bin/env python3
"""Hook de complexidade ciclomática -- limite de 15 por função.

Regra CLAUDE.md seção 8: simplicidade > elegância. Funções com
complexidade >15 indicam que precisam ser extraídas em auxiliares.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

MAX_COMPLEXITY = 15
WARNING_THRESHOLD = 10
IGNORE_FILES = ["__init__.py", "conftest.py"]


class ComplexityVisitor(ast.NodeVisitor):
    """Calcula complexidade ciclomática de uma função AST."""

    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)


def calculate_complexity(node: ast.AST) -> int:
    """Retorna complexidade ciclomática de uma função."""
    visitor = ComplexityVisitor()
    visitor.visit(node)
    return visitor.complexity


def get_changed_files() -> list[str]:
    """Retorna arquivos .py para checar (args > staged > src/)."""
    if len(sys.argv) > 1:
        return [f for f in sys.argv[1:] if f.endswith(".py")]

    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
            capture_output=True,
            text=True,
            check=False,
        )
        files = result.stdout.strip().split("\n")
        return [f for f in files if f.endswith(".py") and f.startswith("src/") and "/tests/" not in f]
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def main() -> int:
    """Verifica complexidade ciclomática em arquivos alterados."""
    print("Verificando complexidade ciclomática...")

    files_to_check = get_changed_files()
    high_complexity: list[str] = []
    warnings: list[str] = []

    for filepath in files_to_check:
        if not filepath:
            continue
        if any(ig in filepath for ig in IGNORE_FILES):
            continue
        if "/tests/" in filepath or filepath.startswith("tests/"):
            continue

        path = Path(filepath)
        if not path.exists():
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError) as e:
            print(f"Erro ao parsear {filepath}: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = calculate_complexity(node)
                msg = f"{filepath}:{node.lineno} -> {node.name}() = {complexity}"
                if complexity > MAX_COMPLEXITY:
                    high_complexity.append(msg)
                elif complexity > WARNING_THRESHOLD:
                    warnings.append(msg)

    if warnings:
        print(f"\n{len(warnings)} funções com complexidade alta (>{WARNING_THRESHOLD}):")
        for w in warnings[:10]:
            print(f"  ! {w}")
        if len(warnings) > 10:
            print(f"  ... e mais {len(warnings) - 10}")

    if high_complexity:
        print(f"\n{len(high_complexity)} funções com complexidade crítica (>{MAX_COMPLEXITY}):")
        for h in high_complexity[:10]:
            print(f"  ! {h}")
        if len(high_complexity) > 10:
            print(f"  ... e mais {len(high_complexity) - 10}")
        print("\nConsidere:")
        print("  - Extrair funções auxiliares")
        print("  - Usar early returns")
        print("  - Simplificar condições aninhadas")
        return 1

    if not warnings and not high_complexity:
        print("OK: Complexidade dentro dos limites")

    return 0


if __name__ == "__main__":
    sys.exit(main())

# "A perfeição é atingida não quando nada mais há a acrescentar, mas quando nada mais se pode retirar." -- Antoine de Saint-Exupéry
