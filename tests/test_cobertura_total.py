"""Testes da Sprint META-COBERTURA-TOTAL-01.

Cobre:
  - Contrato ``ResultadoExtracao`` em ``src.extractors.base``.
  - Lint estático ``scripts/check_cobertura_total.py``.
  - Auditoria ``scripts/auditar_cobertura_total.py`` (modo dry-run).

Decisão D7 do dono em 2026-04-29: extrair tudo das imagens e pdfs, cada
valor, catalogar tudo. Estes testes guardam o invariante.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from src.extractors.base import ResultadoExtracao

_RAIZ_REPO = Path(__file__).resolve().parents[1]
_SCRIPT_LINT = _RAIZ_REPO / "scripts" / "check_cobertura_total.py"
_SCRIPT_AUDITAR = _RAIZ_REPO / "scripts" / "auditar_cobertura_total.py"


# ---------------------------------------------------------------------------
# ResultadoExtracao -- contrato canônico
# ---------------------------------------------------------------------------


def test_cobertura_zero_potencial_retorna_um():
    """Sem valores potenciais, cobertura é considerada plena (1.0)."""
    r = ResultadoExtracao()
    assert r.cobertura == 1.0


def test_cobertura_calculo_simples():
    """Razão valores_extraidos / valores_potenciais."""
    r = ResultadoExtracao(valores_extraidos=8, valores_potenciais=10)
    assert r.cobertura == pytest.approx(0.8)


def test_validar_aprova_quando_acima_do_minimo():
    """Cobertura >= cobertura_minima retorna True sem warning."""
    r = ResultadoExtracao(
        valores_extraidos=19,
        valores_potenciais=20,
        cobertura_minima=0.95,
    )
    assert r.validar() is True


def test_validar_reprova_e_emite_warning(caplog):
    """Cobertura abaixo do mínimo retorna False e dispara warning estruturado."""
    logger = logging.getLogger("teste_d7")
    r = ResultadoExtracao(
        valores_extraidos=5,
        valores_potenciais=10,
        cobertura_minima=0.95,
        tipo_documento="nfce_modelo_65",
        arquivo_origem="cupom_X.pdf",
    )
    with caplog.at_level(logging.WARNING, logger="teste_d7"):
        ok = r.validar(logger=logger)
    assert ok is False
    assert any(
        "[D7] cobertura abaixo do mínimo" in registro.message
        for registro in caplog.records
    )


def test_validar_aprova_quando_potencial_zero():
    """Potencial=0 e extraidos=0 são tratados como cobertura plena."""
    r = ResultadoExtracao(valores_extraidos=0, valores_potenciais=0)
    assert r.validar() is True


# ---------------------------------------------------------------------------
# Lint estático -- check_cobertura_total.py
# ---------------------------------------------------------------------------


def _rodar_lint_em_arquivo_temporario(tmp_path: Path, conteudo: str) -> tuple[int, str]:
    """Roda o lint apontando para um diretório temporário com 1 arquivo.py.

    Aproveita que o lint expõe ``auditar_arquivo`` -- chamamos diretamente sem
    monkeypatch da raiz. Mais robusto que reescrever caminho.
    """
    sys.path.insert(0, str(_RAIZ_REPO / "scripts"))
    try:
        import importlib

        modulo = importlib.import_module("check_cobertura_total")
    finally:
        sys.path.pop(0)
    arquivo = tmp_path / "extrator_falso.py"
    arquivo.write_text(conteudo, encoding="utf-8")
    violacoes = modulo.auditar_arquivo(arquivo)
    return len(violacoes), "\n".join(v.motivo for v in violacoes)


def test_lint_detecta_extrair_com_return_vazio_silencioso(tmp_path):
    """Função `extrair` que termina em `return []` sem logger é violação."""
    conteudo = textwrap.dedent(
        """
        def extrair():
            x = 1
            return []
        """
    ).strip()
    qtd, motivo = _rodar_lint_em_arquivo_temporario(tmp_path, conteudo)
    assert qtd == 1
    assert "return []" in motivo


def test_lint_aceita_extrair_com_logger_warning(tmp_path):
    """Função `extrair` com logger.warning antes do `return []` é OK."""
    conteudo = textwrap.dedent(
        """
        import logging
        logger = logging.getLogger(__name__)

        def extrair():
            logger.warning('algo deu errado')
            return []
        """
    ).strip()
    qtd, _motivo = _rodar_lint_em_arquivo_temporario(tmp_path, conteudo)
    assert qtd == 0


def test_lint_ignora_funcao_sem_prefixo_extrair(tmp_path):
    """Apenas funções com prefixo 'extrair', 'parsear', '_parse', '_extrair'."""
    conteudo = textwrap.dedent(
        """
        def helper():
            return []
        """
    ).strip()
    qtd, _motivo = _rodar_lint_em_arquivo_temporario(tmp_path, conteudo)
    assert qtd == 0


def test_lint_subprocess_em_extratores_reais_passa():
    """Roda o lint via subprocess sobre src/extractors/ real -- baseline 0 violações."""
    res = subprocess.run(
        [sys.executable, str(_SCRIPT_LINT)],
        capture_output=True,
        text=True,
        check=False,
    )
    # Atualmente baseline é 0 violações; se subir aqui é porque alguém regrediu.
    assert res.returncode == 0, f"lint falhou: {res.stdout}{res.stderr}"


# ---------------------------------------------------------------------------
# Auditoria -- auditar_cobertura_total.py
# ---------------------------------------------------------------------------


def test_auditar_dry_run_imprime_sumario():
    """Modo dry-run imprime sumario sem gravar arquivo."""
    res = subprocess.run(
        [sys.executable, str(_SCRIPT_AUDITAR)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    assert "[D7]" in res.stdout
    assert "extratores" in res.stdout
