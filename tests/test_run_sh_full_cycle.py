"""Testes do modo --full-cycle do run.sh (Sprint 101).

Cobre apenas o contrato do shell wrapper: help mostra o modo, exemplo
está documentado, branch de case existe e regressões nos modos antigos
(--inbox, --tudo) continuam intactas. Nenhum teste invoca o pipeline
real --- isso é trabalho de make smoke / gauntlet.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
_RUN_SH = _RAIZ / "run.sh"


@pytest.fixture(scope="module")
def conteudo_run_sh() -> str:
    return _RUN_SH.read_text(encoding="utf-8")


class TestContratoFonte:
    def test_branch_case_full_cycle_existe(self, conteudo_run_sh: str) -> None:
        """O case --full-cycle precisa existir explicitamente em run.sh."""
        assert "--full-cycle)" in conteudo_run_sh, (
            "Sprint 101: branch --full-cycle não está registrado em run.sh"
        )

    def test_branch_case_inbox_continua_existindo(self, conteudo_run_sh: str) -> None:
        """Regression: --inbox separado segue funcional."""
        assert "--inbox)" in conteudo_run_sh

    def test_branch_case_tudo_continua_existindo(self, conteudo_run_sh: str) -> None:
        """Regression: --tudo separado segue funcional."""
        assert "--tudo)" in conteudo_run_sh

    def test_full_cycle_aborta_se_inbox_falhar(self, conteudo_run_sh: str) -> None:
        """Acceptance: ciclo completo deve parar se inbox falhar.

        Procura padrão idiomático de aborto dentro do bloco --full-cycle:
        algum exit 1 ou erro explícito após inbox.
        """
        match = re.search(
            r"--full-cycle\)(.*?)(?=\n\s+--[\w-]+\)|\nesac)",
            conteudo_run_sh,
            re.DOTALL,
        )
        assert match is not None, "Bloco --full-cycle não encontrado"
        bloco = match.group(1)
        assert "inbox_processor" in bloco, "Inbox não é invocada no full-cycle"
        assert "exit 1" in bloco or "abortando" in bloco.lower(), (
            "full-cycle não declara aborto explícito quando inbox falha"
        )

    def test_help_lista_full_cycle(self, conteudo_run_sh: str) -> None:
        """Acceptance: --help/-h precisa mencionar --full-cycle."""
        # Busca a função exibir_help
        match = re.search(r"exibir_help\(\)\s*\{(.*?)\n\}", conteudo_run_sh, re.DOTALL)
        assert match is not None, "Função exibir_help não encontrada"
        corpo_help = match.group(1)
        assert "--full-cycle" in corpo_help, "exibir_help não menciona --full-cycle"

    def test_menu_interativo_bash_tem_opcao_R(self, conteudo_run_sh: str) -> None:
        """Acceptance: menu bash tem 'R Rota completa'."""
        assert "Rota completa" in conteudo_run_sh
        assert "acao_rota_completa" in conteudo_run_sh


class TestExecucaoHelp:
    @pytest.mark.skipif(
        not (_RAIZ / ".venv" / "bin" / "python").exists(),
        reason="precisa do .venv instalado",
    )
    def test_run_sh_help_renderiza_full_cycle(self) -> None:
        """Roda `./run.sh --help` de verdade e confere que cita --full-cycle."""
        proc = subprocess.run(
            ["bash", str(_RUN_SH), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd=str(_RAIZ),
        )
        assert proc.returncode == 0, (
            f"run.sh --help falhou: rc={proc.returncode}, stderr={proc.stderr}"
        )
        assert "--full-cycle" in proc.stdout, (
            f"--help não cita --full-cycle. stdout: {proc.stdout!r}"
        )


class TestMenuInterativo:
    def test_python_menu_tem_acao_rota_completa(self) -> None:
        """O dispatcher Python expõe a chave 'R' apontando para rota completa."""
        import importlib.util

        script = _RAIZ / "scripts" / "menu_interativo.py"
        spec = importlib.util.spec_from_file_location("menu_interativo", script)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert "R" in mod.OPCOES_MENU
        assert "Rota completa" in mod.OPCOES_MENU["R"]
        assert "R" in mod._DISPATCHER  # noqa: SLF001 -- inspeção legítima de teste


# "Um comando é melhor que dois quando ambos são sempre rodados juntos."
# -- princípio do menor atrito (Sprint 101)
