#!/bin/bash
# finish_sprint.sh -- Encerra uma sprint do Ouroboros.
#
# Uso:
#   ./scripts/finish_sprint.sh NN              -> encerra sprint NN (numérica ou ID textual)
#   ./scripts/finish_sprint.sh ID-TEXTUAL      -> encerra sprint com ID textual
#   ./scripts/finish_sprint.sh --gate-only     -> só roda gate (4 checks), sem mover spec
#
# Modo encerramento:
#   1. Localiza sprint_<ID>_*.md em docs/sprints/backlog/ (ou producao/, fallback)
#   2. Valida estrutura (scripts/ci/validate_sprint_structure.py) -- soft
#   3. Roda gate canônico (checks 4,5,6 do VALIDATOR_BRIEF)
#   4. Atualiza Status e concluida_em (check 9)
#   5. Move para docs/sprints/concluidos/
#   6. git add do move; commit fica para o operador
#
# Modo gate-only:
#   1. Roda apenas checks 4 (lint), 5 (smoke), 6 (pytest baseline)
#   2. Exit 0 se tudo verde; exit 1 com diagnóstico se algo falha

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

VENV=".venv"
BASELINE_FILE=".ouroboros/pytest_baseline.txt"
PYTEST_LOG="$(mktemp -t finish_sprint_pytest.XXXXXX.log)"
trap 'rm -f "$PYTEST_LOG"' EXIT

# --------------------------------------------------------------------------
# Função: gate canônico (checks 4, 5, 6 do VALIDATOR_BRIEF Fase DEPOIS)
# --------------------------------------------------------------------------
run_gate() {
    if [ ! -d "$VENV" ]; then
        echo "[erro] Ambiente virtual .venv não encontrado. Rode ./install.sh"
        return 1
    fi

    echo "=== Gate canônico (checks 4, 5, 6 do VALIDATOR_BRIEF) ==="

    echo "[4/9] make lint..."
    if ! make lint; then
        echo "[FALHA] make lint falhou. Veja saída acima."
        return 1
    fi

    echo "[5/9] make smoke..."
    if ! make smoke; then
        echo "[FALHA] make smoke falhou. Veja saída acima."
        return 1
    fi

    echo "[6/9] pytest baseline..."
    mkdir -p "$(dirname "$BASELINE_FILE")"
    # Captura saída; não bloqueia em exit code não-zero (pytest pode falhar mesmo
    # com baseline mantida -- o que importa é a contagem de passed).
    "$VENV/bin/pytest" tests/ -q --tb=no > "$PYTEST_LOG" 2>&1 || true
    N=$(grep -aoE "[0-9]+ passed" "$PYTEST_LOG" | head -1 | grep -aoE "[0-9]+" || echo "0")
    if [ -z "$N" ] || [ "$N" = "0" ]; then
        echo "[FALHA] não conseguiu extrair contagem de pytest passed."
        tail -10 "$PYTEST_LOG"
        return 1
    fi
    if [ -f "$BASELINE_FILE" ]; then
        OLD=$(cat "$BASELINE_FILE")
        if [ "$N" -lt "$OLD" ]; then
            echo "[FALHA] pytest regrediu: baseline $OLD -> atual $N"
            return 1
        fi
        echo "      baseline $OLD -> atual $N (mantida ou crescida)"
    else
        echo "      criando baseline inicial: $N"
    fi
    echo "$N" > "$BASELINE_FILE"

    echo "=== Gate OK (checks 4, 5, 6 verdes; pytest=$N) ==="
    return 0
}

