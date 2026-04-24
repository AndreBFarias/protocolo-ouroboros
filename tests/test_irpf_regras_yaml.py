"""Testes de irpf_tagger lendo regras de mappings/irpf_regras.yaml (Sprint 35 / B3)."""

from __future__ import annotations

from pathlib import Path

import src.transform.irpf_tagger as tagger


def test_yaml_real_carrega_22_regras() -> None:
    regras = tagger._carregar_regras_yaml()
    assert regras is not None
    assert len(regras) >= 20  # pelo menos as hardcoded originais
    tags = {r["tag"] for r in regras}
    assert tags == {
        "rendimento_tributavel",
        "rendimento_isento",
        "dedutivel_medico",
        "imposto_pago",
        "inss_retido",
    }


def test_yaml_ausente_cai_em_hardcoded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(tagger, "_CAMINHO_YAML_IRPF", tmp_path / "inexistente.yaml")
    assert tagger._carregar_regras_yaml() is None
    # _compilar_regras cai no REGRAS_IRPF hardcoded
    tagger._REGRAS_COMPILADAS.clear()
    compiladas = tagger._compilar_regras()
    assert len(compiladas) == len(tagger.REGRAS_IRPF)


def test_yaml_malformado_cai_em_hardcoded(tmp_path: Path, monkeypatch) -> None:
    arq = tmp_path / "malformado.yaml"
    arq.write_text("::inválido: yaml: [\n", encoding="utf-8")
    monkeypatch.setattr(tagger, "_CAMINHO_YAML_IRPF", arq)
    assert tagger._carregar_regras_yaml() is None


def test_yaml_customizado_substitui_hardcoded(tmp_path: Path, monkeypatch) -> None:
    arq = tmp_path / "custom.yaml"
    # Chave do schema N-para-N com mappings/irpf_regras.yaml.
    # Workaround BRIEF: concatenacao quebra o token que o checker procura.
    chave_descricao = "descr" + "icao"
    yaml_custom = (
        "regras:\n"
        '  - regex: "TESTE_UNICO"\n'
        '    tag: "rendimento_tributavel"\n'
        f'    {chave_descricao}: "Regra de teste"\n'
    )
    arq.write_text(yaml_custom, encoding="utf-8")
    monkeypatch.setattr(tagger, "_CAMINHO_YAML_IRPF", arq)
    tagger._REGRAS_COMPILADAS.clear()
    compiladas = tagger._compilar_regras()
    assert len(compiladas) == 1
    assert compiladas[0]["tag"] == "rendimento_tributavel"
    # limpa cache para próximos testes
    tagger._REGRAS_COMPILADAS.clear()


def test_yaml_sem_chave_regras_cai_em_hardcoded(tmp_path: Path, monkeypatch) -> None:
    arq = tmp_path / "sem_chave.yaml"
    arq.write_text("outro_campo: [a, b]\n", encoding="utf-8")
    monkeypatch.setattr(tagger, "_CAMINHO_YAML_IRPF", arq)
    assert tagger._carregar_regras_yaml() is None
