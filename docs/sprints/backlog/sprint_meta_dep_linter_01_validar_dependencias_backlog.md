---
id: META-DEP-LINTER-01-VALIDAR-DEPENDENCIAS-BACKLOG
titulo: Sprint META-DEP-LINTER-01 — Linter de dependências entre specs em backlog
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint META-DEP-LINTER-01 — Linter de dependências entre specs em backlog

**Origem**: achado da terceira sessão de validação (DOC-VERDADE-01.F, 2026-04-29). Spec MICRO-01 declara `Depende de: DOC-02, DOC-19` (ambas em backlog), mas não há mecanismo que avise antes de começar a executar. Risco: Opus começa MICRO-01, descobre no meio que dependência não fechou, ramifica improvisado.
**Prioridade**: P3
**Onda**: 1 (anti-migué metodológico)
**Esforço estimado**: 3h
**Depende de**: META-CÓDIGO-RELACIONADO-01 (mesma família — convém fechar antes para reusar pattern)

## Problema

Cada spec em `docs/sprints/backlog/*.md` tem campo `**Depende de**: <slug ou nenhuma>`. Mas:

- Não há linter que cruze esse grafo de dependência antes de despachar execução.
- Sprint pode ser começada com dependência ainda em backlog (não fechada).
- Ramificação improvisada no meio da execução é custo real (visto em DOC-VERDADE-01.F: terceira sessão propôs MICRO-01a/01b para contornar bloqueio descoberto na hora).

## Hipótese

`scripts/lint_dependencias_backlog.py` que:
1. Para cada spec em backlog, lê campo `Depende de`.
2. Resolve cada dependência: fechada (existe em `concluidos/`) ou aberta (existe em `backlog/`).
3. Emite `docs/auditorias/dependencias_<data>.md` com:
   - Specs com **dependência aberta** (não pode executar agora — bloqueada).
   - Specs com **dependência fechada** (livre para executar).
   - Specs sem dependência declarada.
   - Ciclos de dependência se houver (improvável, mas o linter pega).

`make sprint-disponiveis` chama o linter e lista as desbloqueadas, ordenadas por payoff (cruza com prioridade no SPRINTS_INDEX).

## Implementação proposta

1. `scripts/lint_dependencias_backlog.py` (~150L) com argparse: `--executar` grava relatório, sem flag = stdout.
2. Target `make sprint-disponiveis` no Makefile.
3. Documentar em `docs/SUPERVISOR_OPUS.md §3` tabela "pergunta → skill": "Qual sprint posso executar agora?" → `make sprint-disponiveis`.
4. Eventual integração com SPRINTS_INDEX: regenerar tabela com coluna "status dependência" anotada.

## Acceptance criteria

- Linter funcional contra estado real (82 specs em backlog).
- Pelo menos 5 sprints com dependência aberta identificadas.
- Pelo menos 10 sprints sem dependência ou com dependência fechada (livres).
- Sem ciclos detectados (ou se houver, virar achado-bloqueio).

## Proof-of-work

`python scripts/lint_dependencias_backlog.py` exit 0 com tabela visível. `make sprint-disponiveis` mostra sprint ordenadas.

---

## Papel do supervisor (Opus Claude Code)

Conforme ADR-13 e `docs/SUPERVISOR_OPUS.md`, eu (Opus principal nesta sessão interativa) executo esta sprint metodológica:

1. Crio o script standalone em `scripts/`.
2. Adiciono target no Makefile.
3. Atualizo SUPERVISOR_OPUS.md §3 com nova entrada na tabela skill.
4. Rodo o linter contra backlog real e registro relatório como proof-of-work.

**NÃO há chamada Anthropic API.** Regra inviolável (ADR-13).

## Gate anti-migué

9 checks padrão.
