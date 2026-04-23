#!/bin/bash
set -euo pipefail

echo "=== Protocolo Ouroboros -- Instalação ==="

VENV=".venv"

if [ -d "$VENV" ]; then
    if "$VENV/bin/python" -c "import sys" 2>/dev/null; then
        echo "Ambiente virtual válido. Atualizando dependências..."
    else
        echo "Ambiente virtual corrompido. Recriando..."
        rm -rf "$VENV"
        python3 -m venv "$VENV"
    fi
    source "$VENV/bin/activate"
else
    echo "Criando ambiente virtual..."
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
fi

echo "Atualizando pip..."
pip install --upgrade pip --quiet

echo "Instalando dependências do projeto..."
pip install -e ".[dashboard,dev]" --quiet

# Dependências de sistema
echo "Verificando dependências de sistema..."

# Libs para o Python compilar módulos nativos completos (Sprint 86.1).
# Sem libbz2-dev, o módulo _bz2 fica fora do build do pyenv e networkx/pyvis
# levantam ImportError em runtime. Checagem rápida: _bz2 precisa importar.
if ! python3 -c "import _bz2" 2>/dev/null; then
    echo "Instalando libs de compilação nativa (libbz2-dev + libffi-dev + libssl-dev + zlib1g-dev)..."
    sudo apt install -y libbz2-dev libffi-dev libssl-dev zlib1g-dev xz-utils || \
        echo "[AVISO] Libs nativas faltando. Rode: sudo apt install -y libbz2-dev libffi-dev libssl-dev zlib1g-dev xz-utils"
    echo "[AVISO] Após instalar as libs, recompile o Python alvo via pyenv e recrie .venv:"
    echo "        pyenv uninstall 3.12.1 && pyenv install 3.12.1 && rm -rf .venv && ./install.sh"
else
    echo "[OK] _bz2 disponível no Python"
fi

# OCR (para screenshots de contas de energia)
if ! command -v tesseract &> /dev/null; then
    echo "Instalando tesseract-ocr (necessário para OCR de contas de energia)..."
    sudo apt install -y tesseract-ocr tesseract-ocr-por || \
        echo "[AVISO] tesseract-ocr não instalado. Rode: sudo apt install -y tesseract-ocr tesseract-ocr-por"
else
    echo "[OK] tesseract-ocr já instalado"
fi

# pre-commit
if ! "$VENV/bin/pre-commit" --version &> /dev/null; then
    echo "Instalando pre-commit..."
    "$VENV/bin/pip" install pre-commit --quiet
fi

# Criar estrutura de diretórios
mkdir -p \
    inbox \
    data/raw/andre/{nubank_cartao,c6_cc,c6_cartao,itau_cc,santander_cartao} \
    data/raw/vitoria/{nubank_pf_cc,nubank_pj_cc,nubank_pj_cartao} \
    data/processed \
    data/output \
    data/output/backup \
    data/historico \
    docs/pessoal/{andre,vitoria,contratos,saude} \
    docs/extractors \
    docs/sprints \
    logs \
    mappings \
    tests/fixtures

# Instalar launcher .desktop
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/ouroboros.desktop" "$DESKTOP_DIR/" 2>/dev/null && \
    echo "[OK] Launcher instalado em $DESKTOP_DIR/ouroboros.desktop" || \
    echo "[AVISO] Não foi possível instalar launcher .desktop"

echo ""
echo "=== Instalação completa ==="
echo ""
echo "Uso:"
echo "  1. Jogue arquivos brutos em inbox/"
echo "  2. Rode: ./run.sh --inbox    (processa inbox)"
echo "  3. Rode: ./run.sh --tudo     (processa tudo)"
echo "  4. Rode: ./run.sh --mes 2026-04  (mês específico)"
echo "  5. Rode: ./run.sh --dashboard    (abre Streamlit)"

# "Não há vento favorável para quem não sabe onde quer chegar." -- Sêneca
