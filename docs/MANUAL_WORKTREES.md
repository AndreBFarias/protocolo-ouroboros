# MANUAL_WORKTREES.md

Garbage collection de worktrees `.claude/worktrees/agent-*` e branches `worktree-agent-*`.

Documento operacional. Atualizado em 2026-05-15.

---

## Contexto

Cada `executor-sprint` despachado via Agent com `isolation: "worktree"` cria:

1. Um worktree em `.claude/worktrees/agent-<id>/`
2. Uma branch `worktree-agent-<id>`

Após merge para `main`, ambos ficam órfãos. O acúmulo polui:

- `git worktree list` (75+ entradas)
- `git branch` (ilegível)
- Disco em `.claude/worktrees/` (cada worktree pode ter ~1GB de venv duplicado)

A ferramenta canônica para limpar é `scripts/limpar_worktrees_agentes.sh`.

---

## Quando deletar

Critério principal: a branch da worktree está **mergeada em `main`**.

`git merge-base --is-ancestor refs/heads/<branch> main` retornando 0 = MERGED = seguro deletar.

Critérios secundários (para revisão humana):

- Branch NÃO-mergeada com worktree órfão > 30 dias sem commit: candidato a investigação.
- Worktree de sprint que foi REPROVADA e abandonada: deletar manualmente após confirmar com o supervisor.

---

## Quando preservar

- Worktree atual de execução. **A ferramenta auto-protege** — nunca deleta o worktree de onde foi invocada.
- Worktrees com trabalho não-mergeado que ainda fará parte de futuras sprints.
- Worktrees do supervisor humano (não-agent — em paths fora de `.claude/worktrees/agent-*`).

---

## Uso da ferramenta

### Dry-run (recomendado sempre)

```bash
./scripts/limpar_worktrees_agentes.sh
# ou
make gc-worktrees
```

Saída:

```
=== MERGED (seguro deletar) ===
  [MERGED]   /.../agent-a08cf0d5...   branch ux/onda-v-2-12  -> DELETAR
  [MERGED]   /.../agent-a128771a...   branch worktree-agent-a128771a  -> DELETAR
  ...

=== NO-MERGE (revisar antes de deletar) ===
  [NO-MERGE] /.../agent-a0a87d91...   branch worktree-agent-a0a87d91  -> REVISAR
  ...

=== AUTO-PROTEGIDO (worktree atual, nunca deletado) ===
  [SELF]     /.../agent-af7606cd...   branch worktree-agent-af7606cd  -> PRESERVADO

Resumo: 47 a deletar, 38 a revisar, 1 auto-protegido.
```

### Aplicação (deleta apenas MERGED)

```bash
./scripts/limpar_worktrees_agentes.sh --apply
```

A ferramenta:

1. Salva `git reflog --all` em `/tmp/reflog_pre_gc_<ts>.txt` antes de qualquer deleção.
2. Para cada candidato MERGED:
   - `git worktree remove --force <path>`
   - `git branch -D <branch>`
3. Auto-protege o worktree atual em duas camadas (defesa em camadas, padrão `(n)`).

### Proteger paths específicos

```bash
./scripts/limpar_worktrees_agentes.sh --apply \
    --protect=.claude/worktrees/agent-deadbeef \
    --protect=.claude/worktrees/agent-cafebabe
```

A flag `--protect=<path>` pode ser usada múltiplas vezes. Útil quando há sessões de executor-sprint vivas em outros worktrees-agente que você não quer matar acidentalmente. **Recomendado** quando rodar `--apply` do main.

### Aplicação com NO-MERGE (PERIGOSO)

```bash
./scripts/limpar_worktrees_agentes.sh --apply --include-no-merge
```

Use apenas após inspeção manual confirmar que as branches NO-MERGE não têm trabalho útil. Risco real de perda — recuperação só via reflog.

### Recusa de --apply em worktree-agente

Se você invocar `--apply` de dentro de um worktree-agente (sessão executor-sprint), o script **recusa** e sugere o comando correto a partir do main. Mecanismo evita auto-deleção da sessão em execução.

---

## Recuperação via reflog

Se acidentalmente deletou uma branch com trabalho útil:

1. Abrir o backup gerado em `/tmp/reflog_pre_gc_<ts>.txt`.
2. Localizar o último SHA da branch deletada (busca por nome da branch ou por descrição do commit).
3. Recriar a branch a partir do SHA:

```bash
# exemplo: branch deletada era worktree-agent-deadbeef, ultimo SHA 1a2b3c4
git branch worktree-agent-deadbeef 1a2b3c4
```

4. Se a branch tinha worktree e quiser recriá-lo:

```bash
git worktree add .claude/worktrees/agent-deadbeef worktree-agent-deadbeef
```

Importante: reflog default expira em 90 dias. Para recuperações mais antigas, sem chance.

---

## Comandos banidos

A ferramenta NÃO usa (padrão `(ii)` do `VALIDATOR_BRIEF.md`):

- `rm -rf` em subdir do worktree (usa `git worktree remove --force`).
- `git reset --hard` (não há necessidade).
- `git clean -fd` (não há necessidade).
- `git stash` em qualquer variante.
- `git checkout -f`.
- `git config --global`.

Substitutos canônicos:

| Banido | Substituto |
|---|---|
| `rm -rf .claude/worktrees/agent-x` | `git worktree remove --force <path>` |
| Deletar branch manualmente | `git branch -D <branch>` |

---

## Limites operacionais

Higiene recomendada:

- Manter `git worktree list \| wc -l` abaixo de 30.
- Rodar `make gc-worktrees` semanalmente e revisar o output.
- Aplicar `--apply` apenas após revisão visual da lista MERGED.
- NUNCA rodar `--apply` de dentro de um worktree agente (a ferramenta auto-protege, mas a higiene recomenda rodar a partir do repo main).

---

## Histórico

- 2026-05-15: Sprint META-GC-WORKTREES-BRANCHES — criada a ferramenta + manual. Lista inicial: 86 worktrees, 47 branches MERGED.

---

*"Casa limpa não é casa morta; é casa onde se sabe achar as coisas." — princípio do garbage collector com bom-senso*
