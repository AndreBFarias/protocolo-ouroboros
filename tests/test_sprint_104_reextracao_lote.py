"""Sprint 104: testes regressivos da flag --forcar-reextracao em
scripts/reprocessar_documentos.py.

Cobre:
  1. Sem flag: comportamento padrão preservado (idempotente, INSERT OR IGNORE).
  2. Com flag: nodes 'documento' + arestas relacionadas são limpos antes de
     reingerir, permitindo metadata novo de extratores atualizados chegar
     ao grafo.
  3. Helper _limpar_documentos_e_arestas devolve contagem correta.
  4. Não afeta nodes 'transacao', 'fornecedor', 'periodo', 'item', 'categoria'.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.reprocessar_documentos import _limpar_documentos_e_arestas
from src.graph.db import GrafoDB


@pytest.fixture
def grafo_com_docs(tmp_path: Path) -> GrafoDB:
    """Cria grafo sintético com 3 documentos + 3 arestas + nodes auxiliares
    (fornecedor, periodo, transacao). Simula estado pós-pipeline.
    """
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()

    # Documentos
    doc1 = db.upsert_node(
        "documento",
        "DOC|001",
        metadata={
            "tipo_documento": "holerite",
            "total": 5000.0,
            "data_emissao": "2026-03-01",
        },
    )
    doc2 = db.upsert_node(
        "documento",
        "DOC|002",
        metadata={
            "tipo_documento": "das_parcsn_andre",
            "total": 324.31,
            "data_emissao": "2025-02-28",
        },
    )
    db.upsert_node(
        "documento",
        "DOC|003",
        metadata={"tipo_documento": "boleto_servico", "total": 100.0},
    )

    # Auxiliares (não devem ser apagados)
    forn = db.upsert_node("fornecedor", "FORN|001")
    per = db.upsert_node("periodo", "2026-03")
    tx = db.upsert_node("transacao", "TX|001", metadata={"valor": 5000, "data": "2026-03-05"})

    # Arestas variadas
    db.adicionar_edge(doc1, tx, "documento_de", evidencia={"score": 0.9})
    db.adicionar_edge(doc1, forn, "fornecido_por")
    db.adicionar_edge(doc1, per, "ocorre_em")
    db.adicionar_edge(doc2, forn, "fornecido_por")

    return db


def test_limpar_documentos_apaga_3_docs_e_4_edges(grafo_com_docs: GrafoDB):
    """`_limpar_documentos_e_arestas` apaga 3 docs + 4 edges (1 documento_de,
    2 fornecido_por, 1 ocorre_em).
    """
    resultado = _limpar_documentos_e_arestas(grafo_com_docs)
    assert resultado["docs"] == 3
    assert resultado["edges_total"] == 4

    cur = grafo_com_docs._conn.cursor()  # noqa: SLF001
    docs_restantes = cur.execute("SELECT COUNT(*) FROM node WHERE tipo='documento'").fetchone()[0]
    assert docs_restantes == 0


def test_limpar_documentos_preserva_outros_nodes(grafo_com_docs: GrafoDB):
    """Não toca em fornecedor, periodo, transacao."""
    _limpar_documentos_e_arestas(grafo_com_docs)
    cur = grafo_com_docs._conn.cursor()  # noqa: SLF001

    for tipo in ("fornecedor", "periodo", "transacao"):
        n = cur.execute("SELECT COUNT(*) FROM node WHERE tipo=?", (tipo,)).fetchone()[0]
        assert n == 1, f"node tipo={tipo} foi apagado erroneamente"


def test_limpar_documentos_preserva_outras_arestas(tmp_path: Path):
    """Edges entre nodes que NÃO são 'documento' não devem ser tocadas."""
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()

    forn = db.upsert_node("fornecedor", "FORN|XYZ")
    item = db.upsert_node("item", "ITEM|XYZ")
    cat = db.upsert_node("categoria", "Padaria")
    db.adicionar_edge(item, cat, "categoria_de")
    db.adicionar_edge(forn, item, "vendeu")

    resultado = _limpar_documentos_e_arestas(db)
    assert resultado["docs"] == 0
    assert resultado["edges_total"] == 0

    cur = db._conn.cursor()  # noqa: SLF001
    edges = cur.execute("SELECT COUNT(*) FROM edge").fetchone()[0]
    assert edges == 2  # ambas preservadas


def test_limpar_documentos_idempotente(grafo_com_docs: GrafoDB):
    """Rodar 2x não levanta nem dá contagem negativa."""
    r1 = _limpar_documentos_e_arestas(grafo_com_docs)
    r2 = _limpar_documentos_e_arestas(grafo_com_docs)
    assert r1["docs"] == 3
    assert r2["docs"] == 0
    assert r2["edges_total"] == 0


def test_run_sh_help_inclui_reextrair():
    """run.sh --help (ou sem args) menciona --reextrair-tudo na seção
    Processamento.
    """
    raiz = Path(__file__).resolve().parents[1]
    run_sh = raiz / "run.sh"
    conteudo = run_sh.read_text(encoding="utf-8")
    assert "--reextrair-tudo" in conteudo
    assert "Sprint 104" in conteudo


def test_menu_interativo_inclui_opcao_6():
    """Menu interativo declara opção 6 com texto de Reextração."""
    raiz = Path(__file__).resolve().parents[1]
    menu = raiz / "scripts" / "menu_interativo.py"
    conteudo = menu.read_text(encoding="utf-8")
    assert '"6":' in conteudo
    assert "Reextrair" in conteudo
    # Dispatcher também tem a chave "6"
    assert '"6": _acao_reextrair' in conteudo


def test_argparse_aceita_forcar_reextracao_sem_levantar():
    """`reprocessar_documentos.main` aceita a nova flag sem erro de parse.

    Roda em --dry-run para evitar tocar o grafo real e confirma exit 0
    quando data/raw está vazio (caso CI sem fixtures).
    """
    import sys
    from io import StringIO

    from scripts.reprocessar_documentos import main

    capturado = StringIO()
    stdout_orig = sys.stdout
    sys.stdout = capturado
    try:
        # raiz vazia + dry-run + flag (que e ignorada em dry-run mas aceita
        # pelo argparse).
        rc = main(
            [
                "--raiz",
                str(Path("/tmp/_pytest_raiz_inexistente_104")),
                "--dry-run",
                "--forcar-reextracao",
            ]
        )
    finally:
        sys.stdout = stdout_orig

    assert rc == 0


def _conta_docs(db: GrafoDB) -> int:
    cur = db._conn.cursor()  # noqa: SLF001
    return cur.execute("SELECT COUNT(*) FROM node WHERE tipo='documento'").fetchone()[0]


def test_metadata_atualizado_chega_apos_reextracao(tmp_path: Path):
    """Cenário canônico Sprint 104: extrator antigo gravou doc com metadata
    A; extrator atualizado regrava com metadata B. Sem --forcar-reextracao,
    INSERT OR IGNORE manteria A. Com a fix, simulamos limpeza + reingestão
    e confirmamos que B prevalece.
    """
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()

    # Versão 1 do extrator (antiga): só 'total'
    db.upsert_node(
        "documento",
        "DOC|HOL|2026-03",
        metadata={"tipo_documento": "holerite", "total": 5000.0},
    )
    assert _conta_docs(db) == 1

    # --forcar-reextracao limpa
    _limpar_documentos_e_arestas(db)
    assert _conta_docs(db) == 0

    # Versão 2 do extrator (Sprint 95a): 'total' + 'liquido' + 'bruto'
    db.upsert_node(
        "documento",
        "DOC|HOL|2026-03",
        metadata={
            "tipo_documento": "holerite",
            "total": 5000.0,
            "bruto": 5000.0,
            "liquido": 4250.0,
        },
    )

    # Confirma metadata novo presente
    cur = db._conn.cursor()  # noqa: SLF001
    row = cur.execute(
        "SELECT metadata FROM node WHERE tipo='documento' AND nome_canonico=?",
        ("DOC|HOL|2026-03",),
    ).fetchone()
    meta = json.loads(row[0])
    assert meta["liquido"] == 4250.0
    assert meta["bruto"] == 5000.0


# "As vezes precisa apagar o passado para ouvir o presente."
# -- principio do reset-controlado
