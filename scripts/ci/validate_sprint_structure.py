#!/usr/bin/env python3
"""Valida estrutura de documentação das sprints do Ouroboros.

Verifica se cada `sprint_NN_*.md` em docs/sprints/ respeita o padrão
canônico (título, frontmatter, seções obrigatórias). Saída não-zero
bloqueia merge em CI.

Uso:
    .venv/bin/python scripts/ci/validate_sprint_structure.py
    .venv/bin/python scripts/ci/validate_sprint_structure.py docs/sprints/producao/sprint_22_consolidacao.md
    .venv/bin/python scripts/ci/validate_sprint_structure.py --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DIR_SPRINTS = BASE_DIR / "docs" / "sprints"
DIRS_ATIVAS = ("producao", "backlog")


@dataclass(frozen=True)
class Regra:
    """Regra de validação de uma seção obrigatória."""

    nome: str
    pattern: str
    obrigatoria: bool
    descricao: str


REGRAS: tuple[Regra, ...] = (
    Regra(
        nome="titulo",
        pattern=r"^#\s+Sprint\s+\d+[a-z]*\s+--?\s+",
        obrigatoria=True,
        descricao="Título no formato '# Sprint NN -- Nome'",
    ),
    Regra(
        nome="status",
        pattern=r"^\*\*Status:\*\*\s+(PENDENTE|PLANEJADA|EM\s+ANDAMENTO|CONCLUÍDA|OBSOLETA|CANCELADA)",
        obrigatoria=True,
        descricao="Campo obrigatório **Status:** com valor reconhecido",
    ),
    Regra(
        nome="data",
        pattern=r"^\*\*Data:\*\*\s+\d{4}-\d{2}-\d{2}",
        obrigatoria=True,
        descricao="Campo **Data:** em formato ISO YYYY-MM-DD",
    ),
    Regra(
        nome="prioridade",
        pattern=r"^\*\*Prioridade:\*\*\s+(CR[IÍ]TICA|ALTA|M[EÉ]DIA|MEDIA|BAIXA)",
        obrigatoria=True,
        descricao="Campo **Prioridade:** com valor reconhecido",
    ),
    Regra(
        nome="tipo",
        pattern=r"^\*\*Tipo:\*\*\s+(Feature|Bugfix|Refactor|Valida[çc][ãa]o|Infra|Documenta[çc][ãa]o)",
        obrigatoria=True,
        descricao="Campo **Tipo:** com valor reconhecido",
    ),
    Regra(
        nome="secao_problema",
        pattern=r"^##\s+Problema\b",
        obrigatoria=True,
        descricao="Seção '## Problema'",
    ),
    Regra(
        nome="secao_implementacao",
        pattern=r"^##\s+Implementa[çc][ãa]o\b",
        obrigatoria=True,
        descricao="Seção '## Implementação'",
    ),
    Regra(
        nome="secao_verificacao",
        pattern=r"^##\s+Verifica[çc][ãa]o\b",
        obrigatoria=True,
        descricao="Seção '## Verificação'",
    ),
    Regra(
        nome="citacao_final",
        pattern=r"\*\"[^\"]+\"\s*--\s*\S+",
        obrigatoria=True,
        descricao="Citação de filósofo ao final do arquivo",
    ),
    Regra(
        nome="secao_armadilhas",
        pattern=r"^##\s+Armadilhas\b",
        obrigatoria=False,
        descricao="Seção '## Armadilhas Conhecidas' (recomendada)",
    ),
)


class ValidadorSprint:
    """Validador de um único arquivo de sprint."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        self.conteudo = caminho.read_text(encoding="utf-8")
        self.erros: list[str] = []
        self.avisos: list[str] = []

    def validar(self) -> tuple[bool, list[str], list[str]]:
        """Aplica as regras e retorna (sucesso, erros, avisos)."""
        self.erros.clear()
        self.avisos.clear()

        for regra in REGRAS:
            if not re.search(regra.pattern, self.conteudo, re.MULTILINE):
                msg = f"[{regra.nome}] {regra.descricao}"
                if regra.obrigatoria:
                    self.erros.append(msg)
                else:
                    self.avisos.append(msg)

        self._validar_nome_arquivo()
        return (len(self.erros) == 0, list(self.erros), list(self.avisos))

    def _validar_nome_arquivo(self) -> None:
        """Garante que o nome do arquivo segue sprint_NN_descritivo.md."""
        if not re.match(r"^sprint_\d+[a-z]?_[a-z0-9_]+\.md$", self.caminho.name):
            self.erros.append(
                f"[nome_arquivo] '{self.caminho.name}' não segue padrão sprint_NN_descritivo.md"
            )


