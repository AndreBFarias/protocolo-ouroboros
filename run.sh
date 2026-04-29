#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV=".venv"
XLSX="data/output/ouroboros_2026.xlsx"

# ─────────────────────────────────────────────────────────
# Cores ANSI (desabilitadas fora de TTY interativo)
# ─────────────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
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

# ─────────────────────────────────────────────────────────
# Mensagens formatadas
# ─────────────────────────────────────────────────────────
msg_ok()    { echo -e "    ${GREEN}${BOLD}ok${NC}   $1"; }
msg_erro()  { echo -e "    ${RED}${BOLD}erro${NC} $1"; }
msg_info()  { echo -e "    ${CYAN}..${NC}   $1"; }
msg_aviso() { echo -e "    ${YELLOW}!!${NC}   $1"; }

# Sprint 108: helper para encadear automacoes Opus em ordem fixa.
# Cada passo loga início/fim/duracao em logs/auditoria_opus.log.
# Falha-soft: erro em um passo não aborta os proximos.
run_passo() {
    local nome="$1"
    shift
    local inicio  # início em ASCII para compat com bash sem locale
    inicio=$(date +%s)
    msg_info "[Sprint 108] ${nome}..."
    mkdir -p logs
    if "$@" >> logs/auditoria_opus.log 2>&1; then
        local dur=$(($(date +%s) - inicio))
        msg_ok "[Sprint 108] ${nome} OK (${dur}s)"
        return 0
    else
        msg_aviso "[Sprint 108] ${nome} falhou; seguindo (smoke aritmetico no fim captura regressao)"
        return 1
    fi
}

# ─────────────────────────────────────────────────────────
# Funções utilitárias
# ─────────────────────────────────────────────────────────
verificar_venv() {
    if [ ! -d "$VENV" ]; then
        echo ""
        msg_erro "Ambiente virtual não encontrado."
        echo -e "         ${DIM}Execute${NC} ./install.sh ${DIM}para configurar.${NC}"
        echo ""
        exit 1
    fi
    source "$VENV/bin/activate"
}

backup_xlsx() {
    if compgen -G "data/output/ouroboros_*.xlsx" > /dev/null 2>&1; then
        local backup_dir="data/output/backup/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        cp data/output/ouroboros_*.xlsx "$backup_dir/" 2>/dev/null || true
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
        stat -c '%Y' "$XLSX" 2>/dev/null | \
            xargs -I{} date -d @{} '+%d/%m/%Y %H:%M' 2>/dev/null || echo "---"
    else
        echo "---"
    fi
}

confirmar() {
    local mensagem="$1"
    echo -ne "    ${YELLOW}${mensagem}${NC} ${DIM}[s/N]${NC} "
    read -r resposta
    [[ "$resposta" =~ ^[sS]$ ]]
}

aguardar_retorno() {
    echo ""
    echo -ne "    ${DIM}Enter para continuar${NC} "
    read -r
}

