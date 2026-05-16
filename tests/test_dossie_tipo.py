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
    stub = dossie_tipo._dir_tipo("test_tipo") / "provas_artesanais" / f"{'a' * 64}.json"
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
    # Sprint FIX-REGREDINDO-SEMANTICA: novo schema usa divergencias_ativas.  # noqa: accent
    assert sha in estado["divergencias_ativas"]
    assert sha in estado["_historico_divergencias"]
    # Relatorio MD gerado  # noqa: accent
    divs = list((dossie_tipo._dir_tipo("test_tipo") / "divergencias").glob("*.md"))
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


# ---------------------------------------------------------------------------
# Sprint FIX-REGREDINDO-SEMANTICA-2026-05-15: schema novo separa divergencias  # noqa: accent
# ativas (esvazia ao revalidar OK) de historico (acumula sempre). REGREDINDO  # noqa: accent
# detecta divergencias ativas mesmo na primeira graduacao.  # noqa: accent
# ---------------------------------------------------------------------------


def test_migracao_idempotente_estado_legado(isolar_paths: Path) -> None:
    """Estado legado (`amostras_divergentes` acumulativo) migra para schema novo.

    Idempotente: aplicar migrador 2x produz mesmo resultado.
    """
    dossie_tipo.cmd_abrir("legado_tipo")
    sha_ok = "1" * 64
    sha_ja_revalidado = "2" * 64
    sha_ainda_diverge = "3" * 64

    # Simula estado legado: amostras_divergentes contém AMBOS (revalidado E não-revalidado)
    estado = dossie_tipo._ler_estado("legado_tipo")
    estado["amostras_ok"] = [sha_ok, sha_ja_revalidado]
    estado["amostras_divergentes"] = [sha_ja_revalidado, sha_ainda_diverge]
    # Remove campos novos para forcar migracao  # noqa: accent
    estado.pop("divergencias_ativas", None)
    estado.pop("_historico_divergencias", None)
    dossie_tipo._gravar_estado("legado_tipo", estado)

    # Forca releitura via _ler_estado (que chama _migrar_estado_schema)
    estado_migrado = dossie_tipo._ler_estado("legado_tipo")
    assert "amostras_divergentes" not in estado_migrado
    assert estado_migrado["_historico_divergencias"] == [sha_ja_revalidado, sha_ainda_diverge]
    # divergencias_ativas = amostras_divergentes - amostras_ok
    assert estado_migrado["divergencias_ativas"] == [sha_ainda_diverge]

    # Idempotencia: roda migrador de novo
    estado_2 = dossie_tipo._migrar_estado_schema(estado_migrado)
    assert estado_2 == estado_migrado


def test_revalidar_ok_remove_de_divergencias_ativas(isolar_paths: Path) -> None:
    """Amostra que divergiu, ao revalidar OK, sai de `divergencias_ativas`
    mas permanece em `_historico_divergencias` para auditoria."""
    sha = "a" * 64
    # 1. Comparacao divergente  # noqa: accent
    dossie_tipo.cmd_prova_artesanal("teste_revalidar", sha)
    p = dossie_tipo._dir_tipo("teste_revalidar") / "provas_artesanais" / f"{sha}.json"
    payload = json.loads(p.read_text())
    payload["campos_canonicos"] = {"valor": 100.0}
    p.write_text(json.dumps(payload))
    cache = dossie_tipo.DIR_OPUS_CACHE / f"{sha}.json"
    cache.write_text(json.dumps({"valor": 999.99}))
    dossie_tipo.cmd_comparar("teste_revalidar", sha)
    estado = dossie_tipo._ler_estado("teste_revalidar")
    assert sha in estado["divergencias_ativas"]
    assert sha in estado["_historico_divergencias"]

    # 2. Revalidacao OK (ETL corrigido)  # noqa: accent
    cache.write_text(json.dumps({"valor": 100.0}))
    dossie_tipo.cmd_comparar("teste_revalidar", sha)
    estado = dossie_tipo._ler_estado("teste_revalidar")
    assert sha in estado["amostras_ok"]
    assert sha not in estado["divergencias_ativas"]  # saiu
    assert sha in estado["_historico_divergencias"]  # mantem historico


def test_graduar_dispara_regredindo_na_primeira_vez(isolar_paths: Path) -> None:
    """Bug original: REGREDINDO so disparava se status_antes == GRADUADO.

    Agora dispara mesmo na primeira transicao PENDENTE -> GRADUADO se ha
    `divergencias_ativas` (regra (k) fix da auditoria 2026-05-15).
    """
    dossie_tipo._garantir_estrutura_dossie("regredido_primeira")
    estado = dossie_tipo._ler_estado("regredido_primeira")
    estado["amostras_ok"] = ["a" * 64, "b" * 64]  # suficiente para graduar
    estado["divergencias_ativas"] = ["c" * 64]  # mas ha divergencia ativa  # noqa: accent
    dossie_tipo._gravar_estado("regredido_primeira", estado)

    rc = dossie_tipo.cmd_graduar_se_pronto("regredido_primeira")
    assert rc == 0
    final = dossie_tipo._ler_estado("regredido_primeira")
    assert final["status"] == dossie_tipo.STATUS_REGREDINDO, (
        f"esperado REGREDINDO, veio {final['status']}"
    )


