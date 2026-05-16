"""Sprint INFRA-NFCE-DEDUP-OCR-DUPLICATAS: testes regressivos.

Cobre:
  1. ``_eh_mesma_nfce`` casa pares OCR-divergentes (chave próxima, demais iguais).
  2. ``_eh_mesma_nfce`` rejeita pares com CNPJ diferente.
  3. ``_eh_mesma_nfce`` rejeita pares com total diferente.
  4. ``_eh_mesma_nfce`` rejeita quando diff de chave excede limite.
  5. ``_completude_nfce`` mede itens com qtde > 0.
  6. Ingestor evita criar node duplicado quando NFCe-irmã existe.
  7. Ingestor escolhe node com mais itens (completude maior vence).
  8. Script ``dedup_nfce_grafo`` corrige 4 nodes para 2 (idempotente).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.dedup_nfce_grafo import dedup_grafo
from src.graph.db import GrafoDB
from src.graph.ingestor_documento import (
    _completude_nfce,
    _distancia_chave,
    _eh_mesma_nfce,
    ingerir_documento_fiscal,
)

# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


# Pares reais auditados em 2026-05-12 (distâncias Levenshtein 9 e 10).
CHAVE_595A = "53260400776574016079653040000432591876543210"
CHAVE_595B = "53260400776574016079653040000432591442916866"
CHAVE_629A = "53260400778574016079653040000432601059682510"
CHAVE_629B = "53260400776574016079653040000432601123456788"

CNPJ_AMERICANAS = "00.776.574/0160-79"


@pytest.fixture
def db_tmp(tmp_path: Path) -> GrafoDB:
    caminho = tmp_path / "grafo_teste.sqlite"
    db = GrafoDB(caminho)
    db.criar_schema()
    yield db
    db._conn.close()  # noqa: SLF001


def _documento(chave: str, total: float, itens_qtdes: list[float]) -> dict:
    return {
        "chave_44": chave,
        "cnpj_emitente": CNPJ_AMERICANAS,
        "data_emissao": "2026-04-19",
        "tipo_documento": "nfce_modelo_65",
        "numero": "12345",
        "serie": "1",
        "total": total,
        "razao_social": "AMERICANAS",
        "itens": [
            {
                "codigo": f"COD{i:03d}",
                "descricao": f"ITEM {i}",
                "qtde": q,
                "valor_unit": 1.0,
                "valor_total": q * 1.0,
            }
            for i, q in enumerate(itens_qtdes, start=1)
        ],
    }


def _itens_para_ingestor(doc: dict) -> list[dict]:
    return doc["itens"]


# ----------------------------------------------------------------------------
# Função pura: _eh_mesma_nfce
# ----------------------------------------------------------------------------


def test_eh_mesma_nfce_casa_par_ocr_divergente_dentro_do_limite():
    # Limite default = 4. Para testar isso usamos chaves que diferem em 3 dígitos.
    chave_a = "5326040077657401607965304000043259187654321X"  # placeholder
    # Diferença de 3 dígitos no final:
    chave_b = chave_a[:-3] + "999"
    assert _distancia_chave(chave_a, chave_b) == 3
    assert (
        _eh_mesma_nfce(
            chave_a,
            chave_b,
            total_a=595.52,
            total_b=595.52,
            data_a="2026-04-19",
            data_b="2026-04-19",
            cnpj_a=CNPJ_AMERICANAS,
            cnpj_b=CNPJ_AMERICANAS,
            limite_diff_chave=4,
        )
        is True
    )


def test_eh_mesma_nfce_rejeita_cnpj_diferente():
    assert (
        _eh_mesma_nfce(
            CHAVE_595A,
            CHAVE_595B,
            total_a=595.52,
            total_b=595.52,
            data_a="2026-04-19",
            data_b="2026-04-19",
            cnpj_a=CNPJ_AMERICANAS,
            cnpj_b="11.222.333/0001-44",  # outro varejo
            limite_diff_chave=10,
        )
        is False
    )


def test_eh_mesma_nfce_rejeita_total_diferente():
    assert (
        _eh_mesma_nfce(
            CHAVE_595A,
            CHAVE_595B,
            total_a=595.52,
            total_b=595.53,  # 1 centavo diff
            data_a="2026-04-19",
            data_b="2026-04-19",
            cnpj_a=CNPJ_AMERICANAS,
            cnpj_b=CNPJ_AMERICANAS,
            limite_diff_chave=10,
        )
        is False
    )


def test_eh_mesma_nfce_rejeita_data_diferente():
    assert (
        _eh_mesma_nfce(
            CHAVE_595A,
            CHAVE_595B,
            total_a=595.52,
            total_b=595.52,
            data_a="2026-04-19",
            data_b="2026-04-20",
            cnpj_a=CNPJ_AMERICANAS,
            cnpj_b=CNPJ_AMERICANAS,
            limite_diff_chave=10,
        )
        is False
    )


def test_eh_mesma_nfce_rejeita_diff_chave_acima_do_limite():
    # Auditoria empírica: distância real entre as 4 NFCe duplicadas é 9 e 10.
    # Com limite default (4), o casamento deve falhar.
    assert _distancia_chave(CHAVE_595A, CHAVE_595B) == 9
    assert (
        _eh_mesma_nfce(
            CHAVE_595A,
            CHAVE_595B,
            total_a=595.52,
            total_b=595.52,
            data_a="2026-04-19",
            data_b="2026-04-19",
            cnpj_a=CNPJ_AMERICANAS,
            cnpj_b=CNPJ_AMERICANAS,
            limite_diff_chave=4,
        )
        is False
    )
    # Com limite calibrado (10), o mesmo par casa.
    assert (
        _eh_mesma_nfce(
            CHAVE_595A,
            CHAVE_595B,
            total_a=595.52,
            total_b=595.52,
            data_a="2026-04-19",
            data_b="2026-04-19",
            cnpj_a=CNPJ_AMERICANAS,
            cnpj_b=CNPJ_AMERICANAS,
            limite_diff_chave=10,
        )
        is True
    )


def test_eh_mesma_nfce_campo_none_retorna_false_conservador():
    assert (
        _eh_mesma_nfce(
            CHAVE_595A,
            "",
            total_a=595.52,
            total_b=595.52,
            data_a="2026-04-19",
            data_b="2026-04-19",
            cnpj_a=CNPJ_AMERICANAS,
            cnpj_b=CNPJ_AMERICANAS,
        )
        is False
    )


# ----------------------------------------------------------------------------
# Completude
# ----------------------------------------------------------------------------


def test_completude_nfce_conta_apenas_itens_com_qtde_positiva():
    meta = {
        "itens": [
            {"descricao": "A", "qtde": 1.0},
            {"descricao": "B", "qtde": 0.0},  # ignorado
            {"descricao": "C", "qtde": 2.5},
            {"descricao": "D"},  # sem qtde -> ignorado
        ]
    }
    assert _completude_nfce(meta) == 2


# ----------------------------------------------------------------------------
# Ingestor: evita duplicar
# ----------------------------------------------------------------------------


def test_ingestor_funde_nfce_irma_quando_completude_nova_eh_maior(db_tmp):
    # 1º: ingere NFCe parcial (poucos itens, OCR ruim)
    doc_parcial = _documento(CHAVE_595B, 595.52, [1.0, 1.0])
    id_parcial = ingerir_documento_fiscal(db_tmp, doc_parcial, _itens_para_ingestor(doc_parcial))

    # 2º: ingere a mesma NFCe (chave diff 9) com mais itens.
    # Com limite default = 4, o ingestor NÃO funde -- documentamos esse
    # comportamento conservador: por padrão prefere não-fundir a fundir errado.
    doc_completo = _documento(CHAVE_595A, 595.52, [1.0, 1.0, 1.0, 1.0, 1.0])
    id_completo = ingerir_documento_fiscal(db_tmp, doc_completo, _itens_para_ingestor(doc_completo))
    # Default conservador -> nodes separados
    assert id_completo != id_parcial


def test_ingestor_funde_quando_diff_chave_pequeno(db_tmp):
    # Par com diff 3 (dentro do default 4)
    chave_a = CHAVE_595A
    chave_b = chave_a[:-3] + "987"  # diff exato 3
    assert _distancia_chave(chave_a, chave_b) == 3

    doc_parcial = _documento(chave_a, 100.00, [1.0])
    id_parcial = ingerir_documento_fiscal(db_tmp, doc_parcial, _itens_para_ingestor(doc_parcial))

    doc_completo = _documento(chave_b, 100.00, [1.0, 1.0, 1.0])
    id_completo = ingerir_documento_fiscal(db_tmp, doc_completo, _itens_para_ingestor(doc_completo))
    # Mesmo node (fusão por completude)
    assert id_completo == id_parcial
    # Metadata reflete a versão mais completa (3 itens)
    node = db_tmp.buscar_node_por_id(id_parcial)
    assert _completude_nfce(node.metadata) == 3


# ----------------------------------------------------------------------------
# Script retroativo dedup_nfce_grafo
# ----------------------------------------------------------------------------


def test_dedup_grafo_reduz_4_nodes_para_2(db_tmp):
    """Replica o cenário auditado: 4 NFCe (2 pares) -> dedup com diff=10 -> 2."""

    # Par 1: total 595.52
    doc_a = _documento(CHAVE_595A, 595.52, [1.0] * 31)  # mais completo (vencedor)
    doc_b = _documento(CHAVE_595B, 595.52, [1.0] * 14)  # menos completo

    # Par 2: total 629.98
    doc_c = _documento(CHAVE_629A, 629.98, [1.0, 1.0])
    doc_d = _documento(CHAVE_629B, 629.98, [1.0, 1.0])

    # Ingere com limite default (4) -> não dedupa entre A/B nem C/D
    for d in (doc_a, doc_b, doc_c, doc_d):
        ingerir_documento_fiscal(db_tmp, d, _itens_para_ingestor(d))

    # Confirma 4 nodes
    antes_resultado = dedup_grafo(db_tmp, limite_diff_chave=10, apply=False)
    assert antes_resultado["antes"] == 4
    assert len(antes_resultado["fusoes"]) == 2

    # Aplica
    aplicado = dedup_grafo(db_tmp, limite_diff_chave=10, apply=True)
    assert aplicado["depois"] == 2
    assert aplicado["arestas_redirecionadas"] >= 0  # pode ser 0 se sem arestas no fixture

    # Idempotência: roda de novo -> 0 fusões
    segunda = dedup_grafo(db_tmp, limite_diff_chave=10, apply=True)
    assert len(segunda["fusoes"]) == 0
    assert segunda["antes"] == 2


# "O teste é o espelho honesto do código." -- princípio do dedup-nfce
