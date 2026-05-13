"""Testes do hook SessionStart local do protocolo-ouroboros.

Cobrem os cenários canônicos: payload vazio, `graduacao_tipos.json`
ausente, snapshot válido, JSON corrompido e invocação por subprocess.

Falha-soft é invariante: o hook sempre retorna exit 0 e nunca quebra
o boot da sessão.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
_PATH_HOOK = _RAIZ / ".claude" / "hooks" / "session-start-projeto.py"


def _carregar_modulo_hook():
    """Carrega o hook como módulo isolado (não é pacote Python)."""
    spec = importlib.util.spec_from_file_location(
        "session_start_projeto_modulo",
        _PATH_HOOK,
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def hook(monkeypatch, tmp_path):
    """Carrega o módulo do hook e isola PATH_GRADUACAO em tmp_path."""
    modulo = _carregar_modulo_hook()
    monkeypatch.setattr(
        modulo,
        "PATH_GRADUACAO",
        tmp_path / "graduacao_tipos.json",
    )
    monkeypatch.setattr(
        modulo,
        "PATH_ROADMAP",
        tmp_path / "ROADMAP_ATE_PROD.md",
    )
    monkeypatch.setattr(
        modulo,
        "PATH_BACKLOG",
        tmp_path / "backlog",
    )
    return modulo


def test_payload_vazio_retorna_exit_zero(hook, monkeypatch, capsys):
    """Payload vazio em stdin produz exit 0 e JSON válido em stdout."""
    monkeypatch.setattr("sys.stdin", _StdinFake(""))
    rc = hook.main()
    saida = capsys.readouterr().out

    assert rc == 0
    data = json.loads(saida)
    assert "additionalContext" in data
    assert "Briefing local do protocolo-ouroboros" in data["additionalContext"]


def test_graduacao_ausente_mensagem_generica(hook, monkeypatch, capsys):
    """Sem `graduacao_tipos.json`, briefing inclui mensagem genérica."""
    monkeypatch.setattr("sys.stdin", _StdinFake("{}"))
    rc = hook.main()
    contexto = json.loads(capsys.readouterr().out)["additionalContext"]

    assert rc == 0
    assert "graduacao_tipos.json ausente" in contexto
    assert "dossie_tipo.py snapshot" in contexto


def test_graduacao_valida_inclui_totais(hook, monkeypatch, capsys):
    """Snapshot válido produz linha 'X GRADUADOS, Y CALIBRANDO, Z PENDENTE'."""
    hook.PATH_GRADUACAO.write_text(
        json.dumps(
            {
                "totais": {"GRADUADO": 3, "CALIBRANDO": 5, "PENDENTE": 14},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.stdin", _StdinFake("{}"))
    rc = hook.main()
    contexto = json.loads(capsys.readouterr().out)["additionalContext"]

    assert rc == 0
    assert "3 GRADUADOS" in contexto
    assert "5 CALIBRANDO" in contexto
    assert "14 PENDENTE" in contexto


def test_graduacao_corrompida_falha_soft(hook, monkeypatch, capsys):
    """JSON corrompido em `graduacao_tipos.json` não quebra o hook."""
    hook.PATH_GRADUACAO.write_text("{ esto não é json válido", encoding="utf-8")
    monkeypatch.setattr("sys.stdin", _StdinFake("{}"))
    rc = hook.main()
    contexto = json.loads(capsys.readouterr().out)["additionalContext"]

    assert rc == 0
    assert "ilegivel" in contexto or "ilegível" in contexto


def test_hook_executavel_via_subprocess():
    """Invocação ponta-a-ponta: stdin vazio, exit 0, JSON válido em stdout."""
    proc = subprocess.run(
        [sys.executable, str(_PATH_HOOK)],
        input="{}",
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(_RAIZ),
    )

    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert "additionalContext" in data
    assert "Briefing local" in data["additionalContext"]


def test_epico_ativo_indeterminado_quando_roadmap_ausente(hook, monkeypatch, capsys):
    """Sem ROADMAP/backlog, briefing reporta épico indeterminado."""
    monkeypatch.setattr("sys.stdin", _StdinFake("{}"))
    rc = hook.main()
    contexto = json.loads(capsys.readouterr().out)["additionalContext"]

    assert rc == 0
    assert "indeterminado" in contexto


class _StdinFake:
    """Substituto mínimo de sys.stdin para testes."""

    def __init__(self, conteudo: str) -> None:
        self._conteudo = conteudo

    def read(self) -> str:  # noqa: D401
        return self._conteudo


# "O teste é a única prova honesta de que o código fala o que promete." -- Sócrates