# --------------------------------------------------------------------------
# Função: atualiza frontmatter YAML (status + concluida_em) ou fallback markdown
# --------------------------------------------------------------------------
atualizar_status_e_concluida_em() {
    local arquivo="$1"
    local data_hoje
    data_hoje="$(date +%Y-%m-%d)"

    # YAML frontmatter -- preferido (specs novas)
    if head -1 "$arquivo" | grep -q "^---$"; then
        # status: backlog | em-andamento -> concluída
        sed -i -E 's/^(status:\s*)(backlog|em-andamento|em_andamento|in-progress).*$/\1concluída/' "$arquivo"
        # concluida_em: null -> data hoje
        sed -i -E "s/^(concluida_em:\s*)(null|~|''|\"\")\s*\$/\1${data_hoje}/" "$arquivo"
        # Se concluida_em ausente, adicionar logo após status:
        if ! grep -qE "^concluida_em:" "$arquivo"; then
            sed -i -E "/^status:/a concluida_em: ${data_hoje}" "$arquivo"
        fi
    fi

    # Fallback markdown -- specs antigas com **Status:**
    if grep -qE "^\*\*Status:\*\*" "$arquivo"; then
        if grep -q "^\*\*Status:\*\*\s*CONCLUÍDA" "$arquivo"; then
            echo "      (Status markdown já estava CONCLUÍDA)"
        else
            sed -i -E 's/^\*\*Status:\*\*.*$/**Status:** CONCLUÍDA/' "$arquivo"
        fi
    fi
}

# --------------------------------------------------------------------------
# Função: localiza arquivo da sprint dado ID (numérico ou textual)
# --------------------------------------------------------------------------
localizar_spec() {
    local id="$1"
    local resultado=""

    # 1. backlog/sprint_<ID>_*.md
    shopt -s nullglob
    local candidatos=("docs/sprints/backlog/sprint_${id}_"*.md)
    shopt -u nullglob

    # 2. backlog/sprint_<ID>.md (sem sufixo)
    if [ ${#candidatos[@]} -eq 0 ]; then
        shopt -s nullglob
        candidatos=("docs/sprints/backlog/sprint_${id}.md")
        shopt -u nullglob
    fi

    # 3. producao/sprint_<ID>_*.md (compat com fluxo antigo, se existir)
    if [ ${#candidatos[@]} -eq 0 ] && [ -d "docs/sprints/producao" ]; then
        shopt -s nullglob
        candidatos=("docs/sprints/producao/sprint_${id}_"*.md)
        shopt -u nullglob
    fi

    if [ ${#candidatos[@]} -eq 0 ]; then
        echo "[erro] Nenhuma sprint_${id}*.md em docs/sprints/backlog/ (ou producao/)" >&2
        return 1
    fi
    if [ ${#candidatos[@]} -gt 1 ]; then
        echo "[erro] Ambiguidade: múltiplos arquivos sprint_${id}* encontrados:" >&2
        printf '    %s\n' "${candidatos[@]}" >&2
        return 1
    fi
    printf '%s\n' "${candidatos[0]}"
    return 0
}

# --------------------------------------------------------------------------
# Parser de argumentos
# --------------------------------------------------------------------------
if [ "${1:-}" = "" ]; then
    echo "Uso: $0 NN                  (encerra sprint NN/ID, move + atualiza frontmatter)"
    echo "     $0 --gate-only         (só roda gate, sem mover spec)"
    exit 1
fi

if [ "$1" = "--gate-only" ]; then
    run_gate
    exit $?
fi

# Modo encerramento de sprint
SPRINT_ID="$1"
CONCLUIDOS="docs/sprints/concluidos"

if [ ! -d "$VENV" ]; then
    echo "[erro] Ambiente virtual .venv não encontrado. Rode ./install.sh"
    exit 1
fi

ARQUIVO="$(localizar_spec "$SPRINT_ID")"
NOME_BASE="$(basename "$ARQUIVO")"
DESTINO="$CONCLUIDOS/$NOME_BASE"

echo "[info] Validando estrutura de $NOME_BASE..."
if ! "$VENV/bin/python" scripts/ci/validate_sprint_structure.py "$ARQUIVO"; then
    echo "[aviso] Validação de estrutura reportou falhas. Não bloqueia o encerramento (soft check)."
fi

echo "[info] Rodando gate canônico ANTES de mover spec..."
if ! run_gate; then
    echo "[erro] REPROVADO: gate canônico falhou. Sprint NÃO encerrada."
    exit 1
fi

echo "[info] Atualizando frontmatter (status + concluida_em)..."
atualizar_status_e_concluida_em "$ARQUIVO"

echo "[info] Movendo para $CONCLUIDOS/..."
mkdir -p "$CONCLUIDOS"
git mv "$ARQUIVO" "$DESTINO"

echo "[info] Sprint ${SPRINT_ID} encerrada em $DESTINO"
echo "      Próximo passo: revisar diff e criar commit descritivo."