def test_graduar_limpo_nao_dispara_regredindo(isolar_paths: Path) -> None:
    """Graduacao sem divergencias_ativas (mesmo com historico) marca GRADUADO."""
    dossie_tipo._garantir_estrutura_dossie("graduado_limpo")
    estado = dossie_tipo._ler_estado("graduado_limpo")
    estado["amostras_ok"] = ["a" * 64, "b" * 64]
    estado["divergencias_ativas"] = []  # sem divergencias ativas  # noqa: accent
    estado["_historico_divergencias"] = ["c" * 64]  # historico nao influi  # noqa: accent
    dossie_tipo._gravar_estado("graduado_limpo", estado)

    dossie_tipo.cmd_graduar_se_pronto("graduado_limpo")
    final = dossie_tipo._ler_estado("graduado_limpo")
    assert final["status"] == dossie_tipo.STATUS_GRADUADO, (
        f"esperado GRADUADO, veio {final['status']}"
    )


# ---------------------------------------------------------------------------
# Sprint META-TIPOS-ALIAS-BIDIRECIONAL-2026-05-15: resolve cisma entre  # noqa: accent
# `tipos_documento.yaml` (intake) e dossiê/grafo via campo `aliases_graduacao`.  # noqa: accent
# ---------------------------------------------------------------------------


@pytest.fixture
def yaml_com_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cria YAML sintético com aliases para testes isolados."""
    yaml_path = tmp_path / "tipos.yaml"
    yaml_path.write_text(
        "tipos:\n"
        "  - id: nfce_consumidor_eletronica\n"
        '    aliases_graduacao: ["nfce_modelo_65"]\n'
        "  - id: holerite\n"
        "    aliases_graduacao: []\n"
        "  - id: dirpf_retif\n",  # sem campo aliases_graduacao
        encoding="utf-8",
    )
    monkeypatch.setattr(dossie_tipo, "PATH_TIPOS_YAML", yaml_path)
    dossie_tipo._aliases_map.cache_clear()
    yield yaml_path
    dossie_tipo._aliases_map.cache_clear()


def test_aliases_map_le_yaml(isolar_paths: Path, yaml_com_alias: Path) -> None:
    """`_aliases_map()` retorna 2 dicts: alias->canonico e canonico->aliases."""
    a2c, c2a = dossie_tipo._aliases_map()
    assert a2c == {"nfce_modelo_65": "nfce_consumidor_eletronica"}
    assert c2a == {
        "nfce_consumidor_eletronica": ["nfce_modelo_65"],
        "holerite": [],
        "dirpf_retif": [],
    }


def test_resolver_canonico_alias_e_canonico(isolar_paths: Path, yaml_com_alias: Path) -> None:
    """`_resolver_canonico` mapeia alias -> canonico e preserva canonico/desconhecido."""  # noqa: accent
    canonico = "nfce_consumidor_eletronica"
    assert dossie_tipo._resolver_canonico("nfce_modelo_65") == canonico
    assert dossie_tipo._resolver_canonico(canonico) == canonico
    assert dossie_tipo._resolver_canonico("tipo_inexistente") == "tipo_inexistente"


def test_dir_tipo_alias_e_canonico_resolvem_mesmo_dossie(
    isolar_paths: Path, yaml_com_alias: Path
) -> None:
    """`_dir_tipo` aceita alias OU canonico e devolve o mesmo dossie fisico
    quando este existe sob qualquer dos nomes (preserva legado)."""  # noqa: accent
    # Simula dossie historico em path com nome de ALIAS (anterior a esta sprint):  # noqa: accent
    # pre-criamos o diretorio manualmente para nao acionar logica de criacao.  # noqa: accent
    legacy_dir = dossie_tipo.DIR_DOSSIES / "nfce_modelo_65"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "estado.json").write_text('{"tipo":"nfce","status":"PENDENTE"}')

    # Ambas as entradas resolvem para o mesmo path fisico (o legacy):  # noqa: accent
    dir_via_alias = dossie_tipo._dir_tipo("nfce_modelo_65")
    dir_via_canonico = dossie_tipo._dir_tipo("nfce_consumidor_eletronica")
    assert dir_via_alias == dir_via_canonico
    assert dir_via_alias.name == "nfce_modelo_65"  # preserva nome fisico legado  # noqa: accent


def test_snapshot_usa_chave_canonica_com_dossie_path(
    isolar_paths: Path, yaml_com_alias: Path
) -> None:
    """Snapshot agrega sob chave canonica do YAML (resolve alias). Campo
    `dossie_path` no value preserva o nome fisico do dossie no disco."""  # noqa: accent
    # Dossie legado com nome de alias (pre-existente, anterior a esta sprint).  # noqa: accent
    legacy_dir = dossie_tipo.DIR_DOSSIES / "nfce_modelo_65"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "estado.json").write_text(
        '{"tipo":"nfce_modelo_65","status":"GRADUADO","amostras_ok":["a"],'
        '"_historico_divergencias":[],"divergencias_ativas":[]}'
    )
    # Dossie criado com nome canonico (cenario novo).  # noqa: accent
    dossie_tipo._garantir_estrutura_dossie("holerite")

    dossie_tipo.cmd_snapshot()
    snap = json.loads(dossie_tipo.PATH_GRADUACAO.read_text())
    # nfce_modelo_65 (alias) agregado sob chave canonica:  # noqa: accent
    assert "nfce_consumidor_eletronica" in snap["tipos"]
    assert "nfce_modelo_65" not in snap["tipos"]
    assert snap["tipos"]["nfce_consumidor_eletronica"]["dossie_path"] == "nfce_modelo_65"
    # holerite (canonico) agregado sob seu proprio nome:  # noqa: accent
    assert "holerite" in snap["tipos"]
    assert snap["tipos"]["holerite"]["dossie_path"] == "holerite"


# "Teste é como ritual: sem ele, ciclo só existe no papel." -- princípio do teste vivo
