"""Testes de ``src/extractors/opus_visao.py`` (Sprint INFRA-OCR-OPUS-VISAO).

Cobertura:
    1. Cache hit: JSON canônico pré-populado é retornado direto.
    2. Cache miss: gera pedido em ``opus_ocr_pendentes/<sha>.txt`` e devolve
       stub ``aguardando_supervisor=True``.
    3. Schema canônico: cache canônico do cupom NSP valida contra
       ``mappings/schema_opus_ocr.json``.
    4. Idempotência sha256: mesmo conteúdo, nome diferente → mesmo cache.
    5. Modo produção: ``OPUS_API_KEY`` levanta ``NotImplementedError``.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from jsonschema import validate

from src.extractors.opus_visao import (
    calcular_sha256,
    extrair_via_opus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RAIZ_REPO = Path(__file__).resolve().parent.parent
DIR_FIXTURES = RAIZ_REPO / "tests" / "fixtures" / "opus_ocr"
SCHEMA_PATH = RAIZ_REPO / "mappings" / "schema_opus_ocr.json"

CUPOM_NSP = DIR_FIXTURES / "cupom_real_nsp.jpeg"
SHA_NSP = "2e43640dde52352439716cb7854af244effa3cc0f9d2c9d7f2aa31454b37f73e"
CACHE_CANONICO_NSP = DIR_FIXTURES / "cache_canonico" / f"{SHA_NSP}.json"


@pytest.fixture
def diretorios_tmp(tmp_path: Path) -> tuple[Path, Path]:
    """Diretórios isolados para cache e pendentes (não tocam ``data/``)."""
    cache = tmp_path / "cache"
    pendentes = tmp_path / "pendentes"
    return cache, pendentes


@pytest.fixture
def cache_pre_populado(tmp_path: Path) -> tuple[Path, Path]:
    """Cache simulando rodada anterior do supervisor (cupom NSP transcrito)."""
    cache = tmp_path / "cache"
    pendentes = tmp_path / "pendentes"
    cache.mkdir(parents=True)
    shutil.copy(CACHE_CANONICO_NSP, cache / f"{SHA_NSP}.json")
    return cache, pendentes


# ---------------------------------------------------------------------------
# Pré-condições da fixture
# ---------------------------------------------------------------------------


def test_fixture_cupom_existe_e_tem_sha_canonico() -> None:
    """A fixture real precisa existir e ter o sha256 declarado.

    Defesa em camadas: se alguém regerar a imagem, o sha bate em pedaços
    (cache canônico, schema, teste). Esse smoke barra divergência.
    """
    assert CUPOM_NSP.exists(), f"Fixture ausente: {CUPOM_NSP}"
    assert calcular_sha256(CUPOM_NSP) == SHA_NSP


def test_cache_canonico_valida_contra_schema() -> None:
    """O cache pré-populado para o cupom NSP precisa casar com o JSON Schema."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    cache = json.loads(CACHE_CANONICO_NSP.read_text(encoding="utf-8"))
    # Remover campo informativo "_observacao" (não faz parte do schema)
    cache.pop("_observacao", None)
    validate(instance=cache, schema=schema)


def test_cache_canonico_aritmetica_fecha() -> None:
    """Soma dos itens deve bater o total declarado (R$ 513,31)."""
    cache = json.loads(CACHE_CANONICO_NSP.read_text(encoding="utf-8"))
    soma = round(sum(item["valor_total"] for item in cache["itens"]), 2)
    assert soma == cache["total"], f"soma={soma} declarado={cache['total']}"
    assert len(cache["itens"]) == 52, "Caso 2 da auditoria fixou 52 itens"


# ---------------------------------------------------------------------------
# Comportamento: cache hit
# ---------------------------------------------------------------------------


def test_cache_hit_retorna_dados_canonicos(
    cache_pre_populado: tuple[Path, Path],
) -> None:
    """Quando o cache existe, a função retorna o dict canônico direto."""
    cache, pendentes = cache_pre_populado
    resultado = extrair_via_opus(CUPOM_NSP, dir_cache=cache, dir_pendentes=pendentes)

    assert resultado["sha256"] == SHA_NSP
    assert resultado["tipo_documento"] == "cupom_fiscal_foto"
    assert resultado["estabelecimento"]["razao_social"] == "Comercial NSP LTDA"
    assert resultado["total"] == 513.31
    assert len(resultado["itens"]) == 52
    # Cache hit não cria pendente
    assert not (pendentes / f"{SHA_NSP}.txt").exists()


def test_cache_hit_idempotente_em_chamadas_repetidas(
    cache_pre_populado: tuple[Path, Path],
) -> None:
    """Chamar 2x devolve dados equivalentes sem regerar pendente."""
    cache, pendentes = cache_pre_populado
    a = extrair_via_opus(CUPOM_NSP, dir_cache=cache, dir_pendentes=pendentes)
    b = extrair_via_opus(CUPOM_NSP, dir_cache=cache, dir_pendentes=pendentes)
    assert a == b


