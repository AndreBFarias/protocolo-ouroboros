#!/usr/bin/env bash
# inbox_watcher.sh -- dispara ./run.sh --inbox quando arquivos chegam em inbox/.
#
# Acionado por systemd path-unit (infra/systemd/ouroboros-inbox.path).
# Aplica debounce de 60s para evitar disparo em cópia parcial.
# Respeita lockfile (.ouroboros.lock) se outro pipeline está rodando.
# Logs estruturados em logs/inbox_watcher.log.
#
# Filosofia: pipeline que espera ordem humana é pipeline meio-mecanizado.

set -euo pipefail

# Configuração (overridable via env)
PROJETO_RAIZ="${OUROBOROS_RAIZ:-/home/andrefarias/Desenvolvimento/protocolo-ouroboros}"
DEBOUNCE_SEC="${INBOX_WATCHER_DEBOUNCE:-60}"
LOCKFILE_PATH="${OUROBOROS_LOCKFILE:-${PROJETO_RAIZ}/data/.ouroboros.lock}"
LOG_DIR="${PROJETO_RAIZ}/logs"
LOG_FILE="${LOG_DIR}/inbox_watcher.log"
INBOX_DIR="${PROJETO_RAIZ}/inbox"
RUN_SCRIPT="${PROJETO_RAIZ}/run.sh"

# Flags
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --help|-h)
            cat <<'AJUDA'
Uso: inbox_watcher.sh [--dry-run] [--help]

Disparado por systemd path-unit quando inbox/ recebe arquivos.

Variáveis de ambiente:
  OUROBOROS_RAIZ          (default: /home/andrefarias/Desenvolvimento/protocolo-ouroboros)
  INBOX_WATCHER_DEBOUNCE  segundos de espera após última mudança (default: 60)
  OUROBOROS_LOCKFILE      caminho do lockfile concorrência (default: <raiz>/data/.ouroboros.lock)

Flags:
  --dry-run               não executa run.sh, só loga decisão
  --help                  mostra esta ajuda

Saída códigos:
  0 = inbox processada com sucesso ou skip legítimo (lock/vazio)
  1 = falha na execução do pipeline
AJUDA
            exit 0
            ;;
    esac
done

# Garante dir de log
mkdir -p "${LOG_DIR}"

log() {
    local nivel="$1"; shift
    local msg="$*"
    local agora
    agora="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    printf '%s [%s] inbox_watcher: %s\n' "${agora}" "${nivel}" "${msg}" | tee -a "${LOG_FILE}" >&2
}

log "INFO" "watcher_disparado raiz=${PROJETO_RAIZ} debounce=${DEBOUNCE_SEC}s dry_run=${DRY_RUN}"

# Verificação 0: inbox existe?
if [[ ! -d "${INBOX_DIR}" ]]; then
    log "WARN" "inbox_ausente path=${INBOX_DIR} -- nada a processar"
    exit 0
fi

# Debounce: aguarda DEBOUNCE_SEC, depois confere se inbox ainda tem arquivos novos.
# Se durante a espera não chegou nada novo (mtime estável), processa.
contar_arquivos() {
    find "${INBOX_DIR}" -maxdepth 5 -type f -not -name '.gitkeep' -not -name '.gitignore' 2>/dev/null | wc -l
}

snapshot_mtime() {
    find "${INBOX_DIR}" -maxdepth 5 -type f -not -name '.gitkeep' -not -name '.gitignore' -printf '%T@\n' 2>/dev/null \
        | sort -rn | head -1
}

CONTAGEM_INICIAL="$(contar_arquivos)"
MTIME_INICIAL="$(snapshot_mtime)"
log "INFO" "inbox_estado_inicial arquivos=${CONTAGEM_INICIAL} mtime_topo=${MTIME_INICIAL:-vazio}"

if [[ "${CONTAGEM_INICIAL}" -eq 0 ]]; then
    log "INFO" "inbox_vazia -- skip"
    exit 0
fi

# Debounce
log "INFO" "debounce_aguardando segundos=${DEBOUNCE_SEC}"
sleep "${DEBOUNCE_SEC}"

CONTAGEM_FINAL="$(contar_arquivos)"
MTIME_FINAL="$(snapshot_mtime)"

if [[ "${MTIME_INICIAL}" != "${MTIME_FINAL}" ]]; then
    log "INFO" "debounce_arquivos_ainda_chegando mtime_inicial=${MTIME_INICIAL:-vazio} mtime_final=${MTIME_FINAL:-vazio} -- skip ciclo (próximo path-change re-dispara)"
    exit 0
fi

if [[ "${CONTAGEM_FINAL}" -eq 0 ]]; then
    log "INFO" "inbox_esvaziada_durante_debounce -- skip"
    exit 0
fi

# Verificação de lockfile (concorrência com ./run.sh manual)
if [[ -f "${LOCKFILE_PATH}" ]]; then
    LOCK_PID="$(cat "${LOCKFILE_PATH}" 2>/dev/null || echo desconhecido)"
    log "WARN" "lockfile_ativo path=${LOCKFILE_PATH} pid=${LOCK_PID} -- outro pipeline em execução, skip"
    exit 0
fi

# Execução
log "INFO" "inbox_processing_inicio arquivos=${CONTAGEM_FINAL}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "INFO" "dry_run_decidiu_processar -- não executando run.sh"
    exit 0
fi

if [[ ! -x "${RUN_SCRIPT}" ]]; then
    log "ERROR" "run_script_ausente path=${RUN_SCRIPT}"
    exit 1
fi

cd "${PROJETO_RAIZ}"
if "${RUN_SCRIPT}" --inbox >>"${LOG_FILE}" 2>&1; then
    log "INFO" "inbox_processed exit_code=0"
    exit 0
else
    CODIGO=$?
    log "ERROR" "inbox_falha exit_code=${CODIGO}"
    exit 1
fi