separador() {
    local titulo="$1"
    local cor="${2:-$DIM}"
    local titulo_len=${#titulo}
    local pad=$((46 - titulo_len))
    if [ "$pad" -lt 4 ]; then pad=4; fi
    local dashes=""
    for ((i = 0; i < pad; i++)); do dashes+="─"; done
    echo ""
    echo -e "    ${cor}──── ${titulo} ${dashes}${NC}"
    echo ""
}

# ─────────────────────────────────────────────────────────
# Cache de estatísticas (evita reler XLSX a cada loop)
# ─────────────────────────────────────────────────────────
_CACHE_TRANSACOES=""
_CACHE_MESES=""
_CACHE_ATUALIZADO=""
_CACHE_VALIDO=false

invalidar_cache() { _CACHE_VALIDO=false; }

carregar_dados() {
    if [ "$_CACHE_VALIDO" = true ]; then return; fi
    local dados
    dados=$(contar_transacoes)
    _CACHE_TRANSACOES="${dados%%|*}"
    _CACHE_MESES="${dados##*|}"
    _CACHE_ATUALIZADO=$(ultima_atualizacao)
    _CACHE_VALIDO=true
}

# ─────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────
exibir_banner() {
    carregar_dados

    clear
    echo ""
    echo -e "    ${MAGENTA}${BOLD}"
    echo "    ╔══════════════════════════════════════════════════╗"
    echo "    ║                                                  ║"
    echo "    ║    ╭─╮  PROTOCOLO  OUROBOROS                     ║"
    echo "    ║    ╰─╯  Pipeline Financeiro Pessoal              ║"
    echo "    ║                                                  ║"
    echo "    ╚══════════════════════════════════════════════════╝"
    echo -e "    ${NC}"
    echo ""
    printf "    ${WHITE}%s${NC} ${DIM}transações${NC}" "$_CACHE_TRANSACOES"
    printf "   ${WHITE}%s${NC} ${DIM}meses${NC}" "$_CACHE_MESES"
    printf "   ${DIM}atualizado${NC} ${WHITE}%s${NC}\n" "$_CACHE_ATUALIZADO"
    echo ""
}

# ─────────────────────────────────────────────────────────
# Menu
# ─────────────────────────────────────────────────────────
exibir_menu() {
    separador "PROCESSAMENTO" "$GREEN"
    echo -e "    ${GREEN}${BOLD}R${NC}   Rota completa: inbox + tudo ${DIM}(padrão)${NC}"
    echo -e "    ${GREEN}${BOLD}1${NC}   Processar inbox"
    echo -e "    ${GREEN}${BOLD}2${NC}   Processar mês específico"
    echo -e "    ${GREEN}${BOLD}3${NC}   Processar todos os dados"

    separador "VISUALIZAÇÃO" "$CYAN"
    echo -e "    ${CYAN}${BOLD}4${NC}   Abrir dashboard"
    echo -e "    ${CYAN}${BOLD}5${NC}   Gerar relatório mensal"

    separador "INTEGRAÇÃO" "$BLUE"
    echo -e "    ${BLUE}${BOLD}6${NC}   Sincronizar Obsidian"
    echo -e "    ${BLUE}${BOLD}7${NC}   Gerar pacote IRPF"

    separador "QUALIDADE" "$YELLOW"
    echo -e "    ${YELLOW}${BOLD}8${NC}   Health check"
    echo -e "    ${YELLOW}${BOLD}9${NC}   Gauntlet"

    echo ""
    echo -e "    ${DIM}0   Sair${NC}"
    echo ""
}

# ─────────────────────────────────────────────────────────
# Ações do menu
# ─────────────────────────────────────────────────────────
acao_rota_completa() {
    echo ""
    if confirmar "Rodar rota completa (inbox + tudo)?"; then
        echo ""
        msg_info "Rota completa: inbox + tudo (Sprint 101)..."
        echo ""
        backup_xlsx
        python -m src.integrations.controle_bordo --executar || msg_aviso "Adapter do vault reportou erro(s); seguindo."
        if python -m src.inbox_processor; then
            msg_ok "Inbox processada; iniciando pipeline completo..."
            echo ""
            if python -m src.pipeline --tudo; then
                echo ""
                msg_ok "Rota completa concluída."
            else
                echo ""
                msg_erro "Falha no pipeline."
            fi
        else
            echo ""
            msg_erro "Inbox falhou; abortando ciclo completo."
        fi
        invalidar_cache
    else
        echo ""
        msg_info "Cancelado."
    fi
    aguardar_retorno
}

acao_processar_inbox() {
    echo ""
    msg_info "Processando inbox unificada (vault + legado)..."
    echo ""
    backup_xlsx
    # Sprint 70 (Fase IOTA): adapter varre vault + legado, roteia financeiros
    python -m src.integrations.controle_bordo --executar || msg_aviso "Adapter do vault reportou erro(s); seguindo."
    if python -m src.inbox_processor; then
        echo ""
        msg_ok "Inbox processada."
    else
        echo ""
        msg_erro "Falha ao processar inbox."
    fi
    invalidar_cache
    aguardar_retorno
}

acao_processar_mes() {
    echo ""
    echo -ne "    ${DIM}Mês${NC} ${WHITE}(YYYY-MM)${NC} ${DIM}[${NC}$(date +%Y-%m)${DIM}]:${NC} "
    read -r mes_input
    local mes="${mes_input:-$(date +%Y-%m)}"
    echo ""
    msg_info "Processando ${mes}..."
    echo ""
    backup_xlsx
    if python -m src.pipeline --mes "$mes"; then
        echo ""
        msg_ok "Mês ${mes} processado."
    else
        echo ""
        msg_erro "Falha ao processar ${mes}."
    fi
    invalidar_cache
    aguardar_retorno
}

acao_processar_tudo() {
    echo ""
    if confirmar "Processar TODOS os dados?"; then
        echo ""
        msg_info "Processando todos os dados..."
        echo ""
        backup_xlsx
        if python -m src.pipeline --tudo; then
            echo ""
            msg_ok "Pipeline completo."
        else
            echo ""
            msg_erro "Falha no pipeline."
        fi
        invalidar_cache
    else
        echo ""
        msg_info "Cancelado."
    fi
    aguardar_retorno
}

acao_abrir_dashboard() {
    echo ""
    msg_info "Abrindo dashboard Streamlit..."
    echo ""
    streamlit run src/dashboard/app.py || true
    aguardar_retorno
}

acao_gerar_relatorio() {
    echo ""
    echo -ne "    ${DIM}Mês do relatório${NC} ${WHITE}(YYYY-MM)${NC} ${DIM}[${NC}$(date +%Y-%m)${DIM}]:${NC} "
    read -r mes_rel
    mes_rel="${mes_rel:-$(date +%Y-%m)}"
    echo ""
    msg_info "Gerando relatório de ${mes_rel}..."
    echo ""
    if python -c "
import pandas as pd
from src.load.relatorio import gerar_relatorio_mes
from pathlib import Path
xlsx = sorted(Path('data/output').glob('ouroboros_*.xlsx'))
if not xlsx:
    print('    XLSX não encontrado. Execute o pipeline primeiro.')
    raise SystemExit(1)
df = pd.read_excel(xlsx[-1], sheet_name='extrato')
transacoes = df.to_dict('records')
conteudo = gerar_relatorio_mes(transacoes, '${mes_rel}')
saida = Path('data/output/${mes_rel}_relatorio.md')
saida.write_text(conteudo, encoding='utf-8')
print(f'    Salvo em: {saida}')
"; then
        echo ""
        msg_ok "Relatório de ${mes_rel} gerado."
    else
        echo ""
        msg_erro "Falha ao gerar relatório."
    fi
    aguardar_retorno
}

acao_sincronizar_obsidian() {
    echo ""
    msg_info "Sincronizando com Obsidian..."
    echo ""
    if python -m src.obsidian.sync; then
        echo ""
        msg_ok "Sincronização concluída."
    else
        echo ""
        msg_erro "Falha na sincronização."
    fi
    aguardar_retorno
}

acao_pacote_irpf() {
    echo ""
    echo -ne "    ${DIM}Ano do IRPF${NC} ${WHITE}[${NC}$(date +%Y)${DIM}]:${NC} "
    read -r ano_input
    local ano="${ano_input:-$(date +%Y)}"
    echo ""
    msg_info "Gerando pacote IRPF ${ano}..."
    echo ""
    if python -m src.irpf --ano "$ano"; then
        echo ""
        msg_ok "Pacote IRPF ${ano} gerado."
    else
        echo ""
        msg_erro "Falha ao gerar pacote IRPF ${ano}. Ver logs."
    fi
    aguardar_retorno
}

acao_health_check() {
    echo ""
    msg_info "Executando health check..."
    echo ""
    if python -m src.utils.health_check; then
        echo ""
        msg_ok "Health check concluído."
    else
        echo ""
        msg_aviso "Health check reportou problemas."
    fi
    aguardar_retorno
}

acao_gauntlet() {
    echo ""
    msg_info "Executando gauntlet..."
    echo ""
    if python -m scripts.gauntlet.gauntlet; then
        echo ""
        msg_ok "Gauntlet concluído."
    else
        echo ""
        msg_aviso "Gauntlet reportou falhas."
    fi
    aguardar_retorno
}

# ─────────────────────────────────────────────────────────
# Loop do menu interativo
# ─────────────────────────────────────────────────────────
executar_menu() {
    while true; do
        exibir_banner
        exibir_menu

        echo -ne "    ${BOLD}>${NC} ${DIM}[R]${NC} "
        read -r escolha
        # Default R: entrada vazia roda a rota completa (Sprint 101).
        escolha="${escolha:-R}"

        case "$escolha" in
            r|R) acao_rota_completa ;;
            1) acao_processar_inbox ;;
            2) acao_processar_mes ;;
            3) acao_processar_tudo ;;
            4) acao_abrir_dashboard ;;
            5) acao_gerar_relatorio ;;
            6) acao_sincronizar_obsidian ;;
            7) acao_pacote_irpf ;;
            8) acao_health_check ;;
            9) acao_gauntlet ;;
            0)
                echo ""
                echo -e "    ${DIM}Até a próxima.${NC}"
                echo ""
                exit 0
                ;;
            *)
                msg_aviso "Opção inválida. Escolha R, 0 a 9."
                sleep 0.8
                ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────
