#!/usr/bin/env bash
# Hook de exceções silenciosas -- proíbe "except:" vazio ou com "pass".
# Regra CLAUDE.md secao 3: error handling explicito, nunca silent failures.

set -euo pipefail

VIOLATIONS=$(grep -rEn '^[[:space:]]*except[[:space:]]*:[[:space:]]*$' src/ --include="*.py" 2>/dev/null | grep -v __pycache__ || true)

PASS_VIOLATIONS=$(grep -rEn -A1 '^[[:space:]]*except' src/ --include="*.py" 2>/dev/null | grep -E 'pass$' | grep -v __pycache__ || true)

if [ -n "$VIOLATIONS" ] || [ -n "$PASS_VIOLATIONS" ]; then
    echo ""
    echo "======================================================================"
    echo "HOOK FALHOU: check_silent_except"
    echo "======================================================================"
    echo ""
    echo "O QUE FAZ: Proibe except vazio ou except...pass sem tratamento"
    echo ""

    if [ -n "$VIOLATIONS" ]; then
        echo "VIOLACOES (except vazio):"
        echo "$VIOLATIONS"
        echo ""
    fi

    if [ -n "$PASS_VIOLATIONS" ]; then
        echo "VIOLACOES (except ... pass):"
        echo "$PASS_VIOLATIONS"
        echo ""
    fi

    echo "COMO CORRIGIR:"
    echo "  1. Especifique a exceção: except ValueError as e:"
    echo "  2. Logue o erro: logger.error(f\"Erro: {e}\")"
    echo "  3. NUNCA use except: pass -- esconde bugs"
    echo ""
    echo "DOCUMENTACAO: CLAUDE.md secao 3"
    echo "======================================================================"
    echo ""
    exit 1
fi

exit 0

# "Erro escondido e divida acumulando juros." -- principio basico
