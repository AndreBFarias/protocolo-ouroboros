"""Testes do `_descobrir_extratores` (Sprint INFRA-DESCOBRIR-EXTRATORES-REFATORA).

Cobre: count canonico, env var desabilitar, falha-soft em import error.
"""

from __future__ import annotations

import pytest

import src.pipeline as pipeline_mod


@pytest.fixture(autouse=True)
def _limpa_env(monkeypatch):
    """Garante isolamento de env entre testes."""
    monkeypatch.delenv("OUROBOROS_EXTRATORES_DESABILITADOS", raising=False)
    yield


def test_descobrir_acha_extratores_canonicos():
    """Sem env var, todos os extratores canônicos são importados (ou logados)."""
    classes = pipeline_mod._descobrir_extratores()
    # Lista canônica tem 20 entries; pelo menos 18 devem importar (margem
    # de erro para dependências opcionais como pdfplumber/tesseract):
    assert len(classes) >= 18
    assert len(classes) <= len(pipeline_mod.EXTRATORES_CANONICOS)


def test_descobrir_pula_via_env_var(monkeypatch):
    """OUROBOROS_EXTRATORES_DESABILITADOS=nome,nome2 pula esses."""
    monkeypatch.setenv("OUROBOROS_EXTRATORES_DESABILITADOS", "nubank_cartao,c6_cc")
    classes = pipeline_mod._descobrir_extratores()
    nomes = {c.__name__ for c in classes}
    assert "ExtratorNubankCartao" not in nomes
    assert "ExtratorC6CC" not in nomes


def test_descobrir_via_argumento_explicito():
    """Argumento `desabilitados` tem precedência sobre env var."""
    classes_todos = pipeline_mod._descobrir_extratores(desabilitados=set())
    classes_filtrados = pipeline_mod._descobrir_extratores(
        desabilitados={"itau_pdf", "santander_pdf"}
    )
    nomes_filtrados = {c.__name__ for c in classes_filtrados}
    assert "ExtratorItauPDF" not in nomes_filtrados
    assert "ExtratorSantanderPDF" not in nomes_filtrados
    assert len(classes_todos) >= len(classes_filtrados) + 2


def test_descobrir_preserva_ordem_canonica():
    """Ordem das classes retornadas espelha EXTRATORES_CANONICOS."""
    classes = pipeline_mod._descobrir_extratores()
    # Primeira classe na lista deve ser ExtratorNubankCartao (módulo nubank_cartao):
    assert classes[0].__name__ == "ExtratorNubankCartao"
    # Última classe esperada: ExtratorReciboNaoFiscal
    assert classes[-1].__name__ == "ExtratorReciboNaoFiscal"


def test_descobrir_falha_soft_em_modulo_inexistente(monkeypatch, caplog):
    """Modulo inexistente é logado mas não crasha."""
    import logging

    # Injeta um modulo inválido na lista canônica:
    canonicos_orig = pipeline_mod.EXTRATORES_CANONICOS.copy()
    monkeypatch.setattr(
        pipeline_mod,
        "EXTRATORES_CANONICOS",
        canonicos_orig + [("src.extractors.nao_existe", "ExtratorFake")],
    )

    with caplog.at_level(logging.WARNING, logger="pipeline"):
        pipeline_mod._descobrir_extratores()
    # Real continuam funcionando + fake foi logado:
    assert any("nao_existe" in r.message for r in caplog.records)


# "Lista declarativa elimina ritual. Ritual sempre que repetido vira código morto."
# -- princípio do DRY honesto
