#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV=".venv"
XLSX="data/output/ouroboros_2026.xlsx"

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
verificar_venv() {
    if [ ! -d "$VENV" ]; then
        echo -e "${RED}Ambiente virtual não encontrado.${NC}"
        echo -e "${DIM}Rode ./install.sh primeiro.${NC}"
        exit 1
    fi
    source "$VENV/bin/activate"
}

backup_xlsx() {
    if compgen -G "data/output/ouroboros_*.xlsx" > /dev/null 2>&1; then
        BACKUP_DIR="data/output/backup/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp data/output/ouroboros_*.xlsx "$BACKUP_DIR/" 2>/dev/null || true
    fi
}

contar_transacoes() {
    if compgen -G "data/output/ouroboros_*.xlsx" > /dev/null 2>&1; then
        "$VENV/bin/python" -c "
import openpyxl, sys
from pathlib import Path
arquivos = sorted(Path('data/output').glob('ouroboros_*.xlsx'))
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

ultima_atualizacao() {
    if [ -f "$XLSX" ]; then
        stat -c '%Y' "$XLSX" 2>/dev/null | xargs -I{} date -d @{} '+%d/%m/%Y %H:%M' 2>/dev/null || echo "---"
    else
        echo "---"
    fi
}

confirmar() {
    local mensagem="$1"
    echo -ne "  ${YELLOW}${mensagem} [s/N]: ${NC}"
    read -r resposta
    [[ "$resposta" =~ ^[sS]$ ]]
}

aguardar_retorno() {
    echo ""
    echo -ne "  ${DIM}Pressione Enter para voltar ao menu...${NC}"
    read -r
}

# ─────────────────────────────────────────────────────────────────
# BANNER E MENU
# ─────────────────────────────────────────────────────────────────
exibir_banner() {
    local dados
    dados=$(contar_transacoes)
    local transacoes="${dados%%|*}"
    local meses="${dados##*|}"
    local atualizado
    atualizado=$(ultima_atualizacao)

    clear
    echo ""
    echo -e "${MAGENTA}"
    echo "  ╔══════════════════════════════════════════════════╗"
    echo "  ║                                                  ║"
    echo "  ║           PROTOCOLO OUROBOROS                      ║"
    echo "  ║           Pipeline Financeiro Pessoal            ║"
    echo "  ║                                                  ║"
    echo "  ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo -e "  ${DIM}${transacoes} transações | ${meses} meses | Atualizado: ${atualizado}${NC}"
    echo ""
}

exibir_menu() {
    echo -e "  ${GREEN}${BOLD}PROCESSAMENTO${NC}"
    echo -e "  ${GREEN}[1]${NC} Processar inbox          ${GREEN}[2]${NC} Processar mês"
    echo -e "  ${GREEN}[3]${NC} Processar tudo"
    echo ""
    echo -e "  ${CYAN}${BOLD}VISUALIZAÇÃO${NC}"
    echo -e "  ${CYAN}[4]${NC} Dashboard Streamlit      ${CYAN}[5]${NC} Gerar relatório"
    echo ""
    echo -e "  ${BLUE}${BOLD}INTEGRAÇÃO${NC}"
    echo -e "  ${BLUE}[6]${NC} Sincronizar Obsidian     ${BLUE}[7]${NC} Pacote IRPF"
    echo ""
    echo -e "  ${YELLOW}${BOLD}QUALIDADE${NC}"
    echo -e "  ${YELLOW}[8]${NC} Health check             ${YELLOW}[9]${NC} Gauntlet"
    echo ""
    echo -e "  ${DIM}[0] Sair${NC}"
    echo ""
}

executar_menu() {
    while true; do
        exibir_banner
        exibir_menu

        echo -ne "  ${BOLD}> ${NC}"
        read -r escolha

        case "$escolha" in
            1)
                echo ""
                echo -e "  ${GREEN}Processando inbox...${NC}"
                echo ""
                backup_xlsx
                python -m src.inbox_processor || true
                aguardar_retorno
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
                python -m src.pipeline --mes "$mes" || true
                aguardar_retorno
                ;;
            3)
                echo ""
                if confirmar "Processar TODOS os dados? Pode demorar."; then
                    echo ""
                    echo -e "  ${GREEN}Processando todos os dados...${NC}"
                    echo ""
                    backup_xlsx
                    python -m src.pipeline --tudo || true
                else
                    echo -e "  ${DIM}Cancelado.${NC}"
                fi
                aguardar_retorno
                ;;
            4)
                echo ""
                echo -e "  ${CYAN}Abrindo dashboard...${NC}"
                echo ""
                streamlit run src/dashboard/app.py || true
                aguardar_retorno
                ;;
            5)
                echo ""
                echo -ne "  ${CYAN}Mês do relatório (YYYY-MM) [$(date +%Y-%m)]: ${NC}"
                read -r mes_rel
                mes_rel="${mes_rel:-$(date +%Y-%m)}"
                echo ""
                echo -e "  ${CYAN}Gerando relatório de ${mes_rel}...${NC}"
                echo ""
                python -c "
