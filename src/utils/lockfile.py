"""Lockfile/PIDfile baseado em ``fcntl.flock`` para serializar escritas.

Sprint INFRA-CONCORRENCIA-PIDFILE (2026-05-16). Resolve cenário de
concorrência:

1. Dono roda ``./run.sh --tudo`` enquanto dashboard está aberto: SQLite
   WAL mitiga grafo, mas XLSX em escrita via openpyxl pode corromper.
2. Cron/hook dispara ``--inbox`` enquanto dono roda ``--full-cycle``: 2
   pipelines escrevendo grafo. Dedup ambíguo.

Estratégia: arquivo de lock em ``data/.pipeline.lock`` com ``LOCK_EX |
LOCK_NB``. Quem pegou primeiro escreve seu PID. Quem chega depois recebe
``BlockingIOError`` e pode reagir (exit 1, retry com timeout, ou esperar
silencioso conforme caso de uso).

API canônica::

    from src.utils.lockfile import Lockfile, lock_ativo

    with Lockfile(path, "rota completa pipeline"):
        executar()  # critical section

    # Em outro processo (dashboard):
    if lock_ativo(path):
        st.toast("Pipeline rodando, dados podem estar obsoletos")

Padrão (n) defesa em camadas: lock em Python (esta classe) + lock em
Bash (flock no run.sh) — duas barreiras independentes.
"""

from __future__ import annotations

import fcntl
import os
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType

from src.utils.logger import configurar_logger

logger = configurar_logger("lockfile")


class LockfileOcupado(BlockingIOError):
    """Tentativa de adquirir lock que já está mantido por outro processo."""

    def __init__(self, path: Path, pid_dono: int | None) -> None:
        msg = (
            f"Lockfile {path} ja mantido por PID {pid_dono if pid_dono else 'desconhecido'}. "
            f"Outra instancia do pipeline esta rodando."
        )
        super().__init__(msg)
        self.path = path
        self.pid_dono = pid_dono


class Lockfile(AbstractContextManager):
    """Context manager que adquire lock exclusivo via fcntl.flock.

    Uso típico::

        with Lockfile(Path("data/.pipeline.lock"), "ETL completo"):
            # zona crítica

    Em caso de outro processo mantendo o lock: levanta ``LockfileOcupado``
    contendo o PID-dono lido do arquivo (se gravado).
    """

    def __init__(self, path: Path, descricao: str) -> None:
        self.path = path
        self.descricao = descricao
        self._fd: int | None = None

    def __enter__(self) -> "Lockfile":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Abre/cria, sem truncar — se outro processo já escreveu o PID,
        # queremos ler para a mensagem de erro:
        self._fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pid_dono = _ler_pid_do_arquivo(self.path)
            os.close(self._fd)
            self._fd = None
            raise LockfileOcupado(self.path, pid_dono) from None
        # Lock adquirido — escreve nosso PID + descrição:
        os.lseek(self._fd, 0, os.SEEK_SET)
        os.ftruncate(self._fd, 0)
        os.write(
            self._fd,
            f"{os.getpid()}\n{self.descricao}\n".encode("utf-8"),
        )
        logger.info(
            "Lock adquirido em %s (PID=%d, descricao=%s).",
            self.path,
            os.getpid(),
            self.descricao,
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None
            # Apaga o arquivo de lock para sinalizar "limpo" — próximo
            # acquire encontra estado fresco:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            logger.info("Lock liberado em %s.", self.path)


def _ler_pid_do_arquivo(path: Path) -> int | None:
    """Lê o PID gravado no lock (1ª linha) sem aguardar."""
    try:
        primeira_linha = path.read_text(encoding="utf-8").splitlines()[0]
        return int(primeira_linha.strip())
    except (OSError, IndexError, ValueError):
        return None


def lock_ativo(path: Path) -> bool:
    """Verifica se existe lock ativo no path (não tenta adquirir).

    Útil para o dashboard: se True, render mostra toast "pipeline rodando".
    Implementação: tenta adquirir lock SHARED em modo NB — se falha, há
    EX lock ativo. Libera imediatamente.

    Falha-soft: se arquivo não existe ou erro de fs, retorna False.
    """
    if not path.exists():
        return False
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
    finally:
        os.close(fd)


def pid_do_lock(path: Path) -> int | None:
    """Retorna PID que mantém o lock (se houver e for legível)."""
    if not lock_ativo(path):
        return None
    return _ler_pid_do_arquivo(path)


# "Duas mãos no mesmo tear desfazem o tecido." -- principio da serializacao
