#!/usr/bin/env bash
# Verifica se modulos Python usam logger ao inves de print().
# Regra: CLAUDE.md secao 5 -- nunca print() em producao.
# Isenta: tests, dashboard (Streamlit), scripts (CLI), __init__.py.

set -euo pipefail

ERRORS=0
WARNINGS=0

IGNORE_FILES=(
    "conftest.py"
    "__init__.py"
    "run_tests.py"
    "doc_generator.py"
    "validator.py"
)

is_ignored() {
    local file="$1"
    for pattern in "${IGNORE_FILES[@]}"; do
        if [[ "$file" == *"$pattern"* ]]; then
            return 0
        fi
    done
    return 1
}

echo "Verificando uso de logger..."

STAGED=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null | grep -E '\.py$' || true)

if [ -z "$STAGED" ]; then
    echo "OK: nenhum .py staged"
    exit 0
fi

for file in $STAGED; do
    if [[ ! -f "$file" ]]; then
        continue
    fi

    if [[ "$file" == *"/tests/"* ]] || [[ "$file" == "tests/"* ]]; then
        continue
    fi

    if [[ "$file" == *"/dashboard/"* ]] || [[ "$file" == "scripts/"* ]]; then
        continue
    fi

    if [[ "$file" == "hooks/"* ]]; then
        continue
    fi

    if is_ignored "$file"; then
        continue
    fi

    has_logger=$(grep -cE "(get_logger|logging\.getLogger|from src\.utils\.logger|import logging)" "$file" 2>/dev/null || echo "0")
    has_print=$(grep -cE "^[[:space:]]*print\(" "$file" 2>/dev/null || echo "0")

    if [[ $has_print -gt 0 ]]; then
        if [[ $has_logger -eq 0 ]]; then
            echo "ERRO: $file usa print() sem logger configurado"
            echo "  -> Adicione: from src.utils.logger import get_logger"
            echo "  -> Use: logger = get_logger(__name__)"
            ERRORS=$((ERRORS + 1))
        else
            echo "AVISO: $file tem $has_print print() que poderiam ser logger"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
done

echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo "FALHA: $ERRORS arquivo(s) sem logger configurado usando print()"
    exit 1
fi

if [[ $WARNINGS -gt 0 ]]; then
    echo "AVISO: $WARNINGS arquivo(s) com print() que podem virar logger"
fi

echo "OK: verificação de logger concluída"
exit 0

# "Medir e controlar, ou ser controlado." -- Peter Drucker
