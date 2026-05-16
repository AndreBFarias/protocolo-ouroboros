#!/usr/bin/env python3
"""Normaliza specs de sprint em ``docs/sprints/`` para frontmatter YAML canônico.

Três subcomandos:

- ``auditar``: lista specs sem frontmatter ou com campos obrigatórios faltantes.
  Exit 0 se todas estão OK; exit 1 caso contrário.
- ``normalizar``: adiciona frontmatter inferido para specs que não têm.
  Não destrói conteúdo existente; só prepende bloco YAML.
- ``validar``: garante que o YAML de TODAS as specs em ``backlog/`` e
  ``concluidos/`` é parseável (yaml.safe_load não levanta) e tem campos
  obrigatórios. Exit 0/1.

Uso típico::

    python scripts/normalizar_specs.py auditar
    python scripts/normalizar_specs.py normalizar --excluir sprint_x.md
    python scripts/normalizar_specs.py validar

Princípio do parseável: sem frontmatter, spec é diário; com frontmatter,
é registro.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

# Campos obrigatórios mínimos no frontmatter canônico.
CAMPOS_OBRIGATORIOS = (
    "id",
    "titulo",
    "status",
    "concluida_em",
    "prioridade",
    "data_criacao",
    "epico",
    "depende_de",
)

# Diretórios canônicos de specs.
RAIZ_REPO = Path(__file__).resolve().parents[1]
DIR_BACKLOG = RAIZ_REPO / "docs" / "sprints" / "backlog"
DIR_CONCLUIDOS = RAIZ_REPO / "docs" / "sprints" / "concluidos"

# Regex do delimitador YAML ``---`` no início do arquivo.
RE_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Comentários HTML inline (``<!-- ... -->``) que aparecem em valores e
# quebram o parser YAML estrito. São removidos antes do parse.
RE_COMENTARIO_HTML = re.compile(r"<!--.*?-->")

# Inferência de prioridade quando o corpo cita ``Prioridade: PN``.
RE_PRIORIDADE_INLINE = re.compile(r"prioridade\s*[:=]\s*[\"']?(P[0-3])[\"']?", re.IGNORECASE)


@dataclass
class ResultadoSpec:
    """Resultado da inspeção de uma spec."""

    path: Path
    tem_frontmatter: bool
    campos_faltantes: list[str]
    parse_ok: bool
    erro_parse: str = ""


def carregar_frontmatter(texto: str) -> tuple[dict | None, str | None]:
    """Extrai frontmatter YAML do início de ``texto``.

    Retorna ``(dict, None)`` em sucesso; ``(None, mensagem)`` em erro.
    """
    match = RE_FRONTMATTER.match(texto)
    if not match:
        return None, "sem frontmatter"
    bruto = RE_COMENTARIO_HTML.sub("", match.group(1))
    try:
        dados = yaml.safe_load(bruto) or {}
    except yaml.YAMLError as exc:
        return None, f"yaml inválido: {exc}"
    if not isinstance(dados, dict):
        return None, "frontmatter não é dict"
    return dados, None


def inspecionar(path: Path) -> ResultadoSpec:
    """Examina uma spec e relata campos faltantes/erros de parse."""
    texto = path.read_text(encoding="utf-8")
    dados, erro = carregar_frontmatter(texto)
    if dados is None:
        return ResultadoSpec(
            path=path,
            tem_frontmatter=False,
            campos_faltantes=list(CAMPOS_OBRIGATORIOS),
            parse_ok=False,
            erro_parse=erro or "",
        )
    faltantes = [campo for campo in CAMPOS_OBRIGATORIOS if campo not in dados]
    return ResultadoSpec(
        path=path,
        tem_frontmatter=True,
        campos_faltantes=faltantes,
        parse_ok=True,
    )


def coletar_specs() -> list[Path]:
    """Retorna lista ordenada de specs em ``backlog/`` e ``concluidos/``."""
    arquivos: list[Path] = []
    for diretorio in (DIR_BACKLOG, DIR_CONCLUIDOS):
        if diretorio.is_dir():
            arquivos.extend(sorted(diretorio.glob("*.md")))
    return arquivos


def inferir_id(path: Path) -> str:
    """Deriva ``id`` canônico do nome do arquivo (slug em CAIXA ALTA)."""
    nome = path.stem
    if nome.startswith("sprint_"):
        nome = nome[len("sprint_") :]
    # Remove sufixo de data ``_YYYY-MM-DD`` quando presente.
    nome = re.sub(r"_\d{4}-\d{2}-\d{2}$", "", nome)
    return nome.replace("_", "-").upper()


def inferir_titulo(texto_pos_frontmatter: str, fallback: str) -> str:
    """Pega o primeiro ``# Header`` ou primeira linha não-vazia."""
    for linha in texto_pos_frontmatter.splitlines():
        bruta = linha.strip()
        if not bruta:
            continue
        if bruta.startswith("#"):
            return bruta.lstrip("#").strip() or fallback
        return bruta[:140]
    return fallback


def inferir_prioridade(texto: str) -> str:
    """Procura ``Prioridade: PN`` no corpo. Default ``P2`` (conservador)."""
    match = RE_PRIORIDADE_INLINE.search(texto)
    if match:
        return match.group(1).upper()
    return "P2"


def inferir_data_criacao(path: Path, fallback: str) -> str:
    """Data de criação via ``git log --diff-filter=A``. Fallback se git falhar."""
    try:
        saida = subprocess.run(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--follow",
                "--format=%aI",
                "--",
                str(path),
            ],
            cwd=RAIZ_REPO,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return fallback
    linhas = [linha.strip() for linha in saida.stdout.splitlines() if linha.strip()]
    if not linhas:
        return fallback
    # Última linha = commit mais antigo (criação).
    return linhas[-1][:10]


