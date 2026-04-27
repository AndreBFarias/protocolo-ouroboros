"""Testes da Sprint 87.7 — reconciliação boleto↔transação via grafo.

Cobertura:
  1. `carregar_boletos_via_grafo` retorna None quando cobertura < limiar.
  2. Marca `pago` quando há aresta `documento_de`.
  3. Marca `pendente` quando não há aresta e vencimento é futuro.
  4. Marca `atrasado` quando não há aresta e vencimento é passado.
  5. `carregar_boletos_inteligente` com db=None cai para heurística textual.
  6. `carregar_boletos_inteligente` com cobertura abaixo do limiar cai para textual.
  7. `carregar_boletos_inteligente` com cobertura suficiente usa o grafo.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.analysis import pagamentos as pg
from src.graph.db import GrafoDB


@pytest.fixture
def grafo_vazio(tmp_path: Path):
    """Grafo SQLite novo, schema aplicado, sem nodes."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


def _popular_arestas_dummy(db: GrafoDB, quantidade: int) -> None:
    """Cria `quantidade` arestas `documento_de` entre pares (doc_i, tx_i).

    Usado para atingir o limiar de cobertura sem depender do boleto sob teste.
    """
    for i in range(quantidade):
        id_doc = db.upsert_node("documento", f"dummy-doc-{i}", metadata={})
        id_tx = db.upsert_node("transacao", f"dummy-tx-{i}", metadata={})
        db.adicionar_edge(id_doc, id_tx, "documento_de")


class TestCarregarBoletosViaGrafo:
    def test_retorna_none_abaixo_limiar(self, grafo_vazio: GrafoDB) -> None:
        """Grafo com 5 arestas < limiar 10 deve devolver None (sinal de fallback)."""
        db = grafo_vazio
        _popular_arestas_dummy(db, 5)

        resultado = pg.carregar_boletos_via_grafo(
            db, prazos=None, hoje=date(2026, 4, 22), limiar=10
        )
        assert resultado is None

    def test_marca_pago_quando_ha_aresta(self, grafo_vazio: GrafoDB) -> None:
        """Node boleto com aresta `documento_de` -> status=pago."""
        db = grafo_vazio
        # Atinge limiar via dummies
        _popular_arestas_dummy(db, 10)

        id_boleto = db.upsert_node(
            "documento",
            "boleto-sesc-2026-03",
            metadata={
                "tipo_documento": "boleto_servico",
                "total": 103.93,
                "razao_social": "SESC",
                "vencimento": "2026-03-19",
                "data_emissao": "2026-03-15",
            },
        )
        id_tx = db.upsert_node(
            "transacao",
            "tx-sesc-pago",
            metadata={"data": "2026-03-17", "valor": -103.93},
        )
        db.adicionar_edge(id_boleto, id_tx, "documento_de", peso=0.9)

        df = pg.carregar_boletos_via_grafo(db, prazos=None, hoje=date(2026, 4, 22), limiar=10)
        assert df is not None
        # Filtra o boleto sob teste (ignora dummies, que não têm tipo_documento)
        linha_sesc = df[df["fornecedor"] == "SESC"]
        assert len(linha_sesc) == 1
        assert linha_sesc.iloc[0]["status"] == pg.STATUS_PAGO
        assert linha_sesc.iloc[0]["valor"] == pytest.approx(103.93)

    def test_marca_pendente_quando_sem_aresta_e_futuro(self, grafo_vazio: GrafoDB) -> None:
        """Node boleto sem aresta, vencimento no futuro -> status=pendente."""
        db = grafo_vazio
        _popular_arestas_dummy(db, 10)

        db.upsert_node(
            "documento",
            "boleto-futuro",
            metadata={
                "tipo_documento": "boleto_servico",
                "total": 250.00,
                "razao_social": "ENEL",
                "vencimento": "2026-05-10",
                "data_emissao": "2026-04-10",
            },
        )

        df = pg.carregar_boletos_via_grafo(db, prazos=None, hoje=date(2026, 4, 22), limiar=10)
        assert df is not None
        linha = df[df["fornecedor"] == "ENEL"]
        assert len(linha) == 1
        assert linha.iloc[0]["status"] == pg.STATUS_PENDENTE

    def test_marca_atrasado_quando_sem_aresta_e_passado(self, grafo_vazio: GrafoDB) -> None:
        """Node boleto sem aresta, vencimento no passado -> status=atrasado."""
        db = grafo_vazio
        _popular_arestas_dummy(db, 10)

        db.upsert_node(
            "documento",
            "boleto-atrasado",
            metadata={
                "tipo_documento": "boleto_servico",
                "total": 88.00,
                "razao_social": "CAESB",
                "vencimento": "2026-03-15",
                "data_emissao": "2026-02-15",
            },
        )

        df = pg.carregar_boletos_via_grafo(db, prazos=None, hoje=date(2026, 4, 22), limiar=10)
        assert df is not None
        linha = df[df["fornecedor"] == "CAESB"]
        assert len(linha) == 1
        assert linha.iloc[0]["status"] == pg.STATUS_ATRASADO

    def test_vencimento_ausente_marca_pendente(self, grafo_vazio: GrafoDB) -> None:
        """Boleto sem campo `vencimento` em metadata -> pendente (graceful)."""
        db = grafo_vazio
        _popular_arestas_dummy(db, 10)

        db.upsert_node(
            "documento",
            "boleto-sem-venc",
            metadata={
                "tipo_documento": "boleto_servico",
                "total": 42.00,
                "razao_social": "DESCONHECIDO",
            },
        )

        df = pg.carregar_boletos_via_grafo(db, prazos=None, hoje=date(2026, 4, 22), limiar=10)
        assert df is not None
        linha = df[df["fornecedor"] == "DESCONHECIDO"]
        assert len(linha) == 1
        assert linha.iloc[0]["status"] == pg.STATUS_PENDENTE


