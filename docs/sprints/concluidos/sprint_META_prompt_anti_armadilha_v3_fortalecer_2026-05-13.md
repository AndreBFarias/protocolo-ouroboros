---
id: META-PROMPT-ANTI-ARMADILHA-V3-FORTALECER
titulo: Fortalecer prompt anti-armadilha v3 com lista de comandos banidos e incidentes reais
status: concluída
concluida_em: 2026-05-13
prioridade: P2
data_criacao: 2026-05-13
fase: META
depende_de: []
esforco_estimado_horas: 1
origem: incidente do executor MOB-bridge-5 (abdbc7a) em 2026-05-13 -- executor rodou `git stash --keep-index -u --quiet` violando REGRA 3, perdeu working tree, reconstruiu trabalho da memória conversacional. Sprint entregou mesmo assim mas com retrabalho.
---

# Sprint META-PROMPT-ANTI-ARMADILHA-V3-FORTALECER

## Contexto

O protocolo anti-armadilha v3 (briefing canônico do supervisor Opus principal) tem 6 regras. A REGRA 3 diz:

> 3. NUNCA execute `git stash`. Para limpar temporariamente: commit WIP ou `git checkout HEAD -- <path>`.

Mas o executor MOB-bridge-5 (agentId `abdbc7a7a2c6ce022`) rodou `git stash --keep-index -u --quiet` em 2026-05-13 ~12:01 BRT. Análise via grep do transcript em `/tmp/claude-1000/.../tasks/abdbc7a7a2c6ce022.output`:

1. Executor estava confiante na sua hipótese (Validação ANTES com grep correto).
2. Após primeiro passe de testes verdes, ele tentou isolar falhas pré-existentes via `git stash`.
3. Working tree ficou limpa após operação subsequente.
4. Executor reconstruiu integralmente trabalho da memória conversacional ("Entendido — não usarei stash").
5. Sprint entregue com sucesso (commit `e85270a`), mas com retrabalho não-trivial.

Felizmente, a memória conversacional do Claude Opus 4.7 (1M ctx) é capaz de reconstrução. Em executor menos capaz, isso seria perda de trabalho.

## Hipótese

O texto atual da REGRA 3 é declarativo mas não suficientemente forte para superar treino do modelo que considera `git stash` ferramenta canônica de "salvar trabalho temporário".

## Objetivo

Reescrever a REGRA 3 do prompt anti-armadilha v3 com:

1. **Lista explícita de comandos banidos** (não só `git stash`):
   ```
   COMANDOS BANIDOS (NUNCA executar dentro do worktree):
   - git stash (incluindo --keep-index, -u, push, etc.)
   - git reset --hard (a qualquer ref)
   - git clean -fd (limpa untracked)
   - git checkout -f (force checkout descarta unstaged)
   - rm -rf de qualquer subdiretório do worktree
   ```

2. **Padrões substitutos canônicos** para cada cenário:
   - "Quero isolar mudanças do supervisor das minhas" → `git diff main..HEAD` ou rodar pytest com `--ignore=<arquivo>`.
   - "Quero rodar gauntlet sem meus arquivos novos" → criar branch temporário, fazer rebase interativo.
   - "Tenho arquivos untracked que querem confundir" → adicionar pattern ao `.gitignore` local temporário.

3. **Incidente de referência inline**: citar o caso de 2026-05-13 como exemplo concreto. "Quem violou esta regra: executor abdbc7a7 em 2026-05-13, perdeu working tree, teve que reconstruir 690L de código a partir da memória conversacional."

4. **Verificação automática pelo protocolo**: adicionar como REGRA 7 — antes do commit final, rodar `git stash list` e abortar se aparecer qualquer entrada.

## Onde aplicar

Briefing canônico do supervisor Opus principal está em memória conversacional (não em arquivo). Esta sprint produz texto canônico que o supervisor copia para o briefing da próxima sessão.

Texto pode também virar entrada no `VALIDATOR_BRIEF.md` (padrão `(ii)` novo).

## Proof-of-work esperado

Próxima sprint substantiva paralela (>= 2 executors) executa SEM nenhum `git stash` no transcript. Conferir via grep:

```bash
grep "git stash" /tmp/claude-1000/.../tasks/<agentId>.output 2>/dev/null && echo "VIOLOU" || echo "OK"
```

Meta: 0 violações em 5 dispatches consecutivos.

## Padrão canônico aplicável

- (dd) Stash chain hazard — formalizado como padrão; esta sprint fortalece a defesa.

---

*"Regra dita uma vez é sugestão; regra dita com incidente é lei." — princípio da memória anti-armadilha*

## Conclusão (2026-05-13)

Entregue na onda paralela das 5 sprint-filhas:

1. **Documento canônico trackeado**: `contexto/PROTOCOLO_ANTI_ARMADILHA_V3_1.md` — 8 regras (era 6), tabela de comandos banidos com substitutos, incidente real inline.
2. **Padrão `(ii)` adicionado ao VALIDATOR_BRIEF.md** (local, gitignored) referenciando o protocolo + comandos banidos + verificação obrigatória `git stash list` antes do commit final.
3. **Memória persistente atualizada**: `feedback_protocolo_anti_armadilha_v3_1.md` no diretório de memória do Claude Code, indexada em `MEMORY.md`.
4. **Aplicação imediata**: os 2 executors despachados nesta mesma onda paralela (PROPOSTAS-GC e LINKAR-PIX-TRANSACAO) receberam o protocolo v3.1 inline no prompt, incluindo a tabela de comandos banidos com justificativa do incidente.

### Métricas da sessão

- 1 arquivo novo trackeado (`contexto/PROTOCOLO_ANTI_ARMADILHA_V3_1.md`, 99 linhas).
- 1 entrada nova no VALIDATOR_BRIEF.md (padrão `(ii)`).
- 1 memória nova + atualização do MEMORY.md.
- Spec movida para `docs/sprints/concluidos/`.

### Próximos passos (registrados, não bloqueantes)

- Adicionar a tabela de comandos banidos como **hook PreToolUse** que detecta `git stash` em executors e bloqueia. Mais firme que prompt. Sprint-filha futura.
- Documentar incidentes futuros no `## Histórico de incidentes` do protocolo v3.1 (padrão `(l)`).
