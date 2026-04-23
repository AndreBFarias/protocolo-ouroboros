"""Testes da Sprint 87.2 (ADR-20) — coluna "Doc?" do Extrato consultando grafo.

Cobertura:
  1-3. Helper `src.graph.queries.transacoes_com_documento` em grafo sintético.
  4-6. Função pura `src.dashboard.paginas.extrato._marcar_tracking`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.dashboard.paginas.extrato import _marcar_tracking
from src.graph.db import GrafoDB
from src.graph.queries import transacoes_com_documento


@pytest.fixture
def grafo_vazio(tmp_path: Path) -> GrafoDB:
    """Grafo SQLite novo, schema aplicado, sem nodes."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


class TestTransacoesComDocumento:
    def test_grafo_vazio_retorna_set_vazio(self, grafo_vazio: GrafoDB) -> None:
        resultado = transacoes_com_documento(grafo_vazio)
        assert resultado == set()

    def test_detecta_uma_aresta_documento_de(self, grafo_vazio: GrafoDB) -> None:
        db = grafo_vazio
        id_tx = db.upsert_node(
            "transacao",
            "abc123hashtx",
            metadata={"data": "2026-03-17", "valor": -103.93, "local": "SESC"},
        )
        id_doc = db.upsert_node(
            "documento",
            "boleto-sesc-2026-03",
            metadata={"tipo_documento": "boleto_servico", "total": 103.93},
        )
        db.adicionar_edge(id_doc, id_tx, "documento_de", peso=0.9)

        # GrafoDB normaliza nome_canonico para uppercase (ver `normalizar_nome_canonico`)
        resultado = transacoes_com_documento(db)
        assert resultado == {"ABC123HASHTX"}

    def test_ignora_outros_tipos_de_aresta(self, grafo_vazio: GrafoDB) -> None:
        """Arestas `fornecido_por`, `ocorre_em` etc. NÃO contam para tracking."""
        db = grafo_vazio
        id_tx = db.upsert_node("transacao", "hashtxoutro", metadata={})
        id_forn = db.upsert_node("fornecedor", "LOJA X", metadata={})
        id_periodo = db.upsert_node("periodo", "2026-03", metadata={})
        db.adicionar_edge(id_tx, id_forn, "contraparte")
        db.adicionar_edge(id_tx, id_periodo, "ocorre_em")

        resultado = transacoes_com_documento(db)
        assert resultado == set()

    def test_multiplas_transacoes_com_doc(self, grafo_vazio: GrafoDB) -> None:
        """Sanity check: cobertura de 2+ arestas distintas é retornada completa."""
        db = grafo_vazio
        id_tx1 = db.upsert_node("transacao", "hash_tx_1", metadata={})
        id_tx2 = db.upsert_node("transacao", "hash_tx_2", metadata={})
        db.upsert_node("transacao", "hash_tx_3", metadata={})  # sem doc
        id_doc1 = db.upsert_node("documento", "doc1", metadata={})
        id_doc2 = db.upsert_node("documento", "doc2", metadata={})
        db.adicionar_edge(id_doc1, id_tx1, "documento_de")
        db.adicionar_edge(id_doc2, id_tx2, "documento_de")

        resultado = transacoes_com_documento(db)
        assert resultado == {"HASH_TX_1", "HASH_TX_2"}
        assert "HASH_TX_3" not in resultado


class TestMarcarTracking:
    def test_marca_ok_quando_identificador_em_ids_com_doc(self) -> None:
        row = pd.Series(
            {"identificador": "tx-123", "categoria": "Farmácia"}
        )
        obrigatorias = frozenset({"Farmácia", "Aluguel"})
        ids_com_doc = {"tx-123"}
        assert _marcar_tracking(row, obrigatorias, ids_com_doc) == "OK"

    def test_marca_exclamacao_quando_categoria_obrigatoria_sem_doc(self) -> None:
        row = pd.Series(
            {"identificador": "tx-456", "categoria": "Aluguel"}
        )
        obrigatorias = frozenset({"Farmácia", "Aluguel"})
        ids_com_doc: set[str] = set()
        assert _marcar_tracking(row, obrigatorias, ids_com_doc) == "!"

    def test_marca_vazio_quando_nao_obrigatoria_e_sem_doc(self) -> None:
        row = pd.Series(
            {"identificador": "tx-789", "categoria": "Lazer"}
        )
        obrigatorias = frozenset({"Farmácia", "Aluguel"})
        ids_com_doc: set[str] = set()
        assert _marcar_tracking(row, obrigatorias, ids_com_doc) == ""

    def test_row_sem_identificador_cai_no_fallback(self) -> None:
        """Quando df não tem coluna `identificador` (estado atual), lógica cai
        no fallback de categoria obrigatória."""
        row = pd.Series({"categoria": "Farmácia"})
        obrigatorias = frozenset({"Farmácia"})
        ids_com_doc = {"qualquer-id"}
        # Sem identificador na row, nunca bate em ids_com_doc -> fallback
        assert _marcar_tracking(row, obrigatorias, ids_com_doc) == "!"


# "Verificar antes de afirmar — o grafo é fonte de verdade." -- Sprint 87.2
