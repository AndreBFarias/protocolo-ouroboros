#!/bin/bash
# Pre-commit check local -- roda ruff + verifica dados financeiros
# Uso: ./scripts/pre-commit-check.sh (ou integrar ao hook global)

set -euo pipefail

VENV=".venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "$VENV" ]; then
    echo "[AVISO] Ambiente virtual não encontrado. Pulando checks."
    exit 0
fi

source "$VENV/bin/activate"

echo "=== Pre-commit check ==="

# 1. Ruff check
echo -n "Ruff check... "
if ruff check src/ tests/ --quiet 2>/dev/null; then
    echo "[OK]"
else
    echo "[FALHA]"
    ruff check src/ tests/ 2>/dev/null
    exit 1
fi

# 2. Ruff format check
echo -n "Ruff format... "
if ruff format --check src/ tests/ --quiet 2>/dev/null; then
    echo "[OK]"
else
    echo "[FALHA] Rode: make format"
    exit 1
fi

# 3. Verificar dados financeiros nos arquivos staged
echo -n "Dados financeiros... "
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '\.py$' | grep -v 'mappings/' | grep -v 'tests/fixtures/' || true)
if [ -z "$STAGED_FILES" ]; then
    echo "[OK] (nenhum .py staged)"
    exit 0
fi

FOUND=0
for f in $STAGED_FILES; do
    if grep -qE '\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}' "$f" 2>/dev/null; then
        echo ""
        echo "[BLOQUEADO] CPF/CNPJ encontrado em: $f"
        FOUND=1
    fi
done

if [ "$FOUND" -eq 0 ]; then
    echo "[OK]"
else
    exit 1
fi

# 4. Verificação de acentuação (T1 -- bloqueia commit)
echo -n "Acentuação PT-BR... "
if python scripts/check_acentuacao.py 2>/dev/null; then
    echo "[OK]"
else
    echo "[FALHA]"
    python scripts/check_acentuacao.py 2>/dev/null || true
    exit 1
fi

# 5. Freshness do gauntlet (T2 -- apenas avisa)
python scripts/check_gauntlet_freshness.py 2>/dev/null || true

echo "=== Checks concluídos ==="
