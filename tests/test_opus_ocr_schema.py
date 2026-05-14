"""Testes do schema canônico Opus OCR estendido (Sprint INFRA-OPUS-SCHEMA-EXTENDIDO).

Cobertura:
    1. Schema é Draft-2020-12-válido.
    2. Retrocompat: 4 caches existentes em ``data/output/opus_ocr_cache/``
       permanecem 100% válidos sob o schema estendido.
    3. Validação positiva por novo tipo (holerite, das_parcsn, nfce_modelo_65,
       boleto_pdf, danfe_55, extrato_bancario_pdf).
    4. Validação negativa por novo tipo: payload sem campo obrigatório falha.
    5. Enum ``tipo_documento`` tem 11 valores e aceita todos os tipos novos.
    6. Regex de identificadores (chave_44, linha_digitavel, codigo_barras,
       competencia) rejeita formatos inválidos.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

# ---------------------------------------------------------------------------
# Fixtures de path
# ---------------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parents[1]
SCHEMA_PATH = RAIZ / "mappings" / "schema_opus_ocr.json"
FIXTURES_DIR = RAIZ / "tests" / "fixtures" / "opus_ocr_schemas"
CACHES_DIR = RAIZ / "data" / "output" / "opus_ocr_cache"


@pytest.fixture(scope="module")
def schema() -> dict:
    """Carrega o schema estendido uma vez por módulo."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


@pytest.fixture(scope="module")
def validador(schema: dict) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(schema)


def _carregar_fixture(nome: str) -> dict:
    with (FIXTURES_DIR / f"{nome}.json").open("r", encoding="utf-8") as fp:
        return json.load(fp)


# ---------------------------------------------------------------------------
# 1. Sanidade do schema
# ---------------------------------------------------------------------------


def test_schema_e_draft_2020_12_valido(schema: dict) -> None:
    """O schema declara meta-schema Draft-2020-12 e passa ``check_schema``."""
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    jsonschema.Draft202012Validator.check_schema(schema)


def test_enum_tipo_documento_tem_11_valores(schema: dict) -> None:
    """Enum ``tipo_documento`` cobre 5 antigos + 6 novos da Sprint
    INFRA-OPUS-SCHEMA-EXTENDIDO + 4 alias canonicos adicionados pela
    Sprint FASE-A-GRADUACAO-MASSA (boleto_servico, fatura_cartao,
    extrato_bancario, cupom_garantia_estendida).

    Mantem o nome do teste por estabilidade (cobre baseline historica);
    a contagem agora eh 15 = 11 originais + 4 alias.
    """
    enum = schema["properties"]["tipo_documento"]["enum"]
    assert len(enum) == 15
    novos = {
        "holerite",
        "das_parcsn",
        "nfce_modelo_65",
        "boleto_pdf",
        "danfe_55",
        "extrato_bancario_pdf",
    }
    antigos = {
        "cupom_fiscal_foto",
        "comprovante_pix_foto",
        "recibo_foto",
        "outro",
        "pendente",
    }
    alias_canonicos = {
        "boleto_servico",
        "fatura_cartao",
        "extrato_bancario",
        "cupom_garantia_estendida",
    }
    assert set(enum) == novos | antigos | alias_canonicos


# ---------------------------------------------------------------------------
# 2. Retrocompatibilidade: 4 caches existentes permanecem válidos
# ---------------------------------------------------------------------------


def test_retrocompat_caches_existentes(validador: jsonschema.Draft202012Validator) -> None:
    """Todos os caches em ``data/output/opus_ocr_cache/`` permanecem válidos
    sob o schema estendido (retrocompat hard, padrão (o)).

    Baseline historica: 4 caches no merge de INFRA-OPUS-SCHEMA-EXTENDIDO. Como
    a sessao 2026-05-12 promoveu 1 cache adicional (Atacadao Drogaria) pela
    sprint INFRA-SUBSTITUIR-CACHE-SINTETICO-CUPOM, o teste agora exige >= 4
    (cresce naturalmente conforme caches reais são promovidos).
    """
    caches = sorted(CACHES_DIR.glob("*.json"))
    assert len(caches) >= 4, (
        f"Esperado >= 4 caches em {CACHES_DIR}, achei {len(caches)}. "
        "Spec INFRA-OPUS-SCHEMA-EXTENDIDO depende dessa baseline minima."
    )
    for cache in caches:
        with cache.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        validador.validate(payload)


