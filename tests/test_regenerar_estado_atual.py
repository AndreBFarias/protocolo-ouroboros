"""Testes do regenerador de métricas vivas do ESTADO_ATUAL.md.

Sprint META-ESTADO-ATUAL-AUTO (2026-05-15). Cobre: geração de bloco,
substituição idempotente entre markers, inserção quando markers ausentes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Import por path direto (evita conflito com nome de subpacote):
_SPEC = importlib.util.spec_from_file_location(
    "regenerar_estado_atual",
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "regenerar_estado_atual.py",
)
assert _SPEC and _SPEC.loader
regen = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(regen)


def test_gerar_bloco_metricas_contem_chaves_canonicas(monkeypatch) -> None:
    """O bloco gerado tem todas as métricas mandatórias."""
    # Mock dos coletores para teste determinístico:
    monkeypatch.setattr(regen, "_pytest_count", lambda: "1234 tests collected")
    monkeypatch.setattr(regen, "_smoke_status", lambda: "10/10 contratos OK")
    monkeypatch.setattr(regen, "_lint_status", lambda: "exit 0")
    monkeypatch.setattr(regen, "_grafo_stats", lambda: (7000, 24000))
    monkeypatch.setattr(regen, "_tipos_graduados", lambda: (9, 22))
    monkeypatch.setattr(regen, "_extratores_count", lambda: 23)
    monkeypatch.setattr(regen, "_ultimo_commit", lambda: "abc1234 teste")

    bloco = regen.gerar_bloco_metricas()
    assert "TESTES: 1234 tests collected" in bloco
    assert "SMOKE: 10/10 contratos OK" in bloco
    assert "LINT: exit 0" in bloco
    assert "GRAFO: 7000 nodes / 24000 edges" in bloco
    assert "TIPOS GRADUADOS: 9/22" in bloco
    assert "EXTRATORES: 23" in bloco
    assert "ÚLTIMO COMMIT: abc1234 teste" in bloco


def test_aplicar_no_arquivo_substitui_entre_markers() -> None:
    """Markers existentes ditam fronteira; conteúdo entre é substituído."""
    md_original = (
        "# Doc\n\n"
        "## Versao + saude geral\n\n"
        f"{regen.MARKER_INICIO}\n"
        "```\n"
        "BLOCO ANTIGO\n"
        "```\n"
        f"{regen.MARKER_FIM}\n\n"
        "outra seção\n"
    )
    novo_bloco = "```\nBLOCO NOVO\n```\n"
    resultado = regen.aplicar_no_arquivo(md_original, novo_bloco)
    assert "BLOCO ANTIGO" not in resultado
    assert "BLOCO NOVO" in resultado
    assert "outra seção" in resultado  # preserva resto do MD


def test_aplicar_no_arquivo_insere_markers_quando_ausentes() -> None:
    """Sem markers: insere logo após cabeçalho `## Versao + saude geral`."""
    md_sem_markers = (
        "# Doc\n\n"
        "## Versao + saude geral\n\n"
        "```\n"
        "TEXTO ESTÁTICO HISTÓRICO\n"
        "```\n\n"
        "## outra seção\n"
    )
    novo_bloco = "```\nBLOCO NOVO\n```\n"
    resultado = regen.aplicar_no_arquivo(md_sem_markers, novo_bloco)
    assert regen.MARKER_INICIO in resultado
    assert regen.MARKER_FIM in resultado
    assert "BLOCO NOVO" in resultado
    assert "TEXTO ESTÁTICO HISTÓRICO" in resultado  # preserva bloco legado


def test_aplicar_no_arquivo_idempotente(monkeypatch, tmp_path: Path) -> None:
    """Aplicar 2× consecutivas com mesmas métricas produz mesmo arquivo."""
    md_inicial = (
        "## Versao + saude geral\n\n"
        f"{regen.MARKER_INICIO}\n"
        "```\nOLD\n```\n"
        f"{regen.MARKER_FIM}\n"
    )
    bloco_fixo = "```\nFIXED\n```\n"
    primeira = regen.aplicar_no_arquivo(md_inicial, bloco_fixo)
    segunda = regen.aplicar_no_arquivo(primeira, bloco_fixo)
    assert primeira == segunda


def test_tipos_graduados_lê_canonico_do_yaml(monkeypatch, tmp_path: Path) -> None:
    """`_tipos_graduados` usa total do YAML (não count do JSON)."""
    yaml_path = tmp_path / "tipos.yaml"
    yaml_path.write_text(
        "tipos:\n  - id: a\n  - id: b\n  - id: c\n", encoding="utf-8"
    )
    json_path = tmp_path / "graduacao.json"
    json_path.write_text(
        '{"totais": {"GRADUADO": 1, "PENDENTE": 0}}', encoding="utf-8"
    )
    monkeypatch.setattr(regen, "PATH_GRADUACAO", json_path)
    monkeypatch.setattr(regen, "_RAIZ", tmp_path)
    # PATH_GRADUACAO é resolvido em runtime mas _RAIZ não — precisamos do yaml path:
    (tmp_path / "mappings").mkdir()
    (tmp_path / "mappings" / "tipos_documento.yaml").write_text(
        yaml_path.read_text(encoding="utf-8"), encoding="utf-8"
    )

    grad, total = regen._tipos_graduados()
    assert grad == 1
    assert total == 3  # do YAML, não do JSON


# "Documento que envelhece à mão é documento que mente sozinho."
# -- princípio do snapshot vivo
