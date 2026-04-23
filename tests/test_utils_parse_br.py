"""Sprint INFRA-parse-br: testes canônicos de parse_valor_br e parse_valor_br_float."""

import pytest

from src.utils.parse_br import parse_valor_br, parse_valor_br_float

# parse_valor_br (nullable)


def test_parse_valor_br_formato_com_milhar():
    assert parse_valor_br("1.234,56") == pytest.approx(1234.56)


def test_parse_valor_br_formato_simples():
    assert parse_valor_br("103,93") == pytest.approx(103.93)


def test_parse_valor_br_none_entra_none_sai():
    assert parse_valor_br(None) is None


def test_parse_valor_br_vazio_vira_none():
    assert parse_valor_br("") is None
    assert parse_valor_br("   ") is None


def test_parse_valor_br_invalido_vira_none():
    assert parse_valor_br("abc") is None
    assert parse_valor_br("R$ 127,00") is None  # prefixo não é responsabilidade


# parse_valor_br_float (não-nullable)


def test_parse_valor_br_float_formato_brasileiro():
    assert parse_valor_br_float("1.234,56") == pytest.approx(1234.56)


def test_parse_valor_br_float_none_usa_default():
    assert parse_valor_br_float(None) == 0.0
    assert parse_valor_br_float(None, default=-1.0) == -1.0


def test_parse_valor_br_float_vazio_usa_default():
    assert parse_valor_br_float("") == 0.0
    assert parse_valor_br_float("abc", default=99.0) == 99.0
