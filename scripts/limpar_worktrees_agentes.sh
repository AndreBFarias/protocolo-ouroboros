#!/usr/bin/env bash
# limpar_worktrees_agentes.sh
#
# Garbage collection de worktrees em `.claude/worktrees/agent-*` + branches
# `worktree-agent-*` ja mergeadas em main.
#
# Dry-run por padrao. Use `--apply` para executar de fato.
# Backup do reflog salvo em /tmp/reflog_pre_gc_<ts>.txt antes de qualquer delecao.
#
# Comandos canonicos:
#   git worktree remove --force <path>   (não usar rm -rf)
#   git branch -D <branch>               (delecao explicita)
#
# Auto-proteção: rejeita se o worktree atual aparece na lista de candidatos.
#
# Padroes aplicaveis: (m) Branch reversivel; (ii) Comandos git banidos.
#
# Uso:
#   ./scripts/limpar_worktrees_agentes.sh                # dry-run
#   ./scripts/limpar_worktrees_agentes.sh --apply        # executa MERGED
#   ./scripts/limpar_worktrees_agentes.sh --include-no-merge --apply
#                                                       # inclui NO-MERGE (perigoso)

set -euo pipefail

APPLY=0
INCLUDE_NO_MERGE=0
declare -a PROTECT_LIST=()

for arg in "$@"; do
    case "$arg" in
        --apply)
            APPLY=1
            ;;
        --include-no-merge)
            INCLUDE_NO_MERGE=1
            ;;
        --protect=*)
            PROTECT_LIST+=("${arg#--protect=}")
            ;;
        --help|-h)
            cat <<'HELP'
Uso: limpar_worktrees_agentes.sh [--apply] [--include-no-merge] [--protect=<path>]

  (sem flag)            Dry-run. Lista worktrees agent-* + status MERGED/NO-MERGE.
  --apply               Deleta worktrees MERGED + branches MERGED. Backup reflog antes.
  --include-no-merge    Em combinação com --apply: também deleta NO-MERGE
                        (PERIGOSO -- pode perder trabalho. Use com cautela).
  --protect=<path>      Protege explicitamente o worktree em <path>, mesmo que
                        esteja MERGED. Pode ser usada multiplas vezes.

Auto-proteção: o worktree atual (se for agent-) nunca é deletado.
HELP
            exit 0
            ;;
        *)
            echo "Argumento desconhecido: $arg" >&2
            echo "Use --help para ver opcoes." >&2
            exit 2
            ;;
    esac
done

# Normaliza paths da PROTECT_LIST.
declare -a PROTECT_NORM=()
for p in "${PROTECT_LIST[@]}"; do
    if [[ -d "$p" ]]; then
        PROTECT_NORM+=("$(cd "$p" && pwd)")
    else
        PROTECT_NORM+=("$p")
    fi
done

# Detecta raiz do repo e worktree atual.
CURRENT_WT="$(git rev-parse --show-toplevel)"

# Resolve o repo main (common-dir) -- script pode ser invocado de qualquer worktree.
COMMON_DIR="$(cd "$CURRENT_WT" && git rev-parse --git-common-dir)"
# Garante caminho absoluto.
COMMON_DIR="$(cd "$COMMON_DIR" && pwd)"
MAIN_ROOT="$(dirname "$COMMON_DIR")"
if [[ ! -d "$MAIN_ROOT/.git" ]] && [[ ! -f "$MAIN_ROOT/.git" ]]; then
    echo "ERRO: não foi possivel resolver o repo main a partir de $CURRENT_WT" >&2
    exit 1
fi

# Sanity: se o worktree atual eh um worktree-agent, refuse --apply
# (sessao de executor pode estar viva; risco de auto-delecao).
IS_AGENT_WT=0
if [[ "$CURRENT_WT" == */.claude/worktrees/agent-* ]]; then
    IS_AGENT_WT=1
fi

