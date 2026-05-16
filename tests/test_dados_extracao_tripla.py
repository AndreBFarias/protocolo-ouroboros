"""Testes do carregador ``src/dashboard/dados_extracao_tripla.py``.

Sprint INFRA-EXTRACAO-TRIPLA-SCHEMA. Cobre:

  - Graceful fallback quando o JSON não existe.
  - Graceful fallback quando o JSON está corrompido.
  - Graceful fallback quando o schema é inválido (ex: não tem chave
    ``registros``).
  - Leitura bem-sucedida do JSON canônico real do projeto, com pelo menos
    3 registros e Opus populado em cada.
  - Helpers ``contar_divergencias`` e ``calcular_paridade`` em casos
    canônicos (consenso total, divergência total, mistura).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dashboard.dados_extracao_tripla import (
    CAMINHO_PADRAO,
    calcular_paridade,
    carregar_extracoes_triplas,
    contar_divergencias,
)

# ----------------------------------------------------------------------------
# carregar_extracoes_triplas: graceful fallbacks
# ----------------------------------------------------------------------------


def test_carregar_inexistente_devolve_lista_vazia(tmp_path: Path) -> None:
    """Arquivo ausente devolve [] sem levantar."""
    alvo = tmp_path / "nao_existe.json"
    assert carregar_extracoes_triplas(alvo) == []


def test_carregar_json_invalido_devolve_lista_vazia(tmp_path: Path) -> None:
    """JSON corrompido devolve [] sem levantar."""
    alvo = tmp_path / "corrompido.json"
    alvo.write_text("{ isso não é json válido", encoding="utf-8")
    assert carregar_extracoes_triplas(alvo) == []


def test_carregar_schema_sem_registros_devolve_lista_vazia(tmp_path: Path) -> None:
    """JSON válido sem chave ``registros`` devolve []."""
    alvo = tmp_path / "schema_errado.json"
    alvo.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    assert carregar_extracoes_triplas(alvo) == []


def test_carregar_registros_nao_lista_devolve_lista_vazia(tmp_path: Path) -> None:
    """Se ``registros`` não é lista, devolve []."""
    alvo = tmp_path / "registros_dict.json"
    alvo.write_text(
        json.dumps({"registros": {"x": 1}}),
        encoding="utf-8",
    )
    assert carregar_extracoes_triplas(alvo) == []


# ----------------------------------------------------------------------------
# carregar_extracoes_triplas: arquivo canônico real do projeto
# ----------------------------------------------------------------------------


def test_carregar_canonico_real_tem_3_ou_mais_registros() -> None:
    """O JSON canônico produzido por scripts/popular_extracao_tripla.py
    tem >=3 registros, todos com Opus populado.

    Parte da validação de aceitação da sprint
    INFRA-EXTRACAO-TRIPLA-SCHEMA. Pula gracefully se o JSON não existe
    (ex: ambiente CI mínimo sem dado).
    """
    if not CAMINHO_PADRAO.exists():
        pytest.skip("data/output/extracao_tripla.json ausente neste ambiente.")
    registros = carregar_extracoes_triplas()
    assert len(registros) >= 3, f"esperado >=3 registros, achei {len(registros)}"
    com_opus = [r for r in registros if r.get("opus", {}).get("campos")]
    assert len(com_opus) >= 3, f"esperado >=3 registros com Opus populado, achei {len(com_opus)}"


def test_carregar_canonico_real_tem_divergencia_em_cada_registro() -> None:
    """Cada um dos 3 primeiros registros tem >=1 campo divergente entre
    ETL e Opus (requisito de aceitação da spec).
    """
    if not CAMINHO_PADRAO.exists():
        pytest.skip("data/output/extracao_tripla.json ausente neste ambiente.")
    registros = carregar_extracoes_triplas()
    for r in registros[:3]:
        assert contar_divergencias(r) >= 1, f"sha256={r.get('sha256')} sem divergência ETL×Opus"


# ----------------------------------------------------------------------------
# Helpers: contar_divergencias / calcular_paridade
# ----------------------------------------------------------------------------


def _registro_fake(
    etl_campos: dict[str, list],
    opus_campos: dict[str, list],
) -> dict:
    return {
        "sha256": "fake",
        "filename": "fake.pdf",
        "tipo": "fake",
        "etl": {"extractor_versao": "v0", "campos": etl_campos},
        "opus": {"versao": "v0", "campos": opus_campos},
        "humano": {"validado_em": None, "campos": {}},
    }


def test_contar_divergencias_consenso_total() -> None:
    r = _registro_fake(
        {"a": ["x", 1.0], "b": ["y", 1.0]},
        {"a": ["x", 1.0], "b": ["y", 1.0]},
    )
    assert contar_divergencias(r) == 0


def test_contar_divergencias_uma_divergencia() -> None:
    r = _registro_fake(
        {"a": ["x", 1.0], "b": ["y", 1.0]},
        {"a": ["x", 1.0], "b": ["z", 0.7]},
    )
    assert contar_divergencias(r) == 1


def test_contar_divergencias_ignora_vazios() -> None:
    """Se um lado é vazio, não conta como divergência."""
    r = _registro_fake(
        {"a": ["x", 1.0]},
        {"a": ["", 0.0]},
    )
    assert contar_divergencias(r) == 0


def test_calcular_paridade_consenso_total() -> None:
    r = _registro_fake(
        {"a": ["x", 1.0], "b": ["y", 1.0]},
        {"a": ["x", 1.0], "b": ["y", 1.0]},
    )
    assert calcular_paridade(r) == pytest.approx(100.0)


def test_calcular_paridade_metade() -> None:
    r = _registro_fake(
        {"a": ["x", 1.0], "b": ["y", 1.0]},
        {"a": ["x", 1.0], "b": ["DIFERENTE", 0.7]},
    )
    assert calcular_paridade(r) == pytest.approx(50.0)


def test_calcular_paridade_sem_chaves_comuns() -> None:
    r = _registro_fake(
        {"a": ["x", 1.0]},
        {"b": ["y", 1.0]},
    )
    assert calcular_paridade(r) == 0.0


# "Quem testa a base, valida o telhado." -- princípio INFRA
