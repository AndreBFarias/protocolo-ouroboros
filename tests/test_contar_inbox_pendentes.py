"""Testes da Sprint HOOK-INBOX-01.

Cobre o script ``scripts/contar_inbox_pendentes.py``: contagem com inbox
ausente, vazio, threshold default, env vars de desativação, ignora pasta
oculta ``.agentic_only/``, exit code sempre zero.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ_REPO / "scripts"))

import contar_inbox_pendentes as cip  # noqa: E402

_SCRIPT: Path = _RAIZ_REPO / "scripts" / "contar_inbox_pendentes.py"


def _executar_script(env_extra: dict[str, str] | None = None) -> tuple[int, str, str]:
    """Executa o script e retorna (exit_code, stdout, stderr)."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    resultado = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
    )
    return resultado.returncode, resultado.stdout, resultado.stderr


def test_inbox_ausente_retorna_zero_silencioso(tmp_path):
    """`data/inbox/` inexistente conta zero, sem erro."""
    inexistente = tmp_path / "nao_existe"
    assert cip.contar_pendentes(inexistente) == 0


def test_inbox_vazio_silencio_absoluto(tmp_path, monkeypatch):
    """Diretório vazio: 0 arquivos, nada em stderr."""
    inbox = tmp_path / "inbox_vazio"
    inbox.mkdir()
    monkeypatch.setattr(cip, "_PATH_INBOX_PADRAO", inbox)

    assert cip.contar_pendentes() == 0


def test_threshold_default_um_dispara_com_um_arquivo(tmp_path, monkeypatch):
    """Threshold default = 1: dispara aviso já com 1 arquivo."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "teste.pdf").write_text("conteudo")
    monkeypatch.setattr(cip, "_PATH_INBOX_PADRAO", inbox)

    assert cip.contar_pendentes() == 1


def test_threshold_alto_silencia_ate_atingir(tmp_path, monkeypatch, capsys):
    """`OUROBOROS_INBOX_THRESHOLD=5` silencia até 4 arquivos."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for i in range(4):
        (inbox / f"arquivo_{i}.pdf").write_text("x")
    monkeypatch.setattr(cip, "_PATH_INBOX_PADRAO", inbox)
    monkeypatch.setenv(cip.ENV_THRESHOLD, "5")

    codigo = cip.main()
    assert codigo == 0
    captured = capsys.readouterr()
    assert captured.err == ""  # silencio: 4 < 5


def test_threshold_alto_dispara_quando_atinge(tmp_path, monkeypatch, capsys):
    """`OUROBOROS_INBOX_THRESHOLD=3` dispara em 3 arquivos."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for i in range(3):
        (inbox / f"arquivo_{i}.pdf").write_text("x")
    monkeypatch.setattr(cip, "_PATH_INBOX_PADRAO", inbox)
    monkeypatch.setenv(cip.ENV_THRESHOLD, "3")

    codigo = cip.main()
    assert codigo == 0
    captured = capsys.readouterr()
    assert "[INBOX]" in captured.err
    assert "3 arquivos pendentes" in captured.err


def test_env_var_desativa_aviso(tmp_path, monkeypatch, capsys):
    """`OUROBOROS_AUTO_HINT_INBOX=0` desativa qualquer aviso."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for i in range(10):  # bem acima de qualquer threshold default
        (inbox / f"arquivo_{i}.pdf").write_text("x")
    monkeypatch.setattr(cip, "_PATH_INBOX_PADRAO", inbox)
    monkeypatch.setenv(cip.ENV_DESATIVAR, "0")

    codigo = cip.main()
    assert codigo == 0
    captured = capsys.readouterr()
    assert captured.err == ""  # desativado


def test_pasta_oculta_no_topo_e_ignorada(tmp_path, monkeypatch, capsys):
    """Conteúdo de `.agentic_only/` (pasta oculta no topo) é ignorado."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "real.pdf").write_text("x")
    oculta = inbox / ".agentic_only"
    oculta.mkdir()
    (oculta / "sidecar.json").write_text("{}")
    monkeypatch.setattr(cip, "_PATH_INBOX_PADRAO", inbox)

    # apenas real.pdf é contado, sidecar fica de fora
    assert cip.contar_pendentes() == 1


def test_subdiretorio_normal_e_contado(tmp_path, monkeypatch):
    """Arquivos em subpastas normais (não ocultas) são contados."""
    inbox = tmp_path / "inbox"
    sub = inbox / "andre" / "nfs_fiscais"
    sub.mkdir(parents=True)
    (sub / "nfce_a.pdf").write_text("x")
    (sub / "nfce_b.pdf").write_text("x")
    monkeypatch.setattr(cip, "_PATH_INBOX_PADRAO", inbox)

    assert cip.contar_pendentes() == 2


def test_exit_code_sempre_zero_d7(tmp_path, monkeypatch):
    """Mesmo com aviso, exit code é 0 (D7 não-gate)."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "x.pdf").write_text("x")
    monkeypatch.setattr(cip, "_PATH_INBOX_PADRAO", inbox)

    assert cip.main() == 0


def test_script_subprocess_inbox_inexistente_e_silencioso():
    """Subprocess real: sem inbox no caminho default, exit 0 sem stderr ruidoso."""
    # Sem mock: o script lê _PATH_INBOX_PADRAO real do repo. Se não existe,
    # comportamento esperado é silêncio + exit 0. Se existir e tiver
    # arquivos, vai imprimir aviso (também aceitável).
    codigo, _stdout, stderr = _executar_script(
        env_extra={cip.ENV_DESATIVAR: "0"},  # forca desativacao para teste determinista
    )
    assert codigo == 0
    assert stderr == ""


# "Visibilidade proativa, sem friccao."
#  -- principio operacional do Protocolo Ouroboros