echo "==> limpar_worktrees_agentes.sh"
echo "    Repo main: $MAIN_ROOT"
echo "    Worktree atual (protegido): $CURRENT_WT"
if [[ $IS_AGENT_WT -eq 1 ]]; then
    echo "    Aviso: rodando de dentro de um worktree-agent. --apply sera recusado."
fi
echo "    Modo: $( [[ $APPLY -eq 1 ]] && echo 'APPLY' || echo 'DRY-RUN' )"
if [[ $INCLUDE_NO_MERGE -eq 1 ]]; then
    echo "    Incluindo NO-MERGE (perigoso)"
fi
echo

# Recusa --apply quando rodando de dentro de worktree-agent.
if [[ $APPLY -eq 1 ]] && [[ $IS_AGENT_WT -eq 1 ]]; then
    echo "ERRO: --apply não permitido a partir de worktree-agent ($CURRENT_WT)." >&2
    echo "       Saia do worktree-agent e rode a partir do repo main:" >&2
    echo "       cd $MAIN_ROOT && ./scripts/limpar_worktrees_agentes.sh --apply" >&2
    exit 1
fi

# Confirma que branch main existe.
if ! git -C "$MAIN_ROOT" rev-parse --verify main >/dev/null 2>&1; then
    echo "ERRO: branch 'main' não encontrada em $MAIN_ROOT" >&2
    exit 1
fi

# Coleta lista de worktrees em formato porcelain.
declare -a WT_PATHS=()
declare -a WT_BRANCHES=()
declare -a WT_HEADS=()

current_path=""
current_branch=""
current_head=""

while IFS= read -r line; do
    if [[ "$line" =~ ^worktree[[:space:]]+(.+)$ ]]; then
        current_path="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^HEAD[[:space:]]+([0-9a-f]+)$ ]]; then
        current_head="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^branch[[:space:]]+refs/heads/(.+)$ ]]; then
        current_branch="${BASH_REMATCH[1]}"
    elif [[ -z "$line" ]]; then
        if [[ -n "$current_path" ]]; then
            WT_PATHS+=("$current_path")
            WT_BRANCHES+=("$current_branch")
            WT_HEADS+=("$current_head")
        fi
        current_path=""
        current_branch=""
        current_head=""
    fi
done < <(git -C "$MAIN_ROOT" worktree list --porcelain; echo "")

# Filtra apenas worktrees em `.claude/worktrees/agent-*`.
declare -a MERGED_PATHS=()
declare -a MERGED_BRANCHES=()
declare -a NOMERGE_PATHS=()
declare -a NOMERGE_BRANCHES=()
declare -a SKIPPED_CURRENT=()

is_protected() {
    local candidate="$1"
    if [[ "$candidate" == "$CURRENT_WT" ]]; then
        return 0
    fi
    for p in "${PROTECT_NORM[@]}"; do
        if [[ "$candidate" == "$p" ]]; then
            return 0
        fi
    done
    return 1
}

for i in "${!WT_PATHS[@]}"; do
    path="${WT_PATHS[$i]}"
    branch="${WT_BRANCHES[$i]}"

    # So agent-*
    if [[ "$path" != */.claude/worktrees/agent-* ]]; then
        continue
    fi

    # AUTO-proteção: nunca processa o worktree atual ou paths em --protect.
    if is_protected "$path"; then
        SKIPPED_CURRENT+=("$path|$branch")
        continue
    fi

    # Sem branch -> ignora (detached HEAD raro em agent-).
    if [[ -z "$branch" ]]; then
        continue
    fi

    # Checa se branch esta merged em main.
    if git -C "$MAIN_ROOT" merge-base --is-ancestor "refs/heads/$branch" main 2>/dev/null; then
        MERGED_PATHS+=("$path")
        MERGED_BRANCHES+=("$branch")
    else
        NOMERGE_PATHS+=("$path")
        NOMERGE_BRANCHES+=("$branch")
    fi
done