# ---------------------------------------------------------------------------
# Comportamento: cache miss
# ---------------------------------------------------------------------------


def test_cache_miss_cria_pedido_pendente(
    diretorios_tmp: tuple[Path, Path],
) -> None:
    """Sem cache, registra pedido em ``<dir_pendentes>/<sha>.txt`` com path."""
    cache, pendentes = diretorios_tmp
    resultado = extrair_via_opus(
        CUPOM_NSP, dir_cache=cache, dir_pendentes=pendentes
    )

    assert resultado["aguardando_supervisor"] is True
    assert resultado["tipo_documento"] == "pendente"
    assert resultado["sha256"] == SHA_NSP

    arquivo_pedido = pendentes / f"{SHA_NSP}.txt"
    assert arquivo_pedido.exists()
    conteudo = arquivo_pedido.read_text(encoding="utf-8")
    assert conteudo == str(CUPOM_NSP.resolve())


def test_cache_miss_nao_cria_arquivo_de_cache(
    diretorios_tmp: tuple[Path, Path],
) -> None:
    """Em cache miss, o JSON ainda NÃO é criado — só após o supervisor.

    Trava regressão: a função não pode "alucinar" um JSON canônico do
    nada; só o supervisor humano (ou modo API futuro) pode gerar.
    """
    cache, pendentes = diretorios_tmp
    extrair_via_opus(CUPOM_NSP, dir_cache=cache, dir_pendentes=pendentes)
    assert not (cache / f"{SHA_NSP}.json").exists()


def test_supervisor_processa_pedido_e_segunda_chamada_ve_cache(
    diretorios_tmp: tuple[Path, Path],
) -> None:
    """Simula fluxo completo: miss → supervisor grava cache → hit."""
    cache, pendentes = diretorios_tmp

    # 1. primeira chamada: gera pedido
    primeiro = extrair_via_opus(
        CUPOM_NSP, dir_cache=cache, dir_pendentes=pendentes
    )
    assert primeiro["aguardando_supervisor"] is True

    # 2. supervisor humano transcreve a imagem para o cache
    cache.mkdir(parents=True, exist_ok=True)
    shutil.copy(CACHE_CANONICO_NSP, cache / f"{SHA_NSP}.json")

    # 3. segunda chamada: cache hit, retorna dados canônicos
    segundo = extrair_via_opus(
        CUPOM_NSP, dir_cache=cache, dir_pendentes=pendentes
    )
    assert segundo.get("aguardando_supervisor") is None
    assert segundo["total"] == 513.31


# ---------------------------------------------------------------------------
# Imagem inexistente
# ---------------------------------------------------------------------------


def test_imagem_inexistente_levanta_filenotfounderror(tmp_path: Path) -> None:
    """Path inválido vira erro explícito (não silencia)."""
    with pytest.raises(FileNotFoundError):
        extrair_via_opus(
            tmp_path / "inexistente.jpg",
            dir_cache=tmp_path / "cache",
            dir_pendentes=tmp_path / "pendentes",
        )


# ---------------------------------------------------------------------------
# Modo produção (stub)
# ---------------------------------------------------------------------------


def test_opus_api_key_levanta_notimplemented(
    diretorios_tmp: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quando a env var existe, modo produção é stub explícito."""
    cache, pendentes = diretorios_tmp
    monkeypatch.setenv("OPUS_API_KEY", "fake-para-teste")
    with pytest.raises(NotImplementedError, match="produção"):
        extrair_via_opus(
            CUPOM_NSP, dir_cache=cache, dir_pendentes=pendentes
        )


# ---------------------------------------------------------------------------
# Idempotência por sha256 (não pelo nome)
# ---------------------------------------------------------------------------


def test_imagem_renomeada_bate_mesmo_cache(
    cache_pre_populado: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Cópia da imagem com outro nome resolve o mesmo sha → mesmo cache."""
    cache, pendentes = cache_pre_populado
    copia = tmp_path / "outro_nome.jpeg"
    shutil.copy(CUPOM_NSP, copia)

    resultado = extrair_via_opus(copia, dir_cache=cache, dir_pendentes=pendentes)
    assert resultado["sha256"] == SHA_NSP
    assert resultado["total"] == 513.31


# ---------------------------------------------------------------------------
# Limpeza de env var de teste
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _limpar_opus_api_key() -> None:
    """Garante que ``OPUS_API_KEY`` jamais vaza entre testes."""
    valor_antes = os.environ.pop("OPUS_API_KEY", None)
    yield
    if valor_antes is not None:
        os.environ["OPUS_API_KEY"] = valor_antes


# "Cada chamada que repete a anterior é cache fiel; cada chamada que
#  inventa, é alucinação." -- princípio do cache idempotente
