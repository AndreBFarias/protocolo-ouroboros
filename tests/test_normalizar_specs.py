"""Testes do normalizador de frontmatter de specs.

Cobre auditoria, normalização, validação e idempotência usando fixtures
sintéticas em ``tmp_path``. Não toca specs reais do repositório.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import normalizar_specs as norm  # noqa: E402,I001


SPEC_OK = """---
id: TESTE-OK
titulo: spec exemplar
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-13
fase: SANEAMENTO
epico: 8
depende_de: []
tipo_documental_alvo: null
---

# Sprint TESTE-OK

Corpo qualquer.
"""

SPEC_SEM_FM = """# Sprint sem frontmatter

Texto livre. Prioridade: P1 mencionada inline.
"""

SPEC_FM_PARCIAL = """---
id: TESTE-PARCIAL
titulo: faltam campos
---

Corpo.
"""


@pytest.fixture
def vault(tmp_path, monkeypatch):
    """Cria estrutura backlog/concluidos sintética e redireciona o módulo."""
    backlog = tmp_path / "backlog"
    concluidos = tmp_path / "concluidos"
    backlog.mkdir()
    concluidos.mkdir()
    monkeypatch.setattr(norm, "DIR_BACKLOG", backlog)
    monkeypatch.setattr(norm, "DIR_CONCLUIDOS", concluidos)
    monkeypatch.setattr(norm, "RAIZ_REPO", tmp_path)
    return SimpleNamespace(raiz=tmp_path, backlog=backlog, concluidos=concluidos)


def _escrever(path: Path, conteudo: str) -> None:
    path.write_text(conteudo, encoding="utf-8")


def test_auditar_spec_ok_exit_zero(vault, capsys):
    _escrever(vault.backlog / "sprint_ok.md", SPEC_OK)
    args = SimpleNamespace(excluir=[])
    rc = norm.cmd_auditar(args)
    saida = capsys.readouterr().out
    assert rc == 0
    assert "0 pendencias" in saida


def test_auditar_lista_spec_sem_frontmatter(vault, capsys):
    _escrever(vault.backlog / "sprint_sem_fm.md", SPEC_SEM_FM)
    args = SimpleNamespace(excluir=[])
    rc = norm.cmd_auditar(args)
    saida = capsys.readouterr().out
    assert rc == 1
    assert "SEM_FRONTMATTER" in saida
    assert "sprint_sem_fm.md" in saida


def test_auditar_lista_campos_faltantes(vault, capsys):
    _escrever(vault.backlog / "sprint_parcial.md", SPEC_FM_PARCIAL)
    args = SimpleNamespace(excluir=[])
    rc = norm.cmd_auditar(args)
    saida = capsys.readouterr().out
    assert rc == 1
    assert "CAMPOS_FALTANTES" in saida
    # Faltam: status, concluida_em, prioridade, data_criacao, epico, depende_de
    assert "status" in saida
    assert "prioridade" in saida


def test_normalizar_adiciona_frontmatter_sem_destruir(vault, capsys):
    path = vault.backlog / "sprint_sem_fm.md"
    _escrever(path, SPEC_SEM_FM)
    args = SimpleNamespace(excluir=[], data_fallback="2026-05-13")
    # Mock git para evitar dependência do repo real.
    with patch.object(norm, "inferir_data_criacao", return_value="2026-05-13"):
        rc = norm.cmd_normalizar(args)
    assert rc == 0
    novo = path.read_text(encoding="utf-8")
    assert novo.startswith("---\n")
    # Conteúdo original preservado abaixo do frontmatter.
    assert "Sprint sem frontmatter" in novo
    assert "Prioridade: P1 mencionada inline" in novo
    # Parse confirma campos obrigatórios.
    dados, erro = norm.carregar_frontmatter(novo)
    assert erro is None
    for campo in norm.CAMPOS_OBRIGATORIOS:
        assert campo in dados, f"campo {campo} ausente"
    # Inferiu prioridade P1 do corpo.
    assert dados["prioridade"] == "P1"
    # id veio do nome do arquivo.
    assert dados["id"] == "SEM-FM"


def test_validar_apos_normalizar_parseia_tudo(vault, capsys):
    _escrever(vault.backlog / "sprint_ok.md", SPEC_OK)
    _escrever(vault.backlog / "sprint_sem_fm.md", SPEC_SEM_FM)
    _escrever(vault.concluidos / "sprint_legado.md", SPEC_SEM_FM)
    args_norm = SimpleNamespace(excluir=[], data_fallback="2026-05-13")
    with patch.object(norm, "inferir_data_criacao", return_value="2026-05-13"):
        assert norm.cmd_normalizar(args_norm) == 0
    args_val = SimpleNamespace(excluir=[])
    rc = norm.cmd_validar(args_val)
    saida = capsys.readouterr().out
    assert rc == 0
    assert "3 specs OK" in saida
    # Spec em concluidos/ ganha status=concluida.
    dados, _ = norm.carregar_frontmatter(
        (vault.concluidos / "sprint_legado.md").read_text(encoding="utf-8")
    )
    assert dados["status"] == "concluida"


def test_normalizar_idempotente(vault):
    path = vault.backlog / "sprint_sem_fm.md"
    _escrever(path, SPEC_SEM_FM)
    args = SimpleNamespace(excluir=[], data_fallback="2026-05-13")
    with patch.object(norm, "inferir_data_criacao", return_value="2026-05-13"):
        norm.cmd_normalizar(args)
    apos_primeira = path.read_text(encoding="utf-8")
    with patch.object(norm, "inferir_data_criacao", return_value="2026-05-13"):
        norm.cmd_normalizar(args)
    apos_segunda = path.read_text(encoding="utf-8")
    assert apos_primeira == apos_segunda


def test_excluir_arquivo_pula_normalizacao(vault):
    excluida = vault.backlog / "sprint_excluida.md"
    incluida = vault.backlog / "sprint_incluida.md"
    _escrever(excluida, SPEC_SEM_FM)
    _escrever(incluida, SPEC_SEM_FM)
    args = SimpleNamespace(
        excluir=["sprint_excluida.md"], data_fallback="2026-05-13"
    )
    with patch.object(norm, "inferir_data_criacao", return_value="2026-05-13"):
        norm.cmd_normalizar(args)
    # Excluída permanece sem frontmatter.
    assert not excluida.read_text(encoding="utf-8").startswith("---\n")
    # Incluída foi normalizada.
    assert incluida.read_text(encoding="utf-8").startswith("---\n")


def test_inferir_id_remove_prefixo_e_data():
    path = Path("docs/sprints/backlog/sprint_meta_template_2026-05-13.md")
    assert norm.inferir_id(path) == "META-TEMPLATE"


def test_carregar_frontmatter_yaml_invalido():
    texto = "---\nid: [unclosed\n---\nconteudo\n"
    dados, erro = norm.carregar_frontmatter(texto)
    assert dados is None
    assert "yaml inválido" in erro or "yaml" in erro.lower()
