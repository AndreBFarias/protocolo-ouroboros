#!/usr/bin/env python3
"""Hook: valida citação de filósofo ao final de arquivos .py em src/.

Regra CLAUDE.md seção 10: todo arquivo .py de src/ deve terminar com
um comentário contendo uma citação filosófica/estoica/libertária no
formato aproximado: # "Citação." -- Autor

Arquivos ignorados:
    - __init__.py vazios (ou só com exports)
    - arquivos em tests/ (fixtures e conftest)
    - arquivos auto-gerados (*.egg-info)

Uso:
    python3 hooks/check_citacao_filosofo.py            # checa staged
    python3 hooks/check_citacao_filosofo.py --all       # checa todos src/
    python3 hooks/check_citacao_filosofo.py arq.py ...  # checa específicos
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# Padrão aceita: "..." -- Autor | "..." – Autor | "..." — Autor
# Permite aspas retas ou tipográficas e hífen/travessão. Aplicado sobre
# comentários das últimas linhas já colapsados numa string única, de modo a
# aceitar citações que ocupem duas ou mais linhas de comentário.
CITACAO_REGEX = re.compile(
    r"""["'“‘][^"'”’]{5,}["'”’]\s*[-—–]{1,3}\s*\S+""",
    re.IGNORECASE,
)


def _is_init_vazio(path: Path) -> bool:
    """Retorna True se é __init__.py vazio ou só com exports."""
    if path.name != "__init__.py":
        return False
    try:
        texto = path.read_text(encoding="utf-8")
    except OSError:
        return True
    linhas_significativas = [
        ln.strip()
        for ln in texto.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    # Se só tem imports/exports/docstring/__all__, considerar ok sem citação
    if len(linhas_significativas) <= 10:
        return all(
            ln.startswith(("from ", "import ", "__all__", '"""', "'''"))
            or ln.endswith(('"""', "'''"))
            or ln == ""
            or "=" in ln
            for ln in linhas_significativas
        )
    return False


def _tem_citacao(path: Path) -> bool:
    """Verifica se o arquivo termina com citação válida nas últimas linhas.

    Coleta as últimas 10 linhas; extrai apenas as linhas de comentário
    (iniciadas por `#`), remove o prefixo `#` e junta num texto único.
    Depois aplica o regex -- aceita citações multi-linha.
    """
    try:
        texto = path.read_text(encoding="utf-8")
    except OSError:
        return True

    linhas = texto.rstrip().splitlines()
    if not linhas:
        return False

    fragmentos: list[str] = []
    for linha in linhas[-10:]:
        stripped = linha.strip()
        if stripped.startswith("#"):
            fragmentos.append(stripped.lstrip("#").strip())

    if not fragmentos:
        return False

    texto_colapsado = " ".join(fragmentos)
    return bool(CITACAO_REGEX.search(texto_colapsado))


def _deve_ignorar(path: Path) -> bool:
    """Retorna True se o arquivo deve ser ignorado."""
    partes = path.parts
    if "tests" in partes or "__pycache__" in partes:
        return True
    if any(p.endswith(".egg-info") for p in partes):
        return True
    if _is_init_vazio(path):
        return True
    return False


def _listar_todos_src() -> list[Path]:
    """Retorna todos os .py dentro de src/."""
    if not SRC_DIR.exists():
        return []
    return [p for p in SRC_DIR.rglob("*.py") if not _deve_ignorar(p)]


def _listar_staged() -> list[Path]:
    """Retorna arquivos .py staged dentro de src/."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    paths: list[Path] = []
    for f in result.stdout.strip().splitlines():
        if not f.endswith(".py"):
            continue
        p = PROJECT_ROOT / f
        if not p.exists():
            continue
        if not f.startswith("src/"):
            continue
        if _deve_ignorar(p):
            continue
        paths.append(p)
    return paths


def main() -> int:
    """Ponto de entrada."""
    if "--all" in sys.argv:
        arquivos = _listar_todos_src()
    elif len(sys.argv) > 1:
        arquivos = [Path(a) for a in sys.argv[1:] if a.endswith(".py")]
        arquivos = [p for p in arquivos if p.exists() and not _deve_ignorar(p)]
    else:
        arquivos = _listar_staged()

    sem_citacao: list[Path] = [p for p in arquivos if not _tem_citacao(p)]

    if sem_citacao:
        print()
        print("=" * 60)
        print("  [T2] Arquivos .py sem citação filosófica ao final")
        print("=" * 60)
        print()
        print("  Regra: CLAUDE.md seção 10.")
        print("  Formato aceito:")
        print('    # "A identidade é o primeiro direito." -- Anônimo')
        print()
        for p in sem_citacao:
            rel = p.relative_to(PROJECT_ROOT) if p.is_absolute() else p
            print(f"  - {rel}")
        print()
        print("=" * 60)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

# "Uma vida sem exame não merece ser vivida." -- Sócrates
