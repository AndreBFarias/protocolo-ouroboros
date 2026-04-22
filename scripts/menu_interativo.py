"""Menu interativo do Protocolo Ouroboros (Sprint 80).

Oferece um menu em rich.Prompt com 5 ações principais e uma pergunta
de follow-up (dashboard? relatório? ambos? nada?) após cada ação que
altera o estado do pipeline. Substitui o dispatch cru de flags quando
o usuário roda `./run.sh` sem argumentos.

Arquitetura:

  - Cada ação é uma função `_acao_*` que retorna `True` quando a ação
    foi *disruptiva* (alterou dados, ex: processou inbox) e portanto
    faz sentido oferecer follow-up.
  - `_perguntar_proximo_passo()` usa `rich.prompt.Prompt` com `choices`
    restritas; em input inválido (não interativo / redirecionado) cai
    no default "nada" silenciosamente.
  - Todas as ações pesadas (`./run.sh --inbox`, `--tudo`, `--dashboard`)
    são invocadas como subprocessos para reaproveitar o código bash
    existente em `run.sh` (não reescrevemos o que já funciona).

CLI:

    .venv/bin/python scripts/menu_interativo.py

Uso típico (a partir do shell wrapper):

    ./run.sh           # sem args -> menu Python se stdin é terminal

Em pipes (CI, testes), o menu lê a escolha do stdin. `echo "0" | ...`
sai limpo com código 0.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.prompt import Prompt

    _RICH_DISPONIVEL = True
except ImportError:  # pragma: no cover — rich é dep obrigatória
    _RICH_DISPONIVEL = False
    Console = None  # type: ignore[assignment,misc]
    Prompt = None  # type: ignore[assignment,misc]


_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
_RUN_SH: Path = _RAIZ_REPO / "run.sh"


OPCOES_MENU: dict[str, str] = {
    "1": "Processar Inbox (vault + legado)",
    "2": "Abrir Dashboard (Streamlit)",
    "3": "Gerar Relatório do mês",
    "4": "Sincronizar com Obsidian",
    "5": "Tudo (inbox + pipeline + sync)",
    "0": "Sair",
}

OPCOES_FOLLOW_UP: tuple[str, ...] = ("dashboard", "relatorio", "ambos", "nada")


# ============================================================================
# Helpers
# ============================================================================


def _console() -> "Console":
    if not _RICH_DISPONIVEL:
        raise RuntimeError(
            "Sprint 80 exige `rich` instalado no venv. Rode `./install.sh` para corrigir."
        )
    return Console()


def _rodar_run_sh(*args: str) -> int:
    """Executa `run.sh` com args e retorna o código de saída."""
    cmd = ["bash", str(_RUN_SH), *args]
    proc = subprocess.run(cmd, cwd=str(_RAIZ_REPO), check=False)
    return proc.returncode


def _prompt(msg: str, choices: list[str], default: str) -> str:
    """Wrapper de `Prompt.ask` que tolera stdin não-interativo."""
    if not _RICH_DISPONIVEL:
        return default
    try:
        return Prompt.ask(msg, choices=choices, default=default, show_default=True)
    except EOFError:
        return default


# ============================================================================
# Ações
# ============================================================================


def _acao_inbox() -> bool:
    _console().print("[cyan]Processando inbox unificada (Sprint 70)...[/]")
    _rodar_run_sh("--inbox")
    return True


def _acao_dashboard() -> bool:
    _console().print("[cyan]Abrindo dashboard Streamlit...[/]")
    _rodar_run_sh("--dashboard")
    return False


def _acao_relatorio() -> bool:
    _console().print(
        "[yellow]Relatório gerado automaticamente pelo pipeline. "
        "Use opção 5 (Tudo) para rodar o pipeline completo.[/]"
    )
    return False


def _acao_sync() -> bool:
    _console().print("[cyan]Sincronizando com Obsidian (relatórios + notas ricas)...[/]")
    rc_relatorios = _rodar_run_sh("--sync")
    rc_rico = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "src.obsidian.sync_rico",
            "--executar",
        ],
        cwd=str(_RAIZ_REPO),
        check=False,
    ).returncode
    return rc_relatorios == 0 and rc_rico == 0


def _acao_tudo() -> bool:
    _console().print("[magenta]Executando pipeline completo (Sprint 80)...[/]")
    _rodar_run_sh("--inbox")
    _rodar_run_sh("--tudo")
    subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "src.obsidian.sync_rico",
            "--executar",
        ],
        cwd=str(_RAIZ_REPO),
        check=False,
    )
    return True


_DISPATCHER: dict[str, callable] = {  # type: ignore[type-arg]
    "1": _acao_inbox,
    "2": _acao_dashboard,
    "3": _acao_relatorio,
    "4": _acao_sync,
    "5": _acao_tudo,
}


# ============================================================================
# Pergunta pós-ação
# ============================================================================


def _perguntar_proximo_passo(cons: "Console") -> None:
    cons.print()
    cons.print("[bold]E agora?[/]")
    cons.print(
        "  [green]dashboard[/] - abrir Streamlit\n"
        "  [green]relatorio[/] - ver último relatório\n"
        "  [green]ambos[/]     - dashboard + abrir Obsidian\n"
        "  [green]nada[/]      - encerrar"
    )
    escolha = _prompt("Escolha", choices=list(OPCOES_FOLLOW_UP), default="nada")
    if escolha == "dashboard":
        _acao_dashboard()
    elif escolha == "relatorio":
        _acao_relatorio()
    elif escolha == "ambos":
        _acao_dashboard()
        _acao_relatorio()
    # "nada" → encerra


# ============================================================================
# Menu principal
# ============================================================================


def _render_menu(cons: "Console") -> None:
    cons.rule("[bold purple]Protocolo Ouroboros[/]")
    for chave, descricao in OPCOES_MENU.items():
        cons.print(f"  [cyan]{chave}[/] - {descricao}")


def executar_menu() -> int:
    """Loop principal do menu. Retorna o exit code do processo."""
    cons = _console()
    _render_menu(cons)
    escolha = _prompt("Opção", choices=list(OPCOES_MENU.keys()), default="0")
    if escolha == "0":
        cons.print("[dim]Encerrando.[/]")
        return 0
    acao = _DISPATCHER[escolha]
    disruptiva = acao()
    if disruptiva:
        _perguntar_proximo_passo(cons)
    return 0


def main(argv: list[str] | None = None) -> int:
    del argv  # menu não aceita args posicionais
    # Se stdin não é TTY e não há nenhuma variável pedindo modo não-interativo,
    # ainda rodamos: `_prompt` cai no default e encerra elegantemente.
    if not _RICH_DISPONIVEL:
        sys.stderr.write("rich não está instalado; rode install.sh\n")
        return 1
    if os.environ.get("OUROBOROS_MENU_SKIP") == "1":
        return 0
    try:
        return executar_menu()
    except KeyboardInterrupt:
        _console().print("\n[dim]Encerrando (CTRL-C).[/]")
        return 130


if __name__ == "__main__":
    sys.exit(main())


# "Sem menu o usuário vira manual de CLI." — princípio Sprint 80
