#!/usr/bin/env bash
# Snapshot do estado atual do projeto para ser consumido no início de uma
# sessão interativa do Claude Code (ADR-13). Imprime stdout estruturado em
# markdown -- legível por humano e por LLM sem adaptação.
#
# Uso: ./run.sh --supervisor   OU   bash scripts/supervisor_contexto.sh

set -euo pipefail
cd "$(dirname "$0")/.."

echo "# Estado do Projeto ($(date -I))"
echo

# ----------------------------------------------------------------------------
echo "## XLSX"
if [ -f data/output/ouroboros_2026.xlsx ] && command -v python3 >/dev/null; then
    python3 - <<'PY' 2>/dev/null || echo "(falha ao ler XLSX)"
from pathlib import Path
import pandas as pd
arq = Path("data/output/ouroboros_2026.xlsx")
df = pd.read_excel(arq, sheet_name="extrato")
print(f"- Transações: {len(df):,}")
print(f"- Meses cobertos: {df['mes_ref'].nunique()}")
print(f"- Bancos: {df['banco_origem'].nunique()}")
print(f"- Categorias distintas: {df['categoria'].nunique()}")
PY
else
    echo "(XLSX ausente em data/output/ouroboros_2026.xlsx)"
fi
echo

# ----------------------------------------------------------------------------
echo "## Grafo"
if [ -f data/output/grafo.sqlite ] && command -v sqlite3 >/dev/null; then
    echo '```'
    sqlite3 data/output/grafo.sqlite \
        "SELECT tipo, COUNT(*) AS n FROM node GROUP BY tipo ORDER BY n DESC;" \
        | column -t -s '|'
    echo '```'
    echo
    echo "Total de arestas:"
    echo '```'
    sqlite3 data/output/grafo.sqlite \
        "SELECT tipo, COUNT(*) AS n FROM edge GROUP BY tipo ORDER BY n DESC;" \
        | column -t -s '|'
    echo '```'
else
    echo "(grafo.sqlite ausente ou sqlite3 indisponível)"
fi
echo

# ----------------------------------------------------------------------------
echo "## Propostas Pendentes"
pendentes=$(find docs/propostas -maxdepth 2 -type f -name "*.md" \
    ! -path "*_aprovadas*" ! -path "*_rejeitadas*" \
    ! -name "README.md" ! -name "sprint_*.md" 2>/dev/null | sort)
if [ -z "$pendentes" ]; then
    echo "(nenhuma proposta aberta)"
else
    echo "$pendentes" | while read -r f; do
        slug=$(basename "$f" .md)
        tipo=$(awk -F': ' '/^tipo:/ {print $2; exit}' "$f" 2>/dev/null)
        echo "- [$tipo] $slug -- $f"
    done
fi
echo

# ----------------------------------------------------------------------------
echo "## Últimas Armadilhas"
if [ -f docs/ARMADILHAS.md ]; then
    grep -E "^## [0-9]+\." docs/ARMADILHAS.md | tail -5 | sed 's/^## /- /'
else
    echo "(ARMADILHAS.md ausente)"
fi
echo

# ----------------------------------------------------------------------------
echo "## Últimos Commits"
echo '```'
git log --oneline -10 2>/dev/null || echo "(git indisponível)"
echo '```'
echo

# ----------------------------------------------------------------------------
echo "## Sprints em Andamento"
em_andamento=$(grep -l "^\*\*Status:\*\* EM ANDAMENTO" docs/sprints/producao/*.md 2>/dev/null || true)
if [ -z "$em_andamento" ]; then
    echo "(nenhuma)"
else
    for f in $em_andamento; do
        titulo=$(awk -F': ' '/^# Sprint/ {sub(/^# /, "", $0); print; exit}' "$f")
        echo "- $titulo ($f)"
    done
fi
echo

# ----------------------------------------------------------------------------
echo "## Arquivos em data/raw/_classificar/ (pendentes de humano)"
if [ -d data/raw/_classificar ]; then
    count=$(find data/raw/_classificar -maxdepth 1 -type f 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
        echo "- $count arquivo(s) sem classificação:"
        find data/raw/_classificar -maxdepth 1 -type f 2>/dev/null \
            | head -10 | sed 's|^|  - |'
    else
        echo "(nenhum)"
    fi
else
    echo "(pasta _classificar/ ausente -- nenhum run de intake ainda)"
fi
echo

# ----------------------------------------------------------------------------
echo "## Diário de Melhorias (últimas 3 entradas)"
if [ -f docs/DIARIO_MELHORIAS.md ]; then
    # Extrai headers ### (nível 3) = entradas de sprint/proposta
    grep -E "^### " docs/DIARIO_MELHORIAS.md | head -3 | sed 's/^### /- /'
else
    echo "(DIARIO_MELHORIAS.md ausente)"
fi

# "O estado é a memória da próxima decisão." -- princípio do supervisor