# Help formatado
# ─────────────────────────────────────────────────────────
exibir_help() {
    echo ""
    echo -e "  ${MAGENTA}${BOLD}PROTOCOLO OUROBOROS${NC} ${DIM}-- Pipeline Financeiro Pessoal${NC}"
    echo ""
    echo -e "  ${WHITE}Uso:${NC} ./run.sh ${DIM}[opção]${NC}"
    echo ""
    echo -e "  Sem argumentos abre o menu interativo."
    echo ""
    echo -e "  ${WHITE}Processamento${NC}"
    echo -e "    ${GREEN}--full-cycle${NC}        Rota completa: inbox + tudo (recomendado)"
    echo -e "    ${GREEN}--inbox${NC}             Processa inbox unificada (vault + legado)"
    echo -e "    ${GREEN}--inbox-dry${NC}         Inspeciona inbox unificada sem mover nada"
    echo -e "    ${GREEN}--mes${NC} ${DIM}YYYY-MM${NC}       Processa um mês específico"
    echo -e "    ${GREEN}--tudo${NC}              Processa todos os dados"
    echo -e "    ${GREEN}--reextrair-tudo${NC}    Limpa documentos do grafo e re-ingere com extratores atuais"
    echo ""
    echo -e "  ${WHITE}Visualização${NC}"
    echo -e "    ${CYAN}--dashboard${NC}         Abre o dashboard Streamlit"
    echo -e "    ${CYAN}--relatorio${NC} ${DIM}[MM]${NC}    Gera relatório mensal (padrão: mês atual)"
    echo ""
    echo -e "  ${WHITE}Integração${NC}"
    echo -e "    ${BLUE}--irpf${NC} ${DIM}ANO${NC}          Gera pacote IRPF do ano"
    echo -e "    ${BLUE}--sync${NC}              Sincroniza com vault Obsidian"
    echo ""
    echo -e "  ${WHITE}Qualidade${NC}"
    echo -e "    ${YELLOW}--check${NC}             Health check do ambiente"
    echo -e "    ${YELLOW}--gauntlet${NC}          Gauntlet de testes"
    echo -e "    ${YELLOW}--supervisor${NC}        Snapshot do estado do projeto (contexto para sessão)"
    echo ""
    echo -e "  ${WHITE}Exemplos${NC}"
    echo -e "    ${DIM}\$${NC} ./run.sh --full-cycle"
    echo -e "    ${DIM}\$${NC} ./run.sh --mes 2026-03"
    echo -e "    ${DIM}\$${NC} ./run.sh --relatorio 2026-04"
    echo -e "    ${DIM}\$${NC} ./run.sh --irpf 2026"
    echo ""
}

