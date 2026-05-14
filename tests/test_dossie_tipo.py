"""Testes do CLI canonico de auditoria por tipo documental (dossie_tipo.py).

Cobre as 6 fases do ritual descrito em `docs/CICLO_GRADUACAO_OPERACIONAL.md`:

1. abrir cria estrutura idempotente
2. prova-artesanal cria stub no formato canonico
3. comparar com prova vazia retorna codigo de erro (placeholder PREENCHER)  # noqa: accent
4. comparar com prova + ETL output OK retorna GRADUADO_OK
5. comparar com divergencia gera relatorio MD  # noqa: accent
6. graduar-se-pronto transiciona corretamente PENDENTE -> CALIBRANDO -> GRADUADO
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import dossie_tipo


@pytest.fixture
def isolar_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redireciona DIR_DOSSIES e PATH_GRADUACAO para tmp_path."""
    dossies = tmp_path / "dossies"
    grad = tmp_path / "graduacao_tipos.json"
    cache = tmp_path / "opus_cache"
    cache.mkdir()
    monkeypatch.setattr(dossie_tipo, "DIR_DOSSIES", dossies)
    monkeypatch.setattr(dossie_tipo, "PATH_GRADUACAO", grad)
    monkeypatch.setattr(dossie_tipo, "DIR_OPUS_CACHE", cache)
    monkeypatch.setattr(dossie_tipo, "PATH_GRAFO", tmp_path / "nao_existe.sqlite")
    return tmp_path


def test_abrir_cria_estrutura_idempotente(isolar_paths: Path) -> None:
    rc = dossie_tipo.cmd_abrir("test_tipo")
    assert rc == 0
    d = dossie_tipo._dir_tipo("test_tipo")
    assert (d / "estado.json").exists()
    assert (d / "README.md").exists()
    assert (d / "amostras").is_dir()
    assert (d / "provas_artesanais").is_dir()
    # Idempotencia
    rc2 = dossie_tipo.cmd_abrir("test_tipo")
    assert rc2 == 0


def test_prova_artesanal_cria_stub_canonico(isolar_paths: Path) -> None:
    rc = dossie_tipo.cmd_prova_artesanal("test_tipo", "a" * 64)
    assert rc == 0
    stub = (
        dossie_tipo._dir_tipo("test_tipo")
        / "provas_artesanais"
        / f"{'a' * 64}.json"
    )
    assert stub.exists()
    dados = json.loads(stub.read_text())
    assert dados["sha256"] == "a" * 64
    assert dados["lido_por"] == "opus_4_7_multimodal"
    assert "PREENCHER" in str(dados["campos_canonicos"])


def test_prova_artesanal_nao_sobrescreve(isolar_paths: Path) -> None:
    dossie_tipo.cmd_prova_artesanal("test_tipo", "b" * 64)
    rc = dossie_tipo.cmd_prova_artesanal("test_tipo", "b" * 64)
    assert rc == 1  # ja existe


def test_comparar_falha_com_placeholder(isolar_paths: Path) -> None:
    dossie_tipo.cmd_prova_artesanal("test_tipo", "c" * 64)
    rc = dossie_tipo.cmd_comparar("test_tipo", "c" * 64)
    assert rc == 2  # placeholder PREENCHER detectado


def test_comparar_insuficiente_sem_etl(isolar_paths: Path) -> None:
    sha = "d" * 64
    dossie_tipo.cmd_prova_artesanal("test_tipo", sha)
    # Preenche prova
    p = dossie_tipo._dir_tipo("test_tipo") / "provas_artesanais" / f"{sha}.json"
    payload = json.loads(p.read_text())
    payload["campos_canonicos"] = {"valor": 100.0}
    p.write_text(json.dumps(payload))
    # ETL nao tem cache nem grafo -> INSUFICIENTE  # noqa: accent
    rc = dossie_tipo.cmd_comparar("test_tipo", sha)
    assert rc == 1  # nao-zero (INSUFICIENTE/DIVERGENTE)  # noqa: accent


def test_comparar_graduado_ok(isolar_paths: Path) -> None:
    sha = "e" * 64
    # Cria prova preenchida
    dossie_tipo.cmd_prova_artesanal("test_tipo", sha)
    p = dossie_tipo._dir_tipo("test_tipo") / "provas_artesanais" / f"{sha}.json"
    payload = json.loads(p.read_text())
    payload["campos_canonicos"] = {"valor": 50.0, "data": "2026-05-13"}
    p.write_text(json.dumps(payload))
    # Cria output do ETL no cache
    cache = dossie_tipo.DIR_OPUS_CACHE / f"{sha}.json"
    cache.write_text(json.dumps({"valor": 50.0, "data": "2026-05-13"}))

    rc = dossie_tipo.cmd_comparar("test_tipo", sha)
    assert rc == 0
    estado = dossie_tipo._ler_estado("test_tipo")
    assert sha in estado["amostras_ok"]


