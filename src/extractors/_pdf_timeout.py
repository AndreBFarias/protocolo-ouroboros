"""Timeout para operações pdfplumber via signal.SIGALRM (Sprint INFRA-PDF-TIMEOUT).

PDFs corrompidos ou muito grandes podem fazer pdfplumber hangar
indefinidamente (loop em pdfminer parse). Como o pipeline ETL é serial,
uma travada bloqueia toda execução de ``./run.sh --tudo``.

Estratégia: context manager que arma signal.SIGALRM antes de operação
PDF arriscada. Se passar do limite, levanta ``TimeoutError`` — extrator
captura, loga, retorna dict vazio (falha-soft canônica do projeto).

Limitação: Linux/macOS only (signal.SIGALRM não disponível no Windows).
Suficiente para o caso de uso atual (ambiente do dono é Ubuntu).

Uso típico::

    from src.extractors._pdf_timeout import pdf_timeout

    try:
        with pdf_timeout(30):
            with pdfplumber.open(caminho) as pdf:
                texto = pdf.pages[0].extract_text()
    except TimeoutError:
        logger.error("PDF %s travou (>30s); pulando.", caminho)
        return {}

Configuração via env var ``OUROBOROS_PDF_TIMEOUT`` (default 30s).
"""

from __future__ import annotations

import os
import signal
from contextlib import contextmanager
from typing import Iterator

from src.utils.logger import configurar_logger

logger = configurar_logger("pdf_timeout")

TIMEOUT_DEFAULT_S: int = 30


def timeout_padrao() -> int:
    """Retorna timeout configurado via OUROBOROS_PDF_TIMEOUT (segundos).

    Falha-soft: valor inválido cai no default.
    """
    raw = os.environ.get("OUROBOROS_PDF_TIMEOUT", "")
    if not raw:
        return TIMEOUT_DEFAULT_S
    try:
        valor = int(raw)
        if valor > 0:
            return valor
    except ValueError:
        pass
    logger.warning(
        "OUROBOROS_PDF_TIMEOUT inválido (%r); usando default %ds.",
        raw,
        TIMEOUT_DEFAULT_S,
    )
    return TIMEOUT_DEFAULT_S


@contextmanager
def pdf_timeout(segundos: int | None = None) -> Iterator[None]:
    """Context manager que aborta operação via SIGALRM se demorar mais que N segundos.

    Args:
        segundos: limite em segundos. Se None, usa ``timeout_padrao()``.

    Raises:
        TimeoutError: se a operação interna ultrapassar o limite.

    Notas:
        - Apenas Linux/macOS (SIGALRM). Em outros SOs, vira no-op.
        - Idempotente: salva handler anterior e restaura no exit.
        - Não thread-safe (SIGALRM é signal de processo). Aceitável
          para pipeline serial.
    """
    if not hasattr(signal, "SIGALRM"):
        # Windows: signal não disponível. No-op + warning.
        logger.warning("signal.SIGALRM indisponivel; timeout ignorado.")
        yield
        return

    limite = segundos if segundos and segundos > 0 else timeout_padrao()

    def _handler(_signum, _frame):
        raise TimeoutError(f"Operação PDF excedeu {limite}s")

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(limite)
    try:
        yield
    finally:
        signal.alarm(0)  # desarma
        signal.signal(signal.SIGALRM, old_handler)


# "Pipeline serial morre em 1 travada; timeout é o despertador honesto."
# -- princípio do crash predictable
