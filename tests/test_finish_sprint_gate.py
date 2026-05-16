"""Testes para `scripts/finish_sprint.sh` -- modo --gate-only e parser de args.

Sprint META-FINISH-SPRINT-GATE-COMPLETO (2026-05-15).

Estratégia: invocar o script via subprocess em um ambiente isolado, com mocks
nos binários `make` e `pytest` colocados no início do `PATH` para acelerar
e evitar dependência do estado real do repositório durante os testes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "finish_sprint.sh"


@pytest.fixture
def workspace_isolado(tmp_path: Path) -> Path:
    """Recria um repositório mínimo com finish_sprint.sh, baseline file e .venv vazio.

    Não copia tests/ nem src/ -- os mocks de make/pytest cuidam disso.
    """
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / "scripts").mkdir()
    (raiz / "scripts" / "ci").mkdir()
    (raiz / ".ouroboros").mkdir()
    (raiz / ".venv" / "bin").mkdir(parents=True)
    (raiz / "docs" / "sprints" / "backlog").mkdir(parents=True)
    (raiz / "docs" / "sprints" / "concluidos").mkdir(parents=True)

    # Copia o script real
    shutil.copy(SCRIPT, raiz / "scripts" / "finish_sprint.sh")
    (raiz / "scripts" / "finish_sprint.sh").chmod(0o755)

    # Stub de validate_sprint_structure.py (soft check, sempre OK)
    (raiz / "scripts" / "ci" / "validate_sprint_structure.py").write_text(
        "import sys; sys.exit(0)\n", encoding="utf-8"
    )

    # Stub de python no .venv que apenas executa stdlib
    venv_python = raiz / ".venv" / "bin" / "python"
    venv_python.write_text("#!/bin/bash\nexec /usr/bin/env python3 \"$@\"\n", encoding="utf-8")
    venv_python.chmod(0o755)

    return raiz


def _criar_mocks_verde(workspace: Path, pytest_passed: int = 3050) -> Path:
    """Cria mocks `make` e `pytest` em diretório dedicado, retornando o PATH a usar."""
    mockbin = workspace / "mockbin"
    mockbin.mkdir(exist_ok=True)

    # make: aceita qualquer alvo e imprime sucesso
    (mockbin / "make").write_text(
        "#!/bin/bash\necho \"mock make $*: OK\"\nexit 0\n", encoding="utf-8"
    )
    (mockbin / "make").chmod(0o755)

    # pytest: imprime resumo no formato esperado pelo grep do script
    pytest_stub = workspace / ".venv" / "bin" / "pytest"
    pytest_stub.write_text(
        f"#!/bin/bash\necho \"{pytest_passed} passed, 0 failed in 1.0s\"\nexit 0\n",
        encoding="utf-8",
    )
    pytest_stub.chmod(0o755)

    return mockbin


def _rodar_script(
    workspace: Path,
    args: list[str],
    extra_path: Path | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    path_prefix = str(extra_path) + os.pathsep if extra_path else ""
    env["PATH"] = path_prefix + env.get("PATH", "")
    return subprocess.run(
        ["bash", str(workspace / "scripts" / "finish_sprint.sh"), *args],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


# --------------------------------------------------------------------------
# Teste 1: --gate-only em estado verde retorna 0 e atualiza baseline
# --------------------------------------------------------------------------
def test_gate_only_estado_verde_atualiza_baseline(workspace_isolado: Path) -> None:
    mockbin = _criar_mocks_verde(workspace_isolado, pytest_passed=3050)
    baseline = workspace_isolado / ".ouroboros" / "pytest_baseline.txt"
    baseline.write_text("3000\n", encoding="utf-8")

    resultado = _rodar_script(workspace_isolado, ["--gate-only"], extra_path=mockbin)

    assert resultado.returncode == 0, (
        f"Esperava exit 0 em gate verde. stdout={resultado.stdout!r} stderr={resultado.stderr!r}"
    )
    assert "Gate OK" in resultado.stdout
    novo_baseline = baseline.read_text(encoding="utf-8").strip()
    assert novo_baseline == "3050", f"baseline esperado 3050, achei {novo_baseline!r}"


# --------------------------------------------------------------------------
# Teste 2: --gate-only com pytest regressivo retorna exit 1
# --------------------------------------------------------------------------
def test_gate_only_pytest_regredido_exit_1(workspace_isolado: Path) -> None:
    mockbin = _criar_mocks_verde(workspace_isolado, pytest_passed=2900)
    baseline = workspace_isolado / ".ouroboros" / "pytest_baseline.txt"
    baseline.write_text("3000\n", encoding="utf-8")

    resultado = _rodar_script(workspace_isolado, ["--gate-only"], extra_path=mockbin)

    assert resultado.returncode == 1, (
        f"Esperava exit 1 em regressão. stdout={resultado.stdout!r} stderr={resultado.stderr!r}"
    )
    assert "regrediu" in resultado.stdout
    # Baseline não deve ser sobrescrito quando há regressão
    baseline_apos = baseline.read_text(encoding="utf-8").strip()
    assert baseline_apos == "3000", (
        f"baseline NÃO deveria ter mudado em regressão, achei {baseline_apos!r}"
    )


# --------------------------------------------------------------------------
# Teste 3: sem args mostra usage e exit 1 (parser de argumentos)
# --------------------------------------------------------------------------
def test_sem_args_mostra_uso_e_exit_1(workspace_isolado: Path) -> None:
    resultado = _rodar_script(workspace_isolado, [])

    assert resultado.returncode == 1
    assert "Uso:" in resultado.stdout
    assert "--gate-only" in resultado.stdout


# Aforismo: "Cerimônia mal-feita acumula débito invisível." -- Antístenes
