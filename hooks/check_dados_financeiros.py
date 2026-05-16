#!/usr/bin/env python3
"""Hook pre-commit: bloqueia padrões de dados financeiros (CPF, CNPJ, agência+conta).

Recebe lista de arquivos via argv. Falha (exit 1) se detectar padrão sensível.
Excluído por padrão para arquivos em `mappings/` e `tests/fixtures/` (configurado
em .pre-commit-config.yaml via `exclude`).

Padrões bloqueados:
- CPF: ``\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}``
- CNPJ: ``\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}``
- Combinação ``agencia ... \\d{4} ... conta ... \\d+`` (case-insensitive).

Exclusão de placeholders canônicos: matches cujos dígitos sejam todos zero
(ex.: ``000.000.000-00``, ``00.000.000/0000-00``) são tratados como
documentação inerte (não há CPF/CNPJ válido inteiramente zero) e ignorados.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PADROES = [
    re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}"),
    re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"),
    re.compile(r"agencia.*\d{4}.*conta.*\d+", re.IGNORECASE),
]


def _eh_placeholder_zero(match_texto: str) -> bool:
    """True quando o match tem apenas zeros nos dígitos (placeholder canônico)."""
    apenas_digitos = re.sub(r"\D", "", match_texto)
    return apenas_digitos != "" and all(c == "0" for c in apenas_digitos)


def varrer(arquivos: list[str]) -> list[str]:
    """Devolve lista de violações no formato `<arquivo>:<linha>: <motivo>`."""
    erros: list[str] = []
    for caminho in arquivos:
        try:
            texto = Path(caminho).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, linha in enumerate(texto.splitlines(), start=1):
            for padrao in PADROES:
                achado = padrao.search(linha)
                if achado and not _eh_placeholder_zero(achado.group(0)):
                    erros.append(f"{caminho}:{i}: possível dado financeiro")
                    break
    return erros


def main() -> int:
    erros = varrer(sys.argv[1:])
    if not erros:
        return 0
    print("[BLOQUEADO] Dados financeiros detectados:")
    for e in erros[:10]:
        print(f"  {e}")
    if len(erros) > 10:
        print(f"  ... e mais {len(erros) - 10} ocorrência(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


# "A privacidade é a base da liberdade." -- Hannah Arendt