def test_comparar_divergente_gera_relatorio(isolar_paths: Path) -> None:
    sha = "f" * 64
    dossie_tipo.cmd_prova_artesanal("test_tipo", sha)
    p = dossie_tipo._dir_tipo("test_tipo") / "provas_artesanais" / f"{sha}.json"
    payload = json.loads(p.read_text())
    payload["campos_canonicos"] = {"valor": 100.0, "data": "2026-05-13"}
    p.write_text(json.dumps(payload))
    cache = dossie_tipo.DIR_OPUS_CACHE / f"{sha}.json"
    cache.write_text(json.dumps({"valor": 999.99, "data": "2026-05-13"}))

    rc = dossie_tipo.cmd_comparar("test_tipo", sha)
    assert rc == 1
    estado = dossie_tipo._ler_estado("test_tipo")
    assert sha in estado["amostras_divergentes"]
    # Relatorio MD gerado  # noqa: accent
    divs = list(
        (dossie_tipo._dir_tipo("test_tipo") / "divergencias").glob("*.md")
    )
    assert len(divs) == 1
    md = divs[0].read_text()
    assert "valor_diverge" in md or "Divergencia" in md


def test_graduar_pendente_calibrando_graduado(isolar_paths: Path) -> None:
    sha1 = "1" * 64
    sha2 = "2" * 64
    # Estado inicial
    rc = dossie_tipo.cmd_graduar_se_pronto("test_tipo")
    assert rc == 0
    assert dossie_tipo._ler_estado("test_tipo")["status"] == dossie_tipo.STATUS_PENDENTE

    # Adiciona 1 amostra OK manualmente
    estado = dossie_tipo._ler_estado("test_tipo")
    estado["amostras_ok"].append(sha1)
    dossie_tipo._gravar_estado("test_tipo", estado)
    dossie_tipo.cmd_graduar_se_pronto("test_tipo")
    assert dossie_tipo._ler_estado("test_tipo")["status"] == dossie_tipo.STATUS_CALIBRANDO

    # Adiciona 2a amostra OK
    estado = dossie_tipo._ler_estado("test_tipo")
    estado["amostras_ok"].append(sha2)
    dossie_tipo._gravar_estado("test_tipo", estado)
    dossie_tipo.cmd_graduar_se_pronto("test_tipo")
    assert dossie_tipo._ler_estado("test_tipo")["status"] == dossie_tipo.STATUS_GRADUADO


def test_snapshot_global(isolar_paths: Path) -> None:
    # Cria 3 dossies em estados distintos
    dossie_tipo.cmd_abrir("tipo_a")
    dossie_tipo.cmd_abrir("tipo_b")
    estado_b = dossie_tipo._ler_estado("tipo_b")
    estado_b["amostras_ok"] = ["x" * 64, "y" * 64]
    estado_b["status"] = dossie_tipo.STATUS_GRADUADO
    dossie_tipo._gravar_estado("tipo_b", estado_b)

    rc = dossie_tipo.cmd_snapshot()
    assert rc == 0
    snap = json.loads(dossie_tipo.PATH_GRADUACAO.read_text())
    assert snap["totais"][dossie_tipo.STATUS_GRADUADO] >= 1
    assert "tipo_a" in snap["tipos"]
    assert snap["tipos"]["tipo_b"]["status"] == dossie_tipo.STATUS_GRADUADO


def test_listar_tipos_funciona(isolar_paths: Path, capsys) -> None:
    rc = dossie_tipo.cmd_listar_tipos()
    assert rc == 0
    out = capsys.readouterr().out
    assert "Tipos canonicos" in out


def test_cli_flag_alternativa(isolar_paths: Path) -> None:
    # Sintaxe --abrir TIPO
    rc = dossie_tipo.main(["--abrir", "test_flag"])
    assert rc == 0
    assert dossie_tipo._dir_tipo("test_flag").exists()


# ---------------------------------------------------------------------------
# Sprint META-FIX-DOSSIE-TIPO-BUGS-2026-05-13: regressao dos 2 bugs detectados  # noqa: accent
# na sessao 2026-05-13 (chave_canonica inexistente + heuristica chave unica).  # noqa: accent
# ---------------------------------------------------------------------------


