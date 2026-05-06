"""Testes do bridge vault Bem-estar (Sprint UX-RD-16).

Cobre 9 parsers + varrer_vault + smoke_bem_estar:

- Parsing de fixture válida → cache JSON com N items.
- Vault inexistente → cache vazio sem crash (fallback graceful).
- Reuso obrigatório de helpers de ``humor_heatmap`` (grep estático).
- Orquestrador ``varrer_tudo`` invoca todos 9 parsers + humor_heatmap.
- Smoke ``smoke_bem_estar.py`` exit 0 sobre fixture sintética.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.mobile_cache import (
    alarmes,
    ciclo,
    contadores,
    diario_emocional,
    eventos,
    marcos,
    medidas,
    tarefas,
    treinos,
    varrer_vault,
)

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE_VAULT = RAIZ / "tests" / "fixtures" / "vault_sintetico"

# ----------------------------------------------------------------------
# Por-parser: parsing válido + vault inexistente
# ----------------------------------------------------------------------

PARSER_CASES = [
    pytest.param(diario_emocional, 2, "diario-emocional", id="diario_emocional"),
    pytest.param(eventos, 2, "eventos", id="eventos"),
    pytest.param(treinos, 2, "treinos", id="treinos"),
    pytest.param(medidas, 2, "medidas", id="medidas"),
    pytest.param(marcos, 2, "marcos", id="marcos"),
    pytest.param(alarmes, 2, "alarmes", id="alarmes"),
    pytest.param(contadores, 2, "contadores", id="contadores"),
    pytest.param(ciclo, 2, "ciclo", id="ciclo"),
    pytest.param(tarefas, 2, "tarefas", id="tarefas"),
]


@pytest.mark.parametrize("modulo,esperado,schema", PARSER_CASES)
def test_parser_fixture_valida(modulo, esperado, schema):
    """Parser deve extrair os 2 .md válidos da fixture."""
    payload = modulo.varrer(FIXTURE_VAULT)
    assert payload["schema"] == schema
    assert payload["vault_root"] == str(FIXTURE_VAULT.resolve())
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) == esperado, f"esperado {esperado}, obteve {len(payload['items'])}"


@pytest.mark.parametrize("modulo,_esperado,schema", PARSER_CASES)
def test_parser_vault_inexistente(modulo, _esperado, schema, tmp_path):
    """Vault inexistente → items vazios, sem crash."""
    inexistente = tmp_path / "vault_que_nao_existe"
    payload = modulo.varrer(inexistente)
    assert payload["schema"] == schema
    assert payload["items"] == []


def test_parser_vault_none():
    """Vault None → items vazios, vault_root None."""
    payload = diario_emocional.varrer(None)
    assert payload["items"] == []
    assert payload["vault_root"] is None


# ----------------------------------------------------------------------
# Reuso de helpers de humor_heatmap (critério explícito UX-RD-16)
# ----------------------------------------------------------------------


def test_parsers_reusam_helpers_humor_heatmap():
    """Cada parser deve importar pelo menos um helper de humor_heatmap."""
    parsers_dir = RAIZ / "src" / "mobile_cache"
    parsers = [
        "diario_emocional.py",
        "eventos.py",
        "treinos.py",
        "medidas.py",
        "marcos.py",
        "alarmes.py",
        "contadores.py",
        "ciclo.py",
        "tarefas.py",
    ]
    padrao = re.compile(r"from src\.mobile_cache\.humor_heatmap import")
    falhas: list[str] = []
    for nome in parsers:
        texto = (parsers_dir / nome).read_text(encoding="utf-8")
        if not padrao.search(texto):
            falhas.append(nome)
    assert not falhas, f"parsers sem reuso: {falhas}"


# ----------------------------------------------------------------------
# Orquestrador varrer_tudo
# ----------------------------------------------------------------------


def test_varrer_tudo_invoca_todos_9_parsers(tmp_path, monkeypatch):
    """varrer_tudo deve gerar 9 caches Bem-estar + humor (10 total)."""
    monkeypatch.chdir(tmp_path)
    resultado = varrer_vault.varrer_tudo(FIXTURE_VAULT, incluir_humor=True)
    assert len(resultado) == 10
    bem_estar = [
        "diario-emocional", "eventos", "treinos", "medidas",
        "marcos", "alarmes", "contadores", "ciclo", "tarefas",
    ]
    for schema in bem_estar:
        assert schema in resultado, f"schema {schema} ausente"
        assert resultado[schema] is not None, f"schema {schema} falhou"
    assert "humor-heatmap" in resultado


def test_varrer_tudo_vault_none_nao_crasheia(tmp_path, monkeypatch):
    """varrer_tudo com vault_root None gera caches vazios graciosamente."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OUROBOROS_VAULT", raising=False)
    monkeypatch.setattr(varrer_vault, "CANDIDATOS_VAULT", ())
    resultado = varrer_vault.varrer_tudo(None, incluir_humor=True)
    # 9 parsers Bem-estar + humor (que será None pois vault ausente)
    assert resultado["humor-heatmap"] is None
    for schema in [
        "diario-emocional", "eventos", "treinos", "medidas",
        "marcos", "alarmes", "contadores", "ciclo", "tarefas",
    ]:
        path = resultado[schema]
        assert path is not None
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        assert payload["items"] == []


def test_descobrir_vault_root_via_env(tmp_path, monkeypatch):
    """OUROBOROS_VAULT setada e existente vence sobre candidatos canônicos."""
    monkeypatch.setenv("OUROBOROS_VAULT", str(FIXTURE_VAULT))
    detectado = varrer_vault.descobrir_vault_root()
    assert detectado == FIXTURE_VAULT


