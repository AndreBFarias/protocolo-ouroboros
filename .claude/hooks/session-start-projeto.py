"""Hook SessionStart local do protocolo-ouroboros.

Complementa o hook global do dono (`~/.claude/hooks/session-start-briefing.py`)
com informação específica do projeto: estado de graduação dos tipos
documentais, épico ativo do ROADMAP e comandos canônicos de inventário.

Recebe payload JSON via stdin (formato SessionStart do Claude Code) e
imprime via stdout um JSON com chave `additionalContext`, injetando um
briefing curto no contexto inicial da sessao.

Falha-soft em qualquer exceção: retorna exit 0 sem quebrar o boot da
sessão. Hook ruidoso nunca deve impedir o trabalho.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Raiz do projeto: ../../ a partir de .claude/hooks/.
_RAIZ = Path(__file__).resolve().parents[2]

PATH_GRADUACAO = _RAIZ / "data" / "output" / "graduacao_tipos.json"
PATH_ROADMAP = _RAIZ / "docs" / "sprints" / "ROADMAP_ATE_PROD.md"
PATH_BACKLOG = _RAIZ / "docs" / "sprints" / "backlog"


def main() -> int:
    """Lê payload, monta contexto, imprime JSON com additionalContext."""
    try:
        sys.stdin.read()  # consome payload (não usamos campos específicos)
    except Exception:
        return 0  # falha-soft

    try:
        contexto = montar_contexto_inicial()
        sys.stdout.write(json.dumps({"additionalContext": contexto}))
        sys.stdout.flush()
    except Exception:
        return 0  # falha-soft

    return 0


def montar_contexto_inicial() -> str:
    """Compoe o texto do briefing a partir de estado vivo do repositorio."""
    linhas: list[str] = [
        "## Briefing local do protocolo-ouroboros (hook session-start)",
        "",
        "LEIA ANTES DE QUALQUER SPRINT (auto-carregado via CLAUDE.md):",
        "1. docs/sprints/ROADMAP_ATE_PROD.md",
        "2. docs/CICLO_GRADUACAO_OPERACIONAL.md",
        "3. contexto/COMO_AGIR.md",
        "",
    ]

    linhas.extend(_bloco_graduacao())
    linhas.append("")
    linhas.extend(_bloco_epico_ativo())
    linhas.append("")
    linhas.append("Inventario rapido: `scripts/dossie_tipo.py listar-tipos`.")

    return "\n".join(linhas)


def _bloco_graduacao() -> list[str]:
    """Le `data/output/graduacao_tipos.json` e devolve resumo em uma linha."""
    if not PATH_GRADUACAO.exists():
        return [
            "graduacao_tipos.json ausente -- rode "
            "`scripts/dossie_tipo.py snapshot` para gerar.",
            "Sem snapshot, estado de graduação dos 22 tipos não está capturado.",
        ]
    try:
        bruto = PATH_GRADUACAO.read_text(encoding="utf-8")
        grad = json.loads(bruto)
    except (OSError, json.JSONDecodeError):
        return [
            "graduacao_tipos.json existe mas e ilegivel -- "
            "regenere com `scripts/dossie_tipo.py snapshot`.",
        ]

    totais = grad.get("totais", {}) if isinstance(grad, dict) else {}
    graduados = int(totais.get("GRADUADO", 0))
    calibrando = int(totais.get("CALIBRANDO", 0))
    pendentes = int(totais.get("PENDENTE", 0))
    return [
        f"Estado dos tipos: {graduados} GRADUADOS, "
        f"{calibrando} CALIBRANDO, {pendentes} PENDENTE.",
    ]


def _bloco_epico_ativo() -> list[str]:
    """Devolve linha apontando o epico ativo, por heuristica simples."""
    # Heurística: primeiro épico declarado no ROADMAP que tem ao menos uma
    # sprint em `docs/sprints/backlog/`. Se ROADMAP não existe, devolve
    # apontamento genérico.
    if not PATH_ROADMAP.exists() or not PATH_BACKLOG.exists():
        return ["Epico ativo: indeterminado (ROADMAP ou backlog/ ausente)."]

    try:
        roadmap = PATH_ROADMAP.read_text(encoding="utf-8")
    except OSError:
        return ["Epico ativo: indeterminado (ROADMAP ilegivel)."]

    epicos = re.findall(
        r"^##\s+(?:EPICO|Epico|Épico|ÉPICO)\s+(\d+)[^\n]*",
        roadmap,
        re.M,
    )
    if not epicos:
        return ["Epico ativo: nenhum epico declarado em ROADMAP."]

    try:
        especs_backlog = list(PATH_BACKLOG.glob("sprint_*.md"))
    except OSError:
        especs_backlog = []

    qtd_backlog = len(especs_backlog)
    primeiro_epico = epicos[0]
    return [
        f"Epico ativo (heuristica): epico {primeiro_epico}.",
        f"Sprints em backlog/: {qtd_backlog}.",
    ]


if __name__ == "__main__":
    sys.exit(main())


# "Anfitriao eficiente fala tres linhas e deixa o convidado encontrar o resto." -- Sêneca
