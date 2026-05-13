"""Testes da Sprint INFRA-DEDUP-C6-OFX-XLSX-AMPLO.

Valida o fix arquitetural que elimina 253 pares duplicados no C6/pessoa_a:
- Nível 2a: normalização do `local` removendo prefixo bancário antes do
  primeiro ` - ` (cobre 197 dos 253 pares).
- Nível 2b: pass adicional que consolida pares OFX + XLSX do mesmo banco
  quando `_arquivo_origem` diverge (cobre os 56 restantes onde o XLSX
  C6 traz descrição genérica como `"TRANSF ENVIADA PIX"` enquanto o OFX
  traz `"Pix enviado para X - TRANSF E"`).

Cenário de origem: auditoria DUPLICACAO_C6_OFX_XLSX_2026-05-12.md.
"""

from datetime import date

from src.transform.deduplicator import (
    _consolidar_pares_ofx_xlsx_mesmo_banco,
    _normalizar_local_para_chave,
    deduplicar_por_hash_fuzzy,
)


def _t(
    data_t: date,
    valor: float,
    local: str,
    banco: str = "C6",
    forma: str = "Débito",
    arquivo_origem: str | None = None,
    quem: str = "pessoa_a",
    descricao_original: str | None = None,
) -> dict:
    """Constrói transação canônica para teste."""
    return {
        "data": data_t,
        "valor": valor,
        "forma_pagamento": forma,
        "local": local,
        "quem": quem,
        "categoria": None,
        "classificacao": None,
        "banco_origem": banco,
        "tipo": "Despesa",
        "mes_ref": data_t.strftime("%Y-%m"),
        "tag_irpf": None,
        "obs": None,
        "_identificador": None,
        "_descricao_original": descricao_original or local,
        "_arquivo_origem": arquivo_origem,
    }


# ---------------------------------------------------------------------------
# Caso canônico da spec: par R$ 6.381,14 / 2026-03-06 (salário G4F).
# ---------------------------------------------------------------------------


def test_par_salario_g4f_consolida_via_normalizacao():
    """O par exato da spec deve ser consolidado em 1 linha após o fix.

    OFX produz `"RECEBIMENTO SALARIO - 5127373122-ANDRE DA SILVA BATISTA DE F"`
    XLSX produz `"5127373122-ANDRE DA SILVA BATISTA DE FAR"`

    Truncamento difere (F vs FAR), mas o pass 2b consolida via
    `_arquivo_origem` quando OFX + XLSX colidem no mesmo banco/quem/data/valor.
    """
    ofx = _t(
        date(2026, 3, 6),
        6381.14,
        "RECEBIMENTO SALARIO - 5127373122-ANDRE DA SILVA BATISTA DE F",
        forma="Débito",
        arquivo_origem="BANCARIO_C6_OFX_b0ccc591.ofx",
    )
    xlsx = _t(
        date(2026, 3, 6),
        6381.14,
        "5127373122-ANDRE DA SILVA BATISTA DE FAR",
        forma="Crédito",
        arquivo_origem="BANCARIO_C6_CC_2026-03_af57ffc8.xlsx",
    )
    resultado = deduplicar_por_hash_fuzzy([ofx, xlsx])
    assert len(resultado) == 1, "Par G4F deve consolidar em 1 linha após fix"
    # Preserva o OFX (descrição mais rica)
    assert "RECEBIMENTO SALARIO" in resultado[0]["local"]


# ---------------------------------------------------------------------------
# 5 outros padrões conhecidos (cobrem normalização do nível 2a).
# ---------------------------------------------------------------------------


