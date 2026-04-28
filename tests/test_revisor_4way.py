"""Testes da auditoria 4-way (sessao 2026-04-29).

Cobre:
  - Migração graceful da coluna `valor_grafo_real` em DBs criados antes
    desta sessao (Sprint 103 ou anteriores).
  - Persistencia de `valor_grafo_real` via salvar_marcacao e roundtrip.
  - Export ground_truth_csv com 11 colunas e 3 flags de divergencia
    (ETL/Opus/Grafo, Tipo A vs Tipo B).
  - popular_valor_grafo_real.py: idempotência, falha-soft em DB ausente,
    resolução item_id -> node_id em formatos relativos e absolutos.

Fixtures são SQLite em tmp_path (zero contato com data/output real).
"""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import pytest

from scripts import popular_valor_grafo_real
from src.dashboard.paginas import revisor


@pytest.fixture()
def db_revisao_sem_grafo_real(tmp_path: Path) -> Path:
    """Cria SQLite no schema PRE-sessao-2026-04-29 (so 7 colunas, sem
    valor_grafo_real). Permite testar migração graceful via garantir_schema.
    """
    caminho = tmp_path / "revisao_humana.sqlite"
    conn = sqlite3.connect(caminho)
    conn.executescript(
        """
        CREATE TABLE revisao (
            item_id TEXT NOT NULL,
            dimensao TEXT NOT NULL,
            ok INTEGER,
            observacao TEXT,
            ts TEXT DEFAULT (datetime('now')),
            valor_etl TEXT,
            valor_opus TEXT,
            PRIMARY KEY (item_id, dimensao)
        );
        """
    )
    conn.execute(
        "INSERT INTO revisao (item_id, dimensao, ok, observacao, valor_etl, valor_opus) "
        "VALUES ('item1', 'data', 1, '', '2026-01-01', '2026-01-01')"
    )
    conn.commit()
    conn.close()
    return caminho


@pytest.fixture()
def grafo_4way(tmp_path: Path) -> Path:
    """Grafo sintetico com 1 documento + 1 fornecedor ligados via aresta
    `fornecido_por`. Path absoluto e relativo cobrem inconsistencia AUDIT-PATH.
    """
    destino = tmp_path / "grafo.sqlite"
    conn = sqlite3.connect(destino)
    conn.executescript(
        """
        CREATE TABLE node (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nome_canonico TEXT NOT NULL,
            aliases TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE edge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_id INTEGER NOT NULL,
            dst_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            peso REAL DEFAULT 1.0,
            evidencia TEXT DEFAULT '{}'
        );
        """
    )
    # Documento gravado com path absoluto (formato pre-AUDIT-PATH-RELATIVO)
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            100,
            "documento",
            "FAT_2026-01_1234",
            json.dumps(
                {
                    "arquivo_origem": "/repo/data/raw/andre/holerites/HOLERITE_X.pdf",
                    "data_emissao": "2026-01-15",
                    "total": 5000.0,
                    "razao_social": "G4F",
                    "tipo_documento": "holerite",
                }
            ),
        ),
    )
    conn.execute(
        "INSERT INTO node (id, tipo, nome_canonico, metadata) VALUES (?, ?, ?, ?)",
        (
            101,
            "fornecedor",
            "00394460000141",
            json.dumps({"razao_social": "Receita Federal do Brasil"}),
        ),
    )
    # Documento ligado a fornecedor sintetico
    conn.execute(
        "INSERT INTO edge (src_id, dst_id, tipo) VALUES (100, 101, 'fornecido_por')"
    )
    conn.commit()
    conn.close()
    return destino


class TestMigrarSchema4Way:
    """Migração graceful via garantir_schema para DBs Sprint 103."""

    def test_garantir_schema_adiciona_valor_grafo_real(
        self, db_revisao_sem_grafo_real: Path
    ) -> None:
        revisor.garantir_schema(db_revisao_sem_grafo_real)
        conn = sqlite3.connect(db_revisao_sem_grafo_real)
        try:
            cur = conn.execute("PRAGMA table_info(revisao)")
            colunas = {row[1] for row in cur.fetchall()}
        finally:
            conn.close()
        assert "valor_grafo_real" in colunas
        assert "valor_etl" in colunas
        assert "valor_opus" in colunas

    def test_dado_existente_preservado_apos_migracao(
        self, db_revisao_sem_grafo_real: Path
    ) -> None:
        revisor.garantir_schema(db_revisao_sem_grafo_real)
        marcacoes = revisor.carregar_marcacoes(db_revisao_sem_grafo_real)
        assert len(marcacoes) == 1
        assert marcacoes[0]["item_id"] == "item1"
        assert marcacoes[0]["valor_grafo_real"] is None  # nova coluna NULL


