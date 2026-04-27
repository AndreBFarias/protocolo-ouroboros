# ADR-21 -- Fusão Ouroboros + Controle de Bordo (coabitação canônica)

**Data:** 2026-04-26
**Status:** PROPOSTO (aguarda aprovação humana)
**Origem:** Auditoria 2026-04-26 (`docs/AUDITORIA_2026-04-26.md` + auditoria do agente Opus em `docs/auditoria_vault_2026-04-26.md`)
**Referência:** Sprint 94 (`docs/sprints/backlog/sprint_94_*.md`) e ADR-18 (coabitação estrutural).

## Contexto

Existem hoje dois sistemas paralelos no espaço pessoal do casal:

- `protocolo-ouroboros/` (monorepo de código, ~26.604 LOC em `src/`, 1.530 testes, pipeline ETL financeiro maduro com 22 extratores).
- `~/Controle de Bordo/` (vault Obsidian PARA, 325 MB, 1.439 notas .md, motor próprio de inbox em `.sistema/scripts/`, infra de gauntlet + backups + emoji guardian).

A Sprint 70 (adapter de borda) estabeleceu coabitação read-only: o ouroboros lê `Inbox/` do vault e roteia financeiros para `data/raw/`. O `sync_rico` (Sprint 71) escreve de volta em `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/`. Mas o futuro do projeto (Sprint 94, "Central de Controle de Vida") exige uma decisão arquitetural mais firme: qual lado é canônico?

## Decisão

**`protocolo-ouroboros/` é a raiz canônica de execução. `~/Controle de Bordo/` é a camada de view/captura humana.**

- Toda lógica de ingestão, extração, transformação, persistência (XLSX + grafo SQLite) e dashboard fica no monorepo.
- Toda nota livre, edição humana, plugins Obsidian (Dataview, Templater, Calendar), templates de daily/sprint/conceito ficam no vault.
- O **contrato de I/O** entre os dois é restrito a:
  - **Vault -> Ouroboros (leitura):** `~/Controle de Bordo/Inbox/` (financeiros são puxados pelo adapter Sprint 70).
  - **Ouroboros -> Vault (escrita):** `~/Controle de Bordo/Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/`.
  - Nenhum outro caminho é tocado por escrita cross-projeto.

## Migrações imediatas

**3 módulos do vault para o monorepo:**

| De (vault) | Para (monorepo) | Motivo |
|------------|-----------------|--------|
| `.sistema/scripts/similarity_grouper.py` (~230L) | `src/intake/similarity.py` | Jaccard puro, exclusivo, útil para deduplicar notas geradas pelo `sync_rico` |
| `.sistema/lib/wikilinks.py` (~188L) | `src/utils/wikilinks.py` | Regex de wikilinks, útil para `sync_rico` validar referências |
| `.sistema/scripts/emoji_guardian.py` (~376L) | `scripts/hooks/emoji_guardian.py` | Substitui heurística atual; integra ao pre-commit |

## Deletes do vault (após congelar a fusão)

| Caminho | Motivo |
|---------|--------|
| `Projetos/Protocolo Ouroboros/` (clone fossilizado, 3 .md divergem mtime 2026-04-14) | Documentação canônica vive no monorepo; clone confunde |
| `.sistema/scripts/_desativados/` (6 protótipos) | Mortos formalmente |
| `.sistema/scripts/ocr_detector.py` | Path obsoleto `~/Desenvolvimento/Financas/`, substituído pelo intake do Ouroboros |
| `.sistema/scripts/document_creator.py` | Substituído pelo `sync_rico.py` que opera no grafo |
| `.sistema/backups/2026-04-08/18-45-33__home_andrefarias_Desenvolvimento_Nyx-Code_openclaud_*` (76 .tsx/.ts) | Lixo de backup cross-projeto |

## Mantém no vault sem migrar

| Caminho | Razão |
|---------|-------|
| `.sistema/scripts/inbox_processor.py` (492L) | Processa NOTAS .md em `Inbox/`, não compete com financeiro |
| `.sistema/scripts/content_detector.py` (386L) | Categoriza notas livres por keywords |
| `.sistema/scripts/gauntlet/gauntlet.py` (1.300L) | Validador 8-fases especializado em vault, ortogonal ao `make gauntlet` do monorepo |
| `.sistema/scripts/health_check.py`, `verificar_*` | Saúde do vault |
| `.sistema/scripts/vault_backup.py`, `.sistema/lib/safe_io.py`, `.sistema/lib/protecao.py`, `.sistema/lib/config_loader.py`, `.sistema/scripts/vault_logger.py` | Infra interna |
| `.sistema/scripts/export_to_other_devices.py` | Depende de `devices.yaml`, escopo do vault |

