"""Testes do leitor/validador do cache ``memorias.json`` (ADR-25).

A fixture canônica é ``tests/fixtures/vault_sintetico/`` que contém um
``.ouroboros/cache/memorias.json`` com 12 cápsulas (5 fotos / 2 áudios
/ 3 textos / 2 vídeos), espelhando a sprint INFRA-MEMORIAS-SCHEMA.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from src.mobile_cache.memorias import (
    SCHEMA_VERSION,
    TIPOS_VALIDOS,
    carregar,
    carregar_validado,
    validar,
)

FIXTURE_VAULT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "vault_sintetico"
)


def _payload_fixture() -> dict:
    arquivo = FIXTURE_VAULT / ".ouroboros" / "cache" / "memorias.json"
    return json.loads(arquivo.read_text(encoding="utf-8"))


def test_constantes_canonicas() -> None:
    assert SCHEMA_VERSION == 1
    assert TIPOS_VALIDOS == ("foto", "audio", "texto", "video")


def test_fixture_tem_12_capsulas_com_distribuicao_correta() -> None:
    payload = _payload_fixture()
    assert payload["schema_version"] == 1
    assert len(payload["items"]) == 12
    tipos = [it["tipo"] for it in payload["items"]]
    assert tipos.count("foto") == 5
    assert tipos.count("audio") == 2
    assert tipos.count("texto") == 3
    assert tipos.count("video") == 2


def test_fixture_passa_no_validador() -> None:
    erros = validar(_payload_fixture())
    assert erros == [], f"fixture deveria ser válida; erros: {erros}"


def test_carregar_retorna_payload_completo() -> None:
    payload = carregar(FIXTURE_VAULT)
    assert payload is not None
    assert payload["schema_version"] == 1
    assert len(payload["items"]) == 12


def test_carregar_validado_retorna_items_e_gerado_em() -> None:
    items, gerado_em = carregar_validado(FIXTURE_VAULT)
    assert len(items) == 12
    assert gerado_em == "2026-05-08T12:00:00-03:00"


def test_carregar_vault_none_retorna_lista_vazia() -> None:
    items, gerado_em = carregar_validado(None)
    assert items == []
    assert gerado_em is None


def test_carregar_vault_inexistente_retorna_lista_vazia(tmp_path: Path) -> None:
    items, gerado_em = carregar_validado(tmp_path)
    assert items == []
    assert gerado_em is None


def test_validar_detecta_tipo_invalido() -> None:
    payload = deepcopy(_payload_fixture())
    payload["items"][0]["tipo"] = "audio_curto"
    erros = validar(payload)
    assert any("tipo" in e for e in erros), erros


def test_validar_detecta_campo_obrigatorio_ausente() -> None:
    payload = deepcopy(_payload_fixture())
    del payload["items"][0]["preview_path"]
    erros = validar(payload)
    assert any("preview_path" in e for e in erros), erros


def test_validar_detecta_schema_version_errada() -> None:
    payload = deepcopy(_payload_fixture())
    payload["schema_version"] = 2
    erros = validar(payload)
    assert any("schema_version" in e for e in erros), erros


def test_carregar_validado_payload_invalido_modo_estrito_levanta(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload_fixture())
    payload["items"][0]["tipo"] = "foo"
    cache = tmp_path / ".ouroboros" / "cache"
    cache.mkdir(parents=True)
    (cache / "memorias.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    with pytest.raises(ValidationError):
        carregar_validado(tmp_path, estrito=True)


def test_carregar_validado_payload_invalido_modo_lenient_cai_em_skeleton(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload_fixture())
    payload["items"][0]["tipo"] = "foo"
    cache = tmp_path / ".ouroboros" / "cache"
    cache.mkdir(parents=True)
    (cache / "memorias.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    items, gerado_em = carregar_validado(tmp_path)
    assert items == []
    assert gerado_em == payload["gerado_em"]


def test_para_abrir_count_bate_com_kpi() -> None:
    payload = _payload_fixture()
    para_abrir = sum(1 for it in payload["items"] if it["para_abrir"])
    # Fixture sintética: 2 fotos + 1 áudio + 1 texto + 1 vídeo = 5.
    assert para_abrir == 5


# "A memória é o diário que carregamos conosco." -- Oscar Wilde