class TestSalvarMarcacao4Way:
    """salvar_marcacao deve aceitar e persistir valor_grafo_real."""

    def test_salvar_grava_grafo_real(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rev.sqlite"
        revisor.salvar_marcacao(
            caminho,
            item_id="x",
            dimensao="valor",
            ok=1,
            observacao="",
            valor_etl="100.00",
            valor_opus="100.00",
            valor_grafo_real="100.00",
        )
        m = revisor.carregar_marcacoes(caminho)
        assert m[0]["valor_grafo_real"] == "100.00"

    def test_upsert_preserva_grafo_real_quando_none(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rev.sqlite"
        revisor.salvar_marcacao(
            caminho,
            "y",
            "valor",
            1,
            "",
            valor_etl="50",
            valor_grafo_real="50",
        )
        # Re-UPSERT sem passar valor_grafo_real (None) — deve preservar.
        revisor.salvar_marcacao(
            caminho,
            "y",
            "valor",
            0,
            "novo coment",
            valor_etl="51",
        )
        m = revisor.carregar_marcacoes(caminho)
        assert m[0]["valor_grafo_real"] == "50"
        assert m[0]["valor_etl"] == "51"
        assert m[0]["ok"] == 0


class TestExportCSV4Way:
    """gerar_ground_truth_csv produz 11 colunas com 3 flags."""

    def test_header_contem_11_colunas(self, tmp_path: Path) -> None:
        caminho_db = tmp_path / "rev.sqlite"
        revisor.garantir_schema(caminho_db)
        csv_dest = tmp_path / "out.csv"
        revisor.gerar_ground_truth_csv(caminho_db, csv_dest)
        with csv_dest.open() as f:
            r = csv.reader(f)
            header = next(r)
        assert header == [
            "item_id",
            "dimensao",
            "valor_etl",
            "valor_opus",
            "valor_humano",
            "divergencia",
            "observacao",
            "ts",
            "valor_grafo_real",
            "divergencia_etl_grafo",
            "divergencia_grafo_opus",
        ]

    def test_divergencia_etl_grafo_quando_valores_diferem(self, tmp_path: Path) -> None:
        # Tipo B: ETL extraiu uma coisa, grafo gravou outra (sintetico).
        caminho_db = tmp_path / "rev.sqlite"
        revisor.salvar_marcacao(
            caminho_db,
            "doc1",
            "fornecedor",
            ok=None,
            observacao="",
            valor_etl="ANDRE DA SILVA",
            valor_opus="RECEITA_FEDERAL",
            valor_grafo_real="Receita Federal do Brasil",
        )
        csv_dest = tmp_path / "out.csv"
        revisor.gerar_ground_truth_csv(caminho_db, csv_dest)
        with csv_dest.open() as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["divergencia_etl_grafo"] == "1"
        assert rows[0]["divergencia_grafo_opus"] == "1"  # Opus também diverge

    def test_sem_divergencia_quando_tudo_igual(self, tmp_path: Path) -> None:
        caminho_db = tmp_path / "rev.sqlite"
        revisor.salvar_marcacao(
            caminho_db,
            "doc2",
            "valor",
            ok=1,
            observacao="",
            valor_etl="200.00",
            valor_opus="200.00",
            valor_grafo_real="200.00",
        )
        csv_dest = tmp_path / "out.csv"
        revisor.gerar_ground_truth_csv(caminho_db, csv_dest)
        with csv_dest.open() as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["divergencia"] == "0"
        assert rows[0]["divergencia_etl_grafo"] == "0"
        assert rows[0]["divergencia_grafo_opus"] == "0"


class TestPopularValorGrafoReal:
    """Script popular_valor_grafo_real.py — idempotencia + falha-soft."""

    def test_falha_soft_quando_grafo_nao_existe(self, tmp_path: Path) -> None:
        revisao_db = tmp_path / "rev.sqlite"
        revisor.garantir_schema(revisao_db)
        contagens = popular_valor_grafo_real.popular(
            grafo_db=tmp_path / "nao_existe.sqlite",
            revisao_db=revisao_db,
        )
        assert contagens["total"] == 0  # cedo retorna sem explodir

    def test_idempotente_em_segunda_execucao(
        self, tmp_path: Path, grafo_4way: Path
    ) -> None:
        revisao_db = tmp_path / "rev.sqlite"
        revisor.salvar_marcacao(
            revisao_db,
            "node_100",
            "data",
            ok=None,
            observacao="",
            valor_etl="2026-01-15",
        )
        c1 = popular_valor_grafo_real.popular(
            grafo_db=grafo_4way,
            revisao_db=revisao_db,
        )
        c2 = popular_valor_grafo_real.popular(
            grafo_db=grafo_4way,
            revisao_db=revisao_db,
        )
        assert c1["atualizadas"] == 1
        # Segunda execução deve pular (já_preenchidas) ou não mudar conteúdo.
        m = revisor.carregar_marcacoes(revisao_db)
        assert m[0]["valor_grafo_real"] == "2026-01-15"
        # Idempotência em conteúdo: a string não muda entre runs.
        assert c2["sem_node"] == c1["sem_node"]

    def test_resolve_item_id_relativo_via_node_direto(
        self, tmp_path: Path, grafo_4way: Path
    ) -> None:
        revisao_db = tmp_path / "rev.sqlite"
        revisor.salvar_marcacao(
            revisao_db,
            "node_100",
            "fornecedor",
            ok=None,
            observacao="",
        )
        popular_valor_grafo_real.popular(
            grafo_db=grafo_4way,
            revisao_db=revisao_db,
        )
        m = revisor.carregar_marcacoes(revisao_db)
        # Fornecedor canonico via aresta: usa razao_social do node fornecedor
        assert m[0]["valor_grafo_real"] == "Receita Federal do Brasil"

    def test_dimensao_valor_extrai_total_do_metadata(
        self, tmp_path: Path, grafo_4way: Path
    ) -> None:
        revisao_db = tmp_path / "rev.sqlite"
        revisor.salvar_marcacao(
            revisao_db,
            "node_100",
            "valor",
            ok=None,
            observacao="",
        )
        popular_valor_grafo_real.popular(
            grafo_db=grafo_4way,
            revisao_db=revisao_db,
        )
        m = revisor.carregar_marcacoes(revisao_db)
        assert m[0]["valor_grafo_real"] == "5000.00"


# "Quatro pontos definem um plano." -- princípio do triângulo da verdade
