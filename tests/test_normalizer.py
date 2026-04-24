"""Testes de inferências do normalizer."""

from datetime import date

from src.transform.normalizer import (
    extrair_local,
    gerar_hash_transacao,
    inferir_forma_pagamento,
    inferir_pessoa,
    inferir_tipo_transacao,
    normalizar_transacao,
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
    """Sprint 93f: rótulo canônico `Nubank (PF)` (com parênteses) mapeia
    para Vitória. Antes da 93f o set esperava `Nubank PF` sem parênteses
    enquanto extratores emitiam com parênteses, produzindo fallback Casal."""
    assert inferir_pessoa("Nubank (PF)") == "Vitória"


def test_pessoa_nubank_default_eh_andre():
    """Nubank genérico (sem subtipo) = André."""
    assert inferir_pessoa("Nubank") == "André"


def test_pessoa_desconhecido_eh_casal():
    assert inferir_pessoa("BancoX") == "Casal"


# --- Sprint 55: regressão do classificador de tipo ---


def test_juros_fatura_atrasada_e_despesa():
    """Juros de fatura nunca são Receita, mesmo com valor absoluto positivo."""
    resultado = normalizar_transacao(
        data_transacao=date(2026, 4, 1),
        valor=53.23,
        descricao="Juros por fatura atrasada",
        banco_origem="Nubank",
        tipo_extrato="cartao",
        tipo_sugerido="Despesa",
    )
    assert resultado["tipo"] == "Despesa"


def test_transf_enviada_pix_e_despesa():
    """TRANSF ENVIADA PIX é saída, não Receita."""
    resultado = normalizar_transacao(
        data_transacao=date(2026, 4, 3),
        valor=96.15,
        descricao="TRANSF ENVIADA PIX",
        banco_origem="Nubank",
        tipo_extrato="cc",
        tipo_sugerido="Despesa",
        valor_original_com_sinal=-96.15,
    )
    assert resultado["tipo"] == "Despesa"


def test_fatura_cartao_em_cc_e_transferencia_interna():
    """Pagamento de fatura de cartão em CC = Transferência Interna (não despesa)."""
    resultado = normalizar_transacao(
        data_transacao=date(2026, 4, 14),
        valor=90.64,
        descricao="Fatura de cartão",
        banco_origem="Nubank",
        tipo_extrato="cc",
        tipo_sugerido="Despesa",
        valor_original_com_sinal=-90.64,
    )
    assert resultado["tipo"] == "Transferência Interna"


def test_salario_e_receita():
    """Salário permanece Receita (contrato existente)."""
    resultado = normalizar_transacao(
        data_transacao=date(2026, 4, 8),
        valor=7442.38,
        descricao="PAGTO SALARIO",
        banco_origem="Itaú",
        tipo_extrato="cc",
        tipo_sugerido="Receita",
        valor_original_com_sinal=7442.38,
    )
    assert resultado["tipo"] == "Receita"


def test_compra_varejo_e_despesa():
    """Compra em drogaria com tipo sugerido Despesa não vira Receita."""
    resultado = normalizar_transacao(
        data_transacao=date(2026, 4, 10),
        valor=52.00,
        descricao="DROGARIA SILVA FARMA",
        banco_origem="Nubank",
        tipo_extrato="cartao",
        tipo_sugerido="Despesa",
    )
    assert resultado["tipo"] == "Despesa"


def test_transferencia_interna_prevalece_sobre_tipo_sugerido():
    """Regex de TI sempre ganha, mesmo que extrator diga Despesa."""
    resultado = inferir_tipo_transacao(
        valor=500.0,
        descricao="Transferencia enviada - VITORIA MARIA",
        tipo_sugerido="Despesa",
    )
    assert resultado == "Transferência Interna"


def test_imposto_prevalece_sobre_tipo_sugerido():
    """Regex de Imposto sempre ganha."""
    resultado = inferir_tipo_transacao(
        valor=100.0,
        descricao="DARF Imposto Federal",
        tipo_sugerido="Despesa",
    )
    assert resultado == "Imposto"


def test_tipo_sugerido_invalido_cai_para_regex():
    """tipo_sugerido fora do conjunto válido é ignorado."""
    resultado = inferir_tipo_transacao(
        valor=500.0,
        descricao="Crédito qualquer",
        tipo_sugerido="Coisa Inválida",
        valor_com_sinal=500.0,
    )
    assert resultado == "Receita"


def test_estorno_em_cartao_vira_receita():
    """Título com 'Estorno' no cartão vira Receita via regex."""
    resultado = inferir_tipo_transacao(
        valor=150.0,
        descricao="Estorno de compra - LOJA X",
    )
    assert resultado == "Receita"


# "Quem conhece os outros é sábio; quem conhece a si próprio é iluminado." -- Lao-Tsé