# ─────────────────────────────────────────────────────────
# Execução principal
# ─────────────────────────────────────────────────────────
verificar_venv

trap 'echo -e "\n    ${DIM}Até a próxima.${NC}\n"; exit 0' INT

case "${1:-}" in
    --inbox)
        msg_info "Processando inbox unificada (vault + legado)..."
        backup_xlsx
        # Sprint 70 (Fase IOTA): adapter varre vault + legado primeiro
        python -m src.integrations.controle_bordo --executar || msg_aviso "Adapter do vault reportou erro(s); seguindo."
        python -m src.inbox_processor
        msg_ok "Inbox processada."
        ;;
    --inbox-dry)
        msg_info "Inspecionando inbox unificada (dry-run, sem efeito colateral)..."
        python -m src.integrations.controle_bordo
        ;;
    --menu)
        # Sprint 80: menu interativo em Python com rich.
        exec "$VENV/bin/python" scripts/menu_interativo.py
        ;;
    --mes)
        MES="${2:?Informe o mês no formato YYYY-MM}"
        msg_info "Processando ${MES}..."
        backup_xlsx
        python -m src.pipeline --mes "$MES"
        msg_ok "Mês ${MES} processado."
        ;;
    --tudo)
        msg_info "Processando todos os dados..."
        backup_xlsx
        python -m src.pipeline --tudo
        msg_ok "Pipeline completo."
        ;;
    --full-cycle)
        # Sprint 101 + 108: rota completa com automacoes Opus encadeadas.
        # Ordem fixa: inbox -> dedup_classificar -> migrar_pessoa -> backfill_arquivo_origem
        # -> pipeline-tudo. Cada automacao tem falha-soft.
        msg_info "Rota completa: inbox + automacoes Opus + pipeline (Sprint 101+108)..."
        backup_xlsx
        python -m src.integrations.controle_bordo --executar || msg_aviso "Adapter do vault reportou erro(s); seguindo."
        if ! python -m src.inbox_processor; then
            msg_erro "Inbox falhou; abortando ciclo completo."
            exit 1
        fi
        msg_ok "Inbox processada; iniciando automacoes Opus..."
        run_passo "dedup_classificar" python -m scripts.dedup_classificar_lote --executar
        run_passo "migrar_pessoa_via_cpf" python -m scripts.migrar_pessoa_via_cpf --executar
        run_passo "backfill_arquivo_origem" python -m scripts.backfill_arquivo_origem_lote --executar
        msg_info "Pipeline canonico..."
        python -m src.pipeline --tudo
        run_passo "anti_orfao" python -m src.intake.anti_orfao
        msg_ok "Rota completa concluida."
        ;;
    --reextrair-tudo)
        # Sprint 104 + 108: cleanup automacoes + reextracao completa.
        # AUDIT-MENU-CONFIRMACAO: --sim pula confirmar() (uso pelo menu Python).
        msg_aviso "Reextracao em lote: vai limpar nodes 'documento' do grafo."
        if [[ "${2:-}" == "--sim" ]] || confirmar "Tem certeza? (operação irreversivel)"; then
            msg_info "Rodando automacoes de cleanup antes de reextrair (Sprint 108)..."
            run_passo "dedup_classificar" python -m scripts.dedup_classificar_lote --executar
            run_passo "migrar_pessoa_via_cpf" python -m scripts.migrar_pessoa_via_cpf --executar
            run_passo "backfill_arquivo_origem" python -m scripts.backfill_arquivo_origem_lote --executar
            msg_info "Re-ingerindo documentos com extratores atualizados..."
            python -m scripts.reprocessar_documentos --forcar-reextracao
            run_passo "limpar_revisao_orfaos" python -m scripts.limpar_revisao_orfaos --executar
            run_passo "normalizar_path_relativo" python -m scripts.normalizar_path_relativo --executar
            run_passo "backfill_metadata_pessoa" python -m scripts.backfill_metadata_pessoa --executar
            run_passo "backfill_razao_social_canonica" python -m scripts.backfill_razao_social_canonica --executar
            msg_ok "Reextracao concluida."
        else
            msg_aviso "Operação cancelada."
        fi
        ;;
    --dashboard)
        msg_info "Abrindo dashboard Streamlit..."
        streamlit run src/dashboard/app.py
        ;;
    --check)
        msg_info "Executando health check..."
        python -m src.utils.health_check
        ;;
    --relatorio)
        MES="${2:-$(date +%Y-%m)}"
        msg_info "Gerando relatório de ${MES}..."
        python -c "
