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

# 5. Hooks de disciplina (hooks/*.sh e hooks/*.py)
# Ordem: shell primeiro (independentes de staged), depois python
echo "Hooks de disciplina:"
HOOK_FAIL=0

if [ -d "hooks" ]; then
    for hook in hooks/*.sh hooks/*.py; do
        [ -f "$hook" ] || continue
        name=$(basename "$hook")

        # sprint_auto_move roda no hook real do git, não aqui
        case "$name" in
            sprint_auto_move.py) continue ;;
            # hooks commit-msg rodam via arg único (arquivo de mensagem)
            remove_coauthor.sh|check_commit_msg.py) continue ;;
            # pre-push roda no stage pre-push, não aqui
            pre_push_protect_main.sh) continue ;;
        esac

        echo -n "  $name ... "
        if [[ "$hook" == *.py ]]; then
            if python "$hook" >/tmp/ouro_hook_out 2>&1; then
                echo "[OK]"
            else
                echo "[FALHA]"
                cat /tmp/ouro_hook_out
                HOOK_FAIL=1
            fi
        else
            if bash "$hook" >/tmp/ouro_hook_out 2>&1; then
                echo "[OK]"
            else
                echo "[FALHA]"
                cat /tmp/ouro_hook_out
                HOOK_FAIL=1
            fi
        fi
    done
fi

if [ "$HOOK_FAIL" -ne 0 ]; then
    echo ""
    echo "[BLOQUEADO] Um ou mais hooks falharam. Veja mensagens acima."
    exit 1
fi

# 6. Freshness do gauntlet (T2 -- apenas avisa)
python scripts/check_gauntlet_freshness.py 2>/dev/null || true

echo "=== Checks concluídos ==="
