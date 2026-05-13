---
titulo: Protocolo anti-armadilha v3.1 -- canônico para executor-sprint em worktree
versao: 3.1
data_promulgacao: 2026-05-13
incidente_origem: executor MOB-bridge-5 (agentId abdbc7a7) violou v3.0 REGRA 3, perdeu working tree, reconstruiu 690L da memória conversacional
autor: supervisor Opus principal
escopo: prompt obrigatório injetado em todo dispatch de executor-sprint via Agent tool com isolation worktree
---

# Protocolo anti-armadilha v3.1

Substitui a versão 3.0 (briefing canônico até 2026-05-13). Mudança principal: REGRA 3 ganhou **lista explícita de comandos banidos com justificativa de incidente real**.

## Quando aplicar

Toda vez que o supervisor Opus principal dispatcha `executor-sprint` via `Agent` tool com `isolation: "worktree"`, este protocolo é injetado **inline** no prompt como seção dedicada.

Não é negociável: executor que ignora padrão regista incidente em sprint-filha META e retrabalho.

## As 8 regras (era 6, agora 8)

### REGRA 1 — Working directory invariável
TODOS os comandos Bash devem começar com `cd $WORKTREE`. Nunca `cd` para o main path do supervisor. Worktree é seu universo isolado.

### REGRA 2 — Paths absolutos do worktree
Edit/Write/Read SEMPRE com paths absolutos do WORKTREE (`/home/.../.claude/worktrees/agent-<id>/...`). Path relativo é ambíguo entre cwd shells e tool calls.

### REGRA 3 — Comandos git banidos
**NUNCA execute estes comandos** (incidente real 2026-05-13):

| Comando | Por que banido | Substituto canônico |
|---|---|---|
| `git stash` (qualquer variante) | Empilha untracked + unstaged; em cenário paralelo perde rastro do trabalho próprio | `pytest --ignore=<arquivo>` para isolar; `git diff main..HEAD` para visualizar |
| `git reset --hard <ref>` | Descarta working tree silenciosamente | `git checkout HEAD -- <path>` cirúrgico |
| `git clean -fd` | Remove untracked sem rede de segurança | `.gitignore` local temporário |
| `git checkout -f` | Force descarta unstaged | Commit WIP primeiro, depois checkout |
| `rm -rf` de subdirs | Irreversível | Mover para `.tmp/` ou commit antes |
| `git config --global` | Polui ambiente do supervisor | `git config --local` ou variável env |

**Incidente de referência** (cite-o no commit message se for tentado):

> 2026-05-13 12:01:44 BRT, executor abdbc7a7 (MOB-bridge-5) rodou `git stash --keep-index -u --quiet` querendo "isolar mudanças do supervisor". Working tree foi limpo de arquivos untracked, incluindo seus próprios testes ainda não staged. Reconstruiu 690L de código da memória conversacional. Sprint entregou, mas com retrabalho.

### REGRA 4 — Sincronização antes do commit final
Antes do commit final:
```bash
git fetch origin main
git log HEAD..origin/main
```
Se mostrar commits, fazer rebase ou merge fast-forward. Conflito → PARE e reporte ao supervisor com diagnóstico claro. NÃO force commit com regressão.

### REGRA 5 — Fence claro entre executors paralelos
Quando 2+ executors rodam em paralelo, o supervisor declara **arquivos canônicos de cada um**. Tocar arquivo fora do seu fence = retrabalho garantido no merge.

Antes de Edit/Write em qualquer arquivo, conferir mentalmente: "este path está no meu fence declarado?" Se não, parar e perguntar.

### REGRA 6 — Commit no worktree é obrigatório
Não force-push. Não rebase para main. Não push para origin. Apenas COMMIT no seu branch local — o supervisor faz o merge.

### REGRA 7 — Verificação `git stash list` antes do commit final (NOVA em v3.1)
Antes do commit final, rodar:
```bash
git stash list
```
DEVE estar vazio. Se aparecer entrada, PARE — você violou REGRA 3 em algum momento. Reporte ao supervisor com `git stash show` da entrada para diagnóstico.

### REGRA 8 — Reportar incidentes operacionais (NOVA em v3.1)
Se durante a execução acontecer algo inesperado (working tree fica limpo sozinho, branch resetada, arquivos sumiram), PARE imediatamente e:

1. Rode `git reflog` para auditoria temporal.
2. Rode `git stash list` para verificar se há trabalho stashed.
3. Documente o evento na conclusão da spec (seção "Achados colaterais — protocolo anti-débito").
4. Reconstrua se for possível, mas reporte o evento.

A v3.0 já tinha essa expectativa implícita; a v3.1 a torna explícita.

## Histórico de incidentes

| Data | Executor | Regra violada | Custo | Resolução |
|---|---|---|---|---|
| 2026-05-13 | abdbc7a7 (MOB-bridge-5) | REGRA 3 (`git stash`) | Reconstruiu 690L | Sprint META-PROMPT-ANTI-ARMADILHA-V3-FORTALECER (esta) |

Próximos incidentes documentados aqui (anti-débito, padrão `(l)`).

## Integração com VALIDATOR_BRIEF.md

VALIDATOR_BRIEF.md (local, gitignored) tem padrão `(ii)` que referencia este arquivo. Próximos executors que receberem este protocolo via prompt podem citar a letra `(ii)` em commit messages.

---

*"Regra dita uma vez é sugestão; regra dita com incidente é lei." -- princípio da memória anti-armadilha*
