"""Configuração centralizada de logging com rotação de arquivos."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler


def configurar_logger(nome: str, nivel: int = logging.INFO) -> logging.Logger:
    """Configura e retorna um logger com saída rich no terminal e rotação em arquivo."""
    logger = logging.getLogger(nome)

    if logger.handlers:
        return logger

    logger.setLevel(nivel)

    diretorio_logs = Path(__file__).parent.parent.parent / "logs"
    diretorio_logs.mkdir(exist_ok=True)

    handler_arquivo = RotatingFileHandler(
        diretorio_logs / "controle_de_bordo.log",
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler_arquivo.setLevel(logging.DEBUG)
    handler_arquivo.setFormatter(
        logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    )

    handler_console = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=False,
    )
    handler_console.setLevel(nivel)

    logger.addHandler(handler_arquivo)
    logger.addHandler(handler_console)

    return logger


# "O homem que move montanhas começa carregando pequenas pedras." -- Confúcio