## Resoluções pendentes

1. **3 duplicatas SHA-idênticas raiz vault** (`QUESTIONARIO_VIDA_COMPLETO.md`, `PLANO_FINANCEIRO_2026.md`, `PLANO_FINANCEIRO_ANDRE_VITORIA.md`). Decidir: manter no monorepo `docs/` como fonte canônica e deletar do vault, OU criar wikilink/symlink.
2. **Vault precisa de remote git próprio** (hoje commit único `40b8afe` sem origin). Recomendado: criar repo PRIVADO no GitHub do casal. Destrava CI hooks (gauntlet vault, emoji guardian) sem depender de sync local.
3. **Política de retenção em `.sistema/backups/`**: hoje captura cross-projeto (Hefesto, Nyx-Code, ouroboros worktrees). Recomendar: backups > 30 dias movem para `Arquivo/` (já gitignored e syncignored) ou são deletados.
4. **Variável de ambiente `BORDO_DIR`** continua sendo o único contrato de path entre os dois projetos. Documentar no README.

## Trade-offs aceitos

- **Duplicação intencional de logger e config-loader** (cada lado tem o seu, simples; não vale fundir).
- **Vault não vai pro GitHub do Ouroboros** (privacidade pessoal); precisa de remote próprio.
- **Backups cross-projeto do `vault_backup.py` ficam**, sob política de retenção.
- **Obsidian permanece editor livre** -- ouroboros não substitui interface de edição humana.

## Alternativa rejeitada

"Fundir tudo no monorepo, vault vira só `data/raw/notes/`."

Rejeitada porque:
1. Obsidian precisa ser raiz própria pra plugins funcionarem.
2. PII pessoal do casal não deve misturar com repo de código (mesmo privado).
3. Vault tem 1.439 notas + 159 MB de Arquivo/ que não pertencem a um repo de código.

## Sequência de execução (5 commits sugeridos)

1. **Commit 1 (`feat: ADR-21 + relatório auditoria`)**: este ADR + `docs/AUDITORIA_2026-04-26.md` + `docs/auditoria_vault_2026-04-26.md` + `docs/auditoria_etl_2026-04-26.md`.
2. **Commit 2 (`feat: migrar similarity_grouper do vault`)**: `src/intake/similarity.py` + testes.
3. **Commit 3 (`feat: migrar wikilinks do vault`)**: `src/utils/wikilinks.py` + testes.
4. **Commit 4 (`feat: migrar emoji_guardian como hook`)**: `scripts/hooks/emoji_guardian.py` + integração `pre-commit-check.sh`.
5. **Commit 5 (`chore: limpar vault pós-fusão`)**: deleções listadas em §3 (executado pelo supervisor humano com confirmação por bash).

Cada commit passa lint + smoke independentemente.

## Validação ponta-a-ponta

Após os 5 commits:
- `make lint` verde no monorepo.
- `make smoke` 8/8 contratos OK.
- `pytest tests/test_intake_similarity.py tests/test_utils_wikilinks.py` -- ambos novos verdes.
- Git no vault: `git status` mostra somente as deleções confirmadas; remote OUR pessoal aceita push.
- `find ~/Controle\ de\ Bordo -name "*.tsx" | wc -l` retorna 0 (lixo Nyx-Code limpo).
- `grep "Financas" ~/Controle\ de\ Bordo/.sistema/scripts/` vazio (`ocr_detector.py` deletado).

## Status para Sprint 94 (OMEGA)

Sprint 94 já tem spec completa de fusão por domínio (saúde 94a, identidade 94b, profissional 94c, acadêmico 94d, busca cross 94e, mobile 94f). **Esta ADR-21 cumpre o requisito `acceptance_criteria: ADR-21 criado formalizando Modelo B`** da Sprint 94 spec. A Sprint 94 fica desbloqueada para execução por domínios (12-18 meses, P3 estratégica).

---

*"A coabitação clara é o caminho mais curto entre dois sistemas." -- princípio anti-fusão-bagunçada*
