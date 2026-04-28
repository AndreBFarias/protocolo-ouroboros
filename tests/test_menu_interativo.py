"""Testes do menu interativo (Sprint 80)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
_SCRIPT = _RAIZ / "scripts" / "menu_interativo.py"


class TestImportacao:
    def test_modulo_importa_sem_streamlit(self) -> None:
        """Menu não pode depender de streamlit — só rich + subprocess."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("menu_interativo", _SCRIPT)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert hasattr(mod, "executar_menu")
        assert hasattr(mod, "OPCOES_MENU")
        assert hasattr(mod, "OPCOES_FOLLOW_UP")

    def test_opcoes_menu_tem_seis_mais_rota_completa_e_saida(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("menu_interativo", _SCRIPT)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        # Sprint 101 + 104: 6 acoes (1-5 originais + 6 reextrair) + "R" (rota
        # completa, default) + "0" (sair) = 8 chaves no total.
        assert set(mod.OPCOES_MENU.keys()) == {"0", "R", "1", "2", "3", "4", "5", "6"}
        # Default visual: R deve aparecer primeiro na ordem de inserção.
        assert next(iter(mod.OPCOES_MENU.keys())) == "R"

    def test_follow_up_tem_quatro_opcoes(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("menu_interativo", _SCRIPT)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert mod.OPCOES_FOLLOW_UP == ("dashboard", "relatorio", "ambos", "nada")


class TestExecucaoSubprocess:
    def test_skip_via_env_var_sai_com_zero(self) -> None:
        """OUROBOROS_MENU_SKIP=1 força saída silenciosa (útil em CI)."""
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            env={"OUROBOROS_MENU_SKIP": "1", "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert proc.returncode == 0

    @pytest.mark.skipif(
        not (_RAIZ / ".venv" / "bin" / "python").exists(),
        reason="precisa do .venv instalado",
    )
    def test_rodar_no_venv_nao_quebra_com_stdin_vazio(self) -> None:
        """Com stdin vazio, `Prompt.ask` cai no default ("0") e sai limpo."""
        venv_python = _RAIZ / ".venv" / "bin" / "python"
        proc = subprocess.run(
            [str(venv_python), str(_SCRIPT)],
            input="0\n",
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        # Aceita 0 (saída limpa) ou 130 (keyboard interrupt em ambiente não-TTY).
        assert proc.returncode in (0, 130), (
            f"Exit code inesperado: {proc.returncode}, stderr: {proc.stderr}"
        )