import pandas as pd
from src.load.relatorio import gerar_relatorio_mes
from pathlib import Path
xlsx = sorted(Path('data/output').glob('ouroboros_*.xlsx'))
if not xlsx:
    print('XLSX não encontrado. Execute o pipeline primeiro.')
    raise SystemExit(1)
df = pd.read_excel(xlsx[-1], sheet_name='extrato')
transacoes = df.to_dict('records')
conteudo = gerar_relatorio_mes(transacoes, '$MES')
saida = Path('data/output/${MES}_relatorio.md')
saida.write_text(conteudo, encoding='utf-8')
print(f'Salvo em: {saida}')
"
        msg_ok "Relatório de ${MES} gerado."
        ;;
    --irpf)
        ANO="${2:?Informe o ano}"
        msg_info "Gerando pacote IRPF ${ANO}..."
        python -m src.irpf --ano "$ANO"
        msg_ok "Pacote IRPF ${ANO} gerado."
        ;;
    --sync)
        msg_info "Sincronizando com Obsidian..."
        python -m src.obsidian.sync
        msg_ok "Sincronização concluída."
        ;;
    --gauntlet)
        msg_info "Executando gauntlet..."
        python -m scripts.gauntlet.gauntlet "${@:2}"
        msg_ok "Gauntlet concluído."
        ;;
    --supervisor)
        bash scripts/supervisor_contexto.sh
        ;;
    --help|-h)
        exibir_help
        exit 0
        ;;
    "")
        executar_menu
        ;;
    *)
        msg_erro "Opção desconhecida: ${1}"
        echo ""
        exibir_help
        exit 1
        ;;
esac

# "A liberdade é o reconhecimento da necessidade." -- Baruch Spinoza
