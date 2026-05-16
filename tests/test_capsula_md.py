"""Testes do formato `.capsula.md` (ADR-25-extensao, sprint MOB-spec-galeria-memorias).

Cobertura:

* Parse de fixtures reais (aniversário + show) sem erro.
* Frontmatter valida contra `$defs.capsula_md` de `schema_memorias.json`.
* `companions[]` resolvido para `Path` ao lado do `.md`.
* `carregar_capsulas` ordena por data decrescente.
* `carregar_capsulas` ignora pasta inexistente sem crash.
* `carregar_capsulas` descarta cápsula com frontmatter inválido.
* Companion exige `tipo` e `arquivo`; rejeita campos extras.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dashboard.paginas.be_memorias import (
    Capsula,
    _parsear_capsula_md,
    _validar_capsula_frontmatter,
    carregar_capsulas,
)

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = RAIZ / "tests" / "fixtures" / "capsulas"
SCHEMA_PATH = RAIZ / "mappings" / "schema_memorias.json"


def test_fixtures_existem() -> None:
    """Sanidade: as duas fixtures canônicas estão no repo."""
    fixtures = sorted(FIXTURES.glob("*.capsula.md"))
    nomes = {p.name for p in fixtures}
    assert nomes == {
        "2026-05-12-100000-aniversario-vitoria.capsula.md",
        "2026-05-12-180000-show-rock-band.capsula.md",
    }


def test_parse_aniversario_separa_frontmatter_e_corpo() -> None:
    """Fixture aniversário parseia em (front, corpo) sem perder dado."""
    fix = FIXTURES / "2026-05-12-100000-aniversario-vitoria.capsula.md"
    front, corpo = _parsear_capsula_md(fix.read_text(encoding="utf-8"))
    assert front["titulo"] == "Aniversário da Vitória"
    assert front["slug"] == "aniversario-vitoria"
    assert front["tipo"] == "memoria"
    assert len(front["companions"]) == 3
    assert corpo.startswith("# Aniversário da Vitória")


def test_parse_show_separa_frontmatter_e_corpo() -> None:
    """Fixture show parseia com vídeo + áudio em companions."""
    fix = FIXTURES / "2026-05-12-180000-show-rock-band.capsula.md"
    front, corpo = _parsear_capsula_md(fix.read_text(encoding="utf-8"))
    assert front["tipo"] == "evento"
    assert front["duracao_estimada_min"] == 120
    tipos = {c["tipo"] for c in front["companions"]}
    assert tipos == {"video", "audio"}
    assert "refrão final" in corpo


def test_fixtures_validam_contra_schema() -> None:
    """Frontmatter de ambas as fixtures passa em `$defs.capsula_md`."""
    for fix in sorted(FIXTURES.glob("*.capsula.md")):
        front, _ = _parsear_capsula_md(fix.read_text(encoding="utf-8"))
        _validar_capsula_frontmatter(front)  # não levanta


def test_carregar_capsulas_ordena_data_desc() -> None:
    """`carregar_capsulas` retorna mais recente primeiro (tie-break por hora)."""
    capsulas = carregar_capsulas(FIXTURES)
    assert len(capsulas) == 2
    assert all(isinstance(c, Capsula) for c in capsulas)
    # Mesma data 2026-05-12; tie-break por hora -> 18:00 antes de 10:00.
    assert capsulas[0].frontmatter["hora"] == "18:00:00"
    assert capsulas[1].frontmatter["hora"] == "10:00:00"


def test_carregar_capsulas_resolve_companions_para_paths() -> None:
    """`companions_resolvidos` aponta para arquivos ao lado do `.md`."""
    capsulas = carregar_capsulas(FIXTURES)
    aniversario = next(c for c in capsulas if c.frontmatter["slug"] == "aniversario-vitoria")
    assert len(aniversario.companions_resolvidos) == 3
    for path in aniversario.companions_resolvidos:
        assert isinstance(path, Path)
        assert path.parent == FIXTURES


def test_carregar_capsulas_base_inexistente_devolve_lista_vazia(
    tmp_path: Path,
) -> None:
    """Pasta ausente não crasha; retorna lista vazia."""
    assert carregar_capsulas(tmp_path / "naoexiste") == []


def test_carregar_capsulas_descarta_frontmatter_invalido(tmp_path: Path) -> None:
    """Cápsula com frontmatter quebrado é silenciosamente descartada."""
    invalido = tmp_path / "2099-01-01-000000-invalida.capsula.md"
    invalido.write_text(
        "---\n_schema_version: 1\ntipo: invalido_xyz\n---\nCorpo\n",
        encoding="utf-8",
    )
    assert carregar_capsulas(tmp_path) == []


def test_parse_capsula_sem_delimitador_inicial_falha() -> None:
    """Texto sem `---\\n` inicial gera ValueError."""
    with pytest.raises(ValueError, match="frontmatter inicial"):
        _parsear_capsula_md("# Só corpo\nsem frontmatter\n")


def test_parse_capsula_sem_delimitador_final_falha() -> None:
    """Frontmatter aberto sem fechamento gera ValueError."""
    with pytest.raises(ValueError, match="delimitador final"):
        _parsear_capsula_md("---\ntipo: memoria\nainda no front\n")


def test_companion_obriga_tipo_e_arquivo() -> None:
    """Schema rejeita companion sem `tipo` ou `arquivo`."""
    import jsonschema

    schema_completo = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    subschema = {
        "$schema": schema_completo["$schema"],
        "$ref": "#/$defs/capsula_md",
        "$defs": schema_completo["$defs"],
    }
    front_invalido = {
        "_schema_version": 1,
        "tipo": "memoria",
        "data": "2026-05-12",
        "titulo": "X",
        "slug": "x",
        "companions": [{"tipo": "foto"}],  # falta `arquivo`
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(front_invalido, subschema)
