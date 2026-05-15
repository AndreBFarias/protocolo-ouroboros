"""Testes da página dashboard `src/dashboard/paginas/graduacao_tipos.py`.

Sprint UX-DASH-GRADUACAO-TIPOS-2026-05-15. Foco em: carregamento de dados,
KPIs corretos contra graduacao_tipos.json + tipos_documento.yaml, snapshot
trigger via subprocess (mockado), e listagem de tipos sem dossiê físico.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from src.dashboard.paginas import graduacao_tipos


@pytest.fixture
def fixtures_minimas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cria YAML + graduacao_tipos.json + estrutura de dossiês sintéticos."""
    yaml = tmp_path / "tipos.yaml"
    yaml.write_text(
        "tipos:\n"
        "  - id: tipo_a\n"
        '    aliases_graduacao: ["tipo_a_legacy"]\n'
        "  - id: tipo_b\n"
        "  - id: tipo_sem_dossie\n",
        encoding="utf-8",
    )
    grad = tmp_path / "graduacao_tipos.json"
    grad.write_text(
        json.dumps(
            {
                "gerado_em": "2026-05-15T00:00:00+00:00",
                "tipos": {
                    "tipo_a": {
                        "status": "GRADUADO",
                        "amostras_ok": 3,
                        "divergencias_ativas": 0,
                        "historico_divergencias_count": 2,
                        "dossie_path": "tipo_a_legacy",
                        "atualizado_em": "2026-05-15T00:00:00+00:00",
                    },
                    "tipo_b": {
                        "status": "PENDENTE",
                        "amostras_ok": 0,
                        "divergencias_ativas": 0,
                        "historico_divergencias_count": 0,
                        "dossie_path": "tipo_b",
                        "atualizado_em": "2026-05-15T00:00:00+00:00",
                    },
                },
                "totais": {
                    "PENDENTE": 1,
                    "CALIBRANDO": 0,
                    "GRADUADO": 1,
                    "REGREDINDO": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(graduacao_tipos, "PATH_GRADUACAO", grad)
    monkeypatch.setattr(graduacao_tipos, "PATH_TIPOS_YAML", yaml)
    monkeypatch.setattr(graduacao_tipos, "DIR_DOSSIES", tmp_path / "dossies")
    return tmp_path


def test_carregar_dados_total_e_kpis_consistentes(fixtures_minimas: Path) -> None:
    d = graduacao_tipos._carregar_dados()
    # 3 tipos no YAML; tipo_sem_dossie cai em PENDENTE via fallback.
    assert d["total"] == 3
    assert d["graduados"] == 1  # tipo_a
    assert d["pendentes"] == 2  # tipo_b + tipo_sem_dossie
    assert d["calibrando"] == 0
    assert d["regredindo"] == 0
    # KPIs somam total
    assert (
        d["graduados"] + d["pendentes"] + d["calibrando"] + d["regredindo"]
        == d["total"]
    )


def test_carregar_dados_resolve_alias_no_listing(fixtures_minimas: Path) -> None:
    """Linhas devem mostrar `tipo_a` (canônico) com alias 'tipo_a_legacy'."""
    d = graduacao_tipos._carregar_dados()
    linha_a = next(linha for linha in d["linhas"] if linha["tipo"] == "tipo_a")
    assert linha_a["alias"] == "tipo_a_legacy"
    assert linha_a["dossie_path"] == "tipo_a_legacy"
    # Tipo sem dossiê e sem alias: campo alias mostra travessão.
    linha_sem = next(
        linha for linha in d["linhas"] if linha["tipo"] == "tipo_sem_dossie"
    )
    assert linha_sem["alias"] == "—"
    assert linha_sem["status"] == "PENDENTE"


def test_carregar_dados_grad_json_ausente_devolve_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quando snapshot não existe ainda, _carregar_dados retorna estrutura vazia."""
    monkeypatch.setattr(
        graduacao_tipos, "PATH_GRADUACAO", tmp_path / "nao_existe.json"
    )
    monkeypatch.setattr(
        graduacao_tipos, "PATH_TIPOS_YAML", tmp_path / "nao_existe.yaml"
    )
    d = graduacao_tipos._carregar_dados()
    assert d["total"] == 0
    assert d["graduados"] == 0
    assert d["linhas"] == []


def test_trigger_snapshot_chama_script(fixtures_minimas: Path) -> None:
    """_trigger_snapshot invoca scripts/dossie_tipo.py snapshot via subprocess."""
    fake_completed = mock.MagicMock()
    fake_completed.returncode = 0
    fake_completed.stdout = "Snapshot: ..."
    fake_completed.stderr = ""
    with mock.patch("subprocess.run", return_value=fake_completed) as mocked:
        ok, msg = graduacao_tipos._trigger_snapshot()
    assert ok is True
    assert "Snapshot" in msg
    args, kwargs = mocked.call_args
    assert "snapshot" in args[0]
    assert kwargs.get("timeout") == 30


# "Tabela viva é compromisso: o que aparece aqui é o que de fato existe."
# -- princípio do painel honesto
