"""Testes do backfill de arquivo_original (Sprint 87.5).

Cenários cobertos:
1. Skip quando node já tem `arquivo_original` válido.
2. Copia de `arquivo_origem` para `arquivo_original`.
3. Heurística por nome canônico (substring do stem).
4. Heurística por sha256 (hash do conteúdo).
5. Idempotência (segunda rodada não altera nada).
6. Stats precisas em cenário misto.
7. Flag `--backfill-metadata` do CLI chama a rotina sem rodar o pipeline.

Todos os cenários usam `tmp_path` + `GrafoDB(tmp_path/"grafo.sqlite")`
para nunca tocar o grafo de produção.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.graph.backfill_arquivo_original import backfill_arquivo_original
from src.graph.db import GrafoDB


@pytest.fixture
def db_tmp(tmp_path: Path) -> GrafoDB:
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


def _criar_arquivo(raiz: Path, subpath: str, conteudo: bytes = b"boleto dummy") -> Path:
    destino = raiz / subpath
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)
    return destino


def test_skip_quando_ja_preenchido(db_tmp: GrafoDB, tmp_path: Path) -> None:
    """Node com arquivo_original preenchido não é tocado."""
    db_tmp.upsert_node(
        "documento",
        "BOLETO-SESC-2026-03",
        metadata={"arquivo_original": "/path/ja/existe.pdf", "tipo_documento": "boleto"},
    )
    raw = tmp_path / "data_raw"
    raw.mkdir()
    stats = backfill_arquivo_original(db_tmp, raiz_raw=raw)

    assert stats["total"] == 1
    assert stats["ja_preenchidos"] == 1
    assert stats["backfill_por_origem"] == 0
    assert stats["backfill_por_sha256"] == 0
    assert stats["backfill_por_heuristica"] == 0
    assert stats["nao_encontrados"] == 0
    node = db_tmp.buscar_node("documento", "BOLETO-SESC-2026-03")
    assert node is not None
    assert node.metadata["arquivo_original"] == "/path/ja/existe.pdf"


def test_copia_de_arquivo_origem(db_tmp: GrafoDB, tmp_path: Path) -> None:
    """Node só com arquivo_origem (sem L) ganha arquivo_original idêntico."""
    db_tmp.upsert_node(
        "documento",
        "DANFE-123",
        metadata={"arquivo_origem": "/raw/nf/danfe.pdf", "tipo_documento": "danfe"},
    )
    raw = tmp_path / "data_raw"
    raw.mkdir()
    stats = backfill_arquivo_original(db_tmp, raiz_raw=raw)

    assert stats["backfill_por_origem"] == 1
    assert stats["nao_encontrados"] == 0
    node = db_tmp.buscar_node("documento", "DANFE-123")
    assert node is not None
    assert node.metadata["arquivo_original"] == "/raw/nf/danfe.pdf"
    # arquivo_origem permanece (não apagamos a convenção antiga).
    assert node.metadata["arquivo_origem"] == "/raw/nf/danfe.pdf"


def test_heuristica_por_nome(db_tmp: GrafoDB, tmp_path: Path) -> None:
    """Node sem campo nenhum mas cujo nome_canonico casa com Path.stem."""
    raw = tmp_path / "data_raw"
    arquivo = _criar_arquivo(raw, "casal/boletos/BOLETO_natacao_andre_202603.pdf")
    db_tmp.upsert_node(
        "documento",
        "BOLETO_NATACAO_ANDRE_202603",
        metadata={"tipo_documento": "boleto"},
    )
    stats = backfill_arquivo_original(db_tmp, raiz_raw=raw)

    assert stats["backfill_por_heuristica"] == 1
    assert stats["nao_encontrados"] == 0
    node = db_tmp.buscar_node("documento", "BOLETO_NATACAO_ANDRE_202603")
    assert node is not None
    assert node.metadata["arquivo_original"] == str(arquivo.resolve())


def test_heuristica_por_sha256(db_tmp: GrafoDB, tmp_path: Path) -> None:
    """Node com metadata.sha256 casa o arquivo pelo hash completo do conteúdo."""
    raw = tmp_path / "data_raw"
    conteudo = "conteúdo único do documento teste".encode("utf-8")
    arquivo = _criar_arquivo(raw, "andre/documentos/recibo.pdf", conteudo=conteudo)
    sha = hashlib.sha256(conteudo).hexdigest()

    db_tmp.upsert_node(
        "documento",
        "XY",  # nome curto, força heurística falhar
        metadata={"sha256": sha, "tipo_documento": "recibo"},
    )
    stats = backfill_arquivo_original(db_tmp, raiz_raw=raw)

    assert stats["backfill_por_sha256"] == 1
    assert stats["nao_encontrados"] == 0
    node = db_tmp.buscar_node("documento", "XY")
    assert node is not None
    assert node.metadata["arquivo_original"] == str(arquivo.resolve())


def test_idempotencia(db_tmp: GrafoDB, tmp_path: Path) -> None:
    """Segunda execução com grafo já backfilled devolve zero alterações."""
    db_tmp.upsert_node(
        "documento",
        "NFE-777",
        metadata={"arquivo_origem": "/raw/x.xml", "tipo_documento": "nfe"},
    )
    raw = tmp_path / "data_raw"
    raw.mkdir()
    primeira = backfill_arquivo_original(db_tmp, raiz_raw=raw)
    segunda = backfill_arquivo_original(db_tmp, raiz_raw=raw)

    assert primeira["backfill_por_origem"] == 1
    assert primeira["ja_preenchidos"] == 0
    assert segunda["ja_preenchidos"] == 1
    assert segunda["backfill_por_origem"] == 0
    assert segunda["backfill_por_sha256"] == 0
    assert segunda["backfill_por_heuristica"] == 0
    assert segunda["nao_encontrados"] == 0


def test_stats_precisas(db_tmp: GrafoDB, tmp_path: Path) -> None:
    """Cenário misto: 1 ja_preenchido + 1 origem + 1 nome + 1 sha + 1 órfão."""
    raw = tmp_path / "data_raw"
    # candidato por nome (stem casa substring)
    arq_nome = _criar_arquivo(
        raw, "andre/documentos/RELATORIO_CONSULTA_MEDICA_2026_03.pdf"
    )
    # candidato por sha
    conteudo_sha = "payload único para sha lookup".encode("utf-8")
    arq_sha = _criar_arquivo(raw, "vitoria/xml/nfe.xml", conteudo=conteudo_sha)
    sha = hashlib.sha256(conteudo_sha).hexdigest()

    db_tmp.upsert_node(
        "documento",
        "DOC-JA-PREENCHIDO",
        metadata={"arquivo_original": "/ja/existe.pdf"},
    )
    db_tmp.upsert_node(
        "documento",
        "DOC-ORIGEM",
        metadata={"arquivo_origem": "/raw/algo.pdf"},
    )
    db_tmp.upsert_node(
        "documento",
        "RELATORIO_CONSULTA_MEDICA_2026_03",
        metadata={"tipo_documento": "receita"},
    )
    db_tmp.upsert_node(
        "documento",
        "NFE-HASH-777",
        metadata={"sha256": sha},
    )
    db_tmp.upsert_node(
        "documento",
        "DOC-ORFAO-SEM-PISTA",
        metadata={"tipo_documento": "desconhecido"},
    )

    stats = backfill_arquivo_original(db_tmp, raiz_raw=raw)

    assert stats["total"] == 5
    assert stats["ja_preenchidos"] == 1
    assert stats["backfill_por_origem"] == 1
    assert stats["backfill_por_heuristica"] == 1
    assert stats["backfill_por_sha256"] == 1
    assert stats["nao_encontrados"] == 1

    # Paths corretos nos casos heurísticos.
    doc_nome = db_tmp.buscar_node("documento", "RELATORIO_CONSULTA_MEDICA_2026_03")
    assert doc_nome is not None
    assert doc_nome.metadata["arquivo_original"] == str(arq_nome.resolve())
    doc_sha = db_tmp.buscar_node("documento", "NFE-HASH-777")
    assert doc_sha is not None
    assert doc_sha.metadata["arquivo_original"] == str(arq_sha.resolve())


def test_cli_flag_backfill_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Flag `--backfill-metadata` invoca backfill e não executa pipeline regular."""
    from src import pipeline as pipeline_mod

    # Grafo sintético no tmp_path.
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        "documento",
        "ITAU-EXT-2026-03",
        metadata={"arquivo_origem": "/raw/itau/ext.pdf"},
    )
    db.fechar()

    # Redireciona caminho_padrao para o grafo sintético.
    from src.graph import db as db_mod

    monkeypatch.setattr(db_mod, "caminho_padrao", lambda: tmp_path / "grafo.sqlite")

    chamou_executar = False

    def _fake_executar(**_: object) -> None:
        nonlocal chamou_executar
        chamou_executar = True

    monkeypatch.setattr(pipeline_mod, "executar", _fake_executar)

    with pytest.raises(SystemExit) as exc_info:
        pipeline_mod.main(["--backfill-metadata"])

    assert exc_info.value.code == 0
    assert chamou_executar is False
    saida = capsys.readouterr().out
    assert "total: 1" in saida
    assert "backfill_por_origem: 1" in saida


# "A idempotência é a virtude dos procedimentos que confiam na repetição." -- Heráclito
