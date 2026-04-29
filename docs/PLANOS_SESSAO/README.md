# PLANOS_SESSAO — Snapshots versionados de planos em curso

Diretório que materializa o conhecimento de cada sessão Claude Code interativa em formato versionado, antes que ele evapore com queda da Anthropic ou rotação de modelo.

## Por que existe

Plan mode escreve em `~/.claude/plans/<slug>.md` que é **pessoal**, fora do repo. Outros Opus que assumam a sessão (após queda ou em outra máquina) não têm acesso. Conhecimento crítico (decisões em AskUserQuestion, achados em testes de validação, baseline numérica capturada) vive apenas no contexto da conversa Claude Code atual — se a conversa cai, evapora.

Sprint **DOC-VERDADE-01.A.0** estabeleceu este diretório como ponto canônico onde toda sessão deve materializar:

- O plano em curso (cópia do `~/.claude/plans/<slug>.md`).
- Outputs de testes de validação que produzimos.
- Decisões do dono em plan mode que afetam execução futura.
- Cruzamentos honestos entre fontes (com `grep`/`bash` que verificam alegações).

## Convenção de nome

`<YYYY-MM-DD>_<slug>.md` — data da sessão + slug curto.

Para sessões com múltiplos artefatos, sufixo:
- `<data>_<slug>.md` — plano principal.
- `<data>_<slug>_outputs.md` — outputs de teste / observações.
- `<data>_<slug>_decisoes.md` — log de decisões do dono em plan mode.

## Como um Opus que assume a sessão deve usar

Em `docs/SUPERVISOR_OPUS.md §6` (cláusula de continuidade), este diretório é leitura inicial obrigatória após queda. Ordem:

1. Leia `ls -lt docs/PLANOS_SESSAO/*.md` — ordenação por data, mais recente no topo.
2. Identifique o plano em curso pelo slug + data + `concluida_em` ausente.
3. Leia o `_outputs.md` correspondente para entender o que já foi observado/testado.
4. Confronte com `git log` da semana e `ls docs/sprints/concluidos/` para saber o que efetivamente fechou.
5. Pergunte ao dono se nada bate.

## Não delete arquivos antigos

Mesmo após o plano ser executado e movido para `docs/sprints/concluidos/`, o arquivo aqui fica. Custo de armazenamento é zero, valor de auditabilidade cresce com o tempo.

## Relacionamento com outros artefatos

| Artefato | Onde vive | Vida útil |
|----------|-----------|-----------|
| Plano ativo do Opus | `~/.claude/plans/<slug>.md` | Local, descartável |
| **Cópia versionada do plano** | **`docs/PLANOS_SESSAO/<data>_<slug>.md`** | **Permanente, versionada** |
| Sprint formal pós-execução | `docs/sprints/concluidos/sprint_<id>.md` | Permanente, versionada |
| Histórico cronológico de sessões | `docs/HISTORICO_SESSOES.md` | Permanente |
| Observações de runtime | `docs/auditorias/<tipo>_<data>.md` | Permanente |

`PLANOS_SESSAO/` cobre a janela entre "ideia em plan mode" e "sprint formal aprovada" — é o que faltava antes.
