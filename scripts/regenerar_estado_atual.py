"""Regenera a seção "Versão + saúde geral" do `contexto/ESTADO_ATUAL.md`.

Sprint META-ESTADO-ATUAL-AUTO (2026-05-15). A seção tem métricas vivas que
envelhecem em dias (pytest count, smoke, lint, contagem de extratores,
transações, tipos GRADUADOS). Manter à mão é fonte de erro — o snapshot
de 2026-04-29 declarou "2.018 passed" quando a realidade atual é 3000+.

Markers canônicos no MD:

    <!-- BEGIN_AUTO_METRICAS -->
    ```
    TESTES: ... passed / ... skipped / ... xfailed
    SMOKE: ...
    LINT: ...
    GRAFO: ... nodes / ... edges
    TIPOS GRADUADOS: .../22 (... pendentes)
    EXTRATORES: ... em src/extractors/
    ÚLTIMO COMMIT: <sha> <mensagem>
    ```
    <!-- END_AUTO_METRICAS -->

Uso:

    # Dry-run (default): imprime bloco sem aplicar
    python scripts/regenerar_estado_atual.py

    # Aplica no arquivo (entre markers)
    python scripts/regenerar_estado_atual.py --apply

Idempotente: rodar 2× consecutivas sem mudança de runtime produz mesmo
diff. Hook `pre-push` (opcional) pode invocar este script para garantir
que o ESTADO_ATUAL.md não fique desatualizado.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
PATH_ESTADO_ATUAL = _RAIZ / "contexto" / "ESTADO_ATUAL.md"
PATH_GRAFO = _RAIZ / "data" / "output" / "grafo.sqlite"
PATH_GRADUACAO = _RAIZ / "data" / "output" / "graduacao_tipos.json"
PATH_XLSX = _RAIZ / "data" / "output" / "ouroboros_2026.xlsx"
DIR_EXTRATORES = _RAIZ / "src" / "extractors"

MARKER_INICIO = "<!-- BEGIN_AUTO_METRICAS -->"
MARKER_FIM = "<!-- END_AUTO_METRICAS -->"


def _pytest_count() -> str:
    """Roda `pytest --collect-only -q` e devolve o resumo da última linha."""
    try:
        r = subprocess.run(
            [str(_RAIZ / ".venv" / "bin" / "pytest"), "--collect-only", "-q"],
            cwd=str(_RAIZ),
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Última linha do tipo "3000 tests collected in 3.03s"
        for linha in reversed(r.stdout.strip().splitlines()):
            if "tests collected" in linha or "test collected" in linha:
                return linha.strip()
        return "indisponível"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "indisponível"


def _smoke_status() -> str:
    """Lê o último log de smoke e devolve resumo `N/M contratos OK`."""
    try:
        r = subprocess.run(
            [str(_RAIZ / ".venv" / "bin" / "python"), "scripts/smoke_aritmetico.py", "--strict"],
            cwd=str(_RAIZ),
            capture_output=True,
            text=True,
            timeout=30,
        )
        saida = r.stdout + r.stderr
        match = re.search(r"\[SMOKE-ARIT\]\s+(\d+/\d+\s+contratos\s+OK)", saida)
        if match:
            return match.group(1)
        if "AVISO XLSX" in saida or "XLSX não encontrado" in saida:
            return "skip (XLSX ausente)"
        return "indisponível"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "indisponível"


def _lint_status() -> str:
    """Roda `make lint` e devolve exit code."""
    try:
        r = subprocess.run(
            ["make", "lint"],
            cwd=str(_RAIZ),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return f"exit {r.returncode}"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "indisponível"


def _grafo_stats() -> tuple[int, int]:
    """Devolve (nodes, edges) do grafo SQLite ou (0, 0) se ausente."""
    if not PATH_GRAFO.exists():
        return 0, 0
    try:
        con = sqlite3.connect(str(PATH_GRAFO))
        try:
            n = con.execute("SELECT COUNT(*) FROM node").fetchone()[0]
            e = con.execute("SELECT COUNT(*) FROM edge").fetchone()[0]
            return int(n), int(e)
        finally:
            con.close()
    except sqlite3.Error:
        return 0, 0


def _tipos_graduados() -> tuple[int, int]:
    """Devolve (graduados, total_canônico).

    `total_canônico` é o número de tipos declarados em
    `mappings/tipos_documento.yaml` (fonte canônica, 22 tipos hoje).
    O JSON de graduação pode ter menos entries (só tipos com dossiê físico)
    — usar `len(totais)` daria número errado.
    """
    if not PATH_GRADUACAO.exists():
        return 0, 22
    try:
        dados = json.loads(PATH_GRADUACAO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0, 22
    totais = dados.get("totais") or {}
    grad = int(totais.get("GRADUADO", 0))

    # Lê o total canônico do YAML (não do JSON):
    total_canonico = 22  # fallback se yaml ausente
    yaml_path = _RAIZ / "mappings" / "tipos_documento.yaml"
    if yaml_path.exists():
        try:
            import yaml  # type: ignore[import-untyped]

            doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            tipos = doc.get("tipos") or []
            total_canonico = len([t for t in tipos if t.get("id")])
        except ImportError:
            pass
    return grad, total_canonico


def _extratores_count() -> int:
    """Conta arquivos `.py` em `src/extractors/` (exclui `_*.py` e `__init__`)."""
    if not DIR_EXTRATORES.exists():
        return 0
    arquivos = [
        p
        for p in DIR_EXTRATORES.glob("*.py")
        if not p.name.startswith("_") and p.name != "__init__.py"
    ]
    return len(arquivos)


def _ultimo_commit() -> str:
    """Devolve `<sha7> <subject>` do HEAD."""
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%h %s"],
            cwd=str(_RAIZ),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.stdout.strip() or "indisponível"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "indisponível"


def gerar_bloco_metricas() -> str:
    """Compõe o bloco de métricas vivas pronto para inserir entre markers."""
    nodes, edges = _grafo_stats()
    grad, total_canonico = _tipos_graduados()
    return (
        "```\n"
        f"TESTES: {_pytest_count()}\n"
        f"SMOKE: {_smoke_status()}\n"
        f"LINT: {_lint_status()}\n"
        f"GRAFO: {nodes} nodes / {edges} edges\n"
        f"TIPOS GRADUADOS: {grad}/{total_canonico} no mappings/tipos_documento.yaml\n"
        f"EXTRATORES: {_extratores_count()} em src/extractors/\n"
        f"ÚLTIMO COMMIT: {_ultimo_commit()}\n"
        "```\n"
    )


def aplicar_no_arquivo(conteudo_atual: str, bloco_novo: str) -> str:
    """Substitui entre markers, ou insere markers no início se ausentes."""
    if MARKER_INICIO in conteudo_atual and MARKER_FIM in conteudo_atual:
        padrao = re.compile(
            re.escape(MARKER_INICIO) + r".*?" + re.escape(MARKER_FIM),
            re.DOTALL,
        )
        return padrao.sub(
            MARKER_INICIO + "\n" + bloco_novo + MARKER_FIM,
            conteudo_atual,
        )
    # Markers ausentes: insere logo após o primeiro título `## Versao + saude geral`
    cabecalho = re.compile(r"^## Versao \+ saude geral.*?$", re.MULTILINE)
    match = cabecalho.search(conteudo_atual)
    if match:
        insercao = (
            "\n\n"
            + MARKER_INICIO
            + "\n"
            + bloco_novo
            + MARKER_FIM
            + "\n"
        )
        return (
            conteudo_atual[: match.end()] + insercao + conteudo_atual[match.end() :]
        )
    # Sem cabeçalho: prepend ao fim
    return conteudo_atual + "\n\n" + MARKER_INICIO + "\n" + bloco_novo + MARKER_FIM + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenera métricas do ESTADO_ATUAL.md")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica no arquivo (padrão é dry-run: imprime bloco sem alterar)",
    )
    args = parser.parse_args(argv)

    bloco = gerar_bloco_metricas()

    if not args.apply:
        sys.stdout.write(MARKER_INICIO + "\n")
        sys.stdout.write(bloco)
        sys.stdout.write(MARKER_FIM + "\n")
        return 0

    if not PATH_ESTADO_ATUAL.exists():
        sys.stderr.write(f"ESTADO_ATUAL.md não encontrado: {PATH_ESTADO_ATUAL}\n")
        return 1

    atual = PATH_ESTADO_ATUAL.read_text(encoding="utf-8")
    novo = aplicar_no_arquivo(atual, bloco)
    if novo == atual:
        sys.stdout.write("Sem mudança (já idêntico).\n")
        return 0
    PATH_ESTADO_ATUAL.write_text(novo, encoding="utf-8")
    sys.stdout.write(f"Atualizado: {PATH_ESTADO_ATUAL}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Documento que envelhece à mão é documento que mente sozinho." -- princípio do snapshot vivo
