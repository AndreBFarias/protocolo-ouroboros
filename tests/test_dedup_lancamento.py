"""Testes regressivos da Sprint INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F.

Origem: validação artesanal do holerite G4F (2026-05-12) detectou par
suspeito R$ 6.381,14 em 2026-03-06 no C6/pessoa_a. Investigação revelou
253 pares estruturalmente duplicados por ingestão paralela OFX + XLSX
(ver `docs/auditorias/DUPLICACAO_C6_OFX_XLSX_2026-05-12.md`).

Estes testes:

1. **Documentam** o cenário atual: dedup nível-2 NÃO casa pares OFX/XLSX
   com prefixo bancário no campo `local` (regressão a prevenir).
2. **Validam** a lógica de normalização proposta (sufixo após primeiro
   ` - `) que a sprint-filha INFRA-DEDUP-C6-OFX-XLSX-AMPLO usará.
3. **Garantem** que pares legítimos (transferências reais entre contas
   com mesmo valor/data) continuam preservados.
"""

from datetime import date

from src.transform.deduplicator import deduplicar_por_hash_fuzzy

# ---------------------------------------------------------------------------
# Helper local (não depende da fixture global para isolar a regressão).
# ---------------------------------------------------------------------------


def _t(data_t: date, valor: float, local: str, banco: str = "C6", forma: str = "Débito") -> dict:
    return {
        "data": data_t,
        "valor": valor,
        "forma_pagamento": forma,
        "local": local,
        "quem": "pessoa_a",
        "categoria": None,
        "classificacao": None,
        "banco_origem": banco,
        "tipo": "Transferência Interna",
        "mes_ref": data_t.strftime("%Y-%m"),
        "tag_irpf": None,
        "obs": None,
        "_identificador": None,
        "_descricao_original": local,
    }


# ---------------------------------------------------------------------------
# Helper proposto (lógica que a sprint-filha implementará no dedup).
# Mantido aqui como fonte canônica do teste regressivo.
# ---------------------------------------------------------------------------


def _normalizar_local(local: str) -> str:
    """Remove prefixo bancário antes do primeiro ` - `.

    Padrão OFX: `"RECEBIMENTO SALARIO - 5127373122-ANDRE..."`.
    Padrão XLSX C6: `"5127373122-ANDRE..."`.
    Após normalização ambos viram `"5127373122-ANDRE..."`.
    """
    return local.split(" - ", 1)[-1].strip().upper()


# ---------------------------------------------------------------------------
# Testes regressivos.
# ---------------------------------------------------------------------------


def test_regressao_par_g4f_c6_2026_03_06_nao_casa_sem_normalizar():
    """Documenta cenário atual: par R$ 6.381,14 / 2026-03-06 NÃO dedup
    porque OFX e XLSX produzem `local` com prefixo divergente.

    Esta é a regressão que motivou a sprint-mãe. O teste passa enquanto
    o bug existe e deve ser convertido em xfail/atualizado quando a
    sprint-filha INFRA-DEDUP-C6-OFX-XLSX-AMPLO aplicar fix arquitetural.
    """
    ofx = _t(
        date(2026, 3, 6),
        6381.14,
        "RECEBIMENTO SALARIO - 5127373122-ANDRE DA SILVA BATISTA DE F",
        forma="Débito",
    )
    xlsx = _t(
        date(2026, 3, 6),
        6381.14,
        "5127373122-ANDRE DA SILVA BATISTA DE FAR",
        forma="Crédito",
    )
    resultado = deduplicar_por_hash_fuzzy([ofx, xlsx])
    # Estado atual: ambos preservados (locais distintos -> chave distinta).
    assert len(resultado) == 2, (
        "Dedup atual deve falhar neste par (regressão conhecida). "
        "Quando a sprint-filha aplicar fix, atualizar este teste."
    )


def test_normalizacao_local_remove_prefixo_bancario():
    """A lógica de normalização (sufixo após primeiro ` - `) consolida o
    par OFX/XLSX em uma mesma chave canônica."""
    ofx_local = "RECEBIMENTO SALARIO - 5127373122-ANDRE DA SILVA BATISTA DE F"
    xlsx_local = "5127373122-ANDRE DA SILVA BATISTA DE FAR"

    # Truncamento difere ('F' vs 'FAR'); compara prefixo comum de tamanho
    # determinístico, simulando o que um fingerprint robusto faria.
    norm_ofx = _normalizar_local(ofx_local)
    norm_xlsx = _normalizar_local(xlsx_local)
    prefixo = min(len(norm_ofx), len(norm_xlsx))
    assert norm_ofx[:prefixo] == norm_xlsx[:prefixo]


def test_normalizacao_cobre_padroes_c6_conhecidos():
    """Padrões observados em produção (validados via
    `scripts/investigar_dedup_c6_ofx_xlsx.py`)."""
    pares = [
        (
            "DEBITO DE CARTAO - SACOLAO DA ECONOMIA    Brasília      BRA",
            "SACOLAO DA ECONOMIA    Brasília      BRA",
        ),
        (
            "PGTO FAT CARTAO C6 - Fatura de cartão",
            "Fatura de cartão",
        ),
        (
            "RECEBIMENTO SALARIO - 5127373122-ANDRE DA SILVA BATISTA DE F",
            "5127373122-ANDRE DA SILVA BATISTA DE FAR",
        ),
    ]
    for ofx, xlsx in pares:
        norm_ofx = _normalizar_local(ofx)
        norm_xlsx = _normalizar_local(xlsx)
        prefixo = min(len(norm_ofx), len(norm_xlsx))
        assert norm_ofx[:prefixo] == norm_xlsx[:prefixo], (
            f"Normalização falhou para par OFX/XLSX:\n  ofx={ofx!r}\n  xlsx={xlsx!r}\n"
            f"  norm_ofx={norm_ofx!r}\n  norm_xlsx={norm_xlsx!r}"
        )


def test_normalizacao_preserva_pares_legitimos_diferentes():
    """Pares legítimos (transferências reais com locais materialmente
    distintos) NÃO podem ser consolidados pela normalização proposta.

    Exemplo: pagamento Pix para fornecedor X e crédito recebido de
    fornecedor Y no mesmo dia e mesmo valor.
    """
    pix_para = _normalizar_local("Pix enviado para FORNECEDOR X")
    pix_de = _normalizar_local("Pix recebido de FORNECEDOR Y")
    assert pix_para != pix_de


def test_nivel2_dedup_preserva_par_legitimo_atraves_bancos():
    """Par legítimo entre bancos diferentes (transferência interna do
    casal) tem `local` distinto -> dedup nível-2 não consolida, comportamento
    correto preservado."""
    saida_c6 = _t(
        date(2026, 3, 6),
        500.00,
        "Pix enviado para PESSOA_B",
        banco="C6",
    )
    entrada_nubank = _t(
        date(2026, 3, 6),
        500.00,
        "Pix recebido de PESSOA_A",
        banco="Nubank (PF)",
    )
    resultado = deduplicar_por_hash_fuzzy([saida_c6, entrada_nubank])
    assert len(resultado) == 2, "Par legítimo entre bancos não deve ser consolidado"


# "A duplicacao silenciosa e o erro mais educado: pede licenca antes
# de mentir." -- principio do teste regressivo