def inferir_status(path: Path) -> str:
    """Retorna o status canônico (valor do enum) conforme diretório da spec.

    Valor literal sem acento por convenção do frontmatter do projeto.
    """
    # "concluida" e "backlog" sao valores literais do enum  [noqa: accent]
    return "concluida" if path.parent.name == "concluidos" else "backlog"


def construir_frontmatter(path: Path, texto: str, fallback_data: str) -> dict:
    """Monta dict com campos obrigatórios para uma spec sem frontmatter."""
    id_inferido = inferir_id(path)
    titulo = inferir_titulo(texto, fallback=id_inferido)
    return {
        "id": id_inferido,
        "titulo": titulo,
        "status": inferir_status(path),
        "concluida_em": None,
        "prioridade": inferir_prioridade(texto),
        "data_criacao": inferir_data_criacao(path, fallback_data),
        "fase": "OUTROS",
        "epico": 0,
        "depende_de": [],
        "tipo_documental_alvo": None,
    }


def serializar_frontmatter(dados: dict) -> str:
    """YAML determinístico com chaves na ordem canônica primeiro."""
    ordenado: dict = {}
    for campo in (
        "id",
        "titulo",
        "status",
        "concluida_em",
        "prioridade",
        "data_criacao",
        "fase",
        "epico",
        "depende_de",
        "tipo_documental_alvo",
    ):
        if campo in dados:
            ordenado[campo] = dados[campo]
    # Demais chaves preservadas após a ordem canônica.
    for chave, valor in dados.items():
        if chave not in ordenado:
            ordenado[chave] = valor
    return yaml.safe_dump(ordenado, allow_unicode=True, sort_keys=False, default_flow_style=False)


def aplicar_frontmatter(path: Path, fallback_data: str) -> bool:
    """Adiciona frontmatter inferido se a spec não tem. Retorna True se mudou."""
    texto = path.read_text(encoding="utf-8")
    if RE_FRONTMATTER.match(texto):
        return False
    dados = construir_frontmatter(path, texto, fallback_data)
    bloco = "---\n" + serializar_frontmatter(dados) + "---\n\n"
    novo = bloco + texto.lstrip("\n")
    path.write_text(novo, encoding="utf-8")
    return True


def cmd_auditar(args: argparse.Namespace) -> int:
    """Lista specs com problemas. Exit 1 se houver pendência."""
    pendencias: list[ResultadoSpec] = []
    for path in coletar_specs():
        if path.name in args.excluir:
            continue
        resultado = inspecionar(path)
        if not resultado.tem_frontmatter or resultado.campos_faltantes:
            pendencias.append(resultado)
    if not pendencias:
        print("auditar: 0 pendencias")
        return 0
    print(f"auditar: {len(pendencias)} pendencias")
    for resultado in pendencias:
        rel = resultado.path.relative_to(RAIZ_REPO)
        if not resultado.tem_frontmatter:
            print(f"  SEM_FRONTMATTER {rel} ({resultado.erro_parse})")
        else:
            faltam = ",".join(resultado.campos_faltantes)
            print(f"  CAMPOS_FALTANTES {rel} faltam={faltam}")
    return 1


def cmd_normalizar(args: argparse.Namespace) -> int:
    """Aplica frontmatter inferido onde necessário. Idempotente."""
    mudados: list[Path] = []
    for path in coletar_specs():
        if path.name in args.excluir:
            continue
        if aplicar_frontmatter(path, fallback_data=args.data_fallback):
            mudados.append(path)
    print(f"normalizar: {len(mudados)} arquivos atualizados")
    for path in mudados:
        print(f"  + {path.relative_to(RAIZ_REPO)}")
    return 0


def cmd_validar(args: argparse.Namespace) -> int:
    """Confirma que TODAS as specs têm frontmatter parseável."""
    falhas: list[ResultadoSpec] = []
    total = 0
    for path in coletar_specs():
        if path.name in args.excluir:
            continue
        total += 1
        resultado = inspecionar(path)
        if not resultado.parse_ok or not resultado.tem_frontmatter:
            falhas.append(resultado)
    if not falhas:
        print(f"validar: {total} specs OK")
        return 0
    print(f"validar: {len(falhas)}/{total} specs com problema")
    for resultado in falhas:
        rel = resultado.path.relative_to(RAIZ_REPO)
        print(f"  FALHA {rel}: {resultado.erro_parse or 'campos faltantes'}")
    return 1


def construir_parser() -> argparse.ArgumentParser:
    """Define o CLI argparse com 3 subcomandos."""
    parser = argparse.ArgumentParser(description="Normaliza frontmatter de specs de sprint.")
    parser.add_argument(
        "--excluir",
        action="append",
        default=[],
        metavar="ARQUIVO",
        help="Nome de arquivo (basename) a ignorar; pode repetir.",
    )
    subs = parser.add_subparsers(dest="comando", required=True)

    p_aud = subs.add_parser("auditar", help="Lista specs com problemas.")
    p_aud.set_defaults(func=cmd_auditar)

    p_norm = subs.add_parser("normalizar", help="Adiciona frontmatter inferido onde necessário.")
    p_norm.add_argument(
        "--data-fallback",
        default="2026-05-13",
        help="Data ISO usada quando git log não retorna criação do arquivo.",
    )
    p_norm.set_defaults(func=cmd_normalizar)

    p_val = subs.add_parser("validar", help="Verifica frontmatter parseável global.")
    p_val.set_defaults(func=cmd_validar)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point CLI."""
    parser = construir_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())


# "O que pode ser dito, pode ser dito claramente; e sobre o que não se pode
# falar, deve-se calar." -- Ludwig Wittgenstein
