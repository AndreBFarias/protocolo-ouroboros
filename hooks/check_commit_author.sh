#!/usr/bin/env bash
# [T1] Valida que author/committer do git config não é IA.
# Roda como pre-commit -- bloqueia ANTES do commit acontecer.
# Garante anonimato absoluto (CLAUDE.md secao 2).

set -euo pipefail

AUTHOR_NAME=$(git config --get user.name 2>/dev/null || echo "")
AUTHOR_EMAIL=$(git config --get user.email 2>/dev/null || echo "")

AI_NAMES="claude|anthropic|openai|chatgpt|copilot|gemini|cursor|windsurf|codeium|tabnine|aider|deepseek"
AI_EMAILS="noreply@anthropic|noreply@openai|github-actions"

BLOCKED=0

if echo "$AUTHOR_NAME" | grep -qiE "$AI_NAMES" 2>/dev/null; then
    echo ""
    echo "============================================================"
    echo "  [T1] Author do git config e IA: '$AUTHOR_NAME'"
    echo "============================================================"
    echo "  Corrija: git config user.name 'SeuNome'"
    echo "============================================================"
    BLOCKED=1
fi

if echo "$AUTHOR_EMAIL" | grep -qiE "$AI_EMAILS" 2>/dev/null; then
    echo ""
    echo "============================================================"
    echo "  [T1] Email do git config e de IA: '$AUTHOR_EMAIL'"
    echo "============================================================"
    echo "  Corrija: git config user.email 'seu@email.com'"
    echo "============================================================"
    BLOCKED=1
fi

if [ $BLOCKED -gt 0 ]; then
    exit 1
fi

exit 0

# "A identidade e o primeiro direito." -- pragmatico
