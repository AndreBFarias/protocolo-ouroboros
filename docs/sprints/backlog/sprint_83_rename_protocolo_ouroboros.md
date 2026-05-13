---
id: 83-RENAME-PROTOCOLO-OUROBOROS
titulo: 0. SPEC (machine-readable)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-21'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 83
  title: "Rename: pasta local + repositório GitHub para 'Protocolo Ouroboros' (Title Case)"
  touches:
    - path: ~/Desenvolvimento/protocolo-ouroboros  # renomear para 'Protocolo Ouroboros'
      reason: "padronização Title Case (igual ao Controle de Bordo)"
    - path: .git/config
      reason: "remote.origin.url para novo nome no GitHub"
    - path: CLAUDE.md
      reason: "referências a paths"
    - path: VALIDATOR_BRIEF.md
      reason: "[CORE] Identidade: atualizar nome"
    - path: README.md
      reason: "título + exemplos de comandos"
    - path: pyproject.toml
      reason: "name do pacote se presente"
    - path: run.sh
      reason: "referências internas a path absoluto se houver"
    - path: Makefile
      reason: "idem"
    - path: scripts/*
      reason: "scripts com path absoluto hardcoded"
    - path: docs/**
      reason: "sweep de menções a 'protocolo-ouroboros' em paths"
  n_to_n_pairs:
    - ["caminho local após rename", "remote GitHub após rename"]
  forbidden:
    - "Fazer force-push"
    - "Renomear sem checar trabalho em progresso (git status precisa estar alinhado)"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/ -q"
      timeout: 120
    - cmd: "./run.sh --check"
      timeout: 30
  acceptance_criteria:
    - "Pasta local renomeada de ~/Desenvolvimento/protocolo-ouroboros para ~/Desenvolvimento/Protocolo Ouroboros (ou equivalente Title Case sem acentos)"
    - "Repo GitHub renomeado (via 'gh repo rename')"
    - "remote.origin.url atualizado no .git/config local"
    - "Zero referência hardcoded a 'protocolo-ouroboros' no código (sweep via rg)"
    - "README.md + CLAUDE.md + VALIDATOR_BRIEF.md com nome novo"
    - "Gauntlet verde (lint + pytest + smoke)"
    - "Backup do estado pré-rename (tag git local 'pre-rename-83')"
  proof_of_work_esperado: |
    cd "$HOME/Desenvolvimento/Protocolo Ouroboros"
    git remote -v | grep -i "protocolo.ouroboros"
    rg -l "protocolo-ouroboros" --type-not yaml | head
    # esperado: zero match em código; matches apenas em docs históricos (logs, changelogs)
    make lint && .venv/bin/pytest tests/ -q && ./run.sh --check
```

---

# Sprint 83 — Rename para "Protocolo Ouroboros"

**Status:** BACKLOG
**Prioridade:** P2
**Dependências:** Nenhuma (pode rodar em qualquer janela livre)
**Issue:** RENAME-01

## Problema

Andre quer padronização Title Case (igual `~/Controle de Bordo`). Hoje: `protocolo-ouroboros` kebab-case em disco e no GitHub.

## Implementação

Passos SEQUENCIAIS e reversíveis:

### 1. Backup + tag

```bash
cd ~/Desenvolvimento/protocolo-ouroboros
git tag pre-rename-83
git push origin pre-rename-83
git status  # deve estar limpo ou com mudanças conscientes
```

### 2. Renomear no GitHub

```bash
gh repo rename "Protocolo-Ouroboros"  # GitHub aceita espaço? Testar. Caso contrário: Protocolo-Ouroboros
```

Padrão GitHub: espaços não são permitidos — viram `-`. Então repo fica `Protocolo-Ouroboros`, mas pasta local pode ter espaço.

### 3. Atualizar remote local

```bash
git remote set-url origin git@github.com-personal:[USER]/Protocolo-Ouroboros.git
git fetch origin
```

### 4. Renomear pasta

```bash
cd ~/Desenvolvimento
mv protocolo-ouroboros "Protocolo Ouroboros"
# shells abertos precisam reabrir
```

### 5. Sweep em código

```bash
cd ~/Desenvolvimento/"Protocolo Ouroboros"
rg -l "protocolo-ouroboros" --type-not yaml  # lista matches
# Para cada arquivo, decidir: keep (histórico/log) ou replace
```

Atualizar:
- `CLAUDE.md` — referências a paths
- `VALIDATOR_BRIEF.md` — seção Identidade
- `README.md` — título e comandos
- `pyproject.toml` — name se aplicável

### 6. Gauntlet

```bash
make lint && .venv/bin/pytest tests/ -q && ./run.sh --check
```

## Armadilhas

| Ref | Armadilha | Como evitar |
|---|---|---|
| A83-1 | Processos abertos (streamlit, editores) têm cwd antigo | Matar streamlit, fechar editores antes do `mv` |
| A83-2 | `~/.claude/projects/` tem hash do path antigo | Nova sessão Claude Code vai criar novo hash; memórias antigas ficam no path antigo (ok, ficam de backup) |
| A83-3 | Symlinks internos quebram | rg por `/home/.*/protocolo-ouroboros` e ajustar |
| A83-4 | `nohup` em background morre | Esperar background terminar antes |

## Evidências

- [ ] `git remote -v` mostra novo nome
- [ ] Pasta local com novo nome
- [ ] Gauntlet exit 0
- [ ] Tag `pre-rename-83` existe no GitHub

---

*"Nome é forma, forma é identidade." — princípio"*
