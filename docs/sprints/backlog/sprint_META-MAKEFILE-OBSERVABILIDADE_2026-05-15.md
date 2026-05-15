---
id: META-MAKEFILE-OBSERVABILIDADE
titulo: 5 targets de observabilidade no Makefile (graduados/audit/spec/health-grafo/propostas)
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-15
fase: DX
epico: 8
depende_de:
  - META-ROADMAP-METRICAS-AUTO (audit reusa metricas_prontidao.json)
  - META-SPEC-LINTER (target spec usa linter)
esforco_estimado_horas: 1.5
origem: auditoria 2026-05-15. Makefile tem 17 targets (install, process, inbox, tudo, sync, mobile-cache, dashboard, test, test-cov, lint, format, docs, validate, check, gauntlet, smoke, anti-migue, clean). Faltam targets de observabilidade: `make graduados` (tabela), `make audit` (5 métricas em 30s), `make spec NOME=foo` (cria spec do template), `make health-grafo` (integridade SQLite), `make propostas` (lista propostas pendentes).
---

# Sprint META-MAKEFILE-OBSERVABILIDADE

## Contexto

Dev/IA pergunta "qual o estado atual?" e precisa:
1. Cavar `data/output/graduacao_tipos.json` (com `cat`)
2. Calcular linking/Outros manualmente
3. Saber se grafo está íntegro (sem comando dedicado)
4. Listar propostas paradas (ls escondido)

Cada uma dessas operações deveria ser 1 target Makefile com saída formatada.

## Hipótese e validação ANTES

H1: Makefile atual sem targets de observabilidade:

```bash
grep -E "^(graduados|audit|spec|health-grafo|propostas):" Makefile
# Esperado: 0 hits
```

H2: comandos já existem em scripts mas não estão wireados:

```bash
ls scripts/dossie_tipo.py scripts/gc_propostas_linking.py
# Esperado: ambos existem (CLI prontos)
```

## Objetivo

Adicionar 5 targets ao Makefile:

```makefile
graduados: ## Tabela viva dos 22 tipos canônicos
	@$(PYTHON) scripts/dossie_tipo.py listar-tipos

audit: ## Auditoria rápida (5 métricas em <30s)
	@$(PYTHON) scripts/gerar_metricas_prontidao.py
	@echo ""
	@$(PYTHON) -c "
import json
m = json.load(open('data/output/metricas_prontidao.json'))
print(f\"Tipos GRADUADOS: {m['tipos_graduados']}/22 (meta >=15)\")
print(f\"Linking documento_de: {m['linking_pct']:.2f}% (meta >=30%)\")
print(f\"Categorização Outros: {m['outros_pct']:.1f}% (meta <=5%)\")
print(f\"Pytest: {m['pytest_count']} passed\")
print(f\"Backup grafo: {'OK' if m['backup_recent'] else 'FALHA'}\")
print(f\"Working tree: {'limpo' if not m['working_dirty'] else 'dirty'}\")
print(f\"Propostas pendentes: {m.get('propostas_abertas', 0)}\")
"

spec: ## Cria spec a partir de template (uso: make spec NOME=foo)
	@if [ -z "$(NOME)" ]; then echo "Uso: make spec NOME=meu-id"; exit 1; fi
	@$(PYTHON) scripts/criar_spec.py "$(NOME)"

health-grafo: ## Valida integridade do SQLite grafo
	@sqlite3 data/output/grafo.sqlite "PRAGMA integrity_check;"
	@sqlite3 data/output/grafo.sqlite "PRAGMA foreign_key_check;"
	@$(PYTHON) -c "
from src.graph.db import GrafoDB, caminho_padrao
db = GrafoDB(caminho_padrao())
nodes = db.con.execute('SELECT COUNT(*) FROM node').fetchone()[0]
edges = db.con.execute('SELECT COUNT(*) FROM edge').fetchone()[0]
print(f'Nodes: {nodes}, Edges: {edges}')
print('Esquema OK')
"

propostas: ## Lista propostas pendentes em docs/propostas/
	@$(PYTHON) -c "
from pathlib import Path
import re
abertas = []
for p in Path('docs/propostas').rglob('*.md'):
    t = p.read_text(encoding='utf-8')
    m = re.search(r'^status:\s*(\w+)', t, re.MULTILINE)
    if m and m.group(1) == 'aberta':
        m2 = re.search(r'^id:\s*(.+)', t, re.MULTILINE)
        abertas.append((m2.group(1) if m2 else p.name, p))
if not abertas:
    print('Nenhuma proposta pendente.')
else:
    print(f'{len(abertas)} propostas pendentes:')
    for id, p in abertas:
        print(f'  [{id}] {p}')
"
```

Criar `scripts/criar_spec.py`:
- Lê `docs/sprints/_template.md` (ou cria inline).
- Substitui placeholders (`{{ID}}`, `{{DATA}}`).
- Gera `docs/sprints/backlog/sprint_<id-kebab>_<data>.md`.

## Não-objetivos

- Não substituir comandos `make smoke/lint/test` (estáveis).
- Não criar UI gráfica.
- Não tocar `make help` (já agrega via comentários `##`).

## Proof-of-work runtime-real

```bash
make graduados | head -10
# Esperado: tabela com 22 tipos

make audit
# Esperado: 6 linhas de métrica

NOME=teste make spec
ls docs/sprints/backlog/sprint_teste*.md
# Esperado: arquivo criado
rm docs/sprints/backlog/sprint_teste*.md  # cleanup

make health-grafo
# Esperado: "ok", count nodes/edges

make propostas
# Esperado: lista das 4 propostas pendentes atuais
```

## Acceptance

- 5 targets no Makefile.
- `scripts/criar_spec.py` funcional.
- `make help` mostra os 5 novos targets.
- 4 testes em `tests/test_makefile_targets.py` (via subprocess).
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (a) Edit incremental — só adicionar; não tocar targets existentes.

---

*"Comando explícito é convite ao uso; comando escondido é convite ao esquecimento." — princípio do help acessível*
