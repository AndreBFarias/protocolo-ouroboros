#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV=".venv"

# ─────────────────────────────────────────────────────────────────
# CORES ANSI -- desabilita se não estiver em TTY interativo
# ─────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    CYAN='\033[0;36m'
    WHITE='\033[1;37m'
    BOLD='\033[1m'
    DIM='\033[2m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' MAGENTA=''
    CYAN='' WHITE='' BOLD='' DIM='' NC=''
fi

# ─────────────────────────────────────────────────────────────────
# FUNÇÕES UTILITÁRIAS
# ─────────────────────────────────────────────────────────────────
type_slow() {
    local text="$1"
    local delay="${2:-0.02}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep "$delay"
    done
    echo ""
}

verificar_venv() {
    if [ ! -d "$VENV" ]; then
        echo -e "${RED}Ambiente virtual não encontrado.${NC}"
        echo -e "${DIM}Rode ./install.sh primeiro.${NC}"
        exit 1
    fi
    source "$VENV/bin/activate"
}

backup_xlsx() {
    if compgen -G "data/output/controle_bordo_*.xlsx" > /dev/null 2>&1; then
        BACKUP_DIR="data/output/backup/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp data/output/controle_bordo_*.xlsx "$BACKUP_DIR/" 2>/dev/null || true
    fi
}

contar_transacoes() {
    if compgen -G "data/output/controle_bordo_*.xlsx" > /dev/null 2>&1; then
        "$VENV/bin/python" -c "
import openpyxl, sys
from pathlib import Path
arquivos = sorted(Path('data/output').glob('controle_bordo_*.xlsx'))
if not arquivos:
    print('0|0')
    sys.exit()
wb = openpyxl.load_workbook(arquivos[-1], read_only=True)
if 'extrato' in wb.sheetnames:
    ws = wb['extrato']
    linhas = ws.max_row - 1 if ws.max_row else 0
    meses = set()
    for row in ws.iter_rows(min_row=2, max_col=10, values_only=True):
        if row[9]:
            meses.add(str(row[9]))
    print(f'{linhas}|{len(meses)}')
else:
    print('0|0')
wb.close()
" 2>/dev/null || echo "0|0"
    else
        echo "0|0"
    fi
}

# ─────────────────────────────────────────────────────────────────
# BANNER E MENU
# ─────────────────────────────────────────────────────────────────
exibir_banner() {
    local dados
    dados=$(contar_transacoes)
    local transacoes="${dados%%|*}"
    local meses="${dados##*|}"

    echo ""
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║                                              ║"
    echo "  ║         CONTROLE DE BORDO                    ║"
    echo "  ║         Pipeline Financeiro Pessoal          ║"
    echo "  ║                                              ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo -e "  ${DIM}${transacoes} transações | ${meses} meses processados${NC}"
    echo ""
    sleep 0.3

    echo -ne "  ${MAGENTA}"
    type_slow "...calculando balanço..." 0.03
    echo -e "${NC}"
    echo ""
    sleep 0.4
}

exibir_menu() {
    echo -e "  ${WHITE}O que deseja fazer?${NC}"
    echo ""
    echo -e "  ${GREEN}[1]${NC} Processar inbox"
    echo -e "  ${GREEN}[2]${NC} Processar mês específico"
    echo -e "  ${GREEN}[3]${NC} Processar todos os dados"
    echo -e "  ${CYAN}[4]${NC} Abrir dashboard"
    echo -e "  ${BLUE}[5]${NC} Sincronizar com Obsidian"
    echo -e "  ${YELLOW}[6]${NC} Health check"
    echo -e "  ${MAGENTA}[7]${NC} Gerar pacote IRPF"
    echo -e "  ${RED}[8]${NC} Executar gauntlet"
    echo -e "  ${DIM}[0]${NC} Sair"
    echo ""
}

