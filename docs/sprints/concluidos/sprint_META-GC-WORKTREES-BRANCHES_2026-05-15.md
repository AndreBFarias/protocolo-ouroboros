---
id: META-GC-WORKTREES-BRANCHES
titulo: Garbage collection de worktrees + branches `worktree-agent-*` mergeadas
status: concluída
concluida_em: 2026-05-15
prioridade: P3
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 1
origem: "auditoria 2026-05-15. `git worktree list | wc -l` = 86. `git branch --merged main` mostra ~47 branches mergeadas worktree-agent-*. Polui ergonomia: `git branch` é ilegível, `.claude/worktrees/` ocupa espaço."
---

# Sprint META-GC-WORKTREES-BRANCHES

## Contexto

Cada `executor-sprint` despachado via Agent com `isolation: "worktree"` cria um worktree em `.claude/worktrees/agent-<id>/` + branch `worktree-agent-<id>`. Quando merge é feito, o worktree fica "locked" mas presente. Branch idem.

A lista atual tem:
- 75 worktrees locked (vários de 2-4 semanas atrás)
- ~50 branches mergeadas (worktree-agent-*, sprint/ux-*, sprint/infra-*, *-rebase, ux/onda-v-*)
- Várias ainda NÃO mergeadas (≥30) — algumas legítimas em curso, outras esquecidas

## Hipótese e validação ANTES

H1: contagem confirmada:

```bash
git worktree list | wc -l
# Esperado: ~75

git branch --merged main | grep -E "^\s+worktree-agent-|^\s+sprint/|^\s+ux/|-rebase$" | wc -l
# Esperado: ~50

git branch --no-merged main | grep -E "^\s+worktree-agent-" | wc -l
# Esperado: ~30 (atenção — podem ter trabalho não-mergeado)
```

H2: worktrees lockados têm origem de agent:

```bash
git worktree list | grep "agent-" | wc -l
# Esperado: ~70
```

## Objetivo

1. Criar `scripts/limpar_worktrees_agentes.sh`:
   - Dry-run por padrão (`--apply` para executar).
   - Para cada worktree em `.claude/worktrees/`:
     - Checa se branch está MERGED em main → propõe `git worktree remove --force <path>` + `git branch -D <branch>`.
     - Checa se branch NÃO-merged mas worktree órfão (>30d sem commit): listar com flag warning.
   - Backup do reflog: `git reflog --all > /tmp/reflog_pre_gc_<ts>.txt` antes do apply.
   - Output formato: 
     ```
     [MERGED]    worktree-agent-a08cf0d5...   branch ux/onda-v-2-12  -> DELETAR
     [NO-MERGE]  worktree-agent-a0a87d918... branch worktree-agent-a0a87d918  -> REVISAR
     ...
     Resumo: 50 a deletar, 25 a revisar
     ```
2. Adicionar `make gc-worktrees` no Makefile.
3. Pre-commit hook que avisa se há ≥50 worktrees lockados (limite higiênico).
4. Documentar processo em `docs/MANUAL_WORKTREES.md` — quando deletar, quando preservar, como recuperar trabalho de branch deletada via reflog.

## Não-objetivos

- Não deletar branches NÃO-merged sem revisão humana (potencial perda).
- Não tocar worktrees não-agent (do supervisor humano).
- Não automatizar em CI (decisão humana sempre).

## Proof-of-work runtime-real

```bash
# 1. Dry-run
./scripts/limpar_worktrees_agentes.sh
# Esperado: lista MERGED + NO-MERGE + resumo

# 2. Backup reflog
ls /tmp/reflog_pre_gc_*.txt
# Esperado: 1 arquivo

# 3. Apply
./scripts/limpar_worktrees_agentes.sh --apply
git worktree list | wc -l
# Esperado: <30 (muitos removidos)

# 4. Verificar nada quebrou
make smoke
# Esperado: 10/10
```

## Acceptance

- `scripts/limpar_worktrees_agentes.sh` criado, dry-run por padrão.
- `make gc-worktrees` no Makefile.
- Backup reflog antes do apply.
- Após apply: worktrees < 30, branches *-rebase mergeadas removidas.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (m) Branch reversível — reflog é a rede de segurança.
- (ii) Comandos git banidos — script NÃO usa `git reset --hard` nem `git clean -fd`.

---

*"Casa limpa não é casa morta; é casa onde se sabe achar as coisas." — princípio do garbage collector com bom-senso*
