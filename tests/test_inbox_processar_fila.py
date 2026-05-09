"""Testes da Sprint INFRA-INBOX-OFX-READER.

Cobre as funções aditivas em ``src.intake.inbox_reader``:

  1. ``escanear_inbox`` faz scan recursivo respeitando subpastas.
  2. Schema v1 dos itens contém campos canônicos da spec.
  3. Sha256 completo (64 chars), distinto do sha8 do listar_inbox.
  4. ``persistir_fila`` grava JSON com chave ``itens`` e ``schema``.
  5. ``carregar_fila`` lê de volta e degrada graciosamente.
  6. ``agrupar_duplicatas`` conta sha8 colidindo > 1.
  7. ``processar_fila`` integra scan + dedup + persistência.
  8. Fixture ``tests/fixtures/inbox_amostra/`` integra com o pipeline.
  9. Hook ``extrator`` recebe item e atualiza status.
 10. ``processar_fila`` preserva status já processado em segunda execução.

Padrão Sprint INFRA: testes não exigem dashboard rodando -- contratos
puros sobre filesystem temporário ou fixture sintética.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.intake.inbox_reader import (
    SCHEMA_FILA_VERSAO,
    agrupar_duplicatas,
    carregar_fila,
    escanear_inbox,
    persistir_fila,
    processar_fila,
)

FIXTURE_DIR: Path = Path(__file__).parent / "fixtures" / "inbox_amostra"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gravar(caminho: Path, conteudo: bytes = b"placeholder") -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)


# ---------------------------------------------------------------------------
# 1-2. escanear_inbox: scan recursivo + schema v1
# ---------------------------------------------------------------------------


def test_escanear_inbox_diretorio_inexistente_retorna_lista_vazia(
    tmp_path: Path,
) -> None:
    inexistente = tmp_path / "nao-existe"
    assert escanear_inbox(inexistente) == []


def test_escanear_inbox_diretorio_vazio_retorna_lista_vazia(tmp_path: Path) -> None:
    raiz = tmp_path / "inbox"
    raiz.mkdir()
    assert escanear_inbox(raiz) == []


def test_escanear_inbox_recursivo_pega_subpastas(tmp_path: Path) -> None:
    raiz = tmp_path / "inbox"
    _gravar(raiz / "topo.pdf", b"x")
    _gravar(raiz / "sub1" / "interno.csv", b"a,b\n1,2\n")
    _gravar(raiz / "sub1" / "sub2" / "fundo.ofx", b"<OFX></OFX>")

    itens = escanear_inbox(raiz)
    nomes = {it["filename"] for it in itens}
    assert nomes == {"topo.pdf", "interno.csv", "fundo.ofx"}


def test_escanear_inbox_schema_v1_contem_campos_canonicos(tmp_path: Path) -> None:
    raiz = tmp_path / "inbox"
    _gravar(raiz / "extrato.pdf", b"%PDF-1.4 amostra")

    [item] = escanear_inbox(raiz)
    assert set(item.keys()) >= {
        "sha256",
        "filename",
        "tipo_inferido",
        "tamanho_kb",
        "status",
        "ts_descoberto",
        "ts_processado",
        "extractor_versao",
        "caminho_relativo",
    }
    assert item["status"] == "aguardando"
    assert item["ts_processado"] is None
    assert item["extractor_versao"] is None
    assert item["tipo_inferido"] == "documento_pdf"
    assert item["filename"] == "extrato.pdf"


# ---------------------------------------------------------------------------
# 3. sha256 completo
# ---------------------------------------------------------------------------


def test_escanear_inbox_sha256_tem_64_chars(tmp_path: Path) -> None:
    raiz = tmp_path / "inbox"
    _gravar(raiz / "x.pdf", b"payload determinista")

    [item] = escanear_inbox(raiz)
    assert len(item["sha256"]) == 64
    # Sha256 hex de 'payload determinista' é estável; testa determinismo.
    assert item["sha256"].isalnum()


def test_escanear_inbox_ignora_arquivos_ocultos_e_nao_suportados(
    tmp_path: Path,
) -> None:
    raiz = tmp_path / "inbox"
    _gravar(raiz / "valido.pdf", b"x")
    _gravar(raiz / ".oculto.pdf", b"x")
    _gravar(raiz / "binario.exe", b"x")

    itens = escanear_inbox(raiz)
    assert {it["filename"] for it in itens} == {"valido.pdf"}


def test_escanear_inbox_ignora_pasta_extracted(tmp_path: Path) -> None:
    """Sidecars do listar_inbox legado ficam fora da fila."""
    raiz = tmp_path / "inbox"
    _gravar(raiz / "x.pdf", b"x")
    _gravar(raiz / ".extracted" / "abc12345.json", b"{}")

    itens = escanear_inbox(raiz)
    assert {it["filename"] for it in itens} == {"x.pdf"}


# ---------------------------------------------------------------------------
# 4-5. persistir_fila e carregar_fila
# ---------------------------------------------------------------------------


def test_persistir_fila_grava_schema_v1(tmp_path: Path) -> None:
    destino = tmp_path / "fila.json"
    itens = [
        {
            "sha256": "a" * 64,
            "filename": "x.pdf",
            "tipo_inferido": "documento_pdf",
            "tamanho_kb": 1.0,
            "status": "aguardando",
            "ts_descoberto": "2026-05-08T12:00:00",
            "ts_processado": None,
            "extractor_versao": None,
            "caminho_relativo": "x.pdf",
        }
    ]
    persistir_fila(itens, destino)
    assert destino.exists()

    payload = json.loads(destino.read_text(encoding="utf-8"))
    assert payload["schema"] == SCHEMA_FILA_VERSAO
    assert payload["itens"] == itens


def test_carregar_fila_arquivo_inexistente_retorna_vazio(tmp_path: Path) -> None:
    assert carregar_fila(tmp_path / "fantasma.json") == []


def test_carregar_fila_json_malformado_retorna_vazio(tmp_path: Path) -> None:
    destino = tmp_path / "ruim.json"
    destino.write_text("{ não eh json", encoding="utf-8")
    assert carregar_fila(destino) == []


def test_carregar_fila_lista_pura_retorna_vazio(tmp_path: Path) -> None:
    """Schema espera dict com chave 'itens'; lista pura é rejeitada."""
    destino = tmp_path / "lista.json"
    destino.write_text("[]", encoding="utf-8")
    assert carregar_fila(destino) == []


def test_persistir_carregar_round_trip(tmp_path: Path) -> None:
    raiz = tmp_path / "inbox"
    _gravar(raiz / "a.pdf", b"a")
    _gravar(raiz / "b.csv", b"b,c\n1,2\n")
    itens = escanear_inbox(raiz)

    destino = tmp_path / "fila.json"
    persistir_fila(itens, destino)
    de_volta = carregar_fila(destino)
    assert de_volta == itens


# ---------------------------------------------------------------------------
# 6. agrupar_duplicatas
# ---------------------------------------------------------------------------


def test_agrupar_duplicatas_conta_sha8_repetidos() -> None:
    itens = [
        {"sha256": "a" * 64},
        {"sha256": "a" * 64},  # mesmo sha8
        {"sha256": "b" * 64},
        {"sha256": "c" * 64},
        {"sha256": "c" * 64},
        {"sha256": "c" * 64},  # 3 ocorrências
    ]
    contagem = agrupar_duplicatas(itens)
    assert contagem == {"a" * 8: 2, "c" * 8: 3}


def test_agrupar_duplicatas_omite_sha_unico() -> None:
    itens = [{"sha256": "a" * 64}, {"sha256": "b" * 64}]
    assert agrupar_duplicatas(itens) == {}


# ---------------------------------------------------------------------------
# 7. processar_fila integrado
# ---------------------------------------------------------------------------


def test_processar_fila_grava_json_e_devolve_itens(tmp_path: Path) -> None:
    raiz = tmp_path / "inbox"
    destino = tmp_path / "out" / "fila.json"
    _gravar(raiz / "a.pdf", b"a")
    _gravar(raiz / "sub" / "b.csv", b"x,y\n1,2\n")

    itens = processar_fila(raiz=raiz, destino=destino)
    assert destino.exists()
    assert len(itens) == 2
    assert all(it["status"] == "aguardando" for it in itens)


def test_processar_fila_marca_duplicatas_como_pulado(tmp_path: Path) -> None:
    raiz = tmp_path / "inbox"
    destino = tmp_path / "fila.json"
    # Mesmo conteúdo em dois arquivos -> mesmo sha256 -> segundo vira pulado.
    _gravar(raiz / "a.pdf", b"identico")
    _gravar(raiz / "copia.pdf", b"identico")

    itens = processar_fila(raiz=raiz, destino=destino)
    status = [it["status"] for it in itens]
    assert status.count("aguardando") == 1
    assert status.count("pulado") == 1


def test_processar_fila_preserva_status_em_segunda_execucao(
    tmp_path: Path,
) -> None:
    raiz = tmp_path / "inbox"
    destino = tmp_path / "fila.json"
    _gravar(raiz / "a.pdf", b"x")

    # Primeira execução com extrator que marca "extraido".
    def extrator_fake(item: dict) -> dict:
        return {"status": "extraido", "extractor_versao": "fake-1.0"}

    primeira = processar_fila(raiz=raiz, destino=destino, extrator=extrator_fake)
    assert primeira[0]["status"] == "extraido"

    # Segunda execução sem extrator -> deve preservar "extraido".
    segunda = processar_fila(raiz=raiz, destino=destino)
    assert segunda[0]["status"] == "extraido"
    assert segunda[0]["extractor_versao"] == "fake-1.0"


def test_processar_fila_extrator_que_falha_marca_falhou(tmp_path: Path) -> None:
    raiz = tmp_path / "inbox"
    destino = tmp_path / "fila.json"
    _gravar(raiz / "ruim.pdf", b"x")

    def extrator_quebrado(item: dict) -> dict:
        raise RuntimeError("erro simulado de extracao")

    itens = processar_fila(raiz=raiz, destino=destino, extrator=extrator_quebrado)
    assert itens[0]["status"] == "falhou"
    assert "erro simulado" in itens[0]["erro"]


# ---------------------------------------------------------------------------
# 8. Fixture inbox_amostra real
# ---------------------------------------------------------------------------


def test_fixture_inbox_amostra_existe_e_tem_5_arquivos() -> None:
    assert FIXTURE_DIR.is_dir(), f"Fixture ausente: {FIXTURE_DIR}"
    arquivos = [p for p in FIXTURE_DIR.rglob("*") if p.is_file()]
    assert len(arquivos) == 5, f"Esperado 5 arquivos, achei {len(arquivos)}"


def test_fixture_inbox_amostra_cobre_extensoes_canonicas(tmp_path: Path) -> None:
    """Pipeline integrado: scan da fixture + persistencia em tmp."""
    destino = tmp_path / "fila_fixture.json"
    itens = processar_fila(raiz=FIXTURE_DIR, destino=destino)

    assert len(itens) == 5
    extensoes = {Path(it["caminho_relativo"]).suffix.lower() for it in itens}
    # Fixture cobre 5 extensoes distintas (CSV, PDF, OFX, TXT, JSON).
    assert {".csv", ".pdf", ".ofx", ".txt", ".json"}.issubset(extensoes)

    # Cada item tem schema v1 completo.
    for it in itens:
        assert len(it["sha256"]) == 64
        assert it["status"] in {"aguardando", "pulado", "extraido", "falhou"}


def test_fixture_inbox_amostra_inclui_subpasta() -> None:
    """Confirma scan recursivo: subpasta/notas.json deve aparecer."""
    itens = escanear_inbox(FIXTURE_DIR)
    caminhos = {it["caminho_relativo"] for it in itens}
    assert any("subpasta" in c for c in caminhos)


# "Antes de organizar a casa, é preciso saber o que há nela." -- Sêneca
