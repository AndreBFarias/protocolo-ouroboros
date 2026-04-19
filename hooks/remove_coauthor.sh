#!/usr/bin/env bash
# Remove evidencias de IA de mensagens de commit:
# - Co-Authored-By com nomes de IA
# - Generated with [Claude Code]
# - Mencoes diretas a nomes de IA no titulo/corpo
# Uso: hook commit-msg, recebe caminho do arquivo como argumento.

set -euo pipefail

COMMIT_MSG_FILE="${1:-}"

if [ -z "$COMMIT_MSG_FILE" ] || [ ! -f "$COMMIT_MSG_FILE" ]; then
    echo "[AVISO] Arquivo de commit não encontrado: $COMMIT_MSG_FILE" >&2
    exit 0
fi

# 1. Remove linhas Co-Authored-By com nomes de IA
grep -vi '^Co-Authored-By:.*Claude\|^Co-Authored-By:.*anthropic\|^Co-Authored-By:.*GPT\|^Co-Authored-By:.*OpenAI\|^Co-Authored-By:.*Gemini\|^Co-Authored-By:.*Copilot' "$COMMIT_MSG_FILE" > "$COMMIT_MSG_FILE.tmp" || true
mv "$COMMIT_MSG_FILE.tmp" "$COMMIT_MSG_FILE"

# 2. Remove linhas "Generated with [Claude Code]" e similares
grep -vi 'Generated with \[Claude\|Generated with \[GPT\|Generated with \[Copilot\|Generated with \[Gemini' "$COMMIT_MSG_FILE" > "$COMMIT_MSG_FILE.tmp" || true
mv "$COMMIT_MSG_FILE.tmp" "$COMMIT_MSG_FILE"

# 3. Verificar se título/corpo menciona nomes de IA (bloquear, não auto-corrigir)
AI_PATTERNS="Claude|Anthropic|ChatGPT|GPT-4|OpenAI|Gemini|Copilot|Claude Code|claude-opus|claude-sonnet"

if grep -qiE "$AI_PATTERNS" "$COMMIT_MSG_FILE" 2>/dev/null; then
    MATCHES=$(grep -niE "$AI_PATTERNS" "$COMMIT_MSG_FILE" 2>/dev/null | head -5)
    echo ""
    echo "============================================================"
    echo "  [T1] Mensagem de commit menciona IA"
    echo "============================================================"
    echo ""
    echo "  Mencoes encontradas:"
    echo "$MATCHES" | sed 's/^/    /'
    echo ""
    echo "  Commits devem ser anonimos (CLAUDE.md secao 2)."
    echo "  Remova mencoes a nomes de IA da mensagem."
    echo ""
    echo "============================================================"
    exit 1
fi

exit 0

# "O silencio e ouro, a palavra e prata." -- proverbio
