# Reescrita das 7 LLM-* + AUDITOR-01 sob ADR-13 — registro permanente

> Materializado retroativamente em 2026-04-29 pela melhoria M3 da Sprint DOC-VERDADE-01. A Sprint REVISAO-LLM-ONDA-01 foi executada em 2026-04-28 (commit `5e87caa`), mas o **plano de reescrita em si** vivia apenas no contexto da conversa Claude Code daquela sessão. Outro Opus em clone fresh não tinha como reconstruir a lógica de cada substituição. Este arquivo cobre a lacuna.

## Contexto

Após sessão de execução autônoma, ao iniciar Onda 2 do plan `pure-swinging-mitten`, o Opus principal detectou conflito direto:

- **ADR-13** (Supervisor Artesanal via Claude Code): declara explicitamente NÃO HAVERÁ dependência Python `anthropic`, `src/llm/` NÃO DEVE EXISTIR, supervisor é Claude Code via browser (sessão interativa).
- **Specs LLM-01..07 e AUDITOR-01** (criadas em 2026-04-29 com o plan): falavam em `pip install anthropic`, `src/llm/supervisor.py`, `cost_tracker`, `ANTHROPIC_API_KEY`, cache LRU programático.

Aplicar literalmente as specs LLM-* violaria ADR-13. Solução: **reescrever cada uma preservando a intenção** (cobertura por LLM, proposições, auditoria, métricas de autossuficiência) mas **trocando o mecanismo** de "API programática" para "Claude Code interativo + arquivos versionados".

## Mapeamento canônico da reescrita

### LLM-01 → LLM-01-V2 — Bootstrap de propostas via Claude Code

**Antes (refutado por ADR-13)**:
- `src/llm/supervisor.py` + `cost_tracker.py` + `anthropic>=0.40` em pyproject.
- `Supervisor.chamar()` retorna resposta + custo SQLite.

**Depois**:
- Template Markdown `docs/propostas/_template.md` com frontmatter (id, tipo, hipotese, evidencia, decisao_humana, sha).
- Script `scripts/supervisor_contexto.sh` que dumpa estado do projeto.
- Skill `/auditar-cobertura` (ver LLM-04-V2).

### LLM-02 → LLM-02-V2 — Proposição de extrator via Edit

**Antes**: `supervisor.propor_extractor()` quando classifier=None → spec auto.

**Depois**: Quando `make conformance-<tipo>` retorna exit 1 e tipo não tem extrator, supervisor (Opus interativo) abre `docs/propostas/extracao/<tipo>_<data>.md` via Edit tool, com hipótese + plano + sub-spec sugerida. Skill `/propor-extrator` automatiza pré-popular.

### LLM-03 → LLM-03-V2 — Proposição de regra de categoria via Edit

**Antes**: `supervisor.propor_regra()` cria YAML em `mappings/proposicoes/`.

**Depois**: Mesma rota mas escrita pelo Opus principal via Edit tool durante sessão. Diretório `mappings/proposicoes/` permanece (já é convenção de ADR-13:50).

### LLM-04 → LLM-04-V2 — Auditor via skill `/auditar-cobertura`

**Antes**: `supervisor.auditor()` Modo 2; relatório quinzenal automático.

**Depois**: Skill `/auditar-cobertura` (criada em `.claude/skills/auditar-cobertura/SKILL.md`) recebe período como arg e dispara análise: lê `data/output/grafo.sqlite`, compara com `mappings/categorias.yaml`, gera relatório em `docs/auditorias/cobertura_<periodo>.md`. Humano roda manualmente quando quiser.

### LLM-05 → LLM-05-V2 — Diff de proposições no Revisor 4-way

**Antes**: UI no Revisor para aceitar/rejeitar proposições LLM.

**Depois**: Adicionar tab "Proposições" em `revisor.py` listando arquivos `.md` em `mappings/proposicoes/` + `docs/propostas/`. Botões: aprovar (move para destino final), rejeitar (move para `docs/propostas/_rejeitadas/`).

### LLM-06 → LLM-06-V2 — SHA-guard de propostas

**Antes**: Hash garante que proposta rejeitada com mesmo conteúdo não volta.

**Depois**: Mesma estratégia técnica, implementada como check em `scripts/check_propostas_rejeitadas.py`.

### LLM-07 → LLM-07-V2 — Métricas de autossuficiência (ADR-09)

**Antes**: Métricas % determinístico vs LLM no dashboard.

**Depois**: Mesmo conceito, fonte da métrica: "% determinístico" = nodes com `metadata.fonte: yaml`; "% via supervisor" = nodes com `metadata.fonte: supervisor`. Meta = 100% determinístico (cada proposta aprovada vira regra YAML; "via supervisor" decai).

### AUDITOR-01 → /auditar-cobertura (skill)

**Antes**: Subagent dedicado de relatório de cobertura por pessoa.

**Depois**: Já contemplado em LLM-04-V2 (skill `/auditar-cobertura`). Spec AUDITOR-01 absorvida.

## Princípio canônico estabelecido

**Mecanismo central**: supervisor (Opus principal interativo) abre propostas via Edit tool em `mappings/proposicoes/` ou `docs/propostas/`. Aprovação humana via tab Revisor (LLM-05-V2 futuro) ou edit manual + commit. **Custo marginal zero** (assinatura Claude Max já paga).

**Implementação até hoje**:

| Sub-sprint | Status | Commit |
|------------|--------|--------|
| LLM-01-V2 (template + scripts) | CONCLUÍDA | `bc42a6b` |
| LLM-02-V2 (skill /propor-extrator) | CONCLUÍDA | `30da12f` |
| LLM-04-V2 (skill /auditar-cobertura) | CONCLUÍDA | `f091558` |
| LLM-03-V2 (proposição regra categoria) | backlog | — |
| LLM-05-V2 (tab proposições no Revisor) | backlog | — |
| LLM-06-V2 (SHA-guard) | backlog | — |
| LLM-07-V2 (métricas autossuficiência) | backlog | — |

Specs antigas (LLM-01..07 + AUDITOR-01) movidas para `docs/sprints/arquivadas/` em `5e87caa`.

## Continuidade — para Opus que assumir sessão

Se você for um Opus que precisa entender por que existem specs `LLM-XX-V2` em vez das originais:

1. Leia `docs/adr/ADR-13-supervisor-artesanal-via-claude-code.md`.
2. Leia este arquivo.
3. Veja `docs/sprints/concluidos/sprint_revisao_llm_onda_01_reescrita_sob_adr_13.md` (a spec da Sprint REVISAO-LLM em si).
4. Veja `docs/SUPERVISOR_OPUS.md §1` (regra "supervisor sou eu, não cliente API").

**Nunca** crie `src/llm/` nem instale `anthropic`. Esta foi a primeira armadilha histórica registrada em SUPERVISOR_OPUS.md §9.

---

*"Reescrever sob constraint é mais honesto que ignorar a constraint." — princípio do refactor de specs sob ADR vigente*
