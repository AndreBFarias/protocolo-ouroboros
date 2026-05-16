"""Testes da Lockfile class.

Sprint INFRA-CONCORRENCIA-PIDFILE (2026-05-16). Cobre: adquire +
libera, 2 instâncias concorrentes, lock_ativo, pid_do_lock, cleanup.
"""

from __future__ import annotations

import multiprocessing
import os
import time
from pathlib import Path

import pytest

from src.utils.lockfile import (
    Lockfile,
    LockfileOcupado,
    lock_ativo,
    pid_do_lock,
)


def test_adquire_e_libera_lock(tmp_path: Path) -> None:
    """Sequência básica: with bloco entra e sai sem erro, arquivo limpo."""
    lock_path = tmp_path / "pipeline.lock"
    with Lockfile(lock_path, "teste"):
        assert lock_path.exists()
        # PID + descrição gravados:
        conteudo = lock_path.read_text(encoding="utf-8")
        assert str(os.getpid()) in conteudo
        assert "teste" in conteudo
    # Após sair, arquivo apagado:
    assert not lock_path.exists()


def test_lock_em_diretorio_inexistente_cria_estrutura(tmp_path: Path) -> None:
    """Lockfile cria diretório pai se necessário."""
    lock_path = tmp_path / "sub" / "deep" / "pipe.lock"
    with Lockfile(lock_path, "teste"):
        assert lock_path.exists()
    assert not lock_path.exists()


def test_segunda_aquisicao_simultanea_falha(tmp_path: Path) -> None:
    """Duas chamadas simultâneas: segunda recebe LockfileOcupado."""
    lock_path = tmp_path / "pipeline.lock"
    primeiro = Lockfile(lock_path, "primeiro")
    primeiro.__enter__()
    try:
        with pytest.raises(LockfileOcupado) as exc_info:
            with Lockfile(lock_path, "segundo"):
                pass
        # Exception carrega path e pid:
        assert exc_info.value.path == lock_path
        assert exc_info.value.pid_dono == os.getpid()
    finally:
        primeiro.__exit__(None, None, None)


def test_lock_ativo_detecta_lock_pendente(tmp_path: Path) -> None:
    """``lock_ativo()`` retorna True enquanto lock está mantido."""
    lock_path = tmp_path / "pipeline.lock"
    assert lock_ativo(lock_path) is False  # ausente
    primeiro = Lockfile(lock_path, "x")
    primeiro.__enter__()
    try:
        assert lock_ativo(lock_path) is True
    finally:
        primeiro.__exit__(None, None, None)
    assert lock_ativo(lock_path) is False  # liberado


def test_pid_do_lock_retorna_pid_real(tmp_path: Path) -> None:
    """``pid_do_lock()`` lê o PID do dono do lock."""
    lock_path = tmp_path / "pipeline.lock"
    assert pid_do_lock(lock_path) is None
    primeiro = Lockfile(lock_path, "x")
    primeiro.__enter__()
    try:
        assert pid_do_lock(lock_path) == os.getpid()
    finally:
        primeiro.__exit__(None, None, None)


def _segurar_lock_subprocess(path_str: str, duracao_s: float) -> None:
    """Função auxiliar para teste multiprocess (top-level para pickling)."""
    with Lockfile(Path(path_str), "subprocess"):
        time.sleep(duracao_s)


def test_lock_entre_processos_diferentes(tmp_path: Path) -> None:
    """Subprocesso adquire lock; processo pai recebe LockfileOcupado."""
    lock_path = tmp_path / "pipeline.lock"
    proc = multiprocessing.Process(
        target=_segurar_lock_subprocess,
        args=(str(lock_path), 1.5),
    )
    proc.start()
    # Espera subprocess pegar o lock:
    time.sleep(0.3)
    try:
        with pytest.raises(LockfileOcupado) as exc_info:
            with Lockfile(lock_path, "pai"):
                pass
        # PID do dono = subprocess.pid, não meu PID:
        assert exc_info.value.pid_dono == proc.pid
    finally:
        proc.join(timeout=3)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=2)


# "Duas mãos no mesmo tear desfazem o tecido." -- principio