class TestCarregarBoletosInteligente:
    def test_fallback_quando_sem_db(self) -> None:
        """`db=None` -> usa heurística textual antiga diretamente."""
        extrato = pd.DataFrame(
            {
                "data": ["2026-03-17"],
                "forma_pagamento": ["Boleto"],
                "local": ["SESC"],
                "valor": [-103.93],
                "banco_origem": ["C6"],
                "mes_ref": ["2026-03"],
            }
        )
        resultado = pg.carregar_boletos_inteligente(
            extrato, prazos=None, hoje=date(2026, 4, 22), db=None
        )
        assert isinstance(resultado, pd.DataFrame)
        # Heurística textual marca como pago quando forma_pagamento=Boleto
        assert len(resultado) == 1
        assert resultado.iloc[0]["status"] == pg.STATUS_PAGO

    def test_fallback_quando_abaixo_do_limiar(self, grafo_vazio: GrafoDB) -> None:
        """Grafo com 3 arestas `documento_de` < limiar 10 -> heurística textual."""
        db = grafo_vazio
        _popular_arestas_dummy(db, 3)

        extrato = pd.DataFrame(
            {
                "data": ["2026-03-17"],
                "forma_pagamento": ["Boleto"],
                "local": ["SESC"],
                "valor": [-103.93],
                "banco_origem": ["C6"],
                "mes_ref": ["2026-03"],
            }
        )
        resultado = pg.carregar_boletos_inteligente(
            extrato, prazos=None, hoje=date(2026, 4, 22), db=db, limiar=10
        )
        # Retorno da heurística textual: marca o boleto pago do extrato
        assert isinstance(resultado, pd.DataFrame)
        assert len(resultado) == 1
        assert resultado.iloc[0]["status"] == pg.STATUS_PAGO
        # O fornecedor do textual é `local`, não `razao_social`
        assert resultado.iloc[0]["fornecedor"] == "SESC"

    def test_usa_grafo_quando_cobertura_suficiente(self, grafo_vazio: GrafoDB) -> None:
        """Grafo com >= 10 arestas `documento_de` e boleto_servico -> usa grafo."""
        db = grafo_vazio
        _popular_arestas_dummy(db, 10)

        id_boleto = db.upsert_node(
            "documento",
            "boleto-natacao",
            metadata={
                "tipo_documento": "boleto_servico",
                "total": 180.00,
                "razao_social": "SESC NATACAO",
                "vencimento": "2026-04-20",
                "data_emissao": "2026-04-01",
            },
        )
        id_tx = db.upsert_node(
            "transacao",
            "tx-natacao",
            metadata={"data": "2026-04-18", "valor": -180.00},
        )
        db.adicionar_edge(id_boleto, id_tx, "documento_de", peso=0.95)

        # Extrato vazio - o que importa é o que vem do grafo
        extrato = pd.DataFrame()
        resultado = pg.carregar_boletos_inteligente(
            extrato, prazos=None, hoje=date(2026, 4, 22), db=db, limiar=10
        )
        # Deve vir do grafo -- ignora o fato do extrato estar vazio
        assert isinstance(resultado, pd.DataFrame)
        # Filtra para o boleto sob teste
        linha = resultado[resultado["fornecedor"] == "SESC NATACAO"]
        assert len(linha) == 1
        assert linha.iloc[0]["status"] == pg.STATUS_PAGO
        assert linha.iloc[0]["valor"] == pytest.approx(180.00)


# "Reconciliar via grafo é preferir verdade estrutural a coincidência textual." -- Sprint 87.7
