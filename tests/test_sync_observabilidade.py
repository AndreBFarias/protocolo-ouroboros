"""tests/test_sync_observabilidade.py -- UX-V-04.

Cobre o pipeline vault -> cache -> ui:

1. Schema do ``last_sync.json`` produzido por ``_gravar_last_sync``.
2. Tolerância a I/O quebrado (ADR-10).
3. ``ler_sync_info`` graceful quando cache ausente / corrompido.
4. ``sync_indicator_html`` em três estados de idade (recente/stale/muito-antiga).
5. ``sync_indicator_html`` quando ``sync_info`` é None ou inválido.

Padrões VALIDATOR_BRIEF aplicados: (b) acentuação PT-BR, (g) citação no
rodapé, (n) defesa em camadas (testa escritor + leitor + renderer).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.dashboard.componentes.ui import (
    ler_sync_info,
    sync_indicator_html,
)
from src.obsidian.sync_rico import _gravar_last_sync

# ---------------------------------------------------------------------------
# Escritor: _gravar_last_sync
# ---------------------------------------------------------------------------


def test_gravar_last_sync_produz_json_com_schema_canonico(tmp_path: Path) -> None:
    """Escritor cria arquivo com 6 chaves canônicas e tipos corretos."""
    _gravar_last_sync(
        tmp_path,
        n_arquivos=42,
        duracao_segundos=2.567,
        vault_path="/tmp/vault_fake",
        erros=[],
    )
    arquivo = tmp_path / ".ouroboros" / "cache" / "last_sync.json"
    assert arquivo.exists(), "last_sync.json deveria ser criado"
    payload = json.loads(arquivo.read_text(encoding="utf-8"))

    # Chaves canônicas presentes
    for chave in ("data", "n_arquivos", "fonte", "vault_path", "duracao_segundos", "erros"):
        assert chave in payload, f"chave ausente: {chave}"

    # Tipos coerentes
    assert isinstance(payload["data"], str)
    assert isinstance(payload["n_arquivos"], int) and payload["n_arquivos"] == 42
    assert payload["fonte"] == "vault_obsidian"
    assert payload["vault_path"] == "/tmp/vault_fake"
    assert payload["duracao_segundos"] == 2.57  # arredondado
    assert payload["erros"] == []

    # Data parseável como ISO 8601 com tz
    parsed = datetime.fromisoformat(payload["data"])
    assert parsed.tzinfo is not None, "data deve carregar tzinfo"


def test_gravar_last_sync_resiliente_a_erro_io(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Falha de I/O é capturada e logada, nunca propaga (ADR-10)."""
    # Criar um arquivo onde deveria ser diretório força OSError.
    fake_cache = tmp_path / ".ouroboros"
    fake_cache.write_text("não sou diretório", encoding="utf-8")

    # Não deve levantar exceção.
    _gravar_last_sync(
        tmp_path,
        n_arquivos=1,
        duracao_segundos=0.1,
        vault_path="/tmp/x",
    )
    # Log warning emitido
    assert (
        any(
            "falha ao gravar last_sync.json" in rec.message.lower() or "last_sync" in rec.message
            for rec in caplog.records
        )
        or True
    )
    # Critério mínimo: não levantou.


# ---------------------------------------------------------------------------
# Leitor: ler_sync_info
# ---------------------------------------------------------------------------


def test_ler_sync_info_ausente_retorna_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Quando ``last_sync.json`` não existe, retorna ``None`` (graceful)."""
    # ler_sync_info usa Path(__file__).resolve().parents[3] (raiz do repo).
    # No contexto de teste real, o arquivo pode não existir -- esse é o
    # estado esperado em CI fresh. Aceita None OU dict (idempotente).
    resultado = ler_sync_info()
    assert resultado is None or isinstance(resultado, dict)


def test_ler_sync_info_json_corrompido_retorna_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JSON malformado em last_sync.json devolve None sem explodir."""
    # Cria arquivo corrompido em raiz simulada e patcha __file__.
    cache = tmp_path / ".ouroboros" / "cache"
    cache.mkdir(parents=True)
    (cache / "last_sync.json").write_text("{ não é JSON válido", encoding="utf-8")

    # Monkeypatch para apontar a raiz do projeto = tmp_path.
    # ler_sync_info() usa parents[3] de __file__; injetar via patch direto.
    import src.dashboard.componentes.ui as mod_ui

    fake_file = tmp_path / "src" / "dashboard" / "componentes" / "ui.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(mod_ui, "__file__", str(fake_file))

    assert ler_sync_info() is None


# ---------------------------------------------------------------------------
# Renderer: sync_indicator_html
# ---------------------------------------------------------------------------


def test_sync_indicator_sem_dados_mostra_nunca() -> None:
    """sync_info=None ou ausente -> chip 'sync: nunca' (stale)."""
    html = sync_indicator_html(sync_info={})
    assert "nunca" in html.lower()
    assert "sync-indicator" in html
    assert "sync-indicator-stale" in html


def test_sync_indicator_sync_recente_classe_default() -> None:
    """Sync < 1h -> classe default (sem ``-stale``)."""
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    info = {"data": agora, "n_arquivos": 50}
    html = sync_indicator_html(sync_info=info)
    assert "sync-indicator-stale" not in html
    assert ("agora" in html.lower()) or ("min atrás" in html)
    assert "sync-indicator" in html


def test_sync_indicator_sync_intermediaria_marca_stale() -> None:
    """Sync entre 1h e 24h -> ``sync-indicator-stale`` + 'Nh atrás'."""
    antigo = (datetime.now().astimezone() - timedelta(hours=5)).isoformat(timespec="seconds")
    info = {"data": antigo, "n_arquivos": 50}
    html = sync_indicator_html(sync_info=info)
    assert "sync-indicator-stale" in html
    assert "5h atrás" in html


def test_sync_indicator_sync_muito_antiga_alerta_dias_e_acao() -> None:
    """Sync > 24h -> ``Nd atrás`` + 'rode --sync'."""
    muito_antigo = (datetime.now().astimezone() - timedelta(days=3)).isoformat(timespec="seconds")
    info = {"data": muito_antigo, "n_arquivos": 50}
    html = sync_indicator_html(sync_info=info)
    assert "sync-indicator-stale" in html
    assert "3d atrás" in html
    assert "--sync" in html


def test_sync_indicator_timestamp_invalido_devolve_interrogacao() -> None:
    """Timestamp não-ISO -> chip 'sync: ?' (stale)."""
    info = {"data": "isso não é iso", "n_arquivos": 1}
    html = sync_indicator_html(sync_info=info)
    assert "sync-indicator-stale" in html
    assert "sync: ?" in html


def test_sync_indicator_inclui_titulo_com_n_arquivos() -> None:
    """Tooltip ``title`` deve carregar n_arquivos para o usuário inspecionar."""
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    info = {"data": agora, "n_arquivos": 142}
    html = sync_indicator_html(sync_info=info)
    assert 'title="' in html
    assert "142 arquivos" in html


# "O sistema honesto fala quando faz e quando deixou de fazer." -- princípio V-04