def test_carregar_etl_output_fallback_grafo_nao_crasha(
    isolar_paths: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug 1: grafo real tem coluna `nome_canonico`, não `chave_canonica`.

    Antes do fix, `_carregar_etl_output` crashava com OperationalError quando
    havia cache OCR ausente E grafo presente. Apos fix, deve retornar None
    silenciosamente (cache miss + grafo sem match) sem crash.
    """
    import sqlite3

    # Cria grafo SQLite com schema REAL (sem chave_canonica)
    grafo_path = isolar_paths / "grafo_real.sqlite"
    con = sqlite3.connect(grafo_path)
    con.execute(
        "CREATE TABLE node (id TEXT PRIMARY KEY, tipo TEXT, nome_canonico TEXT, "
        "aliases TEXT, metadata TEXT, created_at TEXT, updated_at TEXT)"
    )
    con.commit()
    con.close()
    monkeypatch.setattr(dossie_tipo, "PATH_GRAFO", grafo_path)

    # Sha inexistente -- fallback deve retornar None sem crash
    r = dossie_tipo._carregar_etl_output("f" * 64)
    assert r is None


def test_carregar_etl_output_grafo_encontra_via_metadata(
    isolar_paths: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defesa em camadas: busca em `nome_canonico` OR `metadata` ambos (padrao (n))."""
    import sqlite3

    grafo_path = isolar_paths / "grafo_match.sqlite"
    con = sqlite3.connect(grafo_path)
    con.execute(
        "CREATE TABLE node (id TEXT PRIMARY KEY, tipo TEXT, nome_canonico TEXT, "
        "aliases TEXT, metadata TEXT, created_at TEXT, updated_at TEXT)"
    )
    sha = "9" * 64
    con.execute(
        "INSERT INTO node VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "node1",
            "documento",
            "HOLERITE|G4F|2025-05",
            "[]",
            json.dumps({"sha256": sha, "valor": 4200.5}),
            "2026-01-01",
            "2026-01-01",
        ),
    )
    con.commit()
    con.close()
    monkeypatch.setattr(dossie_tipo, "PATH_GRAFO", grafo_path)

    r = dossie_tipo._carregar_etl_output(sha)
    assert r is not None
    assert r.get("sha256") == sha
    assert r.get("valor") == 4200.5


def test_listar_candidatos_pix_acha_whatsapp_images(
    isolar_paths: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Bug 2: heuristica antiga split('_')[0] retornava 'comprovante' para
    tipo `comprovante_pix_foto`, que não bate com nomes reais de fotos PIX
    (geralmente `WhatsApp Image ...jpeg`). Fix usa mapa CHAVES_BUSCA explicito.
    """
    # Cria inbox isolado com fotos cujo nome NAO contem 'comprovante'  # noqa: accent
    inbox = isolar_paths / "inbox"
    inbox.mkdir()
    (inbox / "WhatsApp Image 2026-05-13 at 09.32.30.jpeg").write_bytes(b"fake")
    (inbox / "WhatsApp Image 2026-05-13 at 11.25.02.jpeg").write_bytes(b"fake2")
    raw = isolar_paths / "raw"
    raw.mkdir()
    monkeypatch.setattr(dossie_tipo, "_RAIZ_REPO", isolar_paths)

    rc = dossie_tipo.cmd_listar_candidatos("comprovante_pix_foto")
    assert rc == 0
    out = capsys.readouterr().out
    # Deve listar 2 candidatos via chave "whatsapp image" do CHAVES_BUSCA
    assert "Candidatos para tipo `comprovante_pix_foto`" in out
    assert ": 2" in out


def test_listar_candidatos_tipo_nao_mapeado_usa_fallback(
    isolar_paths: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Retrocompatibilidade (padrao (o)): tipo sem entrada em CHAVES_BUSCA
    cai no default split('_')[0]."""
    inbox = isolar_paths / "inbox"
    inbox.mkdir()
    (inbox / "TIPONOVO_amostra.pdf").write_bytes(b"fake")
    monkeypatch.setattr(dossie_tipo, "_RAIZ_REPO", isolar_paths)

    rc = dossie_tipo.cmd_listar_candidatos("tiponovo_subtipo")
    assert rc == 0
    out = capsys.readouterr().out
    assert ": 1" in out


# "Teste é como ritual: sem ele, ciclo só existe no papel." -- princípio do teste vivo
