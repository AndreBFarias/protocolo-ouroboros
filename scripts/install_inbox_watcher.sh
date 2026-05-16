#!/usr/bin/env bash
# install_inbox_watcher.sh -- instala unit files systemd do watcher de inbox.
#
# Copia infra/systemd/ouroboros-inbox.{service,path} para ~/.config/systemd/user/,
# faz daemon-reload, habilita e inicia a path-unit.
#
# Idempotente: re-executar atualiza units sem duplicar.
#
# Flags:
#   --dry-run    não copia nem ativa nada, só mostra plano
#   --uninstall  remove instalação
#   --help

set -euo pipefail

PROJETO_RAIZ="${OUROBOROS_RAIZ:-/home/andrefarias/Desenvolvimento/protocolo-ouroboros}"
ORIGEM_DIR="${PROJETO_RAIZ}/infra/systemd"
DESTINO_DIR="${HOME}/.config/systemd/user"

DRY_RUN=0
UNINSTALL=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --uninstall) UNINSTALL=1 ;;
        --help|-h)
            cat <<'AJUDA'
Uso: install_inbox_watcher.sh [--dry-run] [--uninstall] [--help]

Instala o watcher systemd que dispara ./run.sh --inbox quando arquivos
são detectados em inbox/.

Flags:
  --dry-run    mostra o plano sem aplicar
  --uninstall  desativa e remove as units
  --help       esta mensagem

Saída códigos:
  0 = sucesso
  1 = falha (arquivo ausente, daemon-reload erro, etc.)
AJUDA
            exit 0
            ;;
    esac
done

log() {
    printf '[install_inbox_watcher] %s\n' "$*"
}

executar() {
    # Wrapper que respeita --dry-run.
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        log "DRY-RUN: $*"
    else
        log "RUN: $*"
        eval "$@"
    fi
}

# Verificação básica
if [[ ! -d "${ORIGEM_DIR}" ]]; then
    log "ERRO: ${ORIGEM_DIR} não existe (rode a partir do worktree do projeto?)"
    exit 1
fi

UNITS=(ouroboros-inbox.service ouroboros-inbox.path)

if [[ "${UNINSTALL}" -eq 1 ]]; then
    log "modo uninstall"
    executar "systemctl --user disable --now ouroboros-inbox.path || true"
    executar "systemctl --user disable --now ouroboros-inbox.service || true"
    for unit in "${UNITS[@]}"; do
        if [[ -f "${DESTINO_DIR}/${unit}" ]]; then
            executar "rm -f '${DESTINO_DIR}/${unit}'"
        fi
    done
    executar "systemctl --user daemon-reload"
    log "uninstall concluído"
    exit 0
fi

# Instalação
log "modo install (dry_run=${DRY_RUN})"

executar "mkdir -p '${DESTINO_DIR}'"

for unit in "${UNITS[@]}"; do
    src="${ORIGEM_DIR}/${unit}"
    dst="${DESTINO_DIR}/${unit}"
    if [[ ! -f "${src}" ]]; then
        log "ERRO: unit ausente em ${src}"
        exit 1
    fi
    executar "cp '${src}' '${dst}'"
done

executar "systemctl --user daemon-reload"

# Garante que script do watcher está executável
WATCHER_SCRIPT="${PROJETO_RAIZ}/scripts/inbox_watcher.sh"
if [[ -f "${WATCHER_SCRIPT}" ]]; then
    executar "chmod +x '${WATCHER_SCRIPT}'"
else
    log "AVISO: ${WATCHER_SCRIPT} não encontrado (pulando chmod)"
fi

executar "systemctl --user enable --now ouroboros-inbox.path"

if [[ "${DRY_RUN}" -eq 0 ]]; then
    log "status da path-unit:"
    systemctl --user status ouroboros-inbox.path --no-pager --lines=10 || true
fi

log "instalação concluída"
log "fallback cron documentado em docs/MANUAL_INBOX_WATCHER.md"
