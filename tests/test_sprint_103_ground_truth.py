"""Sprint 103: testes do Revisor com ground-truth (3 colunas ETL/Opus/Humano).

Cobre:
  1. Schema migration: DB antigo (sem valor_etl/valor_opus) é atualizado in-place.
  2. salvar_marcacao com valor_etl persiste corretamente.
  3. extrair_valor_etl_para_dimensao mapeia metadata para 5 dimensoes.
  4. gerar_ground_truth_csv produz CSV com 8 colunas + flag divergencia.
  5. PII mascarada na exportação CSV.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from src.dashboard.paginas.revisor import (
    carregar_marcacoes,
    extrair_valor_etl_para_dimensao,
    garantir_schema,
    gerar_ground_truth_csv,
    salvar_marcacao,
)


def test_garantir_schema_cria_db_novo_com_colunas_103(tmp_path: Path):
    """DB novo já vem com valor_etl e valor_opus."""
    caminho = tmp_path / "rev.sqlite"
    garantir_schema(caminho)
    conn = sqlite3.connect(caminho)
    try:
        cur = conn.execute("PRAGMA table_info(revisao)")
        colunas = {row[1] for row in cur.fetchall()}
    finally:
        conn.close()
    assert "valor_etl" in colunas
    assert "valor_opus" in colunas


def test_garantir_schema_migra_db_antigo(tmp_path: Path):
    """DB criado com schema antigo (sem valor_etl/valor_opus) é migrado."""
    caminho = tmp_path / "rev_antigo.sqlite"
    # Cria schema antigo manualmente.
    conn = sqlite3.connect(caminho)
    conn.executescript(
        """
        CREATE TABLE revisao (
            item_id TEXT NOT NULL,
            dimensao TEXT NOT NULL,
            ok INTEGER,
            observacao TEXT,
            ts TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (item_id, dimensao)
        );
        """
    )
    conn.execute(
        "INSERT INTO revisao (item_id, dimensao, ok, observacao) VALUES (?, ?, ?, ?)",
        ("doc/x.pdf", "valor", 1, "ok no antigo"),
    )
    conn.commit()
    conn.close()

    # garantir_schema deve adicionar as 2 colunas novas SEM perder dados.
    garantir_schema(caminho)

    conn = sqlite3.connect(caminho)
    try:
        cur = conn.execute("PRAGMA table_info(revisao)")
        colunas = {row[1] for row in cur.fetchall()}
        assert "valor_etl" in colunas
        assert "valor_opus" in colunas
        # Linha antiga ainda existe.
        cur2 = conn.execute("SELECT item_id, ok, observacao FROM revisao")
        rows = cur2.fetchall()
        assert len(rows) == 1
        assert rows[0] == ("doc/x.pdf", 1, "ok no antigo")
    finally:
        conn.close()


def test_salvar_marcacao_persiste_valor_etl(tmp_path: Path):
    """salvar_marcacao com valor_etl persiste no DB."""
    caminho = tmp_path / "rev.sqlite"
    salvar_marcacao(
        caminho,
        item_id="doc/teste.pdf",
        dimensao="valor",
        ok=1,
        observacao="conferi",
        valor_etl="100.50",
    )
    marcacoes = carregar_marcacoes(caminho)
    assert len(marcacoes) == 1
    assert marcacoes[0]["valor_etl"] == "100.50"
    assert marcacoes[0]["valor_opus"] is None


def test_salvar_marcacao_preserva_valor_etl_em_update(tmp_path: Path):
    """Re-salvar marcação sem passar valor_etl (None) preserva valor anterior."""
    caminho = tmp_path / "rev.sqlite"
    # Primeira gravação: define valor_etl.
    salvar_marcacao(caminho, "doc/x.pdf", "valor", 1, "", valor_etl="50.00")
    # Segunda gravação: atualiza ok mas não passa valor_etl (None).
    salvar_marcacao(caminho, "doc/x.pdf", "valor", 0, "errado", valor_etl=None)
    marcacoes = carregar_marcacoes(caminho)
    assert len(marcacoes) == 1
    assert marcacoes[0]["ok"] == 0  # atualizado
    assert marcacoes[0]["valor_etl"] == "50.00"  # preservado via COALESCE


def test_extrair_valor_etl_para_dimensao_data():
    """Dimensão 'data' lê metadata.data_emissao."""
    pendencia = {"metadata": {"data_emissao": "2026-03-15"}}
    assert extrair_valor_etl_para_dimensao(pendencia, "data") == "2026-03-15"


def test_extrair_valor_etl_para_dimensao_valor():
    """Dimensão 'valor' formata metadata.total com 2 casas decimais."""
    pendencia = {"metadata": {"total": 1234.5}}
    assert extrair_valor_etl_para_dimensao(pendencia, "valor") == "1234.50"


def test_extrair_valor_etl_para_dimensao_itens_lista():
    pendencia = {"metadata": {"itens": [{"nome": "a"}, {"nome": "b"}]}}
    assert extrair_valor_etl_para_dimensao(pendencia, "itens") == "2 item(ns)"


def test_extrair_valor_etl_para_dimensao_fornecedor_mascara_pii():
    """Razão social com CNPJ embutido mascara o CNPJ."""
    pendencia = {"metadata": {"razao_social": "EMPRESA X LTDA 12.345.678/0001-90"}}
    saida = extrair_valor_etl_para_dimensao(pendencia, "fornecedor")
    assert "EMPRESA X" in saida
    assert "12.345.678" not in saida
    assert "XX.XXX.XXX" in saida


def test_extrair_valor_etl_para_dimensao_pessoa_inferida():
    """Pessoa não preenchida no metadata é inferida do path."""
    pendencia = {"metadata": {}, "caminho": "/data/raw/andre/holerites/foo.pdf"}
    assert extrair_valor_etl_para_dimensao(pendencia, "pessoa") == "andre (inferido)"


def test_extrair_valor_etl_para_dimensao_vazio_quando_sem_dado():
    """Sinal claro de 'pipeline não sabe': string vazia."""
    pendencia = {"metadata": {}, "caminho": "/data/raw/desconhecido.pdf"}
    for dim in ("data", "valor", "itens", "fornecedor", "pessoa"):
        assert extrair_valor_etl_para_dimensao(pendencia, dim) == ""


def test_gerar_ground_truth_csv_db_inexistente_gera_so_cabecalho(tmp_path: Path):
    """DB que não existe: CSV criado com apenas cabeçalho, sem levantar."""
    caminho_db = tmp_path / "nao_existe.sqlite"
    caminho_csv = tmp_path / "out.csv"
    n = gerar_ground_truth_csv(caminho_db, caminho_csv)
    assert n == 0
    with caminho_csv.open(encoding="utf-8") as f:
        linhas = list(csv.reader(f))
    assert len(linhas) == 1  # só header
    assert linhas[0] == [
        "item_id",
        "dimensao",
        "valor_etl",
        "valor_opus",
        "valor_humano",
        "divergencia",
        "observacao",
        "ts",
    ]


def test_gerar_ground_truth_csv_export_completo(tmp_path: Path):
    """3 marcações no DB -> 3 linhas no CSV + cabeçalho. Divergência calculada."""
    caminho_db = tmp_path / "rev.sqlite"
    # Marcação OK (sem divergência).
    salvar_marcacao(
        caminho_db, "doc/a.pdf", "valor", ok=1, observacao="", valor_etl="100.00"
    )
    # Marcação humano marcou Erro (divergência por humano).
    salvar_marcacao(
        caminho_db, "doc/b.pdf", "data", ok=0, observacao="data errada", valor_etl="2026-01-01"
    )
    # Marcação não-aplicável.
    salvar_marcacao(caminho_db, "doc/c.pdf", "itens", ok=None, observacao="")

    caminho_csv = tmp_path / "gt.csv"
    n = gerar_ground_truth_csv(caminho_db, caminho_csv)
    assert n == 3

    with caminho_csv.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Mapeia por item_id para inspecionar.
    por_id = {r["item_id"]: r for r in rows}
    assert por_id["doc/a.pdf"]["valor_humano"] == "OK"
    assert por_id["doc/a.pdf"]["divergencia"] == "0"
    assert por_id["doc/b.pdf"]["valor_humano"] == "Erro"
    assert por_id["doc/b.pdf"]["divergencia"] == "1"
    assert por_id["doc/c.pdf"]["valor_humano"] == "Não-aplicável"


def test_gerar_ground_truth_csv_mascara_pii_em_observacao(tmp_path: Path):
    """Observação humana com CPF cru é mascarada antes de escrever CSV."""
    caminho_db = tmp_path / "rev.sqlite"
    salvar_marcacao(
        caminho_db,
        "doc/x.pdf",
        "fornecedor",
        ok=0,
        observacao="cpf 12345678901 errado",
        valor_etl="EMPRESA Y",
    )
    caminho_csv = tmp_path / "gt.csv"
    gerar_ground_truth_csv(caminho_db, caminho_csv)

    with caminho_csv.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    obs = rows[0]["observacao"]
    assert "12345678901" not in obs
    assert "X" in obs


def test_gerar_ground_truth_csv_divergencia_etl_vs_opus(tmp_path: Path):
    """Quando valor_etl != valor_opus E ambos não-vazios, divergencia=1
    mesmo se humano marcou OK.
    """
    caminho_db = tmp_path / "rev.sqlite"
    salvar_marcacao(
        caminho_db,
        "doc/y.pdf",
        "valor",
        ok=1,
        observacao="",
        valor_etl="100.00",
        valor_opus="105.00",
    )
    caminho_csv = tmp_path / "gt.csv"
    gerar_ground_truth_csv(caminho_db, caminho_csv)

    with caminho_csv.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["divergencia"] == "1"


# "Verdade não se decreta -- se compara." -- princípio do ground-truth honesto
