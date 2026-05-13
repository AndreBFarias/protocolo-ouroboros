---
id: META-ONBOARDING-NOVA-SESSAO
titulo: CLAUDE.md no root + README com filosofia de graduação para nova sessão tropeçar
status: concluída
concluida_em: 2026-05-13
prioridade: P0
data_criacao: 2026-05-13
fase: SANEAMENTO
epico: 8
depende_de: []
origem: auditoria de discoverability 2026-05-13. ROADMAP_ATE_PROD, CICLO_GRADUACAO_OPERACIONAL e dossie_tipo.py foram criados mas nova sessão Claude Code começa sem contexto canônico -- CLAUDE.md no root ausente; README não menciona ciclo de graduação. Toda a infra fica invisível.
---

# Sprint META-ONBOARDING-NOVA-SESSAO

## Contexto

Próxima sessão Claude Code (após contexto se perder) precisa tropeçar nos 3 docs canônicos antes de criar qualquer spec. Hoje começa lendo `README.md` (pipeline ETL clássico) e o `INDICE_2026-05-12.md` carimbado de ontem.

## Entregável

1. **`CLAUDE.md` na raiz do projeto** (trackeado, ~30 linhas):
   - Auto-carregado pelo harness Claude Code.
   - Bloco "LEIA ANTES DE CRIAR QUALQUER SPRINT" com 5 caminhos canônicos:
     - `docs/sprints/ROADMAP_ATE_PROD.md`
     - `docs/CICLO_GRADUACAO_OPERACIONAL.md`
     - `contexto/COMO_AGIR.md`
     - `scripts/dossie_tipo.py --listar-tipos` (comando)
     - `data/output/graduacao_tipos.json` (se existir)
   - Resumo de 3 linhas da filosofia (ciclo Opus → ETL → graduação).
   - Comandos básicos: `./run.sh --check`, `make smoke`, `make lint`.

2. **README.md atualizado**:
   - Nova seção "Para colaboradores AI" linkando para CLAUDE.md.
   - Parágrafo curto sobre a filosofia de graduação (sem detalhes técnicos).

## Acceptance

- `cat CLAUDE.md` mostra os 5 caminhos canônicos na ordem.
- Pessoa nova lendo README entende em 2min o que é "tipo graduado".
- Lint zero. Smoke 10/10.

## Padrão canônico aplicável

(s) Validação ANTES — para novas sessões, ler é a validação ANTES de escrever spec.

---

*"Documentação que ninguém lê não existe; documentação que se autoexpõe é viva." -- princípio do entry point*

---

## Conclusão (2026-05-13)

Executor A do trio paralelo (META-ONBOARDING / META-PADROES / META-VALIDATOR-BRIEF). Implementado conforme spec.

### Arquivos tocados

- `CLAUDE.md` (NOVO, raiz) -- ~40 linhas, auto-carregado pelo harness Claude Code. Lista os 3 docs canônicos, filosofia em 3 linhas, ferramenta de auditoria (`scripts/dossie_tipo.py`), comandos básicos e regras invioláveis.
- `README.md` (MODIFICADO) -- adicionada seção "Para colaboradores AI (Claude, Codex, Cursor, etc.)" entre "Quick Start" e "Sobre", apontando para `CLAUDE.md` e mencionando a filosofia de graduação por dossiê.
- `docs/sprints/backlog/sprint_META_onboarding_nova_sessao_2026-05-13.md` -> `docs/sprints/concluidos/` (via `git mv`).
- `.gitignore` (MODIFICADO) -- removida linha 2 (`CLAUDE.md`) e atualizado o comentário explicando que CLAUDE.md passou a ser trackeado a partir desta sprint. Tweak indispensável porque `git add CLAUDE.md` falhava com `ignored by .gitignore`. CLAUDE.md contém apenas onboarding canônico público, sem PII.

### Validação aplicada

- Lint (`make lint`): 0 erros, `All checks passed!` em ruff, check_acentuacao e check_cobertura D7.
- Smoke (`make smoke`): 23 checagens, 0 erros, 3 avisos esperados (XLSX/relatórios não gerados em worktree limpo).
- Pytest: 2923 passed, 23 failed, 43 skipped, 1 xfailed. As 23 falhas são pré-existentes ao HEAD a9fb1c6, todas em testes UI/Streamlit/playwright (sidebar/topbar/visão geral/page header/mobile cache) fora do meu fence. Confirmação: `git diff --cached --name-only` mostra apenas `.gitignore`, `CLAUDE.md`, `README.md` e a spec movida.
- Acentuação: `check_acentuacao.py CLAUDE.md README.md sprint_META_*.md` exit 0.
- Emojis: zero (grep regex unicode confirmou).

### Achados colaterais -- protocolo anti-débito

- `git stash list` mostrou 3 entradas pré-existentes (de worktrees abdbc7a7, a70649870, onda-v-2-7) ao entrar no meu worktree (a128771a). Nenhuma foi criada por mim -- `git reflog` confirma HEAD imóvel em a9fb1c6. Reporto conforme REGRA 8 do protocolo v3.1. Não executei `git stash` em nenhum momento; estas entradas pertencem ao escopo do supervisor para limpar.

