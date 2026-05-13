"""Testes do contrato canonico do catalogo de exercicios (ADR-29).

Valida:
- schema_exercicios.json e Draft-2020-12 valido;
- os 3 exemplos canonicos passam validacao;
- exemplos invalidos sinteticos sao rejeitados.
"""

from __future__ import annotations

import copy
import glob
import json
from pathlib import Path

import jsonschema
import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCHEMA_PATH = RAIZ / "mappings" / "schema_exercicios.json"
EXEMPLOS_DIR = RAIZ / "mappings" / "exemplos_exercicios"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def exemplo_valido(schema: dict) -> dict:
    return json.loads((EXEMPLOS_DIR / "grupo_a_peito_triceps.json").read_text(encoding="utf-8"))


def test_schema_e_draft_2020_12_valido(schema: dict) -> None:
    """Schema em si esta conforme Draft-2020-12."""
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_schema_declara_campos_obrigatorios_topo(schema: dict) -> None:
    """Top-level exige schema_version, gerado_em, grupos e exercicios."""
    obrigatorios = set(schema["required"])
    assert obrigatorios == {"schema_version", "gerado_em", "grupos", "exercicios"}


def test_enum_musculo_principal_tem_12_valores(schema: dict) -> None:
    """Enum de musculo_principal tem exatamente 12 categorias declaradas pela ADR-29."""
    enum = schema["properties"]["exercicios"]["items"]["properties"]["musculo_principal"]["enum"]
    assert len(enum) == 12
    assert "peito" in enum
    assert "mobilidade" in enum


def test_tres_exemplos_canonicos_existem_e_validam(schema: dict) -> None:
    """Os 3 exemplos canonicos existem e passam jsonschema.validate."""
    paths = sorted(glob.glob(str(EXEMPLOS_DIR / "*.json")))
    assert len(paths) == 3, f"Esperado 3 exemplos, encontrei {len(paths)}: {paths}"
    for caminho in paths:
        dado = json.loads(Path(caminho).read_text(encoding="utf-8"))
        jsonschema.validate(dado, schema)


def test_exemplo_sem_schema_version_e_rejeitado(schema: dict, exemplo_valido: dict) -> None:
    """Remover schema_version invalida o documento."""
    invalido = copy.deepcopy(exemplo_valido)
    del invalido["schema_version"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalido, schema)


def test_musculo_principal_fora_do_enum_e_rejeitado(schema: dict, exemplo_valido: dict) -> None:
    """Valor de musculo_principal fora da enum derruba validacao."""
    invalido = copy.deepcopy(exemplo_valido)
    invalido["exercicios"][0]["musculo_principal"] = "pescoco_inexistente"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalido, schema)


def test_gif_path_sem_extensao_gif_e_rejeitado(schema: dict, exemplo_valido: dict) -> None:
    """gif_path deve casar regex midia/gifs/.+\\.gif."""
    invalido = copy.deepcopy(exemplo_valido)
    invalido["exercicios"][0]["gif_path"] = "midia/gifs/supino_reto.mp4"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalido, schema)


def test_cor_hex_invalida_e_rejeitada(schema: dict, exemplo_valido: dict) -> None:
    """cor_hex precisa seguir #RRGGBB."""
    invalido = copy.deepcopy(exemplo_valido)
    invalido["grupos"][0]["cor_hex"] = "vermelho"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalido, schema)


def test_dificuldade_acima_de_5_e_rejeitada(schema: dict, exemplo_valido: dict) -> None:
    """dificuldade vai de 1 a 5."""
    invalido = copy.deepcopy(exemplo_valido)
    invalido["exercicios"][0]["dificuldade"] = 7
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalido, schema)
