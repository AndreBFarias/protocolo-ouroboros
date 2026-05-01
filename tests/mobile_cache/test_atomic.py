"""Testes do helper ``write_json_atomic``."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.mobile_cache.atomic import write_json_atomic


def test_escrita_atomica_produz_arquivo_final(tmp_path: Path) -> None:
    destino = tmp_path / "subdir" / "cache.json"
    payload = {"chave": "valor", "lista": [1, 2, 3]}

    write_json_atomic(destino, payload)

    assert destino.exists(), "arquivo final deve existir apos escrita atomica"
    conteudo = json.loads(destino.read_text(encoding="utf-8"))
    assert conteudo == payload


def test_escrita_atomica_cria_diretorios_pais(tmp_path: Path) -> None:
    destino = tmp_path / "a" / "b" / "c" / "cache.json"
    write_json_atomic(destino, {"k": 1})
    assert destino.exists()
    assert destino.parent.is_dir()


def test_escrita_atomica_remove_tmp_residual_apos_sucesso(tmp_path: Path) -> None:
    destino = tmp_path / "cache.json"
    write_json_atomic(destino, {"k": 1})
    tmp = destino.with_suffix(".json.tmp")
    assert not tmp.exists(), ".tmp não pode permanecer após os.replace"


def test_escrita_atomica_invoca_os_replace(tmp_path: Path) -> None:
    destino = tmp_path / "cache.json"
    with patch("src.mobile_cache.atomic.os.replace") as replace_mock:
        write_json_atomic(destino, {"k": 1})
        replace_mock.assert_called_once()
        args, _ = replace_mock.call_args
        origem, alvo = args
        assert str(origem).endswith(".tmp")
        assert Path(alvo) == destino


def test_falha_durante_escrita_remove_tmp_e_preserva_destino(tmp_path: Path) -> None:
    destino = tmp_path / "cache.json"
    # Pré-escreve um conteúdo válido para garantir que destino não é tocado.
    destino.write_text(json.dumps({"original": True}), encoding="utf-8")

    with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            write_json_atomic(destino, {"novo": True})

    # Destino preserva conteúdo original.
    assert json.loads(destino.read_text(encoding="utf-8")) == {"original": True}
    # Tmp não deve permanecer.
    tmp = destino.with_suffix(".json.tmp")
    assert not tmp.exists()


def test_payload_em_utf8_preserva_acentos(tmp_path: Path) -> None:
    destino = tmp_path / "cache.json"
    payload = {"pessoa": "pessoa_a", "categoria": "alimentação", "obs": "ônibus"}
    write_json_atomic(destino, payload)

    bruto = destino.read_text(encoding="utf-8")
    assert "alimentação" in bruto
    assert "ônibus" in bruto
    # ensure_ascii=False evita escapes \u00...
    assert "\\u00e7" not in bruto.lower()
