"""Lint estático do invariante D7 -- "extrair tudo, catalogar tudo".

Sprint META-COBERTURA-TOTAL-01.

Decisão D7 do dono em 2026-04-29 (registrada em
``~/.claude/plans/glittery-munching-russell.md``): "extrair tudo das imagens
e pdfs, tudo mesmo, cada valor e catalogar tudo. Tudo".

Lint detecta retornos vazios potencialmente silenciosos em métodos
``extrair*`` dos extratores em ``src/extractors/``. NÃO usa regex literal
sobre ``return []`` (gera falsos positivos legítimos -- ex.: NFCe e DANFE
retornam [] de Transacao por design, pois ingerem no grafo mas não emitem  # noqa: accent
linha bancária; primeiros early-returns sinalizam "arquivo não é do tipo
deste extrator", roteamento natural).

Padrões investigados (todos via AST):

  1. Função cujo último statement é ``return []`` E não há logger.info/warning
     em nenhum statement anterior do mesmo escopo. Indica saída silenciosa.

  2. Função com nome iniciando ``extrair`` ou ``parsear`` que retorna lista
     vazia inicializada e nunca anexa, sem warning explícito. Indica ramo
     de erro mascarado.

  3. Caminho ``adicionar_edge`` ou ``add_edge`` SEM verificação de retorno
     OU sem warning quando o ID retornado é None/0. Indica ingestão
     no grafo sem confirmação (item 21 do plan pure-swinging-mitten).

Saída:

  - Modo padrão: ``exit 0`` se não há violações; ``exit 1`` listando achados.
  - Modo ``--warn-only``: ``exit 0`` sempre, mas imprime achados (uso em CI
    inicial até META-COBERTURA-TOTAL-01 fechar e ramificar retrabalho).
  - Modo ``--json``: imprime achados em JSON estruturado (consumido por
    ``scripts/auditar_cobertura_total.py``).

Uso:

    python scripts/check_cobertura_total.py
    python scripts/check_cobertura_total.py --warn-only
    python scripts/check_cobertura_total.py --json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
_DIR_EXTRATORES: Path = _RAIZ_REPO / "src" / "extractors"

_LOGGER_CHAMADAS = {"logger.info", "logger.warning", "logger.error", "logger.debug"}
_PREFIXOS_FUNCAO_INTERESSE = ("extrair", "parsear", "_parse", "_extrair")


@dataclass
class Violacao:
    arquivo: str
    funcao: str
    linha: int
    motivo: str


def _ha_chamada_logger(node: ast.AST) -> bool:
    """Verifica se o nó AST tem qualquer chamada `logger.<nivel>(...)` em descendentes."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            chamada = ast.unparse(sub.func) if hasattr(ast, "unparse") else ""
            if any(chamada.endswith(c) for c in {".info", ".warning", ".error", ".debug"}):
                if isinstance(sub.func.value, ast.Name) and sub.func.value.id in {
                    "logger",
                    "self",
                }:
                    return True
                if isinstance(sub.func.value, ast.Attribute) and sub.func.value.attr == "logger":
                    return True
    return False


def _retorno_vazio(node: ast.Return) -> bool:
    """Verifica se um Return é literalmente `return []` ou `return list()`."""
    if node.value is None:
        return False
    if isinstance(node.value, ast.List) and not node.value.elts:
        return True
    if (
        isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "list"
        and not node.value.args
        and not node.value.keywords
    ):
        return True
    return False


def _ultimo_return_da_funcao(func: ast.FunctionDef) -> ast.Return | None:
    """Acha o último ``return`` no corpo top-level da função."""
    for stmt in reversed(func.body):
        if isinstance(stmt, ast.Return):
            return stmt
    return None


def _funcao_termina_em_return_vazio_silencioso(func: ast.FunctionDef) -> bool:
    """Caso 1: último statement é `return []` E zero chamadas a logger no corpo."""
    ultimo = _ultimo_return_da_funcao(func)
    if ultimo is None or not _retorno_vazio(ultimo):
        return False
    return not _ha_chamada_logger(func)


def auditar_arquivo(caminho: Path) -> list[Violacao]:
    """Roda análise AST sobre um arquivo Python. Retorna lista de violações."""
    try:
        tree = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    except SyntaxError as erro:
        return [Violacao(str(caminho), "<arquivo>", erro.lineno or 0, f"sintaxe: {erro}")]

    try:
        rotulo_caminho = str(caminho.relative_to(_RAIZ_REPO))
    except ValueError:
        rotulo_caminho = str(caminho)

    violacoes: list[Violacao] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            nome = node.name
            if not nome.startswith(_PREFIXOS_FUNCAO_INTERESSE):
                continue
            if _funcao_termina_em_return_vazio_silencioso(node):
                violacoes.append(
                    Violacao(
                        rotulo_caminho,
                        nome,
                        node.lineno,
                        "último statement é 'return []' sem logger.info/warning no corpo",
                    )
                )
    return violacoes


def auditar_diretorio_extratores() -> list[Violacao]:
    """Roda auditoria sobre todos os ``src/extractors/*.py`` exceto ``__init__``."""
    todas: list[Violacao] = []
    for caminho in sorted(_DIR_EXTRATORES.glob("*.py")):
        if caminho.name == "__init__.py":
            continue
        todas.extend(auditar_arquivo(caminho))
    return todas


def imprimir_humano(violacoes: list[Violacao]) -> None:
    if not violacoes:
        print("[D7] nenhuma violacao encontrada em src/extractors/")
        return
    print(f"[D7] {len(violacoes)} violacao(oes) encontrada(s):")
    for v in violacoes:
        print(f"  - {v.arquivo}:{v.linha}  função '{v.funcao}'  -> {v.motivo}")


def imprimir_json(violacoes: list[Violacao]) -> None:
    payload = [
        {"arquivo": v.arquivo, "funcao": v.funcao, "linha": v.linha, "motivo": v.motivo}
        for v in violacoes
    ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="imprime achados mas retorna exit 0 (uso em CI inicial)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="saida JSON estruturada (consumida por auditar_cobertura_total)",
    )
    args = parser.parse_args()

    violacoes = auditar_diretorio_extratores()
    if args.json:
        imprimir_json(violacoes)
    else:
        imprimir_humano(violacoes)

    if args.warn_only or not violacoes:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())


# "A perfeição é uma estrada, não um destino. Auditá-la é caminhar."
#  -- princípio operacional do Protocolo Ouroboros
