"""Testes de `src/utils/segredos.py` (Sprint SEC-SENHAS-PARA-ENV).

Cobre carregamento de `.env`, falha-soft em ausência, lista de senhas
PDF com ordem canônica + extras alfabéticas.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _reload_segredos(monkeypatch, tmp_path: Path):
    """Reseta estado de cache `_ENV_CARREGADO` entre testes.

    Cada teste cria um `.env` próprio em `tmp_path` e aponta o módulo
    para esse path via monkeypatch. Limpa variáveis PDF_SENHA_* do
    ambiente para evitar contaminação cruzada.
    """
    # Limpa env vars de testes anteriores:
    import os
    chaves_a_remover = [k for k in list(os.environ) if k.startswith("PDF_SENHA_")]
    for k in chaves_a_remover:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.delenv("API_TOKEN_CUSTOM", raising=False)

    # Re-importa segredos.py para reset de _ENV_CARREGADO:
    from src.utils import segredos
    importlib.reload(segredos)
    monkeypatch.setattr(segredos, "_PATH_ENV", tmp_path / ".env")
    monkeypatch.setattr(segredos, "_ENV_CARREGADO", False)
    yield segredos


def test_segredo_devolve_default_se_chave_ausente(_reload_segredos):
    segredos = _reload_segredos
    assert segredos.segredo("CHAVE_INEXISTENTE", "default-x") == "default-x"


def test_segredo_le_env_arquivo(_reload_segredos, tmp_path: Path):
    """Arquivo .env é lido e popula os.environ."""
    segredos = _reload_segredos
    (tmp_path / ".env").write_text("API_TOKEN_CUSTOM=segredo-real\n", encoding="utf-8")
    assert segredos.segredo("API_TOKEN_CUSTOM") == "segredo-real"


def test_segredo_ignora_linha_comentario(_reload_segredos, tmp_path: Path):
    """Linhas começando com # são ignoradas."""
    segredos = _reload_segredos
    (tmp_path / ".env").write_text(
        "# comentario\nAPI_TOKEN_CUSTOM=valor\n# outro comentario\n",
        encoding="utf-8",
    )
    assert segredos.segredo("API_TOKEN_CUSTOM") == "valor"


def test_segredo_remove_aspas_envolventes(_reload_segredos, tmp_path: Path):
    """Aspas duplas ou simples em valor são removidas."""
    segredos = _reload_segredos
    (tmp_path / ".env").write_text(
        'API_TOKEN_CUSTOM="com-aspas"\n',
        encoding="utf-8",
    )
    assert segredos.segredo("API_TOKEN_CUSTOM") == "com-aspas"


def test_senhas_pdf_devolve_ordem_canonica(_reload_segredos, tmp_path: Path):
    segredos = _reload_segredos
    (tmp_path / ".env").write_text(
        "PDF_SENHA_PRIMARIA=p1\n"
        "PDF_SENHA_SECUNDARIA=p2\n"
        "PDF_SENHA_CPF=p3\n",
        encoding="utf-8",
    )
    assert segredos.senhas_pdf() == ["p1", "p2", "p3"]


def test_senhas_pdf_deduplica(_reload_segredos, tmp_path: Path):
    """Senhas idênticas não duplicam (extrai apenas valor único)."""
    segredos = _reload_segredos
    (tmp_path / ".env").write_text(
        "PDF_SENHA_PRIMARIA=mesma\n"
        "PDF_SENHA_SECUNDARIA=mesma\n"
        "PDF_SENHA_CPF=outra\n",
        encoding="utf-8",
    )
    assert segredos.senhas_pdf() == ["mesma", "outra"]


def test_senhas_pdf_inclui_extras_alfabetico(_reload_segredos, tmp_path: Path):
    """PDF_SENHA_* fora das canônicas entram em ordem alfabética após canônicas."""
    segredos = _reload_segredos
    (tmp_path / ".env").write_text(
        "PDF_SENHA_PRIMARIA=p1\n"
        "PDF_SENHA_ZULU=z\n"
        "PDF_SENHA_ALPHA=a\n",
        encoding="utf-8",
    )
    # Esperado: canônica primeiro (p1), depois extras alfabéticas (a, z)
    assert segredos.senhas_pdf() == ["p1", "a", "z"]


def test_senhas_pdf_vazio_quando_nenhum_configurado(_reload_segredos):
    segredos = _reload_segredos
    assert segredos.senhas_pdf() == []


def test_carregar_env_idempotente(_reload_segredos, tmp_path: Path):
    """Chamar _carregar_env_uma_vez 2x não recarrega arquivo."""
    segredos = _reload_segredos
    (tmp_path / ".env").write_text("PDF_SENHA_PRIMARIA=valor1\n", encoding="utf-8")
    segredos._carregar_env_uma_vez()
    # Modifica arquivo direto, sem trigger:
    (tmp_path / ".env").write_text("PDF_SENHA_PRIMARIA=valor2\n", encoding="utf-8")
    segredos._carregar_env_uma_vez()  # Não deve recarregar
    # Valor1 prevalece (cache):
    assert segredos.segredo("PDF_SENHA_PRIMARIA") == "valor1"


# "Segredo guardado em arquivo é segredo confiado a quem o lê." -- princípio
