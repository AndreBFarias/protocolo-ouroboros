.PHONY: help process inbox tudo dashboard test lint format docs validate check install clean gauntlet smoke anti-migue sync mobile-cache graduados audit spec health-grafo propostas gc-worktrees

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

sync: ## Pipeline completo + caches Mobile (alias canônico de --full-cycle)
	./run.sh --full-cycle

mobile-cache: ## Gera apenas os caches readonly do Mobile (humor + financas)
	./run.sh --mobile-cache

dashboard: ## Abre o dashboard Streamlit
	./run.sh --dashboard

test: ## Executa testes
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov: ## Executa testes com relatório de cobertura
	$(PYTHON) -m pytest tests/ --cov=src/transform --cov=src/extractors --cov-report=term-missing

lint: ## Verifica código com ruff + acentuação + cobertura total D7 + forma das specs
	$(RUFF) check src/ tests/ scripts/
	$(PYTHON) scripts/check_acentuacao.py --all
	$(PYTHON) scripts/check_cobertura_total.py
	$(PYTHON) scripts/check_spec.py --soft docs/sprints/backlog/

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
	@echo "Para validar gate 4-way de extrator novo: make conformance-<tipo>."

conformance-%: ## Gate 4-way >=3 amostras verdes (Sprint ANTI-MIGUE-01)
	@$(PYTHON) -m tests.conformance.gate $*

graduados: ## Tabela viva dos tipos canônicos (graduação Opus/ETL)
	@$(PYTHON) scripts/dossie_tipo.py listar-tipos

estado-atual-atualizar: ## Regenera bloco de métricas vivas em contexto/ESTADO_ATUAL.md
	@$(PYTHON) scripts/regenerar_estado_atual.py --apply

audit: ## Auditoria rápida (métricas de prontidão; fallback se script não materializado)
	@if [ -f scripts/gerar_metricas_prontidao.py ]; then \
		$(PYTHON) scripts/gerar_metricas_prontidao.py; \
	else \
		echo "Sprint META-ROADMAP-METRICAS-AUTO ainda não materializada -- métricas vivas pendentes."; \
	fi

spec: ## Cria spec a partir do template (uso: make spec NOME=meu-id)
	@if [ -z "$(NOME)" ]; then echo "Uso: make spec NOME=meu-id"; exit 1; fi
	@$(PYTHON) scripts/criar_spec.py "$(NOME)"

health-grafo: ## Valida integridade do SQLite do grafo + contagem de nós/arestas
	@if [ ! -f data/output/grafo.sqlite ]; then \
		echo "Grafo ausente em data/output/grafo.sqlite -- rode 'make tudo' primeiro."; \
	else \
		sqlite3 data/output/grafo.sqlite "PRAGMA integrity_check;"; \
		sqlite3 data/output/grafo.sqlite "PRAGMA foreign_key_check;"; \
		$(PYTHON) -c "from src.graph.db import GrafoDB, caminho_padrao; db = GrafoDB(caminho_padrao()); n = db._conn.execute('SELECT COUNT(*) FROM node').fetchone()[0]; e = db._conn.execute('SELECT COUNT(*) FROM edge').fetchone()[0]; print(f'Nós: {n}, Arestas: {e}'); print('Esquema OK')"; \
	fi

propostas: ## Lista propostas pendentes em docs/propostas/ (status: aberta)
	@$(PYTHON) -c "\
	from pathlib import Path; \
	import re; \
	raiz = Path('docs/propostas'); \
	abertas = []; \
	[abertas.append((re.search(r'^id:\s*(.+)', t, re.MULTILINE).group(1) if re.search(r'^id:\s*(.+)', t, re.MULTILINE) else p.name, str(p))) for p in raiz.rglob('*.md') if '_obsoletas' not in p.parts and '_rejeitadas' not in p.parts and (t := p.read_text(encoding='utf-8')) and (m := re.search(r'^status:\s*(\w+)', t, re.MULTILINE)) and m.group(1) == 'aberta']; \
	print('Nenhuma proposta pendente.' if not abertas else f'{len(abertas)} propostas pendentes:'); \
	[print(f'  [{i}] {p}') for i, p in abertas]; \
	"

clean: ## Remove artefatos de build (não remove dados)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .ruff_cache .pytest_cache *.egg-info dist build

gc-worktrees: ## Dry-run do GC de worktrees agent-* e branches worktree-agent-* mergeadas
	@./scripts/limpar_worktrees_agentes.sh

# "O segredo da liberdade é a coragem." -- Péricles