def _encontrar_sprints(caminhos: list[str] | None, incluir_legadas: bool) -> list[Path]:
    """Resolve lista de arquivos a validar.

    Sem argumentos e sem `--all`, valida apenas sprints ativas (producao/, backlog/).
    Sprints em concluidos/ e arquivadas/ seguem padrão antigo e são isentas por default.
    """
    if caminhos:
        return [Path(c) for c in caminhos]
    if not DIR_SPRINTS.exists():
        return []
    if incluir_legadas:
        return sorted(DIR_SPRINTS.rglob("sprint_*.md"))
    arquivos: list[Path] = []
    for sub in DIRS_ATIVAS:
        subdir = DIR_SPRINTS / sub
        if subdir.exists():
            arquivos.extend(sorted(subdir.glob("sprint_*.md")))
    return arquivos


def _render_texto(resultados: list[dict]) -> str:
    """Monta saída textual legível."""
    total_erros = sum(len(r["erros"]) for r in resultados)
    total_avisos = sum(len(r["avisos"]) for r in resultados)

    linhas: list[str] = []
    linhas.append("=" * 66)
    linhas.append("  VALIDAÇÃO DE ESTRUTURA DE SPRINTS")
    linhas.append("=" * 66)

    for r in resultados:
        status = "[OK]" if r["sucesso"] else "[FALHA]"
        linhas.append(f"\n{status} {r['arquivo']}")
        if r["erros"]:
            linhas.append("  Erros:")
            for err in r["erros"]:
                linhas.append(f"    - {err}")
        if r["avisos"]:
            linhas.append("  Avisos:")
            for aviso in r["avisos"]:
                linhas.append(f"    - {aviso}")

    linhas.append("")
    linhas.append("=" * 66)
    linhas.append(f"Total: erros={total_erros}, avisos={total_avisos}")
    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida estrutura de sprints do Ouroboros")
    parser.add_argument(
        "arquivos",
        nargs="*",
        help="Arquivos específicos (default: apenas producao/ e backlog/)",
    )
    parser.add_argument("--strict", action="store_true", help="Tratar avisos como erros")
    parser.add_argument("--json", action="store_true", help="Saída JSON")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Incluir concluidos/ e arquivadas/ (sprints legadas podem falhar)",
    )
    args = parser.parse_args()

    arquivos = _encontrar_sprints(args.arquivos, incluir_legadas=args.all)
    if not arquivos:
        sys.stdout.write("Nenhum arquivo de sprint encontrado\n")
        return 0

    resultados: list[dict] = []
    total_erros = 0
    total_avisos = 0

    for caminho in arquivos:
        if not caminho.exists():
            resultados.append(
                {
                    "arquivo": str(caminho),
                    "sucesso": False,
                    "erros": ["Arquivo não encontrado"],
                    "avisos": [],
                }
            )
            total_erros += 1
            continue

        validador = ValidadorSprint(caminho)
        sucesso, erros, avisos = validador.validar()
        total_erros += len(erros)
        total_avisos += len(avisos)
        resultados.append(
            {
                "arquivo": str(caminho.relative_to(BASE_DIR) if BASE_DIR in caminho.parents else caminho),
                "sucesso": sucesso,
                "erros": erros,
                "avisos": avisos,
            }
        )

    if args.json:
        sys.stdout.write(json.dumps(resultados, indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(_render_texto(resultados) + "\n")

    ok = total_erros == 0
    if args.strict:
        ok = ok and total_avisos == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())


# "A estrutura determina o comportamento." -- Peter Senge
