---
id: META-FIX-TESTES-E2E-WORKTREE
titulo: "23 testes E2E playwright/Streamlit falham em worktrees agente"
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-16
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 1.5
origem: "achado colateral do executor `aca4ea99` (INFRA-INBOX-WATCHER) 2026-05-15. Testes em `tests/test_sidebar_canonica.py`, `test_topbar_canonica.py`, `test_visao_geral_canonica.py`, `test_page_header_canonico.py`, `test_filtros_pagina.py` falham consistentemente em qualquer worktree de executor com `cluster Inbox ausente; achei []`. Hipóteses: timing (5s wait_for_timeout insuficiente), worktree path (fixtures vault_sintetico OK mas dashboard tenta carregar data/ ausente), Streamlit race condition no boot."
---

# Sprint META-FIX-TESTES-E2E-WORKTREE

## Contexto

Os 23 testes E2E playwright sobem Streamlit em `127.0.0.1:8770` e
navegam para validar DOM. No main com `data/` presente, todos passam.
Em qualquer worktree de executor (criado por Agent isolation), o DOM
chega vazio porque `data/output/ouroboros_2026.xlsx` não existe.

Impacto: executor reporta "23 errors em pytest" como pré-existentes,
mas isso polui sinal/ruído. Validação por agente fica mais frágil.

## Hipótese e validação ANTES

```bash
# No main: testes passam
.venv/bin/pytest tests/test_sidebar_canonica.py -q
# Esperado: passed

# Em worktree: falham
cd .claude/worktrees/agent-<id>/
.venv/bin/pytest tests/test_sidebar_canonica.py -q
# Esperado: failed (DOM vazio)
```

## Objetivo

Escolher uma das 3 rotas:

**A — Pular testes E2E em worktree**:
- Adicionar `@pytest.mark.dashboard_e2e` em cada um dos 23 testes.
- `pyproject.toml` registra marker.
- `conftest.py` adiciona skip automático quando `data/output/ouroboros_2026.xlsx` ausente.

**B — Symlinkar data/output do main**:
- Quando worktree é criado, link simbólico `data/` → `../../data/`.
- Mas: data/ é gitignored; precisaria de hook fora do git.

**C — Mockar dados no conftest dos testes E2E**:
- Fixture autouse cria XLSX mínimo com 1 transação.
- Streamlit boota com dado real, DOM renderiza.

Recomendação: **Rota A** (mais simples + isolada).

## Não-objetivos

- Não tocar lógica dos testes em si (só skip condicional).
- Não criar dados sintéticos pesados.

## Proof-of-work runtime-real

```bash
cd .claude/worktrees/agent-<algum-id>/
.venv/bin/pytest tests/test_sidebar_canonica.py -q
# Esperado (Rota A): "skipped" não "failed"
```

## Acceptance

- 23 testes E2E com marker `dashboard_e2e`.
- Skip automático em ambiente sem XLSX.
- Pytest > 3080 sem regressão.

## Padrões aplicáveis

- (n) Defesa em camadas — não-bloqueante em ambiente de dev incompleto.

---

*"Teste que falha por ambiente cria ruído; teste que pula honestamente preserva sinal." — princípio do skip condicional*
