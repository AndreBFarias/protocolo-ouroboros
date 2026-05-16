"""Testes da Sprint INFRA-PIPELINE-TRANSACIONALIDADE-2026-05-15.

Cobre rollback granular em estágios do pipeline que tocam o grafo SQLite:
linking de documentos, ER de produtos, categorização de itens. Cada estágio
envolto em `with GrafoDB(...) as db, db.transaction():` deve rejeitar
mutações parciais quando a função interna crashar.

Também cobre o log estruturado `logs/pipeline_falha_<ts>.json` que registra
estágio, traceback e ponteiro para o backup grafo automatic mais recente.
"""

from __future__ import annotations

import json
from pathlib import Path

from src import pipeline
from src.graph.db import GrafoDB


def _setup_grafo_minimo(tmp_path: Path) -> Path:
    """Cria grafo SQLite vazio com schema válido para testes."""
    p = tmp_path / "grafo.sqlite"
    db = GrafoDB(p)
    db.criar_schema()
    db.fechar()
    return p


def test_log_estruturado_grava_estagio_e_traceback(tmp_path: Path, monkeypatch):
    """`_registrar_falha_pipeline_estruturada` materializa JSON canônico."""
    monkeypatch.setattr(pipeline, "RAIZ", tmp_path)
    # Sem backups: campo `ultimo_backup_grafo` deve ser None.
    monkeypatch.setattr(pipeline, "DIR_BACKUP_GRAFO", tmp_path / "_backup_inexistente")

    try:
        raise ValueError("crash sintético no estágio xyz")
    except ValueError as erro:
        destino = pipeline._registrar_falha_pipeline_estruturada("etapa_teste", erro)

    assert destino is not None
    assert destino.exists()
    d = json.loads(destino.read_text(encoding="utf-8"))
    assert d["estagio"] == "etapa_teste"
    assert d["erro_tipo"] == "ValueError"
    assert "crash sintético" in d["erro_mensagem"]
    assert "Traceback" in d["traceback"]
    assert d["ultimo_backup_grafo"] is None


def test_log_estruturado_aponta_backup_mais_recente(tmp_path: Path, monkeypatch):
    """Quando há backups na pasta canônica, log aponta o mais recente."""
    monkeypatch.setattr(pipeline, "RAIZ", tmp_path)
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / f"{pipeline.PREFIXO_BACKUP_GRAFO}2026-05-10_120000.sqlite").write_bytes(b"x")
    (backup_dir / f"{pipeline.PREFIXO_BACKUP_GRAFO}2026-05-15_080000.sqlite").write_bytes(b"y")
    monkeypatch.setattr(pipeline, "DIR_BACKUP_GRAFO", backup_dir)

    try:
        raise RuntimeError("alguma falha")
    except RuntimeError as erro:
        destino = pipeline._registrar_falha_pipeline_estruturada("etapa_x", erro)

    assert destino is not None
    d = json.loads(destino.read_text(encoding="utf-8"))
    # `sorted()` ordena lexicograficamente; "2026-05-15..." > "2026-05-10..."
    assert d["ultimo_backup_grafo"] == f"{pipeline.PREFIXO_BACKUP_GRAFO}2026-05-15_080000.sqlite"


def test_executar_linking_documentos_rollback_em_crash_interno(
    tmp_path: Path, monkeypatch
):
    """Crash mid-linking faz rollback completo: nenhum node/edge criado."""
    grafo_path = _setup_grafo_minimo(tmp_path)
    monkeypatch.setattr(pipeline, "RAIZ", tmp_path)
    monkeypatch.setattr(pipeline, "DIR_BACKUP_GRAFO", tmp_path / "_no_backup")

    # Monkeypatch caminho_padrao para apontar para tmp_path
    from src.graph import db as graph_db_mod

    monkeypatch.setattr(graph_db_mod, "_PATH_DB_PADRAO", grafo_path)

    # Substitui linkar_documentos_a_transacoes por função que muta + crasha.
    from src.graph import linking as linking_mod

    def fake_link(db):
        db.upsert_node("documento", "DOC_QUE_NUNCA_FOI")
        raise RuntimeError("crash mid-linking")

    monkeypatch.setattr(linking_mod, "linkar_documentos_a_transacoes", fake_link)
    monkeypatch.setattr(
        linking_mod, "linkar_pix_transacao", lambda db: {"chamado": False}
    )

    pipeline._executar_linking_documentos()  # captura exception internamente

    # Validação: rollback aconteceu — nó NÃO persistiu.
    db = GrafoDB(grafo_path)
    assert db.buscar_node("documento", "DOC_QUE_NUNCA_FOI") is None
    db.fechar()

    # Log estruturado foi criado:
    logs = list((tmp_path / "logs").glob("pipeline_falha_*.json"))
    assert len(logs) == 1
    d = json.loads(logs[0].read_text(encoding="utf-8"))
    assert d["estagio"] == "linking_documentos"
    assert "crash mid-linking" in d["erro_mensagem"]


def test_executar_er_produtos_rollback_em_crash_interno(tmp_path: Path, monkeypatch):
    """Crash mid-ER faz rollback do grafo + log estruturado."""
    grafo_path = _setup_grafo_minimo(tmp_path)
    monkeypatch.setattr(pipeline, "RAIZ", tmp_path)
    monkeypatch.setattr(pipeline, "DIR_BACKUP_GRAFO", tmp_path / "_no_backup")

    from src.graph import db as graph_db_mod

    monkeypatch.setattr(graph_db_mod, "_PATH_DB_PADRAO", grafo_path)

    from src.graph import er_produtos as er_mod

    def fake_er(db):
        db.upsert_node("produto_canonico", "PRODUTO_REVERTIDO")
        raise RuntimeError("crash mid-ER")

    monkeypatch.setattr(er_mod, "executar_er_produtos", fake_er)

    pipeline._executar_er_produtos()

    db = GrafoDB(grafo_path)
    assert db.buscar_node("produto_canonico", "PRODUTO_REVERTIDO") is None
    db.fechar()

    logs = list((tmp_path / "logs").glob("pipeline_falha_*.json"))
    assert len(logs) == 1
    d = json.loads(logs[0].read_text(encoding="utf-8"))
    assert d["estagio"] == "er_produtos"


# "Comprometer um pedaço por vez é poder voltar atrás sem perder o resto."
# -- princípio transacional
