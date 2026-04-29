#!/bin/bash
# Sprint ANTI-MIGUE-01 -- script wrapper do gate anti-migué.
#
# Roda os 5 checks automatizáveis (lint, smoke, pytest, frontmatter
# concluida_em, gate 4-way para tipo opcional) em sequência. Sai com
# exit 0 apenas se todos passarem. Para extratores novos, exige tipo
# explícito como argumento.
#
# Uso:
#     ./scripts/check_anti_migue.sh                  # checks gerais
#     ./scripts/check_anti_migue.sh --tipo cnh       # + gate 4-way para 'cnh'

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV="$REPO_ROOT/.venv"
PYTHON="$VENV/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "[FAIL] .venv ausente em $VENV. Rode ./install.sh primeiro." >&2
    exit 2
fi

TIPO=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tipo)
            TIPO="$2"
            shift 2
            ;;
        --help|-h)
            sed -n '2,11p' "$0"
            exit 0
            ;;
        *)
            echo "[FAIL] Argumento desconhecido: $1" >&2
            exit 2
            ;;
    esac
done

echo "=== [1/5] make lint ==="
make lint

echo "=== [2/5] make smoke ==="
make smoke

echo "=== [3/5] pytest tests/ -q ==="
"$PYTHON" -m pytest tests/ -q

echo "=== [4/5] check frontmatter concluida_em ==="
"$PYTHON" scripts/check_concluida_em.py

if [ -n "$TIPO" ]; then
    echo "=== [5/5] gate 4-way conformance para tipo=$TIPO ==="
    "$PYTHON" -m tests.conformance.gate "$TIPO"
else
    echo "=== [5/5] gate 4-way conformance: pulado (use --tipo <X> para extratores novos) ==="
fi

echo ""
echo "=== anti-migue gauntlet: TODOS verdes ==="