def test_padrao_cartao_consolida_via_split():
    """`"DEBITO DE CARTAO - <X>"` (OFX) casa com `"<X>"` (XLSX) via split."""
    ofx = _t(
        date(2026, 4, 10),
        50.0,
        "DEBITO DE CARTAO - SACOLAO DA ECONOMIA Brasília BRA",
        arquivo_origem="x.ofx",
    )
    xlsx = _t(
        date(2026, 4, 10),
        50.0,
        "SACOLAO DA ECONOMIA Brasília BRA",
        arquivo_origem="x.xlsx",
    )
    resultado = deduplicar_por_hash_fuzzy([ofx, xlsx])
    assert len(resultado) == 1


def test_padrao_fatura_consolida_via_split():
    """`"PGTO FAT CARTAO C6 - Fatura de cartão"` casa com `"Fatura de cartão"`."""
    ofx = _t(
        date(2026, 4, 24),
        132.61,
        "PGTO FAT CARTAO C6 - Fatura de cartão",
        arquivo_origem="x.ofx",
    )
    xlsx = _t(
        date(2026, 4, 24),
        132.61,
        "Fatura de cartão",
        arquivo_origem="x.xlsx",
    )
    resultado = deduplicar_por_hash_fuzzy([ofx, xlsx])
    assert len(resultado) == 1


def test_padrao_pix_descricao_generica_xlsx_consolida_via_2b():
    """Caso real C6: XLSX traz `"TRANSF ENVIADA PIX"` (genérico), OFX detalha
    o destinatário. Normalização de prefixo NÃO casa (locais materialmente
    distintos); o pass 2b casa via `_arquivo_origem`.
    """
    ofx = _t(
        date(2026, 4, 26),
        530.0,
        "Pix enviado para André da Silva Batista de Farias - TRANSF E",
        forma="Pix",
        arquivo_origem="BANCARIO_C6_OFX_b0ccc591.ofx",
    )
    xlsx = _t(
        date(2026, 4, 26),
        530.0,
        "TRANSF ENVIADA PIX",
        forma="Pix",
        arquivo_origem="BANCARIO_C6_CC_2026-04_af57ffc8.xlsx",
    )
    resultado = deduplicar_por_hash_fuzzy([ofx, xlsx])
    assert len(resultado) == 1
    assert "Pix enviado para" in resultado[0]["local"]


def test_padrao_cdb_ofx_sem_descricao_consolida_via_2b():
    """OFX entrega `"Transação OFX sem descrição"` enquanto XLSX detalha
    `"CDB C6 LIM. GARANT."`. Pass 2b consolida via banco+data+valor.
    """
    ofx = _t(
        date(2026, 5, 29),
        394.84,
        "Transação OFX sem descrição",
        arquivo_origem="x.ofx",
    )
    xlsx = _t(
        date(2026, 5, 29),
        394.84,
        "CDB C6 LIM. GARANT.",
        arquivo_origem="x.xlsx",
    )
    resultado = deduplicar_por_hash_fuzzy([ofx, xlsx])
    assert len(resultado) == 1


def test_padrao_cartao_com_traco_no_meio():
    """Caso real: OFX `"DEBITO DE CARTAO - 60 MINUTOS - Brasília BRA"` (dois
    ` - ` interno) e XLSX `"60 MINUTOS - Brasília BRA"`. O nível 2a sozinho
    não casa (split em primeiro ` - ` produz strings diferentes); o pass 2b
    consolida via `_arquivo_origem`.
    """
    ofx = _t(
        date(2026, 7, 13),
        254.7,
        "DEBITO DE CARTAO - 60 MINUTOS - Brasília BRA",
        arquivo_origem="x.ofx",
    )
    xlsx = _t(
        date(2026, 7, 13),
        254.7,
        "60 MINUTOS - Brasília BRA",
        arquivo_origem="x.xlsx",
    )
    resultado = deduplicar_por_hash_fuzzy([ofx, xlsx])
    assert len(resultado) == 1


# ---------------------------------------------------------------------------
# Preservação de pares legítimos.
# ---------------------------------------------------------------------------