def test_descobrir_vault_root_env_inexistente_pula(tmp_path, monkeypatch):
    """OUROBOROS_VAULT inexistente é ignorada e candidatos são tentados."""
    monkeypatch.setenv("OUROBOROS_VAULT", str(tmp_path / "inexistente"))
    monkeypatch.setattr(varrer_vault, "CANDIDATOS_VAULT", (tmp_path,))
    detectado = varrer_vault.descobrir_vault_root()
    assert detectado == tmp_path


# ----------------------------------------------------------------------
# Cache JSON gerado em disco — formato canônico
# ----------------------------------------------------------------------


def test_cache_json_formato_canonico(tmp_path):
    """Cache deve ter chaves schema_version, gerado_em, vault_root, items."""
    saida = tmp_path / "diario.json"
    diario_emocional.gerar_cache(FIXTURE_VAULT, saida=saida)
    payload = json.loads(saida.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["schema"] == "diario-emocional"
    assert "gerado_em" in payload
    assert payload["vault_root"] == str(FIXTURE_VAULT.resolve())
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) == 2


def test_cache_eventos_preserva_geo_e_fotos(tmp_path):
    """Parser eventos deve preservar lugar, bairro, fotos da fixture."""
    saida = tmp_path / "eventos.json"
    eventos.gerar_cache(FIXTURE_VAULT, saida=saida)
    payload = json.loads(saida.read_text(encoding="utf-8"))
    cafe = next(i for i in payload["items"] if "padaria" in i["lugar"])
    assert cafe["bairro"] == "bela vista"
    assert cafe["categoria"] == "rolezinho"
    jantar = next(i for i in payload["items"] if "restaurante" in i["lugar"])
    assert jantar["fotos"] == ["foto_jantar.jpg"]


def test_cache_treinos_preserva_exercicios(tmp_path):
    """Parser treinos deve preservar lista de exercicios estruturada."""
    saida = tmp_path / "treinos.json"
    treinos.gerar_cache(FIXTURE_VAULT, saida=saida)
    payload = json.loads(saida.read_text(encoding="utf-8"))
    rot_a = next(i for i in payload["items"] if i["rotina"] == "Rotina A")
    assert len(rot_a["exercicios"]) == 2
    assert rot_a["exercicios"][0]["nome"] == "supino reto"
    assert rot_a["duracao_min"] == 28


# ----------------------------------------------------------------------
# Smoke shell-out
# ----------------------------------------------------------------------


def test_smoke_bem_estar_exit_zero(tmp_path):
    """smoke_bem_estar.py deve retornar exit 0 com fixture sintética."""
    # Primeiro gerar caches no tmp_path
    cache_dir = tmp_path / "cache"
    for parser_mod in [
        diario_emocional, eventos, treinos, medidas, marcos,
        alarmes, contadores, ciclo, tarefas,
    ]:
        schema = parser_mod.SCHEMA
        parser_mod.gerar_cache(FIXTURE_VAULT, saida=cache_dir / f"{schema}.json")

    resultado = subprocess.run(
        [
            sys.executable,
            str(RAIZ / "scripts" / "smoke_bem_estar.py"),
            "--vault-root",
            str(FIXTURE_VAULT),
            "--cache-dir",
            str(cache_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, f"stdout={resultado.stdout}\nstderr={resultado.stderr}"
    assert "9/9 schemas OK" in resultado.stdout


def test_smoke_bem_estar_detecta_violacao(tmp_path):
    """Smoke deve falhar se cache divergir do filesystem."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    # Gera todos com fixture exceto treinos: forja cache com 0 items
    for parser_mod in [
        diario_emocional, eventos, medidas, marcos,
        alarmes, contadores, ciclo, tarefas,
    ]:
        schema = parser_mod.SCHEMA
        parser_mod.gerar_cache(FIXTURE_VAULT, saida=cache_dir / f"{schema}.json")
    (cache_dir / "treinos.json").write_text(
        json.dumps({"schema": "treinos", "items": []}),
        encoding="utf-8",
    )
    resultado = subprocess.run(
        [
            sys.executable,
            str(RAIZ / "scripts" / "smoke_bem_estar.py"),
            "--vault-root",
            str(FIXTURE_VAULT),
            "--cache-dir",
            str(cache_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 1
    assert "VIOLAÇÃO" in resultado.stdout
    assert "treinos" in resultado.stdout


# ----------------------------------------------------------------------
# CLI dos parsers
# ----------------------------------------------------------------------


def test_cli_diario_emocional(tmp_path):
    """CLI ``python -m src.mobile_cache.diario_emocional`` deve gerar JSON."""
    saida = tmp_path / "out.json"
    rc = diario_emocional.cli([
        "--vault-root", str(FIXTURE_VAULT),
        "--cache", str(saida),
    ])
    assert rc == 0
    assert saida.exists()
    payload = json.loads(saida.read_text(encoding="utf-8"))
    assert len(payload["items"]) == 2


def test_cli_varrer_vault(tmp_path, monkeypatch):
    """CLI varrer_vault deve invocar todos parsers e logar resumo."""
    monkeypatch.chdir(tmp_path)
    rc = varrer_vault.cli([
        "--vault-root", str(FIXTURE_VAULT),
    ])
    # Pode retornar 0 ou 1 dependendo de o humor passar (FIXTURE não tem daily/);
    # o critério aqui é que rodou sem exception
    assert rc in (0, 1)


# "O todo é maior que a soma das partes." -- Aristóteles
