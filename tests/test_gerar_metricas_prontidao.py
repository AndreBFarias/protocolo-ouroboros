"""Testes do gerador de métricas de prontidão prod.

Sprint META-ROADMAP-METRICAS-AUTO (2026-05-15).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "gerar_metricas_prontidao",
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "gerar_metricas_prontidao.py",
)
assert _SPEC and _SPEC.loader
gm = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gm)


def test_coletar_metricas_estrutura_canonica(monkeypatch) -> None:
    """`coletar_metricas` devolve dict com todas as chaves esperadas."""
    monkeypatch.setattr(gm, "_tipos_graduados", lambda: (9, 22))
    monkeypatch.setattr(gm, "_linking_pct", lambda: (0.41, 25, 6086))
    monkeypatch.setattr(gm, "_outros_pct", lambda: (17.7, 1031, 5840))
    monkeypatch.setattr(gm, "_pytest_count", lambda: 3075)
    monkeypatch.setattr(gm, "_backup_grafo_ativo", lambda: True)
    monkeypatch.setattr(gm, "_transacionalidade_pipeline", lambda: True)
    monkeypatch.setattr(gm, "_lockfile_concorrencia", lambda: False)
    monkeypatch.setattr(gm, "_paginas_dashboard", lambda: 39)

    m = gm.coletar_metricas()
    assert m["tipos_graduados"] == 9
    assert m["tipos_total_canonico"] == 22
    assert m["linking_documento_de_pct"] == 0.41
    assert m["categorizacao_outros_pct"] == 17.7
    assert m["pytest_count"] == 3075
    assert m["backup_grafo_automatico"] is True
    assert m["lockfile_concorrencia"] is False
    assert "gerado_em" in m


def test_renderizar_tabela_markdown_tem_linhas_canonicas() -> None:
    """A tabela markdown contém as 8 linhas de métrica + header."""
    m = {
        "tipos_graduados": 9,
        "tipos_total_canonico": 22,
        "linking_documento_de_pct": 0.41,
        "linking_documento_de_linked": 25,
        "linking_documento_de_total_transacoes": 6086,
        "categorizacao_outros_pct": 17.7,
        "categorizacao_outros_count": 1031,
        "categorizacao_total_transacoes": 5840,
        "pytest_count": 3075,
        "backup_grafo_automatico": True,
        "transacionalidade_pipeline": True,
        "lockfile_concorrencia": False,
        "paginas_dashboard": 39,
    }
    tabela = gm.renderizar_tabela_markdown(m)
    assert "| Tipos GRADUADOS | 9 |" in tabela
    assert "0.41% (25/6086)" in tabela
    assert "17.7% (1031/5840)" in tabela
    assert "| Backup grafo automático | Sim |" in tabela
    assert "| Lockfile concorrência | Não |" in tabela
    assert "| Pytest passed | 3075 |" in tabela


def test_aplicar_no_roadmap_substitui_entre_markers() -> None:
    """Markers existentes ditam fronteira; conteúdo substituído."""
    md = (
        "## Metricas globais de prontidao\n\n"
        f"{gm.MARKER_INICIO}\n"
        "TABELA ANTIGA\n"
        f"{gm.MARKER_FIM}\n\n"
        "outra seção\n"
    )
    nova_tabela = "| X | Y |\n"
    resultado = gm.aplicar_no_roadmap(md, nova_tabela)
    assert "TABELA ANTIGA" not in resultado
    assert "| X | Y |" in resultado
    assert "outra seção" in resultado


def test_aplicar_no_roadmap_idempotente() -> None:
    """Re-rodar com mesma tabela produz mesmo conteúdo."""
    md = f"## Metricas globais de prontidao\n\n{gm.MARKER_INICIO}\nOLD\n{gm.MARKER_FIM}\n"
    tabela = "| X | Y |\n"
    primeira = gm.aplicar_no_roadmap(md, tabela)
    segunda = gm.aplicar_no_roadmap(primeira, tabela)
    assert primeira == segunda


def test_main_grava_json_em_data_output(monkeypatch, tmp_path: Path) -> None:
    """`main()` grava JSON estruturado em PATH_METRICAS_JSON."""
    monkeypatch.setattr(gm, "PATH_METRICAS_JSON", tmp_path / "out.json")
    monkeypatch.setattr(gm, "_tipos_graduados", lambda: (5, 22))
    monkeypatch.setattr(gm, "_linking_pct", lambda: (0.5, 30, 6000))
    monkeypatch.setattr(gm, "_outros_pct", lambda: (15.0, 900, 6000))
    monkeypatch.setattr(gm, "_pytest_count", lambda: 3000)
    monkeypatch.setattr(gm, "_backup_grafo_ativo", lambda: True)
    monkeypatch.setattr(gm, "_transacionalidade_pipeline", lambda: True)
    monkeypatch.setattr(gm, "_lockfile_concorrencia", lambda: False)
    monkeypatch.setattr(gm, "_paginas_dashboard", lambda: 35)

    rc = gm.main([])  # sem --apply-roadmap
    assert rc == 0
    assert (tmp_path / "out.json").exists()
    d = json.loads((tmp_path / "out.json").read_text())
    assert d["tipos_graduados"] == 5
    assert d["pytest_count"] == 3000


# "Métrica viva é métrica medida; métrica morta é métrica copiada."
# -- princípio do contador honesto