def test_transferencia_legitima_entre_bancos_mesma_data_valor_preservada():
    """Par legítimo: pessoa_a envia R$ 1.000,00 do C6 para Nubank na mesma
    data. Bancos diferentes → pass 2b não age. Locais distintos → 2a não
    consolida. Ambos preservados.
    """
    saida_c6 = _t(
        date(2026, 3, 6),
        1000.0,
        "Pix enviado para Nubank de André",
        banco="C6",
        arquivo_origem="x.ofx",
    )
    entrada_nubank = _t(
        date(2026, 3, 6),
        1000.0,
        "Pix recebido de André da Silva",
        banco="Nubank (PF)",
        arquivo_origem="x.csv",
    )
    resultado = deduplicar_por_hash_fuzzy([saida_c6, entrada_nubank])
    assert len(resultado) == 2, "Pares entre bancos diferentes não devem ser consolidados"


def test_normalizar_local_split_simples():
    """Unit test: `_normalizar_local_para_chave` faz split corretamente."""
    assert _normalizar_local_para_chave("PREFIXO - sufixo") == "sufixo"
    assert _normalizar_local_para_chave("apenas sufixo") == "apenas sufixo"
    assert _normalizar_local_para_chave("") == ""
    # split com maxsplit=1: pega tudo após o PRIMEIRO ` - `
    assert _normalizar_local_para_chave("A - B - C") == "b - c"


def test_2b_isolado_descarta_xlsx_preserva_ofx():
    """Pass 2b: quando OFX e XLSX colidem no mesmo banco/data/valor/quem,
    XLSX vai embora; OFX permanece.
    """
    ofx = _t(date(2026, 3, 6), 100.0, "OFX_DETALHADO - X", arquivo_origem="a.ofx")
    xlsx = _t(date(2026, 3, 6), 100.0, "GENERICO", arquivo_origem="b.xlsx")
    resultado = _consolidar_pares_ofx_xlsx_mesmo_banco([ofx, xlsx])
    assert len(resultado) == 1
    assert "OFX_DETALHADO" in resultado[0]["local"]


def test_2b_nao_age_sem_arquivo_origem():
    """Pass 2b é silencioso quando `_arquivo_origem` ausente -- defesa em
    profundidade contra eliminação inadvertida de transações legítimas.
    """
    a = _t(date(2026, 3, 6), 100.0, "X", arquivo_origem=None)
    b = _t(date(2026, 3, 6), 100.0, "Y", arquivo_origem=None)
    resultado = _consolidar_pares_ofx_xlsx_mesmo_banco([a, b])
    assert len(resultado) == 2


def test_2b_nao_age_quando_ambos_sao_ofx():
    """Pass 2b só consolida quando UM é OFX e OUTRO é XLSX/CSV. Dois OFX
    do mesmo arquivo bancário são responsabilidade do nível 2a (chave por
    local normalizado).
    """
    a = _t(date(2026, 3, 6), 100.0, "X", arquivo_origem="a.ofx")
    b = _t(date(2026, 3, 6), 100.0, "Y", arquivo_origem="b.ofx")
    resultado = _consolidar_pares_ofx_xlsx_mesmo_banco([a, b])
    assert len(resultado) == 2


def test_2b_nao_age_quando_quem_diferente():
    """Pass 2b respeita `quem`: pessoa_a OFX vs pessoa_b XLSX não consolida
    (são pessoas distintas, dado financeiro diferente)."""
    a = _t(date(2026, 3, 6), 100.0, "X", arquivo_origem="a.ofx", quem="pessoa_a")
    b = _t(date(2026, 3, 6), 100.0, "Y", arquivo_origem="b.xlsx", quem="pessoa_b")
    resultado = _consolidar_pares_ofx_xlsx_mesmo_banco([a, b])
    assert len(resultado) == 2


# "A duplicação silenciosa é o erro mais educado: pede licença antes
# de mentir." -- princípio INFRA-DEDUP-C6-OFX-XLSX-AMPLO
