"""Linter de specs de sprint (`docs/sprints/backlog/sprint_*.md`).

Verifica forma canônica exigida pelos padrões `(s)`, `(t)` e `(u)` do
VALIDATOR_BRIEF:

1. Frontmatter YAML com campos mandatórios.
2. Seções `## Contexto`, `## Hipótese ... ANTES` (ou `## Validação ANTES`),
   `## Objetivo` (ou `## Implementação`), `## Não-objetivos`, `## Proof-of-work`
   e `## Acceptance` presentes e com conteúdo não-vazio.

Sprint META-SPEC-LINTER 2026-05-15.

Modos:

* Default: lê paths (arquivos ou diretórios) e reporta `OK`/`FALHA` por spec.
  Exit 0 se todas OK, 1 se alguma falha, 2 se erro de uso.
* `--auto-completar`: para cada spec faltando `## Não-objetivos`, faz append
  não-destrutivo com placeholder `(preencher)`. Útil para destravar lint
  global sem decidir conteúdo manualmente.
* `--files`: hook pre-commit passa caminhos absolutos via stdin/argv;
  o linter ignora silenciosamente paths que não casam o padrão de spec.
* `--soft`: reporta falhas mas sempre retorna exit 0. Pensado para
  `make lint` rodando sobre backlog histórico sem destravar suite global;
  hook pre-commit deve usar modo estrito (default).

Uso:
    python scripts/check_spec.py docs/sprints/backlog/
    python scripts/check_spec.py docs/sprints/backlog/sprint_FOO_2026-05-15.md
    python scripts/check_spec.py --auto-completar docs/sprints/backlog/
    python scripts/check_spec.py --files docs/sprints/backlog/sprint_X.md other.md
    python scripts/check_spec.py --soft docs/sprints/backlog/    # make lint
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml

CAMPOS_FRONTMATTER_OBRIGATORIOS: tuple[str, ...] = (
    "id",
    "titulo",
    "status",
    "prioridade",
    "data_criacao",
    "esforco_estimado_horas",
    "origem",
)

# Cada seção mandatória é descrita por (rótulo, regex). Regex casa o cabeçalho
# (`##` com 1+ palavras na linha) com variações de acento PT-BR -- conforme
# padrão `(o)` retrocompatível: aceita ambas as grafias.
SECOES_MANDATORIAS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("contexto", re.compile(r"^##\s+Contexto\b", re.MULTILINE)),
    (
        "hipotese_ou_validacao_antes",
        re.compile(
            r"^##\s+(?:Hip[óo]tese[^\n]*ANTES|Valida[çc][ãa]o\s+ANTES)\b",
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "objetivo_ou_implementacao",
        re.compile(r"^##\s+(?:Objetivo|Implementa[çc][ãa]o)\b", re.MULTILINE | re.IGNORECASE),
    ),
    (
        "nao_objetivos",
        re.compile(r"^##\s+N[ãa]o[- ]objetivos\b", re.MULTILINE | re.IGNORECASE),
    ),
    ("proof_of_work", re.compile(r"^##\s+Proof-of-work\b", re.MULTILINE | re.IGNORECASE)),
    ("acceptance", re.compile(r"^##\s+Acceptance\b", re.MULTILINE | re.IGNORECASE)),
)

RE_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
RE_ARQUIVO_SPEC = re.compile(r"sprint_.*\.md$")
RE_CABECALHO_SECAO = re.compile(r"^##\s+", re.MULTILINE)

PLACEHOLDER_NAO_OBJETIVOS = "\n## Não-objetivos\n\n(preencher)\n"

logger = logging.getLogger(__name__)


def _ler_frontmatter(conteudo: str) -> tuple[dict[str, object] | None, str | None]:
    """Extrai o frontmatter YAML do conteúdo da spec.

    Retorna (dict, None) em caso de sucesso ou (None, mensagem_erro) se não
    casar o padrão ou for YAML inválido.
    """
    match = RE_FRONTMATTER.match(conteudo)
    if not match:
        return None, "frontmatter ausente (esperado bloco ---YAML--- no início)"
    try:
        dados = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return None, f"frontmatter com YAML inválido: {exc}"
    if not isinstance(dados, dict):
        return None, "frontmatter YAML não resolveu para um dicionário"
    return dados, None


def _campos_frontmatter_faltantes(dados: dict[str, object]) -> list[str]:
    """Lista campos mandatórios ausentes ou vazios (`None`, string vazia)."""
    faltantes: list[str] = []
    for campo in CAMPOS_FRONTMATTER_OBRIGATORIOS:
        valor = dados.get(campo)
        if valor is None:
            faltantes.append(campo)
            continue
        if isinstance(valor, str) and not valor.strip():
            faltantes.append(campo)
    return faltantes


def _conteudo_da_secao(corpo: str, posicao: int) -> str:
    """Retorna o texto entre o cabeçalho da seção em `posicao` e a próxima.

    Usa o conjunto de cabeçalhos `## ...` para delimitar.
    """
    # Pula a própria linha do cabeçalho.
    inicio = corpo.find("\n", posicao)
    if inicio == -1:
        return ""
    inicio += 1
    proxima = RE_CABECALHO_SECAO.search(corpo, inicio)
    fim = proxima.start() if proxima else len(corpo)
    return corpo[inicio:fim]


def _secoes_faltantes_ou_vazias(corpo: str) -> list[str]:
    """Detecta seções mandatórias ausentes ou com corpo vazio.

    Marca como falha tanto a seção que não existe quanto a que existe sem
    nenhuma linha de conteúdo (espaço/branco apenas).
    """
    problemas: list[str] = []
    for rotulo, regex in SECOES_MANDATORIAS:
        match = regex.search(corpo)
        if not match:
            problemas.append(f"secao_ausente:{rotulo}")
            continue
        miolo = _conteudo_da_secao(corpo, match.start())
        if not miolo.strip():
            problemas.append(f"secao_vazia:{rotulo}")
    return problemas


def validar_spec(caminho: Path) -> list[str]:
    """Valida uma spec individual. Retorna lista de problemas (vazia = OK)."""
    if not caminho.is_file():
        return [f"arquivo_inexistente:{caminho}"]
    conteudo = caminho.read_text(encoding="utf-8")
    problemas: list[str] = []
    dados, erro = _ler_frontmatter(conteudo)
    if erro is not None:
        problemas.append(f"frontmatter:{erro}")
    elif dados is not None:
        for campo in _campos_frontmatter_faltantes(dados):
            problemas.append(f"campo_faltante:{campo}")
    match = RE_FRONTMATTER.match(conteudo)
    corpo = conteudo[match.end() :] if match else conteudo
    problemas.extend(_secoes_faltantes_ou_vazias(corpo))
    return problemas


def auto_completar(caminho: Path) -> bool:
    """Adiciona `## Não-objetivos\\n(preencher)` ao fim da spec se faltar.

    Operação não-destrutiva: somente faz append. Retorna `True` se modificou,
    `False` caso a seção já exista.
    """
    if not caminho.is_file():
        return False
    conteudo = caminho.read_text(encoding="utf-8")
    for rotulo, regex in SECOES_MANDATORIAS:
        if rotulo == "nao_objetivos" and regex.search(conteudo):
            return False
    if conteudo.endswith("\n"):
        sufixo = PLACEHOLDER_NAO_OBJETIVOS
    else:
        sufixo = "\n" + PLACEHOLDER_NAO_OBJETIVOS
    caminho.write_text(conteudo + sufixo, encoding="utf-8")
    return True


def _expandir_paths(entradas: Iterable[str | Path]) -> list[Path]:
    """Expande paths recebidos: diretórios viram glob `sprint_*.md`.

    Caminhos não casando o padrão `sprint_*.md` são silenciosamente ignorados
    (modo seguro para hook pre-commit que recebe lista heterogênea).
    """
    resultado: list[Path] = []
    for entrada in entradas:
        caminho = Path(entrada)
        if caminho.is_dir():
            resultado.extend(sorted(caminho.glob("sprint_*.md")))
        elif caminho.is_file() and RE_ARQUIVO_SPEC.search(caminho.name):
            resultado.append(caminho)
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_spec",
        description="Verifica estrutura canônica de specs de sprint.",
    )
    parser.add_argument("paths", nargs="+", help="Arquivos ou diretórios contendo specs")
    parser.add_argument(
        "--auto-completar",
        action="store_true",
        help="Adiciona placeholder `## Não-objetivos\\n(preencher)` em specs que faltam.",
    )
    parser.add_argument(
        "--files",
        action="store_true",
        help="Compatibilidade com pre-commit: ignora paths que não casam sprint_*.md.",
    )
    parser.add_argument(
        "--soft",
        action="store_true",
        help=(
            "Reporta falhas mas retorna exit 0. Pensado para `make lint` cobrindo"
            " backlog histórico sem destravar suite global."
        ),
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    specs = _expandir_paths(args.paths)
    if not specs:
        if args.files:
            # Hook pre-commit chamado sem specs no diff: nada a fazer.
            return 0
        logger.error("Nenhuma spec encontrada nos paths informados")
        return 2

    if args.auto_completar:
        modificadas = 0
        for spec in specs:
            if auto_completar(spec):
                logger.info("AUTO-COMPLETOU %s", spec)
                modificadas += 1
        logger.info("Total: %d specs modificadas", modificadas)
        return 0

    total_falhas = 0
    for spec in specs:
        problemas = validar_spec(spec)
        if problemas:
            total_falhas += 1
            logger.error("FALHA: %s %s", spec, problemas)
        else:
            logger.info("OK: %s", spec)
    logger.info("Resumo: %d/%d specs com falhas", total_falhas, len(specs))
    if total_falhas and not args.soft:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Onde não há lei, não há transgressão." -- Paulo de Tarso, Romanos 4:15