# Output da listagem.
echo "=== MERGED (seguro deletar) ==="
if [[ ${#MERGED_PATHS[@]} -eq 0 ]]; then
    echo "  (nenhum)"
else
    for i in "${!MERGED_PATHS[@]}"; do
        printf "  [MERGED]   %-70s branch %s -> DELETAR\n" "${MERGED_PATHS[$i]}" "${MERGED_BRANCHES[$i]}"
    done
fi

echo
echo "=== NO-MERGE (revisar antes de deletar) ==="
if [[ ${#NOMERGE_PATHS[@]} -eq 0 ]]; then
    echo "  (nenhum)"
else
    for i in "${!NOMERGE_PATHS[@]}"; do
        printf "  [NO-MERGE] %-70s branch %s -> REVISAR\n" "${NOMERGE_PATHS[$i]}" "${NOMERGE_BRANCHES[$i]}"
    done
fi

if [[ ${#SKIPPED_CURRENT[@]} -gt 0 ]]; then
    echo
    echo "=== AUTO-PROTEGIDO (worktree atual, nunca deletado) ==="
    for entry in "${SKIPPED_CURRENT[@]}"; do
        path="${entry%%|*}"
        branch="${entry##*|}"
        printf "  [SELF]     %-70s branch %s -> PRESERVADO\n" "$path" "$branch"
    done
fi

echo
echo "Resumo: ${#MERGED_PATHS[@]} a deletar, ${#NOMERGE_PATHS[@]} a revisar, ${#SKIPPED_CURRENT[@]} auto-protegido(s)."

# Dry-run termina aqui.
if [[ $APPLY -eq 0 ]]; then
    echo
    echo "Dry-run completo. Use --apply para executar."
    exit 0
fi

# === aplicação ===
echo
echo "==> APLICANDO deleções"

# Lista de paths/branches a deletar.
declare -a TODO_PATHS=()
declare -a TODO_BRANCHES=()

for i in "${!MERGED_PATHS[@]}"; do
    TODO_PATHS+=("${MERGED_PATHS[$i]}")
    TODO_BRANCHES+=("${MERGED_BRANCHES[$i]}")
done

if [[ $INCLUDE_NO_MERGE -eq 1 ]]; then
    for i in "${!NOMERGE_PATHS[@]}"; do
        TODO_PATHS+=("${NOMERGE_PATHS[$i]}")
        TODO_BRANCHES+=("${NOMERGE_BRANCHES[$i]}")
    done
fi

if [[ ${#TODO_PATHS[@]} -eq 0 ]]; then
    echo "Nada a deletar."
    exit 0
fi

# Auto-proteção final (defesa em camadas, padrao (n)).
for path in "${TODO_PATHS[@]}"; do
    if is_protected "$path"; then
        echo "ERRO: tentativa de deletar worktree protegido ($path). Abortado." >&2
        exit 1
    fi
done

# Backup do reflog antes de qualquer delecao.
ts="$(date +%Y%m%d_%H%M%S)"
backup_path="/tmp/reflog_pre_gc_${ts}.txt"
echo "==> Backup do reflog em $backup_path"
git -C "$MAIN_ROOT" reflog --all > "$backup_path"
echo "    OK ($(wc -l < "$backup_path") linhas)"

# Deleta.
echo
DELETED_OK=0
DELETED_FAIL=0
for i in "${!TODO_PATHS[@]}"; do
    path="${TODO_PATHS[$i]}"
    branch="${TODO_BRANCHES[$i]}"

    echo "  - $path (branch $branch)"
    if git -C "$MAIN_ROOT" worktree remove --force "$path" 2>&1 | sed 's/^/      /'; then
        if git -C "$MAIN_ROOT" branch -D "$branch" 2>&1 | sed 's/^/      /'; then
            DELETED_OK=$((DELETED_OK + 1))
        else
            DELETED_FAIL=$((DELETED_FAIL + 1))
        fi
    else
        DELETED_FAIL=$((DELETED_FAIL + 1))
    fi
done

echo
echo "==> Concluído: $DELETED_OK deletados com sucesso, $DELETED_FAIL falhas."
echo "    Backup do reflog: $backup_path"
echo "    Para recuperar trabalho deletado: ver docs/MANUAL_WORKTREES.md"
