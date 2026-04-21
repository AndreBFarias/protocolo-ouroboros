#!/bin/bash
# finish_sprint.sh -- Encerra uma sprint do Ouroboros.
#
# Uso: ./scripts/finish_sprint.sh NN
#
# 1. Localiza sprint_NN_*.md em docs/sprints/producao/
# 2. Roda validador (scripts/ci/validate_sprint_structure.py)
# 3. Atualiza Status para CONCLUÍDA (se ainda não estiver)
# 4. Move para docs/sprints/concluidos/
# 5. git add do move e prepara commit (não commita automático)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

if [ "${1:-}" = "" ]; then
    echo "Uso: $0 NN (número da sprint)"
    exit 1
fi

NN="$1"
PRODUCAO="docs/sprints/producao"
CONCLUIDOS="docs/sprints/concluidos"
VENV=".venv"

if [ ! -d "$VENV" ]; then
    echo "[erro] Ambiente virtual .venv não encontrado. Rode ./install.sh"
    exit 1
fi

shopt -s nullglob
candidatos=("$PRODUCAO/sprint_${NN}_"*.md)
shopt -u nullglob

if [ ${#candidatos[@]} -eq 0 ]; then
    echo "[erro] Nenhuma sprint_${NN}_*.md em $PRODUCAO"
    exit 1
fi

if [ ${#candidatos[@]} -gt 1 ]; then
    echo "[erro] Ambiguidade: múltiplos arquivos sprint_${NN}_* em $PRODUCAO"
    printf '    %s\n' "${candidatos[@]}"
    exit 1
fi

ARQUIVO="${candidatos[0]}"
NOME_BASE="$(basename "$ARQUIVO")"
DESTINO="$CONCLUIDOS/$NOME_BASE"

echo "[info] Validando estrutura de $NOME_BASE..."
if ! "$VENV/bin/python" scripts/ci/validate_sprint_structure.py "$ARQUIVO"; then
    echo "[erro] Validação falhou. Corrija antes de encerrar a sprint."
    exit 1
fi

echo "[info] Atualizando Status para CONCLUÍDA..."
if grep -q "^\*\*Status:\*\*\s*CONCLUÍDA" "$ARQUIVO"; then
    echo "      (já estava CONCLUÍDA)"
else
    sed -i -E 's/^\*\*Status:\*\*.*$/**Status:** CONCLUÍDA/' "$ARQUIVO"
fi

echo "[info] Movendo para $CONCLUIDOS/..."
mkdir -p "$CONCLUIDOS"
git mv "$ARQUIVO" "$DESTINO"

echo "[info] Rodando smoke aritmético (contratos globais do XLSX)..."
if ! "$VENV/bin/python" scripts/smoke_aritmetico.py --strict; then
    echo "[erro] REPROVADO: smoke aritmético falhou. Revise antes de declarar sprint concluída."
    exit 1
fi

echo "[info] Sprint ${NN} encerrada em $DESTINO"
echo "      Próximo passo: revisar diff e criar commit descritivo (S${NN})."
