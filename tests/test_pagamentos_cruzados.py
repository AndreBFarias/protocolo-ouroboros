"""Testes da Sprint DASH-PAGAMENTOS-CRUZADOS-CASAL.

Cobre: matcher de pessoa devedora, enriquecimento in-place, sentinela de
drift, filtro do pacote IRPF e renderização do widget de pagamentos
cruzados. Caso âncora: DAS PARCSN R$ 324,31 do MEI Andre pago pela
Vitória em 16/04/2025.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.exports.pacote_irpf import _filtrar_por_devedora, compilar_eventos
from src.transform.normalizer import normalizar_transacao
from src.transform.pagamentos_cruzados import (
    contar_pagamentos_cruzados,
    enriquecer_transacoes,
    inferir_pessoa_devedora,
    sentinela_drift_impostos,
)

# ---------------------------------------------------------------------------
# Fixtures: caso âncora DAS R$ 324,31 (MEI Andre pago por Vitória)
# ---------------------------------------------------------------------------


def _das_andre_metadata() -> dict:
    """Metadata canônica do DAS PARCSN fev/2025 do Andre (R$ 324,31)."""
    return {
        "tipo_documento": "das_parcsn_andre",
        "cnpj_emitente": "45.850.636/0001-00",
        "total": 324.31,
        "vencimento": "2025-04-21",
        "periodo_apuracao": "2025-02",
        "razao_social": "ANDRE DA SILVA BATISTA DE FARIAS",
    }


def _transacao_vitoria_paga_das_andre() -> dict:
    """Transação real: Vitória paga DAS de Andre em 16/04/2025 (5 dias antes do venc)."""
    return {
        "data": date(2025, 4, 16),
        "valor": 324.31,
        "quem": "pessoa_b",
        "pessoa_pagadora": "pessoa_b",
        "pessoa_devedora": None,
        "categoria": "Impostos",
        "tag_irpf": "imposto_pago",
        "banco_origem": "Nubank (PF)",
        "local": "DAS RECEITA FEDERAL",
    }


# ---------------------------------------------------------------------------
# Caso 1: DAS Andre + pagamento Vitória -> devedora=Andre, pagadora=Vitória
# ---------------------------------------------------------------------------


def test_das_andre_pago_por_vitoria_atribui_pessoa_a():
    """Transação de pessoa_b pagando DAS de Andre identifica devedora=pessoa_a."""
    transacao = _transacao_vitoria_paga_das_andre()
    documentos = [_das_andre_metadata()]
    devedora = inferir_pessoa_devedora(transacao, documentos)
    assert devedora == "pessoa_a"
    # Função pura: não muta a transação.
    assert transacao["pessoa_devedora"] is None
    assert transacao["pessoa_pagadora"] == "pessoa_b"


# ---------------------------------------------------------------------------
# Caso 2: DAS Andre + pagamento Andre -> ambos iguais
# ---------------------------------------------------------------------------


def test_das_andre_pago_por_andre_devedora_e_pagadora_iguais():
    """Quando o próprio devedor paga, devedora == pagadora == pessoa_a."""
    transacao = {
        "data": date(2025, 4, 18),
        "valor": 324.31,
        "quem": "pessoa_a",
        "pessoa_pagadora": "pessoa_a",
        "pessoa_devedora": None,
        "categoria": "Impostos",
        "banco_origem": "Itaú",
    }
    documentos = [_das_andre_metadata()]
    devedora = inferir_pessoa_devedora(transacao, documentos)
    assert devedora == "pessoa_a"
    # Após enriquecimento, ambas são pessoa_a (pagamento alinhado, não cruzado).
    lista = enriquecer_transacoes([transacao], documentos)
    assert lista[0]["pessoa_pagadora"] == "pessoa_a"
    assert lista[0]["pessoa_devedora"] == "pessoa_a"
    contagem = contar_pagamentos_cruzados(lista)
    assert contagem["cruzados"] == 0
    assert contagem["com_devedora"] == 1


# ---------------------------------------------------------------------------
# Caso 3: Sem documento DAS no grafo -> pessoa_devedora None
# ---------------------------------------------------------------------------


def test_sem_documento_no_grafo_devedora_none():
    """Sem documento candidato, pessoa_devedora fica None (sem chute)."""
    transacao = _transacao_vitoria_paga_das_andre()
    devedora = inferir_pessoa_devedora(transacao, [])
    assert devedora is None


def test_documento_de_outro_valor_nao_casa():
    """Documento com total diferente (R$ 500) não casa com transação R$ 324,31."""
    transacao = _transacao_vitoria_paga_das_andre()
    documentos = [{**_das_andre_metadata(), "total": 500.00}]
    assert inferir_pessoa_devedora(transacao, documentos) is None


def test_documento_fora_janela_30_dias_nao_casa():
    """DAS com vencimento >30 dias da data da transação não casa."""
    transacao = _transacao_vitoria_paga_das_andre()
    documentos = [{**_das_andre_metadata(), "vencimento": "2025-02-01"}]
    # 16/04 - 01/02 = 74 dias, fora da janela.
    assert inferir_pessoa_devedora(transacao, documentos) is None


# ---------------------------------------------------------------------------
# Caso 4: Pacote IRPF Andre inclui imposto pago por Vitória
# ---------------------------------------------------------------------------


def test_pacote_irpf_pessoa_a_inclui_imposto_pago_por_pessoa_b():
    """Filtro por pessoa_a no pacote IRPF inclui transação cuja
    pessoa_devedora=pessoa_a, mesmo que quem=pessoa_b (Vitória pagou)."""
    transacao = _transacao_vitoria_paga_das_andre()
    transacao["pessoa_devedora"] = "pessoa_a"  # após enriquecimento
    transacao["mes_ref"] = "2025-04"

    df = pd.DataFrame([transacao])
    df_a = _filtrar_por_devedora(df, "pessoa_a")
    df_b = _filtrar_por_devedora(df, "pessoa_b")

    assert len(df_a) == 1, "imposto entra na declaração de Andre"
    assert df_a.iloc[0]["valor"] == 324.31
    # Caso 5: pacote de pessoa_b não duplica esse imposto
    assert len(df_b) == 0, "imposto não entra na declaração de Vitória (não é devedora)"


# ---------------------------------------------------------------------------
# Caso 5 (continuação): fallback para quem quando pessoa_devedora=None
# ---------------------------------------------------------------------------


def test_pacote_irpf_fallback_para_quem_quando_devedora_ausente():
    """Transações sem pessoa_devedora caem em quem (retrocompat)."""
    df = pd.DataFrame(
        [
            {
                "quem": "pessoa_a",
                "pessoa_devedora": None,
                "valor": 100.00,
                "mes_ref": "2025-01",
            },
            {
                "quem": "pessoa_b",
                "pessoa_devedora": None,
                "valor": 200.00,
                "mes_ref": "2025-01",
            },
        ]
    )
    df_a = _filtrar_por_devedora(df, "pessoa_a")
    df_b = _filtrar_por_devedora(df, "pessoa_b")
    assert len(df_a) == 1 and df_a.iloc[0]["valor"] == 100.00
    assert len(df_b) == 1 and df_b.iloc[0]["valor"] == 200.00


# ---------------------------------------------------------------------------
# Caso 6: Widget renderiza tabela com pagamentos cruzados
# ---------------------------------------------------------------------------


def test_contar_pagamentos_cruzados_caso_ancora():
    """KPIs do widget: 1 cruzado (Vitória pagou Andre) + 1 alinhado."""
    transacoes = [
        {
            "categoria": "Impostos",
            "pessoa_pagadora": "pessoa_b",
            "pessoa_devedora": "pessoa_a",
            "quem": "pessoa_b",
        },
        {
            "categoria": "Impostos",
            "pessoa_pagadora": "pessoa_a",
            "pessoa_devedora": "pessoa_a",
            "quem": "pessoa_a",
        },
        {
            "categoria": "Impostos",
            "pessoa_pagadora": "pessoa_a",
            "pessoa_devedora": None,
            "quem": "pessoa_a",
        },
        # Não-imposto fica fora da contagem.
        {
            "categoria": "Alimentação",
            "pessoa_pagadora": "pessoa_a",
            "pessoa_devedora": None,
            "quem": "pessoa_a",
        },
    ]
    contagem = contar_pagamentos_cruzados(transacoes)
    assert contagem == {
        "total_impostos": 3,
        "com_devedora": 2,
        "cruzados": 1,
        "sem_match": 1,
    }


# ---------------------------------------------------------------------------
# Casos extras de segurança
# ---------------------------------------------------------------------------


def test_normalizer_inclui_campos_novos_default_none():
    """Padrão (o): normalizar_transacao expõe novos campos sem mudar comportamento."""
    t = normalizar_transacao(
        data_transacao=date(2025, 4, 16),
        valor=-324.31,
        descricao="DAS RECEITA FEDERAL",
        banco_origem="Nubank (PF)",
    )
    assert "pessoa_pagadora" in t
    assert "pessoa_devedora" in t
    # pessoa_pagadora derivada do banco origem (Nubank PF -> pessoa_b).
    assert t["pessoa_pagadora"] == "pessoa_b"
    assert t["pessoa_devedora"] is None


def test_sentinela_alerta_quando_drift_acima_do_limiar():
    """Sentinela emite alerta quando >5% dos impostos sem pessoa_devedora."""
    # 1 imposto com devedora, 9 sem -> 90% drift.
    transacoes = [
        {"categoria": "Impostos", "pessoa_pagadora": "pessoa_a", "pessoa_devedora": "pessoa_a"},
    ] + [
        {"categoria": "Impostos", "pessoa_pagadora": "pessoa_a", "pessoa_devedora": None}
        for _ in range(9)
    ]
    alerta = sentinela_drift_impostos(transacoes, limiar_percentual=5.0)
    assert alerta is not None
    assert "Drift" in alerta or "drift" in alerta.lower()


def test_sentinela_silenciosa_quando_universo_vazio():
    """Sentinela retorna None quando não há impostos no recorte."""
    assert sentinela_drift_impostos([], limiar_percentual=5.0) is None
    assert sentinela_drift_impostos([{"categoria": "Alimentação"}], limiar_percentual=5.0) is None


def test_pacote_irpf_compilar_eventos_funciona_com_campos_novos():
    """compilar_eventos não quebra com colunas pessoa_pagadora/pessoa_devedora."""
    df = pd.DataFrame(
        [
            {
                "tag_irpf": "imposto_pago",
                "valor": 324.31,
                "local": "DAS RECEITA FEDERAL",
                "_descricao_original": "DAS",
                "obs": "",
                "mes_ref": "2025-04",
                "data": "2025-04-16",
                "cnpj_cpf": "45.850.636/0001-00",
                "banco_origem": "Nubank (PF)",
                "quem": "pessoa_b",
                "pessoa_pagadora": "pessoa_b",
                "pessoa_devedora": "pessoa_a",
            },
        ]
    )
    eventos = compilar_eventos(df)
    assert len(eventos) == 1
    assert eventos[0]["tag"] == "imposto_pago"
    assert eventos[0]["valor"] == 324.31


@pytest.mark.parametrize(
    "delta_dias,esperado",
    [
        (0, "pessoa_a"),
        (15, "pessoa_a"),
        (30, "pessoa_a"),
        (31, None),
        (-31, None),
    ],
)
def test_janela_30_dias_borda(delta_dias, esperado):
    """Janela ±30 dias é inclusiva nas bordas; ±31 não casa."""
    from datetime import timedelta

    transacao = _transacao_vitoria_paga_das_andre()
    # ajusta vencimento para distância controlada
    venc = transacao["data"] + timedelta(days=delta_dias)
    documentos = [{**_das_andre_metadata(), "vencimento": venc.isoformat()}]
    assert inferir_pessoa_devedora(transacao, documentos) == esperado


# "Casal que paga conta do outro sem pedir explicacao formal eh ouro contabil."
# -- principio DASH-PAGAMENTOS-CRUZADOS-CASAL
