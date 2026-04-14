#!/bin/bash
set -euo pipefail

VENV=".venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "$VENV" ]; then
    echo "Ambiente virtual não encontrado. Rode ./install.sh primeiro."
    exit 1
fi

source "$VENV/bin/activate"

# Backup automático antes de processar
if [ -f data/output/controle_bordo_*.xlsx ] 2>/dev/null; then
    BACKUP_DIR="data/output/backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    cp data/output/controle_bordo_*.xlsx "$BACKUP_DIR/" 2>/dev/null || true
fi

case "${1:-}" in
    --inbox)
        echo "=== Controle de Bordo -- Processando Inbox ==="
        python -m src.inbox_processor
        ;;
    --mes)
        MES="${2:?Informe o mês no formato YYYY-MM}"
        echo "=== Controle de Bordo -- Processando $MES ==="
        python -m src.pipeline --mes "$MES"
        ;;
    --tudo)
        echo "=== Controle de Bordo -- Processando todos os dados ==="
        python -m src.pipeline --tudo
        ;;
    --dashboard)
        echo "=== Controle de Bordo -- Dashboard ==="
        streamlit run src/dashboard/app.py
        ;;
    --check)
        echo "=== Controle de Bordo -- Health Check ==="
        python -m src.utils.health_check
        ;;
    --irpf)
        ANO="${2:?Informe o ano}"
        echo "=== Controle de Bordo -- IRPF $ANO ==="
        python -m src.irpf --ano "$ANO"
        ;;
    --sync)
        echo "=== Controle de Bordo -- Sincronizando com Obsidian ==="
        python -m src.obsidian.sync
        ;;
    *)
        echo "Uso: ./run.sh [opção]"
        echo ""
        echo "Opções:"
        echo "  --inbox           Processa arquivos do inbox/ (detecta, renomeia, move)"
        echo "  --mes YYYY-MM     Processa um mês específico"
        echo "  --tudo            Processa todos os dados disponíveis"
        echo "  --dashboard       Abre o dashboard Streamlit"
        echo "  --check           Health check do ambiente"
        echo "  --irpf ANO        Gera pacote IRPF do ano"
        echo "  --sync            Sincroniza relatorios com vault Obsidian"
        echo ""
        echo "Exemplos:"
        echo "  ./run.sh --inbox"
        echo "  ./run.sh --mes 2026-04"
        echo "  ./run.sh --tudo"
        exit 0
        ;;
esac

echo ""
echo "=== Concluído ==="

# "A liberdade é o reconhecimento da necessidade." -- Baruch Spinoza
