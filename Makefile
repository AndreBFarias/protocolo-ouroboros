.PHONY: help process inbox tudo dashboard test lint format docs validate check install clean gauntlet smoke anti-migue

SHELL := /bin/bash
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
MES ?= $(shell date +%Y-%m)

help: ## Mostra este menu de ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependências e cria ambiente
	./install.sh

process: ## Processa um mês específico (MES=2026-04)
	./run.sh --mes $(MES)

inbox: ## Processa arquivos do inbox/
	./run.sh --inbox

tudo: ## Processa todos os dados disponíveis
	./run.sh --tudo

dashboard: ## Abre o dashboard Streamlit
	./run.sh --dashboard

test: ## Executa testes
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov: ## Executa testes com relatório de cobertura
	$(PYTHON) -m pytest tests/ --cov=src/transform --cov=src/extractors --cov-report=term-missing

lint: ## Verifica código com ruff + acentuação
	$(RUFF) check src/ tests/ scripts/
	$(PYTHON) scripts/check_acentuacao.py --all

format: ## Formata código com ruff
	$(RUFF) format src/ tests/ scripts/
	$(RUFF) check --fix src/ tests/ scripts/

docs: ## Gera documentação dos extratores
	$(PYTHON) -m src.utils.doc_generator

validate: ## Valida integridade do último XLSX gerado
	$(PYTHON) -c "\
	import openpyxl; \
	from collections import Counter; \
	wb = openpyxl.load_workbook('data/output/ouroboros_2026.xlsx'); \
	ws = wb['extrato']; \
	total = ws.max_row - 1; \
	cats = Counter(row[5] for row in ws.iter_rows(min_row=2, values_only=True)); \
	outros = cats.get('Outros', 0); \
	pct = (total - outros) / total * 100; \
	print(f'Transações: {total}'); \
	print(f'Categorizadas: {pct:.1f}%'); \
	print(f'Abas: {wb.sheetnames}'); \
	clfs = Counter(row[6] for row in ws.iter_rows(min_row=2, values_only=True)); \
	nulos = clfs.get(None, 0); \
	print(f'Classificações nulas: {nulos}'); \
	print('[OK] Validação passou' if pct >= 80 and nulos == 0 else '[FALHA]'); \
	"

check: ## Health check do ambiente
	@echo "=== Health Check ==="
	@test -d $(VENV) && echo "[OK] Ambiente virtual" || echo "[X] Sem ambiente virtual"
	@test -f data/output/ouroboros_2026.xlsx && echo "[OK] XLSX gerado" || echo "[X] XLSX não encontrado"
	@ls data/output/*_relatorio.md 2>/dev/null | wc -l | xargs -I{} echo "[OK] {} relatórios"
	@$(RUFF) check src/ --quiet && echo "[OK] Lint passou" || echo "[X] Lint com erros"
	@echo "=== Concluído ==="

gauntlet: ## Executa gauntlet de testes (validação completa)
	$(PYTHON) -m scripts.gauntlet.gauntlet

smoke: ## Smoke runtime-real (health check + contratos aritméticos)
	@./run.sh --check
	@$(PYTHON) scripts/smoke_aritmetico.py --strict

anti-migue: lint smoke test ## Gauntlet anti-migué (entry point único do gate de 9 checks)
	@echo "=== anti-migue gauntlet OK ==="
	@$(PYTHON) scripts/check_concluida_em.py
	@echo "Atenção: target conformance-<tipo> ainda não disponível -- depende de ANTI-MIGUE-01."

conformance-%: ## Gate 4-way conformance por tipo (depende de ANTI-MIGUE-01)
	@echo "Target conformance-$* aguarda implementação de ANTI-MIGUE-01."
	@echo "Quando o gate 4-way estiver implementado, esta regra rodará pytest tests/conformance/ -k $*."
	@exit 1

clean: ## Remove artefatos de build (não remove dados)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .ruff_cache .pytest_cache *.egg-info dist build

# "O segredo da liberdade é a coragem." -- Péricles
