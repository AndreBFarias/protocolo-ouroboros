"""Sprint DOC-VERDADE-01.A -- Auditor de ESTADO_ATUAL.md vs realidade do repo.

Confronta cada `[A FAZER]` ou `[EM CURSO]` no `contexto/ESTADO_ATUAL.md`
com:
- Existencia de spec correspondente em `docs/sprints/concluidos/`.
- Commits recentes mencionando o slug.

Emite relatório em `docs/auditorias/estado_<data>.md` listando linhas
suspeitas (declaram pendencia mas tem evidencia de fechamento).

NÃO eh cron, NÃO eh auto-fix por default. Modo `--executar` prepara um
diff sugerido em vez de reescrever o arquivo (a aplicação do diff cabe
ao supervisor humano + Opus revisor da sessão).

Uso:
    python scripts/auditar_estado.py             # dry-run, imprime no stdout
    python scripts/auditar_estado.py --executar  # grava relatório em docs/auditorias/

Conforme ADR-13 e docs/SUPERVISOR_OPUS.md: este script eh ferramenta
auxiliar do supervisor (Opus interativo). Não chama Anthropic API.
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[1]
ARQ_ESTADO = RAIZ / "contexto" / "ESTADO_ATUAL.md"
DIR_CONCLUIDAS = RAIZ / "docs" / "sprints" / "concluidos"
DIR_AUDITORIAS = RAIZ / "docs" / "auditorias"

RE_PENDENCIA = re.compile(r"^\s*\[(A FAZER|EM CURSO)\]\s+(.+?)\s*$", re.MULTILINE)
RE_SLUG_MENCIONADO = re.compile(r"\b([A-Z][A-Z0-9_-]{2,}-?\d*)\b")


def carregar_pendencias(caminho: Path) -> list[tuple[int, str, str]]:
    """Retorna lista (linha, status, descricao) de cada [A FAZER] ou [EM CURSO]."""
    if not caminho.exists():
        return []
    texto = caminho.read_text(encoding="utf-8")
    resultado: list[tuple[int, str, str]] = []
    for match in RE_PENDENCIA.finditer(texto):
        linha = texto[: match.start()].count("\n") + 1
        status = match.group(1)
        descricao = match.group(2).strip()
        resultado.append((linha, status, descricao))
    return resultado


def specs_concluidas() -> set[str]:
    """Retorna set de slugs de spec em docs/sprints/concluidos/ (sem extensao .md)."""
    if not DIR_CONCLUIDAS.is_dir():
        return set()
    return {f.stem for f in DIR_CONCLUIDAS.glob("*.md")}


def commits_mencionando(slug: str, limite: int = 5) -> list[str]:
    """Retorna SHAs curtos de commits que mencionam o slug no log."""
    cmd = ["git", "log", f"--grep={slug}", "--format=%h", f"-n{limite}", "--all"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=RAIZ)
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    return [s for s in proc.stdout.strip().splitlines() if s]


def avaliar_pendencia(descricao: str, concluidas: set[str]) -> tuple[str, list[str]]:
    """Para uma descrição de pendencia, retorna (veredito, evidencias).

    Veredito:
    - "PROVAVELMENTE_FECHADA": existe spec em concluídos OU commit mencionando.
    - "INCONCLUSIVO": não deu para inferir.
    """
    evidencias: list[str] = []
    slugs_brutos = RE_SLUG_MENCIONADO.findall(descricao)
    candidatos = {s.lower().replace("-", "_") for s in slugs_brutos if len(s) >= 3}

    for spec_slug in concluidas:
        slug_norm = spec_slug.lower().replace("-", "_")
        for cand in candidatos:
            if cand in slug_norm or slug_norm.startswith(f"sprint_{cand}"):
                evidencias.append(f"spec concluída: docs/sprints/concluidos/{spec_slug}.md")
                break

    for cand in candidatos:
        commits = commits_mencionando(cand.replace("_", "-"))
        for sha in commits[:2]:
            evidencias.append(f"commit menciona '{cand}': {sha}")

    veredito = "PROVAVELMENTE_FECHADA" if evidencias else "INCONCLUSIVO"
    return veredito, evidencias


def montar_relatório(pendencias_avaliadas: list[tuple[int, str, str, str, list[str]]]) -> str:
    hoje = date.today().isoformat()
    linhas = [
        f"# Auditoria de ESTADO_ATUAL.md -- {hoje}",
        "",
        "> Gerado por `scripts/auditar_estado.py` (Sprint DOC-VERDADE-01.A).",
        "> Confronta cada `[A FAZER]` ou `[EM CURSO]` em ESTADO_ATUAL.md com",
        "> realidade do repo: specs em `docs/sprints/concluidos/` + commits no `git log`.",
        "",
        "## Sumario",
        "",
        f"- Pendencias declaradas: {len(pendencias_avaliadas)}",
    ]
    suspeitas = [p for p in pendencias_avaliadas if p[3] == "PROVAVELMENTE_FECHADA"]
    inconclusivas = [p for p in pendencias_avaliadas if p[3] == "INCONCLUSIVO"]
    linhas += [
        f"- Provavelmente ja fechadas (precisam revisao manual): **{len(suspeitas)}**",
        f"- Inconclusivas (sem match obvio em concluidos/git): {len(inconclusivas)}",
        "",
    ]

    if suspeitas:
        linhas += [
            "## Pendencias suspeitas (revisar e atualizar ESTADO_ATUAL)",
            "",
        ]
        for linha, status, descricao, _veredito, evidencias in suspeitas:
            linhas.append(f"### Linha {linha}: `[{status}] {descricao}`")
            linhas.append("")
            for ev in evidencias[:5]:
                linhas.append(f"- {ev}")
            linhas.append("")

    if inconclusivas:
        linhas += [
            "## Pendencias inconclusivas (provavelmente legitimas)",
            "",
        ]
        for linha, status, descricao, _, _ in inconclusivas:
            linhas.append(f"- Linha {linha}: `[{status}] {descricao}`")
        linhas.append("")

    linhas += [
        "---",
        "",
        '*"Doc fotografada precisa de revelacao periodica." -- principio do auditor manual*',
        "",
    ]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Sem flag: imprime no stdout. Com flag: grava em docs/auditorias/.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not ARQ_ESTADO.exists():
        logger.error("ESTADO_ATUAL.md não encontrado em %s", ARQ_ESTADO)
        return 2

    pendencias = carregar_pendencias(ARQ_ESTADO)
    if not pendencias:
        logger.info("[OK] Nenhuma pendencia [A FAZER]/[EM CURSO] em ESTADO_ATUAL.md.")
        return 0

    concluidas = specs_concluidas()
    avaliadas = []
    for linha, status, descricao in pendencias:
        veredito, evidencias = avaliar_pendencia(descricao, concluidas)
        avaliadas.append((linha, status, descricao, veredito, evidencias))

    relatório = montar_relatório(avaliadas)

    if args.executar:
        DIR_AUDITORIAS.mkdir(parents=True, exist_ok=True)
        destino = DIR_AUDITORIAS / f"estado_{date.today().isoformat()}.md"
        destino.write_text(relatório, encoding="utf-8")
        logger.info("[OK] Relatório gravado em %s", destino)
        print(destino)
    else:
        sys.stdout.write(relatório)

    suspeitas = [p for p in avaliadas if p[3] == "PROVAVELMENTE_FECHADA"]
    return 1 if suspeitas else 0


if __name__ == "__main__":
    sys.exit(main())


# "Auditar a propria foto eh ato de honestidade." -- principio DOC-VERDADE-01