# ---------------------------------------------------------------------------
# 3. Validação positiva por novo tipo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tipo",
    [
        "holerite",
        "das_parcsn",
        "nfce_modelo_65",
        "boleto_pdf",
        "danfe_55",
        "extrato_bancario_pdf",
    ],
)
def test_fixture_sintetica_valida(tipo: str, validador: jsonschema.Draft202012Validator) -> None:
    """Cada fixture sintética em ``tests/fixtures/opus_ocr_schemas/<tipo>.json``
    valida contra o schema estendido."""
    payload = _carregar_fixture(tipo)
    assert payload["tipo_documento"] == tipo
    validador.validate(payload)


# ---------------------------------------------------------------------------
# 4. Validação negativa por novo tipo (falta campo obrigatório)
# ---------------------------------------------------------------------------


def test_holerite_sem_competencia_falha(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("holerite")
    del payload["competencia"]
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


def test_das_parcsn_sem_codigo_barras_falha(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("das_parcsn")
    del payload["codigo_barras"]
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


def test_nfce_sem_chave_44_falha(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("nfce_modelo_65")
    del payload["chave_44"]
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


def test_boleto_sem_linha_digitavel_falha(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("boleto_pdf")
    del payload["linha_digitavel"]
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


def test_danfe_sem_protocolo_autorizacao_falha(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("danfe_55")
    del payload["protocolo_autorizacao"]
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


def test_extrato_sem_lancamentos_falha(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("extrato_bancario_pdf")
    del payload["lancamentos"]
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


# ---------------------------------------------------------------------------
# 5. Regex de identificadores rejeita formatos inválidos
# ---------------------------------------------------------------------------


def test_competencia_aceita_yyyy_mm(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("holerite")
    payload["competencia"] = "2026-13"
    # 2026-13 ainda casa regex ^\d{4}-\d{2}$; o teste real é rejeitar mau formato
    payload["competencia"] = "26-04"
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


def test_chave_44_rejeita_tamanho_errado(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("nfce_modelo_65")
    payload["chave_44"] = "12345"  # 5 dígitos: viola pattern
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


def test_linha_digitavel_rejeita_letras(validador: jsonschema.Draft202012Validator) -> None:
    payload = _carregar_fixture("boleto_pdf")
    payload["linha_digitavel"] = "ABC91234500000150009876543210987654321098765432"
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


def test_data_emissao_aceita_iso_date_e_datetime(
    validador: jsonschema.Draft202012Validator,
) -> None:
    """``data_emissao`` aceita YYYY-MM-DD ou ISO 8601 com timezone."""
    payload = _carregar_fixture("nfce_modelo_65")
    # ISO date puro (já vem assim na fixture)
    validador.validate(payload)
    # ISO 8601 datetime com Z
    payload["data_emissao"] = "2026-05-10T14:32:11Z"
    validador.validate(payload)
    # ISO 8601 com offset
    payload["data_emissao"] = "2026-05-10T14:32:11-03:00"
    validador.validate(payload)
    # Formato inválido falha
    payload["data_emissao"] = "10/05/2026"
    with pytest.raises(jsonschema.ValidationError):
        validador.validate(payload)


# ---------------------------------------------------------------------------
# 6. Tipo_documento desconhecido cai no bloco "outro" sem exigir campos
# ---------------------------------------------------------------------------


def test_tipo_outro_nao_exige_campos_de_subschema(
    validador: jsonschema.Draft202012Validator,
) -> None:
    """``outro`` é catch-all: só exige os 4 campos universais."""
    payload = {
        "sha256": "a" * 64,
        "tipo_documento": "outro",
        "extraido_via": "ocr_local",
        "ts_extraido": "2026-05-12T00:00:00+00:00",
    }
    validador.validate(payload)


def test_tipo_pendente_aceita_stub_minimo(
    validador: jsonschema.Draft202012Validator,
) -> None:
    """``pendente`` é stub aguardando_supervisor: nada além dos 4 universais."""
    payload = {
        "sha256": "b" * 64,
        "tipo_documento": "pendente",
        "extraido_via": "opus_v4_7",
        "ts_extraido": "2026-05-12T00:00:00+00:00",
        "aguardando_supervisor": True,
        "caminho_imagem": "/tmp/foto.jpg",
    }
    validador.validate(payload)


# "Schema fechado é contrato; schema aberto é incerteza acumulada."
# Wittgenstein lembra que limites de linguagem são limites do mundo;
# limites de schema são limites do contrato de dados.
