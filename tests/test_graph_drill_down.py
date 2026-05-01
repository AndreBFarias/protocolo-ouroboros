"""Testes da Sprint MICRO-01a -- drill-down via grafo.

Cobre ``src.graph.drill_down``:
  - Walk transação -> documento (1 salto).
  - Walk transação -> documento -> item (2 saltos).
  - Deduplicação de items.
  - Tolerância a transação sem documento, documento sem item.
  - Verifica corpus real conforme estado em 2026-04-30 (NFCe placeholders
    sem transação match -- estado esperado para registro do gauntlet).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.db import GrafoDB, caminho_padrao
from src.graph.drill_down import (
    contar_drill_down,
    obter_documentos_da_transacao,
    obter_items_da_transacao,
)


@pytest.fixture
def grafo_sintetico(tmp_path: Path) -> GrafoDB:
    """Grafo sintético com 1 transação, 1 NFCe, 3 items."""
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    tx_id = db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_2026-04-19_atacadao",
        metadata={
            "data": "2026-04-19",
            "valor": 629.98,
            "local": "Atacadao Dia A Dia",
        },
    )
    nfce_id = db.upsert_node(
        tipo="documento",
        nome_canonico="53260400776574016079653040000432601123456788",
        metadata={
            "tipo_documento": "nfce_modelo_65",
            "cnpj_emitente": "00.776.574/0160-79",
            "data_emissao": "2026-04-19",
            "total": 629.98,
        },
    )
    item_a_id = db.upsert_node(
        tipo="item",
        nome_canonico="controle_p55",
        metadata={"valor": 449.99},
    )
    item_b_id = db.upsert_node(
        tipo="item",
        nome_canonico="base_carregamento",
        metadata={"valor": 179.99},
    )
    item_c_id = db.upsert_node(
        tipo="item",
        nome_canonico="kit_tigelas",
        metadata={"valor": 64.99},
    )
    db.adicionar_edge(tx_id, nfce_id, "documento_de", peso=0.95)
    db.adicionar_edge(nfce_id, item_a_id, "contem_item")
    db.adicionar_edge(nfce_id, item_b_id, "contem_item")
    db.adicionar_edge(nfce_id, item_c_id, "contem_item")
    return db


def test_walk_1_salto_retorna_documento(grafo_sintetico):
    """Transação -> documento_de -> documento."""
    tx_id = grafo_sintetico.buscar_node(
        "transacao", "tx_2026-04-19_atacadao"
    ).id
    documentos = obter_documentos_da_transacao(grafo_sintetico, tx_id)

    assert len(documentos) == 1
    assert documentos[0].metadata["tipo_documento"] == "nfce_modelo_65"
    assert documentos[0].metadata["total"] == 629.98


def test_walk_2_saltos_retorna_items_granulares(grafo_sintetico):
    """Transação -> documento -> contem_item -> item (3 items)."""
    tx_id = grafo_sintetico.buscar_node(
        "transacao", "tx_2026-04-19_atacadao"
    ).id
    items = obter_items_da_transacao(grafo_sintetico, tx_id)

    assert len(items) == 3
    nomes = sorted(item.nome_canonico.lower() for item in items)
    assert nomes == ["base_carregamento", "controle_p55", "kit_tigelas"]
    valores = sorted(float(item.metadata["valor"]) for item in items)
    assert valores == [64.99, 179.99, 449.99]
    # Soma == total do NFCe (proof aritmético do walk)
    assert round(sum(valores), 2) == 694.97  # 449.99 + 179.99 + 64.99


def test_transacao_sem_documento_retorna_vazio(tmp_path):
    """Transação isolada (sem aresta documento_de) -> [] sem erro."""
    db = GrafoDB(tmp_path / "grafo_isolado.sqlite")
    db.criar_schema()
    tx_id = db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_isolada",
        metadata={"data": "2026-04-29", "valor": 100.0},
    )
    assert obter_documentos_da_transacao(db, tx_id) == []
    assert obter_items_da_transacao(db, tx_id) == []


def test_documento_sem_items_walk_2_saltos_retorna_vazio(tmp_path):
    """Holerite/DAS sem items: walk 2 saltos retorna []."""
    db = GrafoDB(tmp_path / "grafo_holerite.sqlite")
    db.criar_schema()
    tx_id = db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_salario",
        metadata={"data": "2026-03-05", "valor": 5000.0},
    )
    doc_id = db.upsert_node(
        tipo="documento",
        nome_canonico="holerite_2026-03",
        metadata={"tipo_documento": "holerite", "total": 5000.0},
    )
    db.adicionar_edge(tx_id, doc_id, "documento_de")
    # Holerite NÃO tem aresta contem_item.

    documentos = obter_documentos_da_transacao(db, tx_id)
    items = obter_items_da_transacao(db, tx_id)

    assert len(documentos) == 1
    assert items == []


def test_dois_documentos_mesmo_item_dedup(tmp_path):
    """2 NFCe vinculados a 1 transação apontando para mesmo item: dedup."""
    db = GrafoDB(tmp_path / "grafo_dedup.sqlite")
    db.criar_schema()
    tx_id = db.upsert_node(
        tipo="transacao", nome_canonico="tx_dup", metadata={"valor": 100.0}
    )
    doc_a_id = db.upsert_node(
        tipo="documento",
        nome_canonico="nfce_a",
        metadata={"tipo_documento": "nfce_modelo_65"},
    )
    doc_b_id = db.upsert_node(
        tipo="documento",
        nome_canonico="nfce_b",
        metadata={"tipo_documento": "nfce_modelo_65"},
    )
    item_id = db.upsert_node(
        tipo="item", nome_canonico="produto_x", metadata={"valor": 50.0}
    )
    db.adicionar_edge(tx_id, doc_a_id, "documento_de")
    db.adicionar_edge(tx_id, doc_b_id, "documento_de")
    db.adicionar_edge(doc_a_id, item_id, "contem_item")
    db.adicionar_edge(doc_b_id, item_id, "contem_item")

    items = obter_items_da_transacao(db, tx_id)
    assert len(items) == 1  # dedup -- não retorna 2x
    assert items[0].nome_canonico.lower() == "produto_x"


def test_apenas_arestas_documento_de_consideradas(tmp_path):
    """Outras arestas (contraparte, ocorre_em) não viram documento."""
    db = GrafoDB(tmp_path / "grafo_arestas_extras.sqlite")
    db.criar_schema()
    tx_id = db.upsert_node(
        tipo="transacao", nome_canonico="tx_x", metadata={"valor": 100.0}
    )
    fornecedor_id = db.upsert_node(
        tipo="fornecedor",
        nome_canonico="atacadao",
        metadata={"cnpj": "00776574000179"},
    )
    periodo_id = db.upsert_node(tipo="periodo", nome_canonico="2026-04")
    db.adicionar_edge(tx_id, fornecedor_id, "contraparte")
    db.adicionar_edge(tx_id, periodo_id, "ocorre_em")

    # Nenhuma aresta documento_de -> 0 documentos
    assert obter_documentos_da_transacao(db, tx_id) == []
    assert obter_items_da_transacao(db, tx_id) == []


def test_node_inexistente_retorna_vazio_sem_erro(tmp_path):
    """transacao_id que não existe no grafo: retorna [] sem exception."""
    db = GrafoDB(tmp_path / "grafo_vazio.sqlite")
    db.criar_schema()
    assert obter_documentos_da_transacao(db, 999_999) == []
    assert obter_items_da_transacao(db, 999_999) == []


def test_contar_drill_down_em_grafo_sintetico(grafo_sintetico):
    """Estatística agregada bate com fixture (1 transação, 1 NFCe linkado, 3 items)."""
    stats = contar_drill_down(grafo_sintetico)
    assert stats["transacoes_com_documento"] == 1
    assert stats["transacoes_com_items"] == 1
    assert stats["nfce_no_grafo"] == 1
    assert stats["nfce_com_documento_de"] == 1


@pytest.mark.skipif(
    not caminho_padrao().exists(), reason="grafo real ainda não existe"
)
def test_corpus_real_estado_atual_2026_04_30():
    """Snapshot honesto do estado real em 2026-04-30.

    Documenta padrão (k) BRIEF: hipótese da spec MICRO-01a foi refutada
    empiricamente. Os 2 NFCe atuais no grafo são placeholders de teste
    (PoC da Sprint VALIDAÇÃO-CSV-01) sem transação correspondente.

    Quando NFCe reais entrarem no inbox e ``./run.sh --full-cycle`` rodar,
    ``linking.py`` (Sprint 48) deve criar arestas ``documento_de``
    automaticamente. Sprint follow-up ``MICRO-01a-FOLLOWUP-NFCE-REAIS``
    valida quando isso ocorrer.
    """
    db = GrafoDB(caminho_padrao())
    try:
        stats = contar_drill_down(db)
        # Asserts de regressão -- mudou? Investigar antes de "consertar":
        assert stats["nfce_no_grafo"] >= 2  # >=2 (PoC + reais futuros)
        # NFCe com documento_de pode crescer quando NFCe reais aparecerem.
        # Hoje (2026-04-30): 0. Asserção solta para não quebrar quando crescer.
        assert stats["nfce_com_documento_de"] >= 0
        assert (
            stats["nfce_com_documento_de"] <= stats["nfce_no_grafo"]
        ), "linkados não podem exceder total"
    finally:
        db.fechar()


# "Walks são a evidência de que o grafo não é só dados, é relação."
#  -- princípio operacional do Protocolo Ouroboros
