#!/usr/bin/env python3
"""Audita cobertura documental de sprints do Protocolo Ouroboros.

Lista sprints em docs/sprints/{concluidos,producao,backlog,arquivadas},
identifica sprints referenciados em commits mas sem documentação,
e gera relatório de cobertura.

Uso:
    .venv/bin/python scripts/audit_sprint_coverage.py
    .venv/bin/python scripts/audit_sprint_coverage.py --verbose
    .venv/bin/python scripts/audit_sprint_coverage.py --json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SPRINT_DIRS = [
    BASE_DIR / "docs" / "sprints" / "concluidos",
    BASE_DIR / "docs" / "sprints" / "producao",
    BASE_DIR / "docs" / "sprints" / "backlog",
    BASE_DIR / "docs" / "sprints" / "arquivadas",
]

LOG = logging.getLogger("audit_sprint_coverage")

SPRINT_FILE_PATTERN = re.compile(r"^sprint_(\d+)([a-z]*)_.*\.md$", re.IGNORECASE)

COMMIT_SPRINT_PATTERNS = [
    re.compile(r"\(S(\d+)([a-z]?)\)", re.IGNORECASE),
    re.compile(r"\bS(\d+)([a-z]?)[):\s]", re.IGNORECASE),
    re.compile(r"\bSprint[\s._-]?(\d+)([a-z]?)\b", re.IGNORECASE),
    re.compile(r"\(S(\d+)-(\d+)\)"),
]


@dataclass
class SprintRef:
    """Referência a sprint encontrada em commits."""

    number: int
    suffix: str = ""
    commits: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.number}{self.suffix}"


def parse_documented_sprints() -> dict[str, Path]:
    """Retorna mapa de sprint label -> filepath para sprints documentados."""
    result: dict[str, Path] = {}

    for directory in SPRINT_DIRS:
        if not directory.exists():
            LOG.warning("Diretório não encontrado: %s", directory)
            continue

        for filepath in sorted(directory.glob("sprint_*.md")):
            match = SPRINT_FILE_PATTERN.match(filepath.name)
            if not match:
                LOG.debug("Arquivo ignorado (padrão não reconhecido): %s", filepath.name)
                continue

            number = int(match.group(1))
            suffix = match.group(2).lower()
            label = f"{number}{suffix}"
            result[label] = filepath

    return result


def extract_sprint_refs_from_commits() -> dict[str, SprintRef]:
    """Extrai referências a sprints das mensagens de commit via git log."""
    try:
        proc = subprocess.run(
            ["git", "log", "--oneline", "--all"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(BASE_DIR),
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        LOG.error("Falha ao executar git log: %s", exc)
        return {}

    if proc.returncode != 0:
        LOG.error("git log retornou código %d: %s", proc.returncode, proc.stderr.strip())
        return {}

    refs: dict[str, SprintRef] = {}

    for line in proc.stdout.splitlines():
        commit_hash = line.split(" ", 1)[0] if " " in line else ""
        message = line.split(" ", 1)[1] if " " in line else line

        found_labels = _extract_labels_from_message(message)
        seen_in_line: set[str] = set()

        for label, number, suffix in found_labels:
            if label in seen_in_line:
                continue
            seen_in_line.add(label)

            if label not in refs:
                refs[label] = SprintRef(number=number, suffix=suffix)
            refs[label].commits.append(f"{commit_hash} {message}")

    return refs


def _extract_labels_from_message(message: str) -> list[tuple[str, int, str]]:
    """Extrai tuplas (label, number, suffix) de uma mensagem de commit."""
    found: list[tuple[str, int, str]] = []

    for pattern in COMMIT_SPRINT_PATTERNS:
        for match in pattern.finditer(message):
            groups = match.groups()

            if pattern == COMMIT_SPRINT_PATTERNS[-1]:
                start = int(groups[0])
                end = int(groups[1])
                if end > start and (end - start) <= 20:
                    for n in range(start, end + 1):
                        found.append((str(n), n, ""))
                continue

            number = int(groups[0])
            suffix = groups[1].lower() if len(groups) > 1 and groups[1] else ""
            found.append((f"{number}{suffix}", number, suffix))

    return found


def build_report(
    documented: dict[str, Path],
    commit_refs: dict[str, SprintRef],
    verbose: bool = False,
) -> str:
    """Constrói relatório de cobertura em texto."""
    doc_labels = set(documented.keys())
    commit_labels = set(commit_refs.keys())

    undocumented_labels = commit_labels - doc_labels
    all_known = doc_labels | commit_labels
    total_known = len(all_known)
    total_documented = len(doc_labels)
    coverage = (total_documented / total_known * 100) if total_known > 0 else 0.0

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("  RELATÓRIO DE COBERTURA DOCUMENTAL DE SPRINTS")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Sprints documentados:             {total_documented}")
    lines.append(f"  Sprints referenciados em commits: {len(commit_labels)}")
    lines.append(f"  Sprints únicos conhecidos:        {total_known}")
    lines.append(f"  Sprints sem documentação:         {len(undocumented_labels)}")
    lines.append(f"  Cobertura documental:             {coverage:.1f}%")
    lines.append("")

    if undocumented_labels:
        sorted_undoc = sorted(undocumented_labels, key=_sort_key_for_label)
        lines.append("-" * 70)
        lines.append("  SPRINTS SEM DOCUMENTAÇÃO (referenciados em commits)")
        lines.append("-" * 70)
        lines.append("")

        for label in sorted_undoc:
            ref = commit_refs[label]
            lines.append(f"  Sprint {label}")
            lines.append(f"    Commits encontrados: {len(ref.commits)}")

            display_commits = ref.commits[:5] if not verbose else ref.commits
            for commit_line in display_commits:
                lines.append(f"      {commit_line}")

            if not verbose and len(ref.commits) > 5:
                lines.append(f"      ... e mais {len(ref.commits) - 5} commits")

            lines.append("")

    doc_only = doc_labels - commit_labels
    if doc_only and verbose:
        sorted_doc_only = sorted(doc_only, key=_sort_key_for_label)
        lines.append("-" * 70)
        lines.append("  SPRINTS DOCUMENTADOS SEM COMMITS ASSOCIADOS")
        lines.append("-" * 70)
        lines.append("")

        for label in sorted_doc_only:
            filepath = documented[label]
            relative = filepath.relative_to(BASE_DIR)
            lines.append(f"  Sprint {label}: {relative}")

        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def build_json_report(
    documented: dict[str, Path],
    commit_refs: dict[str, SprintRef],
) -> dict:
    """Constrói relatório de cobertura em formato JSON."""
    doc_labels = set(documented.keys())
    commit_labels = set(commit_refs.keys())

    undocumented_labels = commit_labels - doc_labels
    all_known = doc_labels | commit_labels
    total_known = len(all_known)
    total_documented = len(doc_labels)
    coverage = (total_documented / total_known * 100) if total_known > 0 else 0.0

    undocumented_entries = []
    for label in sorted(undocumented_labels, key=_sort_key_for_label):
        ref = commit_refs[label]
        undocumented_entries.append(
            {
                "sprint": label,
                "commit_count": len(ref.commits),
                "commits": ref.commits[:10],
            }
        )

    return {
        "total_documented": total_documented,
        "total_in_commits": len(commit_labels),
        "total_known": total_known,
        "undocumented_count": len(undocumented_labels),
        "coverage_percent": round(coverage, 1),
        "undocumented_sprints": undocumented_entries,
    }


def _sort_key_for_label(label: str) -> tuple[int, str]:
    """Ordena labels numericamente com sufixo alfabético como desempate."""
    match = re.match(r"(\d+)(.*)", label)
    if match:
        return (int(match.group(1)), match.group(2))
    return (9999, label)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audita cobertura documental de sprints do Ouroboros"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    documented = parse_documented_sprints()
    commit_refs = extract_sprint_refs_from_commits()

    if args.json:
        report_data = build_json_report(documented, commit_refs)
        sys.stdout.write(json.dumps(report_data, indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(build_report(documented, commit_refs, verbose=args.verbose) + "\n")

    undocumented_count = len(set(commit_refs.keys()) - set(documented.keys()))
    return 1 if undocumented_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())


# "O que não se mede, não se melhora." -- Peter Drucker
