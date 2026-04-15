#!/usr/bin/env python3
"""Verificação de freshness do gauntlet.

Verifica se o gauntlet foi executado nas últimas 24 horas.
T2 warning: não bloqueia commit, apenas avisa.

Uso:
    python scripts/check_gauntlet_freshness.py
"""

import re
import sys
from datetime import datetime
from pathlib import Path

CAMINHO_REPORT: Path = Path(__file__).resolve().parents[1] / "GAUNTLET_REPORT.md"
LIMITE_HORAS: int = 24


def obter_timestamp_gauntlet() -> datetime | None:
    """Extrai o timestamp da última execução do GAUNTLET_REPORT.md."""
    if not CAMINHO_REPORT.exists():
        return None

    try:
        conteudo = CAMINHO_REPORT.read_text(encoding="utf-8")
    except OSError:
        return None

    match = re.search(r"Data:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", conteudo)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def main() -> int:
    """Ponto de entrada principal."""
    timestamp = obter_timestamp_gauntlet()

    if timestamp is None:
        print("\n  [AVISO] GAUNTLET_REPORT.md não encontrado ou sem timestamp.")
        print("          Execute: ./run.sh --gauntlet\n")
        return 0  # T2: não bloqueia

    agora = datetime.now()
    diferenca = agora - timestamp
    horas = diferenca.total_seconds() / 3600

    if horas > LIMITE_HORAS:
        horas_int = int(horas)
        print(f"\n  [AVISO] Gauntlet não executado há {horas_int}h (limite: {LIMITE_HORAS}h)")
        print(f"          Última execução: {timestamp.strftime('%d/%m/%Y %H:%M')}")
        print("          Execute: ./run.sh --gauntlet\n")
        return 0  # T2: não bloqueia

    return 0


if __name__ == "__main__":
    sys.exit(main())

# "A medida de um homem é o que ele faz com o poder." -- Platão
