"""Testes do `_pdf_timeout` helper (Sprint INFRA-PDF-TIMEOUT).

Cobre: timeout dispara, normal passa, env var override, no-op em SO sem SIGALRM.
"""

from __future__ import annotations

import os
import time

import pytest

from src.extractors._pdf_timeout import (
    TIMEOUT_DEFAULT_S,
    pdf_timeout,
    timeout_padrao,
)


def test_timeout_padrao_devolve_default():
    """Sem env var, retorna TIMEOUT_DEFAULT_S."""
    os.environ.pop("OUROBOROS_PDF_TIMEOUT", None)
    assert timeout_padrao() == TIMEOUT_DEFAULT_S


def test_timeout_padrao_le_env_var(monkeypatch):
    """Env var válido sobrescreve default."""
    monkeypatch.setenv("OUROBOROS_PDF_TIMEOUT", "60")
    assert timeout_padrao() == 60


def test_timeout_padrao_ignora_env_invalido(monkeypatch):
    """Env var inválido cai no default."""
    monkeypatch.setenv("OUROBOROS_PDF_TIMEOUT", "abc")
    assert timeout_padrao() == TIMEOUT_DEFAULT_S


def test_timeout_padrao_ignora_negativo(monkeypatch):
    """Valor negativo cai no default."""
    monkeypatch.setenv("OUROBOROS_PDF_TIMEOUT", "-5")
    assert timeout_padrao() == TIMEOUT_DEFAULT_S


@pytest.mark.skipif(
    not hasattr(__import__("signal"), "SIGALRM"),
    reason="signal.SIGALRM indisponivel (Windows)",
)
def test_pdf_timeout_aborta_em_excesso():
    """time.sleep(5) com timeout=1 deve levantar TimeoutError."""
    with pytest.raises(TimeoutError):
        with pdf_timeout(1):
            time.sleep(5)


@pytest.mark.skipif(
    not hasattr(__import__("signal"), "SIGALRM"),
    reason="signal.SIGALRM indisponivel",
)
def test_pdf_timeout_passa_em_operacao_normal():
    """Operação rápida não levanta exceção."""
    with pdf_timeout(2):
        x = 1 + 1
    assert x == 2


@pytest.mark.skipif(
    not hasattr(__import__("signal"), "SIGALRM"),
    reason="signal.SIGALRM indisponivel",
)
def test_pdf_timeout_restaura_handler_apos_exit():
    """Handler anterior é restaurado mesmo em exceção."""
    import signal as sig

    original = sig.getsignal(sig.SIGALRM)
    try:
        with pdf_timeout(1):
            time.sleep(2)
    except TimeoutError:
        pass
    atual = sig.getsignal(sig.SIGALRM)
    # Ponto chave: handler atual == original (não vazou):
    assert atual == original


# "Pipeline serial morre em 1 travada; timeout e o despertador honesto."
# -- principio do crash predictable
