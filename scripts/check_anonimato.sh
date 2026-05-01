#!/usr/bin/env bash
# check_anonimato.sh -- Regra -1 no backend Python (Sprint MOB-bridge-1)
#
# Trava commits que reintroduzem nome real ou referencia a IA em
# src/, tests/ ou scripts/.
#
# Aceita marker `# anonimato-allow: <razao>` na mesma linha do token
# para exemplos legitimos em docstring, fixtures de matcher ou
# comentarios narrativos.
#
# Saidas:
#   exit 0  -- anonimato preservado
#   exit 1  -- violacao detectada (lista as linhas)

set -euo pipefail

cd "$(dirname "$0")/.."

PROIBIDO_IA='claude|anthropic|openai|gpt-[0-9]|chatgpt|by ai|ai-generated'
NOMES_REAIS='Andr[eé]|Vit[oó]ria'

# Exclusoes legitimas conhecidas (ADR-13 cita Claude Code como
# ferramenta de supervisao; CLAUDE.md e nome canonico do arquivo de
# regras em todo o codebase). O check trava apenas referencias novas
# em código executável ou docstring que não seja explanação de ADR.
violacoes_ia=$(
  grep -rniE "$PROIBIDO_IA" src/ tests/ scripts/ \
    --include='*.py' --include='*.sh' 2>/dev/null \
    | grep -viE 'api_key|provider|model|config|client|engine' \
    | grep -v 'anonimato-allow' \
    | grep -viE 'CLAUDE\.md|claude code|claude-code|adr-13|adr 13' \
    | grep -viE 'anthropic api|sem anthropic|nenhuma chamada anthropic|sem chamada' \
    | grep -viE '_materializar_backlog|check_anonimato\.sh' \
    | grep -viE '\.claude/|\.claude"|~/\.claude' \
    || true
)
if [[ -n "$violacoes_ia" ]]; then
  echo "ERRO: anonimato (IA) violado em src/, tests/ ou scripts/:"
  echo "$violacoes_ia"
  exit 1
fi

violacoes_nomes=$(
  grep -rEn "$NOMES_REAIS" src/ tests/ \
    --include='*.py' 2>/dev/null \
    | grep -v 'mappings/pessoas.yaml' \
    | grep -v 'cpfs_pessoas.yaml.example' \
    | grep -v 'anonimato-allow' \
    || true
)
if [[ -n "$violacoes_nomes" ]]; then
  echo "ERRO: nome real hardcoded fora de mappings/ ou marker anonimato-allow:"
  echo "$violacoes_nomes"
  exit 1
fi

echo "OK: anonimato preservado (Regra -1)"
