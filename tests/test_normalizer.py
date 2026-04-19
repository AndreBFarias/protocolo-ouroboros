"""Testes de inferências do normalizer."""

from datetime import date

from src.transform.normalizer import (
    extrair_local,
    gerar_hash_transacao,
    inferir_forma_pagamento,
    inferir_pessoa,
    inferir_tipo_transacao,
)


def test_hash_determinístico():
    """Mesma entrada → mesmo hash (16 chars)."""
    h1 = gerar_hash_transacao(date(2026, 3, 15), "Padaria X", 50.0)
    h2 = gerar_hash_transacao(date(2026, 3, 15), "Padaria X", 50.0)
    assert h1 == h2
    assert len(h1) == 16


def test_hash_ignora_caixa_espacos():
    """Hash normaliza case e trim antes de hashear."""
    h1 = gerar_hash_transacao(date(2026, 3, 15), "  Padaria X  ", 50.0)
    h2 = gerar_hash_transacao(date(2026, 3, 15), "padaria x", 50.0)
    assert h1 == h2


def test_forma_pagamento_pix():
    assert inferir_forma_pagamento("Pix enviado para João", "Nubank", "cc") == "Pix"


def test_forma_pagamento_boleto():
    assert inferir_forma_pagamento("Pagamento de boleto CEMIG", "Itaú", "cc") == "Boleto"


def test_forma_pagamento_cartao_sempre_credito():
    """Fatura de cartão ignora descrição e força Crédito."""
    assert inferir_forma_pagamento("Qualquer coisa", "Nubank", "cartao") == "Crédito"


def test_tipo_transferencia_interna_pix_para_vitoria():
    """Armadilha de PIX para Vitória = TI, não gasto."""
    desc = "Transferencia enviada - VITORIA MARIA"
    assert inferir_tipo_transacao(-500.0, desc) == "Transferência Interna"


def test_tipo_imposto_darf():
    assert inferir_tipo_transacao(-100.0, "DARF Imposto Federal") == "Imposto"


def test_tipo_despesa_padrao_negativo():
    """Valor negativo sem padrão especial → Despesa."""
    assert inferir_tipo_transacao(-50.0, "Compra genérica") == "Despesa"


def test_tipo_receita_valor_positivo():
    """Valor positivo sem padrão → Receita."""
    assert inferir_tipo_transacao(500.0, "Crédito qualquer") == "Receita"


def test_local_extrai_nome_de_pix_nubank():
    """Nubank CC: 'Transferência enviada pelo Pix - NOME - ...'"""
    desc = "Transferência enviada pelo Pix - JOAO SILVA - 12345678901 - BANCO X"
    assert extrair_local(desc) == "JOAO SILVA"


def test_local_fallback_para_descricao_curta():
    """Descrição curta retorna como está."""
    assert extrair_local("Padaria X") == "Padaria X"


def test_pessoa_itau_eh_andre():
    assert inferir_pessoa("Itaú") == "André"


def test_pessoa_nubank_pf_eh_vitoria():
    assert inferir_pessoa("Nubank PF") == "Vitória"


def test_pessoa_nubank_default_eh_andre():
    """Nubank genérico (sem subtipo) = André."""
    assert inferir_pessoa("Nubank") == "André"


def test_pessoa_desconhecido_eh_casal():
    assert inferir_pessoa("BancoX") == "Casal"


# "Quem conhece os outros é sábio; quem conhece a si próprio é iluminado." -- Lao-Tsé
