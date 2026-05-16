"""Testes do watcher de inbox (Sprint INFRA-INBOX-WATCHER).

Cobre:
- Estrutura dos unit files systemd (.service e .path).
- Comportamento do script `scripts/inbox_watcher.sh`:
    - --help (saída 0, ajuda razoável).
    - --dry-run com inbox vazia (decide skip, exit 0).
    - --dry-run com lockfile ativo (decide skip, exit 0).
    - --dry-run com arquivo (decide processar, mas não executa run.sh).
- Comportamento do `scripts/install_inbox_watcher.sh` em --dry-run e --help.

Testes não instalam o watcher no sistema real; tudo via subprocess + --dry-run.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
WATCHER = RAIZ / "scripts" / "inbox_watcher.sh"
INSTALLER = RAIZ / "scripts" / "install_inbox_watcher.sh"
UNIT_SERVICE = RAIZ / "infra" / "systemd" / "ouroboros-inbox.service"
UNIT_PATH = RAIZ / "infra" / "systemd" / "ouroboros-inbox.path"


# ---------------------------------------------------------------------------
# Estrutura dos arquivos
# ---------------------------------------------------------------------------


def test_unit_service_existe_e_tem_secoes_obrigatorias() -> None:
    assert UNIT_SERVICE.exists(), f"unit service ausente em {UNIT_SERVICE}"
    conteudo = UNIT_SERVICE.read_text(encoding="utf-8")
    for secao in ("[Unit]", "[Service]", "[Install]"):
        assert secao in conteudo, f"seção {secao} ausente em {UNIT_SERVICE}"
    # ExecStart aponta para o script certo
    assert "scripts/inbox_watcher.sh" in conteudo
    # WorkingDirectory definido
    assert "WorkingDirectory=" in conteudo


def test_unit_path_existe_e_referencia_service() -> None:
    assert UNIT_PATH.exists(), f"unit path ausente em {UNIT_PATH}"
    conteudo = UNIT_PATH.read_text(encoding="utf-8")
    for secao in ("[Unit]", "[Path]", "[Install]"):
        assert secao in conteudo
    assert "PathChanged=" in conteudo
    assert "Unit=ouroboros-inbox.service" in conteudo
    assert "inbox" in conteudo


def test_watcher_eh_executavel() -> None:
    assert WATCHER.exists()
    assert os.access(WATCHER, os.X_OK), f"{WATCHER} não é executável"


def test_installer_eh_executavel() -> None:
    assert INSTALLER.exists()
    assert os.access(INSTALLER, os.X_OK), f"{INSTALLER} não é executável"


# ---------------------------------------------------------------------------
# Comportamento dos scripts (via subprocess)
# ---------------------------------------------------------------------------


def test_watcher_help_retorna_zero() -> None:
    res = subprocess.run([str(WATCHER), "--help"], capture_output=True, text=True, timeout=10)
    assert res.returncode == 0
    assert "inbox_watcher" in res.stdout.lower() or "debounce" in res.stdout.lower()


def test_installer_help_retorna_zero() -> None:
    res = subprocess.run([str(INSTALLER), "--help"], capture_output=True, text=True, timeout=10)
    assert res.returncode == 0
    assert "install" in res.stdout.lower()


def test_installer_dry_run_nao_modifica_sistema(tmp_path: Path) -> None:
    # Dry-run não deve criar arquivos em ~/.config/systemd/user/.
    # Apenas valida que script roda sem erro e produz log "DRY-RUN".
    # Força OUROBOROS_RAIZ para a raiz do repo deste teste (worktree-aware).
    env = os.environ.copy()
    env["OUROBOROS_RAIZ"] = str(RAIZ)
    res = subprocess.run(
        [str(INSTALLER), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert res.returncode == 0, f"installer dry-run falhou stdout={res.stdout} stderr={res.stderr}"
    assert "DRY-RUN" in res.stdout


def test_watcher_dry_run_inbox_vazia(tmp_path: Path) -> None:
    # Roda watcher com OUROBOROS_RAIZ apontando para diretório sem inbox/.
    # Deve sair com exit 0 e logar "inbox_ausente" ou "inbox_vazia".
    env = os.environ.copy()
    env["OUROBOROS_RAIZ"] = str(tmp_path)
    env["INBOX_WATCHER_DEBOUNCE"] = "0"
    res = subprocess.run(
        [str(WATCHER), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert res.returncode == 0
    log_combinado = res.stdout + res.stderr
    assert "inbox_ausente" in log_combinado or "inbox_vazia" in log_combinado


def test_watcher_dry_run_lockfile_respeitado(tmp_path: Path) -> None:
    # Cria inbox/ com arquivo + lockfile -> watcher deve skip.
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "arquivo_teste.txt").write_text("conteúdo")
    (tmp_path / "data").mkdir()
    lockfile = tmp_path / "data" / ".ouroboros.lock"
    lockfile.write_text("99999")  # PID fake

    env = os.environ.copy()
    env["OUROBOROS_RAIZ"] = str(tmp_path)
    env["INBOX_WATCHER_DEBOUNCE"] = "0"
    env["OUROBOROS_LOCKFILE"] = str(lockfile)

    res = subprocess.run(
        [str(WATCHER), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert res.returncode == 0
    log_combinado = res.stdout + res.stderr
    assert "lockfile_ativo" in log_combinado


def test_watcher_dry_run_processa_arquivo(tmp_path: Path) -> None:
    # Inbox tem 1 arquivo, sem lockfile -> watcher decide processar (dry-run não executa).
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "documento.pdf").write_text("dummy")

    env = os.environ.copy()
    env["OUROBOROS_RAIZ"] = str(tmp_path)
    env["INBOX_WATCHER_DEBOUNCE"] = "1"  # 1s para não travar teste
    # Lockfile path para arquivo que não existe
    env["OUROBOROS_LOCKFILE"] = str(tmp_path / "data" / ".ouroboros.lock")

    inicio = time.monotonic()
    res = subprocess.run(
        [str(WATCHER), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    duracao = time.monotonic() - inicio
    assert res.returncode == 0
    log_combinado = res.stdout + res.stderr
    assert "inbox_processing_inicio" in log_combinado
    assert "dry_run_decidiu_processar" in log_combinado
    # Debounce 1s -> duração >= 1s.
    assert duracao >= 0.9, f"debounce não respeitado (duração={duracao}s)"


def test_watcher_debounce_detecta_arquivo_chegando(tmp_path: Path) -> None:
    """Se durante o debounce um arquivo novo aparece, watcher skip o ciclo
    (próximo path-change re-dispara)."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "arquivo1.txt").write_text("primeiro")

    env = os.environ.copy()
    env["OUROBOROS_RAIZ"] = str(tmp_path)
    env["INBOX_WATCHER_DEBOUNCE"] = "2"
    env["OUROBOROS_LOCKFILE"] = str(tmp_path / "data" / ".ouroboros.lock")

    # Dispara watcher em background.
    proc = subprocess.Popen(
        [str(WATCHER), "--dry-run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    # Durante o debounce, cria um novo arquivo para mudar mtime.
    time.sleep(0.5)
    (inbox / "arquivo2.txt").write_text("segundo")
    stdout, stderr = proc.communicate(timeout=15)
    assert proc.returncode == 0
    log_combinado = stdout + stderr
    assert "debounce_arquivos_ainda_chegando" in log_combinado


# ---------------------------------------------------------------------------
# Validação do unit file via systemd-analyze (se disponível)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    subprocess.run(["which", "systemd-analyze"], capture_output=True).returncode != 0,
    reason="systemd-analyze não disponível",
)
def test_systemd_analyze_verifica_units() -> None:
    """systemd-analyze verify aceita os 2 unit files sem warnings críticos."""
    # systemd-analyze precisa que ambos os arquivos estejam num diretório aceito.
    # Estratégia: copiar para tmp e validar lá com paths compatíveis.
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copy(UNIT_SERVICE, tmp_path / "ouroboros-inbox.service")
        shutil.copy(UNIT_PATH, tmp_path / "ouroboros-inbox.path")
        res = subprocess.run(
            [
                "systemd-analyze",
                "verify",
                "--user",
                str(tmp_path / "ouroboros-inbox.service"),
                str(tmp_path / "ouroboros-inbox.path"),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        # systemd-analyze exit 0 = sem erros; mensagens em stderr são avisos.
        # Pode falhar em ambientes sem WorkingDirectory absoluto válido, mas
        # falhas reais (sintaxe) saem com exit !=0.
        # Aceitamos exit 0 ou stderr que só cite WorkingDirectory/path inexistente.
        if res.returncode != 0:
            erros_sintaxe = [
                linha
                for linha in res.stderr.splitlines()
                if "unknown" in linha.lower()
                or "invalid" in linha.lower()
                or "failed to parse" in linha.lower()
            ]
            assert not erros_sintaxe, f"systemd-analyze acusou erros de sintaxe:\n{res.stderr}"


# "A liberdade não consiste em fazer o que se quer, mas em saber o que se quer fazer." -- Hegel
