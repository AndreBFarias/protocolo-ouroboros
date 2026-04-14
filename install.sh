#!/bin/bash
set -euo pipefail

echo "=== Controle de Bordo -- Instalação ==="

VENV=".venv"

if [ -d "$VENV" ]; then
    echo "Ambiente virtual já existe. Atualizando dependências..."
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

# OCR (fallback para screenshots de contas)
if ! command -v tesseract &> /dev/null; then
    echo "Instalando tesseract-ocr..."
    sudo apt install -y tesseract-ocr tesseract-ocr-por 2>/dev/null || \
        echo "[AVISO] tesseract-ocr não instalado. OCR de imagens não funcionará."
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
