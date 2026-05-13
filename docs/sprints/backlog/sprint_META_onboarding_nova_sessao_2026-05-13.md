---
id: META-ONBOARDING-NOVA-SESSAO
titulo: CLAUDE.md no root + README com filosofia de graduação para nova sessão tropeçar
status: backlog
concluida_em: null
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