import pandas as pd
from src.load.relatorio import gerar_relatorio_mes
from pathlib import Path
xlsx = Path('data/output/ouroboros_2026.xlsx')
if not xlsx.exists():
    print('XLSX não encontrado. Execute o pipeline primeiro.')
    raise SystemExit(1)
df = pd.read_excel(xlsx, sheet_name='extrato')
transacoes = df.to_dict('records')
conteudo = gerar_relatorio_mes(transacoes, '${mes_rel}')
saida = Path('data/output/${mes_rel}_relatorio.md')
saida.write_text(conteudo, encoding='utf-8')
print(f'Relatório salvo em {saida}')
" || true
                aguardar_retorno
                ;;
            6)
                echo ""
                echo -e "  ${BLUE}Sincronizando com Obsidian...${NC}"
                echo ""
                python -m src.obsidian.sync || true
                aguardar_retorno
                ;;
            7)
                echo ""
                echo -ne "  ${MAGENTA}Ano do IRPF [$(date +%Y)]: ${NC}"
                read -r ano_input
                ano="${ano_input:-$(date +%Y)}"
                echo ""
                echo -e "  ${MAGENTA}Gerando pacote IRPF ${ano}...${NC}"
                echo ""
                python -m src.irpf --ano "$ano" || true
                aguardar_retorno
                ;;
            8)
                echo ""
                echo -e "  ${YELLOW}Executando health check...${NC}"
                echo ""
                python -m src.utils.health_check || true
                aguardar_retorno
                ;;
            9)
                echo ""
                echo -e "  ${YELLOW}Executando gauntlet...${NC}"
                echo ""
                python -m scripts.gauntlet.gauntlet || true
                aguardar_retorno
                ;;
            0)
                echo ""
                echo -e "  ${DIM}Até a próxima.${NC}"
                echo ""
                exit 0
                ;;
            *)
                echo -e "  ${RED}Opção inválida. Escolha de 0 a 9.${NC}"
                sleep 1
                ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────
verificar_venv

# Captura Ctrl+C para saída limpa
trap 'echo -e "\n  ${DIM}Até a próxima.${NC}\n"; exit 0' INT

case "${1:-}" in
    --inbox)
        echo "=== Protocolo Ouroboros -- Processando Inbox ==="
        backup_xlsx
        python -m src.inbox_processor
        ;;
    --mes)
        MES="${2:?Informe o mês no formato YYYY-MM}"
        echo "=== Protocolo Ouroboros -- Processando $MES ==="
        backup_xlsx
        python -m src.pipeline --mes "$MES"
        ;;
    --tudo)
        echo "=== Protocolo Ouroboros -- Processando todos os dados ==="
        backup_xlsx
        python -m src.pipeline --tudo
        ;;
    --dashboard)
        echo "=== Protocolo Ouroboros -- Dashboard ==="
        streamlit run src/dashboard/app.py
        ;;
    --check)
        echo "=== Protocolo Ouroboros -- Health Check ==="
        python -m src.utils.health_check
        ;;
    --relatorio)
        MES="${2:-$(date +%Y-%m)}"
        echo "=== Protocolo Ouroboros -- Relatório $MES ==="
        python -c "
import pandas as pd
from src.load.relatorio import gerar_relatorio_mes
from pathlib import Path
xlsx = Path('data/output/ouroboros_2026.xlsx')
if not xlsx.exists():
    print('XLSX não encontrado. Execute o pipeline primeiro.')
    raise SystemExit(1)
df = pd.read_excel(xlsx, sheet_name='extrato')
transacoes = df.to_dict('records')
conteudo = gerar_relatorio_mes(transacoes, '$MES')
saida = Path('data/output/${MES}_relatorio.md')
saida.write_text(conteudo, encoding='utf-8')
print(f'Relatório salvo em {saida}')
"
        ;;
    --irpf)
        ANO="${2:?Informe o ano}"
        echo "=== Protocolo Ouroboros -- IRPF $ANO ==="
        python -m src.irpf --ano "$ANO"
        ;;
    --sync)
        echo "=== Protocolo Ouroboros -- Sincronizando com Obsidian ==="
        python -m src.obsidian.sync
        ;;
    --gauntlet)
        echo "=== Protocolo Ouroboros -- Gauntlet ==="
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
        echo "  --relatorio [MM]  Gera relatório do mês (padrão: atual)"
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
