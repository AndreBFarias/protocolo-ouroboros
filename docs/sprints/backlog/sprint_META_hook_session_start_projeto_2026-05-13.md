---
id: META-HOOK-SESSION-START-PROJETO
titulo: Hook session-start local do projeto que injeta estado vivo no contexto inicial
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-13
fase: OPERACIONAL
epico: 2
depende_de:
  - META-ONBOARDING-NOVA-SESSAO (CLAUDE.md deve existir primeiro)
origem: auditoria 2026-05-13. .claude/hooks/ no projeto está vazio. Briefing inicial só vem dos hooks globais do dono (~/.claude/hooks/), que não conhecem o estado de graduação dos tipos nem o épico ativo. Nova sessão começa sem contexto vivo.
---

# Sprint META-HOOK-SESSION-START-PROJETO

## Contexto

Cada nova sessão Claude Code dispara hooks no diretório do projeto. Hoje `.claude/hooks/` existe mas só contém `worktrees/`. Briefing inicial é genérico (vem de `~/.claude/hooks/session-start-briefing.py`, global).

Para que nova sessão comece sabendo: estado de graduação dos tipos, qual épico do ROADMAP está ativo, sprints em curso -- precisa de hook próprio do projeto.

## Entregável

1. **`.claude/hooks/session-start-projeto.py`** (trackeado):
   - Hook `SessionStart` registrado em `.claude/settings.json` (ou local equivalente).
   - Lê `data/output/graduacao_tipos.json` (se existir) e injeta summary: "X tipos GRADUADOS, Y CALIBRANDO, Z PENDENTE".
   - Lê `docs/sprints/ROADMAP_ATE_PROD.md` e identifica épico ativo (pelo status das sub-sprints em backlog/).
   - Lista 3 documentos canônicos a ler.
   - Injeta no contexto inicial via `additionalContext`.

2. **`.claude/settings.json` (local OU trackeado)**:
   - Registrar o hook na seção `hooks.SessionStart`.
   - Decidir se vai trackeado ou stays local.

3. **Testes** em `tests/test_session_start_projeto.py` simulando payload do hook + verificando output.

## Acceptance

- Nova sessão `claude` no diretório do projeto recebe briefing automático com estado vivo dos tipos.
- Briefing inclui link para CLAUDE.md + ROADMAP + CICLO_GRADUACAO.
- ≥4 testes verdes.
- Falha-soft (sem `graduacao_tipos.json` = mensagem genérica).

## Padrão canônico aplicável

(n) Defesa em camadas -- briefing automatizado complementa CLAUDE.md (que é manual leitura). Duas camadas garantem que nova sessão recebe contexto.

---

*"Hook é a primeira voz que a sessão escuta; deve dizer onde está o mapa." -- princípio do anfitrião*