executar_menu() {
    exibir_banner
    exibir_menu

    while true; do
        echo -ne "  ${BOLD}> ${NC}"
        read -r escolha

        case "$escolha" in
            1)
                echo ""
                echo -e "  ${GREEN}Processando inbox...${NC}"
                echo ""
                backup_xlsx
                python -m src.inbox_processor
                break
                ;;
            2)
                echo ""
                echo -ne "  ${CYAN}Mês (YYYY-MM) [$(date +%Y-%m)]: ${NC}"
                read -r mes_input
                mes="${mes_input:-$(date +%Y-%m)}"
                echo ""
                echo -e "  ${GREEN}Processando ${mes}...${NC}"
                echo ""
                backup_xlsx
                python -m src.pipeline --mes "$mes"
                break
                ;;
            3)
                echo ""
                echo -e "  ${GREEN}Processando todos os dados...${NC}"
                echo ""
                backup_xlsx
                python -m src.pipeline --tudo
                break
                ;;
            4)
                echo ""
                echo -e "  ${CYAN}Abrindo dashboard...${NC}"
                echo ""
                streamlit run src/dashboard/app.py
                break
                ;;
            5)
                echo ""
                echo -e "  ${BLUE}Sincronizando com Obsidian...${NC}"
                echo ""
                python -m src.obsidian.sync
                break
                ;;
            6)
                echo ""
                echo -e "  ${YELLOW}Executando health check...${NC}"
                echo ""
                python -m src.utils.health_check
                break
                ;;
            7)
                echo ""
                echo -ne "  ${MAGENTA}Ano do IRPF [$(date +%Y)]: ${NC}"
                read -r ano_input
                ano="${ano_input:-$(date +%Y)}"
                echo ""
                echo -e "  ${MAGENTA}Gerando pacote IRPF ${ano}...${NC}"
                echo ""
                python -m src.irpf --ano "$ano"
                break
                ;;
            8)
                echo ""
                echo -e "  ${RED}Executando gauntlet...${NC}"
                echo ""
                python -m scripts.gauntlet.gauntlet "${@:2}"
                break
                ;;
            0)
                echo ""
                echo -e "  ${DIM}Até a próxima.${NC}"
                echo ""
                exit 0
                ;;
            *)
                echo -e "  ${RED}Opção inválida. Escolha de 0 a 8.${NC}"
                ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────
verificar_venv

case "${1:-}" in
    --inbox)
        echo "=== Controle de Bordo -- Processando Inbox ==="
        backup_xlsx
        python -m src.inbox_processor
        ;;
    --mes)
        MES="${2:?Informe o mês no formato YYYY-MM}"
        echo "=== Controle de Bordo -- Processando $MES ==="
        backup_xlsx
        python -m src.pipeline --mes "$MES"
        ;;
    --tudo)
        echo "=== Controle de Bordo -- Processando todos os dados ==="
        backup_xlsx
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
    --gauntlet)
        echo "=== Controle de Bordo -- Gauntlet ==="
        python -m scripts.gauntlet.gauntlet "${@:2}"
        ;;
    --menu)
        executar_menu
        ;;
    "")
        executar_menu
        ;;
    *)
        echo "Uso: ./run.sh [opção]"
        echo ""
        echo "Opções:"
        echo "  --inbox           Processa arquivos do inbox/"
        echo "  --mes YYYY-MM     Processa um mês específico"
        echo "  --tudo            Processa todos os dados disponíveis"
        echo "  --dashboard       Abre o dashboard Streamlit"
        echo "  --check           Health check do ambiente"
        echo "  --irpf ANO        Gera pacote IRPF do ano"
        echo "  --sync            Sincroniza relatórios com vault Obsidian"
        echo "  --gauntlet        Executa gauntlet de testes"
        echo "  --menu            Abre o menu interativo"
        echo ""
        echo "Sem argumentos: abre o menu interativo."
        exit 0
        ;;
esac

echo ""
echo -e "${GREEN}=== Concluído ===${NC}"

# "A liberdade é o reconhecimento da necessidade." -- Baruch Spinoza
