"""Testes do anti-órfão na inbox (src/intake/anti_orfao.py).

Cobre Sprint ANTI-MIGUE-02 do plan pure-swinging-mitten:
- Varredura da zona de estagiário (_classificar/, _conferir/) por padrão
- Modo abrangente opcional varre data/raw/ inteiro
- Classificação em integrado / catalogado_orfao / orfao_total / orfao_total_antigo
- Geração de relatório Markdown
- Exit code 1 em modo --strict quando há órfãos antigos
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from src.intake.anti_orfao import (
    Classificacao,
    classificar,
    gerar_relatorio,
    main,
    mapear_documentos_no_grafo,
    varrer_arquivos_inbox,
)


def _criar_grafo(db: Path, documentos: list[dict]) -> None:
    """Cria SQLite minimal com tabelas node + edge."""
    with sqlite3.connect(db) as con:
        con.execute(
            "CREATE TABLE node (id INTEGER PRIMARY KEY, tipo TEXT, "
            "nome_canonico TEXT, aliases TEXT, metadata TEXT, "
            "created_at TEXT, updated_at TEXT)"
        )
        con.execute(
            "CREATE TABLE edge (id INTEGER PRIMARY KEY, src_id INTEGER, "
            "dst_id INTEGER, tipo TEXT, peso REAL, evidencia TEXT, "
            "created_at TEXT)"
        )
        for doc in documentos:
            con.execute(
                "INSERT INTO node (id, tipo, nome_canonico, aliases, metadata, "
                "created_at, updated_at) VALUES (?, 'documento', ?, '[]', ?, '', '')",
                (doc["id"], doc.get("nome", f"doc_{doc['id']}"), json.dumps(doc["meta"])),
            )
            if doc.get("tem_aresta"):
                con.execute(
                    "INSERT INTO edge (src_id, dst_id, tipo, peso, evidencia, created_at) "
                    "VALUES (?, 1, 'documento_de', 1.0, '{}', '')",
                    (doc["id"],),
                )


def test_varredura_padrao_inclui_apenas_zona_estagiario(tmp_path):
    raw = tmp_path / "raw"
    (raw / "_classificar").mkdir(parents=True)
    (raw / "_conferir" / "subpasta").mkdir(parents=True)
    (raw / "andre" / "holerites").mkdir(parents=True)
    (raw / "_classificar" / "doc1.pdf").write_text("x")
    (raw / "_conferir" / "subpasta" / "doc2.jpg").write_text("x")
    (raw / "andre" / "holerites" / "holerite.pdf").write_text("x")

    arquivos = varrer_arquivos_inbox(raw, abrangente=False)

    nomes = sorted(a.name for a in arquivos)
    assert nomes == ["doc1.pdf", "doc2.jpg"]


def test_varredura_abrangente_inclui_subpastas(tmp_path):
    raw = tmp_path / "raw"
    (raw / "_classificar").mkdir(parents=True)
    (raw / "andre" / "holerites").mkdir(parents=True)
    (raw / "originais").mkdir(parents=True)
    (raw / "_envelopes").mkdir(parents=True)
    (raw / "_classificar" / "doc1.pdf").write_text("x")
    (raw / "andre" / "holerites" / "holerite.pdf").write_text("x")
    (raw / "originais" / "preservado.pdf").write_text("x")
    (raw / "_envelopes" / "envelope.pdf").write_text("x")

    arquivos = varrer_arquivos_inbox(raw, abrangente=True)

    nomes = sorted(a.name for a in arquivos)
    assert nomes == ["doc1.pdf", "holerite.pdf"]


def test_extensao_invalida_e_ignorada(tmp_path):
    raw = tmp_path / "raw"
    (raw / "_classificar").mkdir(parents=True)
    (raw / "_classificar" / "valido.pdf").write_text("x")
    (raw / "_classificar" / "ignorado.zip").write_text("x")

    arquivos = varrer_arquivos_inbox(raw, abrangente=False)

    nomes = [a.name for a in arquivos]
    assert "valido.pdf" in nomes
    assert "ignorado.zip" not in nomes


def test_mapear_documentos_separa_com_e_sem_aresta(tmp_path):
    db = tmp_path / "grafo.sqlite"
    _criar_grafo(
        db,
        [
            {
                "id": 10,
                "meta": {"arquivo_origem": "data/raw/_classificar/com_aresta.pdf"},
                "tem_aresta": True,
            },
            {
                "id": 11,
                "meta": {"arquivo_origem": "data/raw/_classificar/sem_aresta.pdf"},
                "tem_aresta": False,
            },
        ],
    )

    mapa = mapear_documentos_no_grafo(db)

    assert mapa["data/raw/_classificar/com_aresta.pdf"]["tem_aresta"] is True
    assert mapa["data/raw/_classificar/sem_aresta.pdf"]["tem_aresta"] is False


def test_classificar_distribui_em_quatro_estados(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw"
    (raw / "_classificar").mkdir(parents=True)
    integrado = raw / "_classificar" / "integrado.pdf"
    catalogado = raw / "_classificar" / "catalogado.pdf"
    recente = raw / "_classificar" / "recente.pdf"
    antigo = raw / "_classificar" / "antigo.pdf"
    for p in (integrado, catalogado, recente, antigo):
        p.write_text("x")
    # antigo vira orfao antigo: mtime 48h atras
    horas_48 = time.time() - 48 * 3600
    os.utime(antigo, (horas_48, horas_48))

    # Aponta RAIZ_REPO para tmp_path para que normalizacao bata
    monkeypatch.setattr("src.intake.anti_orfao.RAIZ_REPO", tmp_path)

    mapa = {
        "data/raw/_classificar/integrado.pdf": {"doc_id": 1, "tem_aresta": True},
        "data/raw/_classificar/catalogado.pdf": {"doc_id": 2, "tem_aresta": False},
    }
    arquivos = [integrado, catalogado, recente, antigo]

    c = classificar(arquivos, mapa, threshold_horas=24)

    assert integrado in c.integrado
    assert catalogado in c.catalogado_orfao
    assert recente in c.orfao_total
    assert antigo in c.orfao_total_antigo


def test_relatorio_md_contem_secoes_relevantes(tmp_path):
    saida = tmp_path / "orfaos.md"
    arq_a = tmp_path / "a.pdf"
    arq_b = tmp_path / "b.pdf"
    arq_a.write_text("x")
    arq_b.write_text("x")
    c = Classificacao(integrado=[arq_a], orfao_total_antigo=[arq_b])

    gerar_relatorio(c, saida)

    conteúdo = saida.read_text(encoding="utf-8")
    assert "# Relatório Anti-Órfão" in conteúdo
    assert "Integrados" in conteúdo
    assert "Órfãos antigos" in conteúdo
    assert "b.pdf" in conteúdo


def test_main_strict_retorna_1_se_ha_orfaos_antigos(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw"
    db = tmp_path / "grafo.sqlite"
    saida = tmp_path / "orfaos.md"
    (raw / "_classificar").mkdir(parents=True)
    antigo = raw / "_classificar" / "antigo.pdf"
    antigo.write_text("x")
    horas_48 = time.time() - 48 * 3600
    os.utime(antigo, (horas_48, horas_48))

    monkeypatch.setattr("src.intake.anti_orfao.RAIZ_REPO", tmp_path)
    _criar_grafo(db, [])

    rc = main(
        [
            "--strict",
            "--threshold-horas",
            "24",
            "--db",
            str(db),
            "--raw",
            str(raw),
            "--saida",
            str(saida),
        ]
    )

    assert rc == 1


def test_main_observador_retorna_0_mesmo_com_orfaos(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw"
    db = tmp_path / "grafo.sqlite"
    saida = tmp_path / "orfaos.md"
    (raw / "_classificar").mkdir(parents=True)
    antigo = raw / "_classificar" / "antigo.pdf"
    antigo.write_text("x")
    horas_48 = time.time() - 48 * 3600
    os.utime(antigo, (horas_48, horas_48))

    monkeypatch.setattr("src.intake.anti_orfao.RAIZ_REPO", tmp_path)
    _criar_grafo(db, [])

    rc = main(
        [
            "--threshold-horas",
            "24",
            "--db",
            str(db),
            "--raw",
            str(raw),
            "--saida",
            str(saida),
        ]
    )

    assert rc == 0


# "O que entra e fica registrado vira luz." -- principio do anti-orfao
