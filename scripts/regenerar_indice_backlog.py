"""Regenera `docs/sprints/backlog/INDICE_<YYYY-MM-DD>.md`.

Sprint META-REGEN-INDICE-BACKLOG (2026-05-17). Catalogador vivo: lê
todas as specs em `docs/sprints/backlog/` (exceto `INDICE_*.md`),
agrupa por épico (frontmatter `epico:`) e prioridade, gera markdown
tabela. Anteriores são arquivados em `_arquivado/`.

Uso CLI::

    python scripts/regenerar_indice_backlog.py            # dry-run stdout
    python scripts/regenerar_indice_backlog.py --apply    # grava arquivo
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
DIR_BACKLOG = _RAIZ / "docs" / "sprints" / "backlog"
DIR_ARQUIVADO = DIR_BACKLOG / "_arquivado"


_PADRAO_FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_PADRAO_CAMPO = re.compile(r"^(\w+):\s*(.*?)$", re.MULTILINE)


def _ler_frontmatter(path: Path) -> dict[str, str]:
    """Extrai campos do frontmatter YAML inicial. Falha-soft: dict vazio."""
    try:
        texto = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = _PADRAO_FRONTMATTER.match(texto)
    if not match:
        return {}
    bloco = match.group(1)
    campos: dict[str, str] = {}
    for m in _PADRAO_CAMPO.finditer(bloco):
        chave = m.group(1).strip()
        valor = m.group(2).strip().strip('"')
        campos[chave] = valor
    return campos


_EPICOS_CANONICOS: dict[str, str] = {
    "1": "Fase A: Graduar tipos documentais",
    "2": "Robustez operacional",
    "3": "Qualidade de dados (linking + categorização)",
    "4": "IRPF + pagador vs beneficiário",
    "5": "UX dashboard",
    "6": "Mobile bridge",
    "7": "LLM v2 + fontes adicionais",
    "8": "Saneamento técnico contínuo",
}


def _coletar_specs() -> list[dict]:
    """Devolve lista de dicts com {path, id, titulo, prioridade, epico, esforco, status}."""
    out: list[dict] = []
    if not DIR_BACKLOG.exists():
        return out
    for path in sorted(DIR_BACKLOG.glob("*.md")):
        if path.name.startswith("INDICE_") or path.parent.name == "_arquivado":
            continue
        fm = _ler_frontmatter(path)
        out.append(
            {
                "path": path.name,
                "id": fm.get("id", path.stem),
                "titulo": fm.get("titulo", "(sem título)"),
                "prioridade": fm.get("prioridade", "?"),
                "epico": fm.get("epico", "?"),
                "esforco": fm.get("esforco_estimado_horas", "?"),
                "status": fm.get("status", "backlog"),
            }
        )
    return out


def _gerar_markdown(specs: list[dict], data_iso: str) -> str:
    """Compõe markdown do índice."""
    total = len(specs)
    por_prioridade: dict[str, int] = defaultdict(int)
    por_epico: dict[str, list[dict]] = defaultdict(list)
    sem_epico: list[dict] = []
    com_status_diferente: list[dict] = []

    for s in specs:
        por_prioridade[s["prioridade"]] += 1
        if s["status"] != "backlog":
            com_status_diferente.append(s)
        if s["epico"] in _EPICOS_CANONICOS:
            por_epico[s["epico"]].append(s)
        else:
            sem_epico.append(s)

    linhas: list[str] = [
        f"# Índice canônico do backlog — {data_iso}",
        "",
        f"**Total**: {total} specs em `docs/sprints/backlog/`.",
        "",
        "**Por prioridade**: " + " · ".join(
            f"{p}={n}" for p, n in sorted(por_prioridade.items())
        ),
        "",
        "Regenerado automaticamente por `scripts/regenerar_indice_backlog.py` "
        "(Sprint META-REGEN-INDICE-BACKLOG).",
        "",
        "---",
        "",
    ]

    if com_status_diferente:
        linhas.append("## Status anômalo (não-backlog)")
        linhas.append("")
        linhas.append("| ID | Status | Path |")
        linhas.append("|---|---|---|")
        for s in com_status_diferente:
            linhas.append(f"| `{s['id']}` | {s['status']} | `{s['path']}` |")
        linhas.append("")

    for epico_id in sorted(_EPICOS_CANONICOS):
        specs_epico = por_epico.get(epico_id, [])
        if not specs_epico:
            continue
        linhas.append(f"## Épico {epico_id}: {_EPICOS_CANONICOS[epico_id]}")
        linhas.append("")
        linhas.append(f"{len(specs_epico)} specs.")
        linhas.append("")
        linhas.append("| ID | Pri | Esforço | Título |")
        linhas.append("|---|---|---|---|")
        for s in sorted(specs_epico, key=lambda x: (x["prioridade"], x["id"])):
            linhas.append(
                f"| `{s['id']}` | {s['prioridade']} | {s['esforco']}h | {s['titulo']} |"
            )
        linhas.append("")

    if sem_epico:
        linhas.append("## Sem épico definido")
        linhas.append("")
        linhas.append(f"{len(sem_epico)} specs sem `epico:` no frontmatter (revisar):")
        linhas.append("")
        linhas.append("| ID | Pri | Path |")
        linhas.append("|---|---|---|")
        for s in sorted(sem_epico, key=lambda x: x["id"]):
            linhas.append(f"| `{s['id']}` | {s['prioridade']} | `{s['path']}` |")
        linhas.append("")

    linhas.append("")
    linhas.append("---")
    linhas.append("")
    linhas.append(
        "*\"Catálogo é mapa do que existe; mapa desatualizado é boato.\""
        " — princípio do índice vivo*"
    )

    return "\n".join(linhas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenera INDICE_*.md do backlog")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava arquivo + arquiva antigos (default: dry-run stdout)",
    )
    args = parser.parse_args(argv)

    if not DIR_BACKLOG.exists():
        sys.stderr.write(f"DIR_BACKLOG não existe: {DIR_BACKLOG}\n")
        return 1

    specs = _coletar_specs()
    data_iso = datetime.now().strftime("%Y-%m-%d")
    md = _gerar_markdown(specs, data_iso)

    if not args.apply:
        sys.stdout.write(md)
        sys.stdout.write(f"\n(dry-run: {len(specs)} specs catalogadas)\n")
        return 0

    # Arquiva antigos:
    DIR_ARQUIVADO.mkdir(parents=True, exist_ok=True)
    arquivados = 0
    for antigo in DIR_BACKLOG.glob("INDICE_*.md"):
        destino = DIR_ARQUIVADO / antigo.name
        if not destino.exists():
            shutil.move(str(antigo), str(destino))
            arquivados += 1

    # Escreve o novo:
    destino_novo = DIR_BACKLOG / f"INDICE_{data_iso}.md"
    destino_novo.write_text(md, encoding="utf-8")

    sys.stdout.write(f"Novo índice: {destino_novo}\n")
    sys.stdout.write(f"Antigos arquivados: {arquivados}\n")
    sys.stdout.write(f"Specs catalogadas: {len(specs)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Catálogo é mapa do que existe; mapa desatualizado é boato." -- princípio
