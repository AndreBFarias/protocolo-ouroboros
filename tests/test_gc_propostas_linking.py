"""Testes do GC de propostas de linking (Sprint INFRA-LINKING-PROPOSTAS-GC).

Cobre:
  1. Classificação atual quando documento existe no grafo.
  2. Classificação obsoleta quando id_grafo sumiu do grafo.
  3. Indeterminada quando proposta não tem `id grafo` no corpo.
  4. Dry-run não move arquivos.
  5. mover_obsoletos preserva conteúdo dentro de _obsoletas/.
  6. Idempotência: re-rodar não move o que já está em _obsoletas/.
  7. Arquivos em _obsoletas/, _aprovadas/, _rejeitadas/ não são reprocessados.
  8. Colisão de nome no mesmo dia: sufixo .N preserva auditoria.
  9. Resumo conta cada categoria corretamente.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.gc_propostas_linking import (
    Classificacao,
    carregar_ids_documento,
    classificar,
    executar,
    extrair_id_grafo,
    listar_propostas,
    mover_obsoletos,
    resumir,
)
from src.graph.db import GrafoDB

# ============================================================================
# Fixtures
# ============================================================================


def _proposta_texto(id_grafo: int, nome_canonico: str = "doc_qualquer") -> str:
    """Gera corpo de proposta sintética com `id grafo` no formato canônico."""
    return (
        "---\n"
        f"id: doc{id_grafo}_conflito\n"
        "tipo: linking\n"
        "motivo: conflito\n"
        "status: aberta\n"
        "---\n"
        "\n"
        "# Conflito de linking documento -> transação\n"
        "\n"
        "## Documento\n"
        "\n"
        f"- id grafo: `{id_grafo}`\n"
        f"- nome_canonico: `{nome_canonico}`\n"
        "- tipo_documento: `boleto_servico`\n"
    )


@pytest.fixture
def pasta_propostas(tmp_path: Path) -> Path:
    """Cria pasta de propostas temporária com subdirs reservados."""
    pasta = tmp_path / "linking"
    pasta.mkdir()
    (pasta / "_obsoletas").mkdir()
    (pasta / "_aprovadas").mkdir()
    (pasta / "_rejeitadas").mkdir()
    return pasta


@pytest.fixture
def grafo_db(tmp_path: Path) -> Path:
    """Cria grafo SQLite com 2 documentos (ids 100, 101)."""
    caminho = tmp_path / "grafo.sqlite"
    db = GrafoDB(caminho)
    db.criar_schema()
    db.upsert_node("documento", "doc_vivo_a", metadata={"id_esperado": 100})
    db.upsert_node("documento", "doc_vivo_b", metadata={"id_esperado": 101})
    db.fechar()
    return caminho


# ============================================================================
# Testes
# ============================================================================


def test_extrair_id_grafo_formato_canonico() -> None:
    """Linha `- id grafo: \\`7422\\`` produz int 7422."""
    texto = _proposta_texto(7422)
    assert extrair_id_grafo(texto) == 7422


def test_extrair_id_grafo_sem_backticks() -> None:
    """Aceita também sem backticks."""
    texto = "## Documento\n\n- id grafo: 9999\n"
    assert extrair_id_grafo(texto) == 9999


def test_extrair_id_grafo_ausente_retorna_none() -> None:
    """Proposta sem `id grafo` no corpo devolve None."""
    texto = "---\nid: foo\n---\n# Sem id grafo aqui."
    assert extrair_id_grafo(texto) is None


def test_listar_propostas_ignora_subdirs(pasta_propostas: Path) -> None:
    """Subdiretórios reservados são ignorados; só .md na raiz."""
    (pasta_propostas / "0001_conflito.md").write_text(_proposta_texto(1), encoding="utf-8")
    (pasta_propostas / "_obsoletas" / "antigo.md").write_text("nada", encoding="utf-8")
    (pasta_propostas / "_aprovadas" / "old.md").write_text("nada", encoding="utf-8")
    (pasta_propostas / "README.txt").write_text("não md", encoding="utf-8")

    propostas = listar_propostas(pasta_propostas)
    assert len(propostas) == 1
    assert propostas[0].name == "0001_conflito.md"


def test_classificar_atual_quando_doc_existe(
    pasta_propostas: Path,
    grafo_db: Path,
) -> None:
    """id_grafo presente no grafo => `atual`."""
    arquivo = pasta_propostas / "0100_conflito.md"
    arquivo.write_text(_proposta_texto(100, "doc_vivo_a"), encoding="utf-8")

    ids_vivos = carregar_ids_documento(grafo_db)
    # Os ids reais são autoincrement; precisamos descobrir os ids do upsert.
    # No fixture criamos 2 docs -> ids 1 e 2.
    assert ids_vivos == {1, 2}

    # Refazemos a proposta apontando para id 1 (que existe no grafo).
    arquivo.write_text(_proposta_texto(1, "doc_vivo_a"), encoding="utf-8")
    resultado = classificar(listar_propostas(pasta_propostas), ids_vivos)
    assert len(resultado) == 1
    assert resultado[0].estado == "atual"
    assert resultado[0].id_grafo == 1


def test_classificar_obsoleto_quando_doc_sumiu(
    pasta_propostas: Path,
    grafo_db: Path,
) -> None:
    """id_grafo ausente do grafo => `obsoleto`."""
    arquivo = pasta_propostas / "9999_conflito.md"
    arquivo.write_text(_proposta_texto(9999), encoding="utf-8")

    ids_vivos = carregar_ids_documento(grafo_db)
    resultado = classificar([arquivo], ids_vivos)
    assert len(resultado) == 1
    assert resultado[0].estado == "obsoleto"
    assert resultado[0].id_grafo == 9999
    assert "ausente_no_grafo" in resultado[0].motivo


def test_classificar_indeterminado_sem_id_grafo(
    pasta_propostas: Path,
    grafo_db: Path,
) -> None:
    """Proposta sem `id grafo` => `indeterminado` (preserva)."""
    arquivo = pasta_propostas / "especial_apolice.md"
    arquivo.write_text("---\nid: foo\n---\n# Sem id grafo.", encoding="utf-8")

    ids_vivos = carregar_ids_documento(grafo_db)
    resultado = classificar([arquivo], ids_vivos)
    assert len(resultado) == 1
    assert resultado[0].estado == "indeterminado"
    assert resultado[0].id_grafo is None


def test_dry_run_nao_move_arquivos(
    pasta_propostas: Path,
    grafo_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """executar sem --mover-obsoletos deixa arquivos no lugar."""
    (pasta_propostas / "9999_conflito.md").write_text(
        _proposta_texto(9999), encoding="utf-8"
    )
    (pasta_propostas / "0001_conflito.md").write_text(
        _proposta_texto(1, "doc_vivo_a"), encoding="utf-8"
    )

    exit_code = executar([
        "--auditar-atual",
        "--pasta",
        str(pasta_propostas),
        "--db",
        str(grafo_db),
    ])
    assert exit_code == 0
    # Arquivos continuam onde estavam.
    assert (pasta_propostas / "9999_conflito.md").exists()
    assert (pasta_propostas / "0001_conflito.md").exists()
    assert not list((pasta_propostas / "_obsoletas").iterdir())

    saida = capsys.readouterr().out
    assert "obsoletas     : 1" in saida
    assert "atuais        : 1" in saida


def test_mover_obsoletos_preserva_conteudo(
    pasta_propostas: Path,
    grafo_db: Path,
) -> None:
    """mover_obsoletos copia conteúdo para _obsoletas/<data>-<nome>."""
    conteudo_original = _proposta_texto(9999, "doc_morto")
    origem = pasta_propostas / "9999_conflito.md"
    origem.write_text(conteudo_original, encoding="utf-8")

    ids_vivos = carregar_ids_documento(grafo_db)
    classificacoes = classificar(listar_propostas(pasta_propostas), ids_vivos)
    movidos = mover_obsoletos(classificacoes, pasta_propostas, hoje=date(2026, 5, 13))

    assert len(movidos) == 1
    destino = movidos[0][1]
    assert destino.exists()
    assert destino.read_text(encoding="utf-8") == conteudo_original
    assert destino.name == "2026-05-13-9999_conflito.md"
    # Origem foi removida.
    assert not origem.exists()


def test_idempotencia_re_rodar_nao_duplica(
    pasta_propostas: Path,
    grafo_db: Path,
) -> None:
    """Re-rodar mover_obsoletos não move o que já foi arquivado."""
    (pasta_propostas / "9999_conflito.md").write_text(
        _proposta_texto(9999), encoding="utf-8"
    )

    ids_vivos = carregar_ids_documento(grafo_db)

    # Primeira passagem: move o único obsoleto.
    cls1 = classificar(listar_propostas(pasta_propostas), ids_vivos)
    movidos1 = mover_obsoletos(cls1, pasta_propostas, hoje=date(2026, 5, 13))
    assert len(movidos1) == 1

    # Segunda passagem: pasta raiz vazia, nada para mover.
    cls2 = classificar(listar_propostas(pasta_propostas), ids_vivos)
    movidos2 = mover_obsoletos(cls2, pasta_propostas, hoje=date(2026, 5, 13))
    assert movidos2 == []

    # _obsoletas/ ainda tem exatamente 1 arquivo (não duplicou).
    arquivados = list((pasta_propostas / "_obsoletas").iterdir())
    assert len(arquivados) == 1


def test_arquivos_em_obsoletas_nao_reprocessados(
    pasta_propostas: Path,
    grafo_db: Path,
) -> None:
    """Arquivos já em _obsoletas/ não aparecem em listar_propostas."""
    (pasta_propostas / "_obsoletas" / "antigo_conflito.md").write_text(
        _proposta_texto(7777), encoding="utf-8"
    )
    (pasta_propostas / "0001_conflito.md").write_text(
        _proposta_texto(1, "doc_vivo_a"), encoding="utf-8"
    )

    propostas = listar_propostas(pasta_propostas)
    nomes = [p.name for p in propostas]
    assert "0001_conflito.md" in nomes
    assert "antigo_conflito.md" not in nomes
    assert len(propostas) == 1


def test_colisao_de_nome_no_mesmo_dia_usa_sufixo(
    pasta_propostas: Path,
    grafo_db: Path,
) -> None:
    """Quando _obsoletas/<data>-<nome>.md já existe, novo recebe sufixo .N."""
    # Pré-existente em _obsoletas/.
    pre = pasta_propostas / "_obsoletas" / "2026-05-13-9999_conflito.md"
    pre.write_text("conteúdo antigo distinto", encoding="utf-8")

    # Nova proposta obsoleta com mesmo nome base.
    origem = pasta_propostas / "9999_conflito.md"
    origem.write_text(_proposta_texto(9999, "novo_doc"), encoding="utf-8")

    ids_vivos = carregar_ids_documento(grafo_db)
    cls = classificar(listar_propostas(pasta_propostas), ids_vivos)
    movidos = mover_obsoletos(cls, pasta_propostas, hoje=date(2026, 5, 13))

    assert len(movidos) == 1
    destino = movidos[0][1]
    assert destino.name == "2026-05-13-9999_conflito.md.1"
    # Pré-existente preservado intacto.
    assert pre.read_text(encoding="utf-8") == "conteúdo antigo distinto"


def test_resumir_conta_categorias() -> None:
    """resumir devolve contagem por estado."""
    classificacoes = [
        Classificacao(Path("a"), "atual", 1, "ok"),
        Classificacao(Path("b"), "atual", 2, "ok"),
        Classificacao(Path("c"), "obsoleto", 3, "morto"),
        Classificacao(Path("d"), "indeterminado", None, "sem_id"),
    ]
    contagem = resumir(classificacoes)
    assert contagem == {"atual": 2, "obsoleto": 1, "indeterminado": 1}


def test_executar_mover_obsoletos_integracao(
    pasta_propostas: Path,
    grafo_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fluxo completo via CLI: --mover-obsoletos move e relata antes/depois."""
    (pasta_propostas / "0001_conflito.md").write_text(
        _proposta_texto(1, "doc_vivo_a"), encoding="utf-8"
    )
    (pasta_propostas / "9999_conflito.md").write_text(
        _proposta_texto(9999), encoding="utf-8"
    )
    (pasta_propostas / "8888_conflito.md").write_text(
        _proposta_texto(8888), encoding="utf-8"
    )

    exit_code = executar([
        "--mover-obsoletos",
        "--pasta",
        str(pasta_propostas),
        "--db",
        str(grafo_db),
    ])
    assert exit_code == 0

    # Raiz: ficou apenas o atual.
    sobrantes = listar_propostas(pasta_propostas)
    assert len(sobrantes) == 1
    assert sobrantes[0].name == "0001_conflito.md"

    # _obsoletas/: 2 arquivos arquivados.
    arquivados = list((pasta_propostas / "_obsoletas").iterdir())
    assert len(arquivados) == 2

    saida = capsys.readouterr().out
    assert "Movidas 2 propostas" in saida


# "Teste é o cinto que segura a calça do refactor." -- princípio do test-doutrinador
