"""Gauntlet -- Sistema de validação do Protocolo Ouroboros.

Inspirado no gauntlet da Luna. Testa o pipeline inteiro com dados sintéticos,
sem mocks, gerando relatório detalhado em GAUNTLET_REPORT.md.

Uso:
    python -m scripts.gauntlet.gauntlet                   # todas as fases
    python -m scripts.gauntlet.gauntlet --apenas categorias  # fase específica
    python -m scripts.gauntlet.gauntlet --listar           # lista fases
"""

import argparse
import sys
import time

from rich.console import Console
from rich.table import Table

from scripts.gauntlet.config import (
    FASES_DISPONIVEIS,
    REPORT_PATH,
    ResultadoFase,
)
from scripts.gauntlet.reporters.markdown_reporter import gerar_relatorio

console = Console()

CORES_FASE: dict[str, str] = {
    "extratores": "green",
    "categorias": "cyan",
    "dedup": "blue",
    "xlsx": "yellow",
    "relatorio": "magenta",
    "projecoes": "bright_cyan",
    "obsidian": "bright_blue",
    "dashboard": "bright_magenta",
}


def _carregar_fase(nome: str) -> ResultadoFase:
    """Importa e executa dinamicamente uma fase pelo nome."""
    modulo_nome = f"scripts.gauntlet.fases.{nome}"

    try:
        import importlib

        modulo = importlib.import_module(modulo_nome)
        return modulo.executar()
    except Exception as e:
        console.print(f"  [red]Erro ao carregar fase '{nome}': {e}[/red]")
        fase = ResultadoFase(nome=nome)
        from scripts.gauntlet.config import ResultadoTeste

        fase.testes.append(ResultadoTeste(
            nome=f"carregar_{nome}",
            passou=False,
            erro=str(e),
        ))
        return fase


def _exibir_banner() -> None:
    """Exibe banner do gauntlet."""
    console.print()
    console.print("  [bold cyan]╔══════════════════════════════════════════╗[/bold cyan]")
    console.print("  [bold cyan]║         GAUNTLET                        ║[/bold cyan]")
    console.print("  [bold cyan]║         Protocolo Ouroboros             ║[/bold cyan]")
    console.print("  [bold cyan]╚══════════════════════════════════════════╝[/bold cyan]")
    console.print()


def _exibir_resultado_fase(fase: ResultadoFase) -> None:
    """Exibe resultado de uma fase no console."""
    cor = CORES_FASE.get(fase.nome, "white")
    status = "[bold green]OK[/bold green]" if fase.passou else "[bold red]FALHA[/bold red]"

    console.print(
        f"  [{cor}]{fase.nome:<12}[/{cor}] "
        f"{status}  "
        f"{fase.ok}/{fase.total} testes  "
        f"[dim]{fase.tempo_total:.1f}s[/dim]"
    )

    for teste in fase.testes:
        if not teste.passou:
            erro = f" -- {teste.erro}" if teste.erro else ""
            console.print(f"    [red]x {teste.nome}: {teste.detalhe}{erro}[/red]")


def _exibir_resumo(fases: list[ResultadoFase], duracao: float) -> None:
    """Exibe tabela resumo final."""
    console.print()

    tabela = Table(title="Resumo do Gauntlet", border_style="cyan")
    tabela.add_column("Fase", style="bold")
    tabela.add_column("Testes", justify="center")
    tabela.add_column("OK", justify="center", style="green")
    tabela.add_column("Falha", justify="center", style="red")
    tabela.add_column("Tempo", justify="right", style="dim")

    for fase in fases:
        falha_style = "red bold" if fase.falhas > 0 else "dim"
        tabela.add_row(
            fase.nome,
            str(fase.total),
            str(fase.ok),
            f"[{falha_style}]{fase.falhas}[/{falha_style}]",
            f"{fase.tempo_total:.1f}s",
        )

    total_ok = sum(f.ok for f in fases)
    total = sum(f.total for f in fases)
    total_falhas = sum(f.falhas for f in fases)

    tabela.add_section()
    tabela.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total}[/bold]",
        f"[bold green]{total_ok}[/bold green]",
        f"[bold red]{total_falhas}[/bold red]",
        f"[bold]{duracao:.1f}s[/bold]",
    )

    console.print(tabela)
    console.print()

    if total_falhas == 0:
        console.print("  [bold green]Gauntlet passou. Todos os testes OK.[/bold green]")
    else:
        console.print(
            f"  [bold red]Gauntlet falhou. {total_falhas} teste(s) com problema.[/bold red]"
        )

    console.print(f"  [dim]Relatório salvo em: {REPORT_PATH}[/dim]")
    console.print()


def executar(fases_selecionadas: list[str] | None = None) -> int:
    """Executa o gauntlet completo ou fases específicas.

    Retorna 0 se tudo passou, 1 se houve falhas.
    """
    _exibir_banner()

    fases_para_rodar = fases_selecionadas or FASES_DISPONIVEIS
    console.print(f"  [dim]Fases: {', '.join(fases_para_rodar)}[/dim]")
    console.print()

    resultados: list[ResultadoFase] = []
    inicio = time.time()

    for nome in fases_para_rodar:
        if nome not in FASES_DISPONIVEIS:
            console.print(f"  [yellow]Fase desconhecida: {nome}[/yellow]")
            continue

        console.print(f"  [dim]Executando fase: {nome}...[/dim]")
        resultado = _carregar_fase(nome)
        resultados.append(resultado)
        _exibir_resultado_fase(resultado)

    duracao = time.time() - inicio

    _exibir_resumo(resultados, duracao)

    relatorio_md = gerar_relatorio(resultados, duracao)
    REPORT_PATH.write_text(relatorio_md, encoding="utf-8")

    total_falhas = sum(f.falhas for f in resultados)
    return 0 if total_falhas == 0 else 1


def main() -> None:
    """Ponto de entrada CLI do gauntlet."""
    parser = argparse.ArgumentParser(
        description="Gauntlet -- Sistema de validação do Protocolo Ouroboros",
    )
    parser.add_argument(
        "--apenas",
        nargs="+",
        choices=FASES_DISPONIVEIS,
        help="Executar apenas as fases especificadas",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Listar fases disponíveis e sair",
    )

    args = parser.parse_args()

    if args.listar:
        console.print("\n  [bold]Fases disponíveis:[/bold]\n")
        for fase in FASES_DISPONIVEIS:
            cor = CORES_FASE.get(fase, "white")
            console.print(f"  [{cor}]{fase}[/{cor}]")
        console.print()
        return

    codigo = executar(args.apenas)
    sys.exit(codigo)


if __name__ == "__main__":
    main()


# "A qualidade nunca é um acidente; é sempre o resultado de um esforço inteligente."
# -- John Ruskin
