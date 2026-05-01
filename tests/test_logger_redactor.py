"""Sprint 99 -- regressão do redactor de PII em logs.

Contrato: filter `FiltroRedactorPII` mascara CPF e CNPJ literais em mensagens
de nível INFO ou superior; preserva DEBUG (uso dev). Função pura
`mascarar_pii` é a unidade testável -- testes do filter exercitam a
integração via `logging` real.
"""

from __future__ import annotations

import logging

import pytest

from src.utils.logger import FiltroRedactorPII, hash_curto_pii, mascarar_pii

# ---------------------------------------------------------------------------
# mascarar_pii (função pura)
# ---------------------------------------------------------------------------


def test_mascarar_pii_cpf_substitui_por_placeholder():
    msg = "fonte: CPF 123.456.789-01 detectado"
    assert mascarar_pii(msg) == "fonte: CPF XXX.XXX.XXX-XX detectado"


def test_mascarar_pii_cnpj_pj_preserva_indicador_matriz():
    """CNPJ /0001-XX (matriz/PJ/MEI) recebe placeholder específico."""
    msg = "CNPJ 52.488.753/0001-10 casou pessoas.yaml"
    assert mascarar_pii(msg) == "CNPJ XX.XXX.XXX/0001-XX casou pessoas.yaml"


def test_mascarar_pii_cnpj_filial_recebe_placeholder_generico():
    msg = "CNPJ 12.345.678/0002-90 detectado"
    assert mascarar_pii(msg) == "CNPJ XX.XXX.XXX/XXXX-XX detectado"


def test_mascarar_pii_combinada_cpf_e_cnpj_no_mesmo_log():
    msg = "CPF 070.475.128-90 e CNPJ 52.488.753/0001-10"
    esperado = "CPF XXX.XXX.XXX-XX e CNPJ XX.XXX.XXX/0001-XX"
    assert mascarar_pii(msg) == esperado


def test_mascarar_pii_mensagem_sem_pii_passa_intacta():
    """Regressão: filter não introduz garbage em mensagens limpas."""
    msg = "pessoa auto-detectada: andre (fonte: path 'andre/')"
    assert mascarar_pii(msg) == msg


def test_mascarar_pii_string_vazia():
    assert mascarar_pii("") == ""


# ---------------------------------------------------------------------------
# hash_curto_pii (função pura)
# ---------------------------------------------------------------------------


def test_hash_curto_pii_e_deterministico_e_oito_hex():
    h = hash_curto_pii("VITORIA MARIA SILVA DOS SANTOS")
    assert len(h) == 8
    assert all(c in "0123456789abcdef" for c in h)
    # determinismo
    assert hash_curto_pii("VITORIA MARIA SILVA DOS SANTOS") == h


def test_hash_curto_pii_normaliza_caixa_e_espacos():
    """Mesmo nome com casing/espaços diferentes gera mesmo hash."""
    a = hash_curto_pii("Andre Farias")  # anonimato-allow: fixture de matcher
    b = hash_curto_pii("  ANDRE FARIAS  ")
    assert a == b


# ---------------------------------------------------------------------------
# FiltroRedactorPII (integração com logging real)
# ---------------------------------------------------------------------------


@pytest.fixture
def logger_com_filter(caplog):
    """Logger isolado com filter aplicado, captura via caplog."""
    log = logging.getLogger("teste-pii-99")
    # limpa filtros pré-existentes (em re-runs)
    log.filters[:] = []
    log.addFilter(FiltroRedactorPII())
    log.setLevel(logging.DEBUG)
    yield log
    log.filters[:] = []


def test_filter_mascara_cpf_em_info(logger_com_filter, caplog):
    with caplog.at_level(logging.INFO, logger="teste-pii-99"):
        logger_com_filter.info("CPF detectado: 123.456.789-01")
    assert any("XXX.XXX.XXX-XX" in r.getMessage() for r in caplog.records)
    assert not any("123.456.789-01" in r.getMessage() for r in caplog.records)


def test_filter_mascara_cnpj_pj_em_info(logger_com_filter, caplog):
    with caplog.at_level(logging.INFO, logger="teste-pii-99"):
        logger_com_filter.info("CNPJ MEI 52.488.753/0001-10 casou")
    msgs = [r.getMessage() for r in caplog.records]
    assert any("XX.XXX.XXX/0001-XX" in m for m in msgs)
    assert not any("52.488.753" in m for m in msgs)


def test_filter_mascara_cnpj_mei_em_info(logger_com_filter, caplog):
    """CNPJ-MEI tem mesmo formato 0001-XX que PJ -- mesmo placeholder."""
    with caplog.at_level(logging.INFO, logger="teste-pii-99"):
        logger_com_filter.info("Pessoa via CNPJ 45.850.636/0001-60 (MEI Andre)")  # anonimato-allow
    msgs = [r.getMessage() for r in caplog.records]
    assert any("XX.XXX.XXX/0001-XX" in m for m in msgs)
    assert not any("45.850.636" in m for m in msgs)


def test_filter_mascara_em_warning_e_error(logger_com_filter, caplog):
    """Niveis acima de INFO também são mascarados."""
    with caplog.at_level(logging.WARNING, logger="teste-pii-99"):
        logger_com_filter.warning("cpf inválido: 070.475.128-90")
        logger_com_filter.error("erro com CNPJ 12.345.678/0001-99")
    msgs = [r.getMessage() for r in caplog.records]
    assert any("XXX.XXX.XXX-XX" in m for m in msgs)
    assert any("XX.XXX.XXX/0001-XX" in m for m in msgs)


def test_filter_preserva_pii_em_debug(logger_com_filter, caplog):
    """Contrato: DEBUG mantém literal para uso de desenvolvedor."""
    with caplog.at_level(logging.DEBUG, logger="teste-pii-99"):
        logger_com_filter.debug("debug raw CPF 123.456.789-01")
        logger_com_filter.debug("debug raw CNPJ 52.488.753/0001-10")
    msgs = [r.getMessage() for r in caplog.records]
    debug_msgs = [m for m in msgs if "debug raw" in m]
    assert any("123.456.789-01" in m for m in debug_msgs)
    assert any("52.488.753/0001-10" in m for m in debug_msgs)


def test_filter_funciona_com_format_args(logger_com_filter, caplog):
    """Mensagem interpolada via %s deve ser mascarada após format."""
    with caplog.at_level(logging.INFO, logger="teste-pii-99"):
        logger_com_filter.info("CPF %s e CNPJ %s", "070.475.128-90", "52.488.753/0001-10")
    msgs = [r.getMessage() for r in caplog.records]
    assert any("XXX.XXX.XXX-XX" in m and "XX.XXX.XXX/0001-XX" in m for m in msgs)
    assert not any("070.475.128-90" in m for m in msgs)
    assert not any("52.488.753" in m for m in msgs)


def test_filter_mensagem_sem_pii_passa_intacta(logger_com_filter, caplog):
    """Regressão: filter não introduz lixo em mensagens limpas."""
    msg = "pessoa auto-detectada: andre (fonte: path 'andre/')"
    with caplog.at_level(logging.INFO, logger="teste-pii-99"):
        logger_com_filter.info(msg)
    assert any(r.getMessage() == msg for r in caplog.records)


# "Log é artefato persistente. PII não pode vazar nele." -- princípio de privacy by default
