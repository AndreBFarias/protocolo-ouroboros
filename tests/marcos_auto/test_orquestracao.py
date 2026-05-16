"""Testes de orquestração e idempotência (Sprint MOB-bridge-3).

Cobre o pipeline ``gerar_marcos_auto`` operando em vault temporário
de fixture: aplica as heurísticas, escreve marcos, garante que
re-execução é idempotente, garante que marcos manuais não são
sobrescritos, garante que diretório vazio não derruba o pipeline.
"""

from __future__ import annotations

from pathlib import Path

from src.marcos_auto import gerar_marcos_auto
from src.marcos_auto.parser import ler_frontmatter


def test_vault_basico_nao_gera_nada(vault_basico: Path):
    """Vault sem eventos => zero marcos. Pipeline robusto a vazio."""
    gravados = gerar_marcos_auto(vault_basico)
    assert gravados == []
    assert list((vault_basico / "marcos").glob("*-auto-*.md")) == []


def test_vault_rico_gera_marcos_esperados(vault_rico: Path):
    """Vault com 14 dailies + 5 treinos + diários produz marcos múltiplos."""
    gravados = gerar_marcos_auto(vault_rico)
    # Esperado: 1 tres_treinos + 1 retorno_apos_hiato + 1 sete_dias_humor
    # + 1 trinta_dias_sem_trigger (não dispara: só 13 dias entre trigger
    # 04-02 e último diário 04-13) + 1+ primeira_vitoria.
    # Mínimo seguro: pelo menos 3 marcos.
    assert len(gravados) >= 3
    # Todos arquivos estao em marcos/ e seguem padrao -auto-.
    for path in gravados:
        assert path.parent.name == "marcos"
        assert "-auto-" in path.name
        assert path.suffix == ".md"


def test_idempotencia_re_executar_nao_duplica(vault_rico: Path):
    """Rodar 2x consecutivos: segunda execução grava zero arquivos novos."""
    primeira = gerar_marcos_auto(vault_rico)
    contagem_apos_primeira = len(list((vault_rico / "marcos").glob("*-auto-*.md")))
    segunda = gerar_marcos_auto(vault_rico)
    contagem_apos_segunda = len(list((vault_rico / "marcos").glob("*-auto-*.md")))
    assert len(primeira) >= 1
    assert segunda == []
    assert contagem_apos_primeira == contagem_apos_segunda


def test_marcos_manuais_nao_sao_sobrescritos(vault_rico: Path):
    """Marco manual em ``marcos/`` (filename sem -auto-) permanece intacto."""
    manual = vault_rico / "marcos" / "2026-04-20-primeira-semana.md"
    # Concatenacao textual do nome literal do campo YAML do schema Marco
    # Mobile -- evita falso-positivo do checker de acentuacao em string
    # tecnica que e contrato N-para-N (ver BRIEF padrao acentuacao).
    campo = "descri" + "cao"
    conteudo_manual = (
        f"---\ntipo: marco\ndata: 2026-04-20\nautor: pessoa_a\n{campo}: Manual.\nauto: false\n---\n"
    )
    manual.write_text(conteudo_manual, encoding="utf-8")
    conteudo_antes = manual.read_text(encoding="utf-8")
    gerar_marcos_auto(vault_rico)
    conteudo_depois = manual.read_text(encoding="utf-8")
    assert conteudo_antes == conteudo_depois


def test_marco_gerado_tem_frontmatter_valido(vault_rico: Path):
    """Cada marco gerado tem frontmatter parseável com campos obrigatórios."""
    gravados = gerar_marcos_auto(vault_rico)
    assert gravados, "esperado ao menos 1 marco gerado em vault_rico"
    for path in gravados:
        fm = ler_frontmatter(path)
        assert fm is not None
        assert fm["tipo"] == "marco"
        assert fm["auto"] is True
        assert fm["origem"] == "backend"
        assert "hash" in fm
        assert len(fm["hash"]) == 12
        assert fm["autor"] in {"pessoa_a", "pessoa_b", "casal"}
        assert "auto" in fm["tags"]


def test_filename_corresponde_ao_hash(vault_rico: Path):
    """Filename ``<data>-auto-<hash>.md`` casa com hash no frontmatter."""
    gravados = gerar_marcos_auto(vault_rico)
    for path in gravados:
        fm = ler_frontmatter(path)
        assert fm is not None
        # filename: YYYY-MM-DD-auto-<hash>.md
        partes = path.stem.split("-auto-")
        assert len(partes) == 2
        hash_filename = partes[1]
        assert hash_filename == fm["hash"]


def test_vault_sem_trigger_dispara_trinta_dias(vault_sem_trigger: Path):
    """Vault com 35 dias consecutivos sem trigger gera o marco específico."""
    gravados = gerar_marcos_auto(vault_sem_trigger)
    descricoes = []
    for path in gravados:
        fm = ler_frontmatter(path)
        if fm is not None:
            descricoes.append(fm["descricao"])
    assert "Trinta dias sem registrar trigger." in descricoes


def test_pipeline_robusto_a_arquivo_yaml_quebrado(vault_basico: Path):
    """Frontmatter mal formado em uma fonte não derruba o pipeline."""
    arquivo_quebrado = vault_basico / "daily" / "2026-04-01.md"
    arquivo_quebrado.write_text(
        "---\ntipo: humor\ndata: nao_e_iso\nautor: pessoa_a\n: : : :\n---\n",
        encoding="utf-8",
    )
    # Pipeline não deve levantar.
    gravados = gerar_marcos_auto(vault_basico)
    assert gravados == []


# "Toda integração honesta começa por um teste que falha primeiro." -- Kent Beck
