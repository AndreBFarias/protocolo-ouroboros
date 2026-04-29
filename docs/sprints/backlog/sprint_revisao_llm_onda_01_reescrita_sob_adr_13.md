---
concluida_em: 2026-04-28
---

# Sprint REVISAO-LLM-ONDA-01 — Reescrita das 7 LLM-* + AUDITOR-01 sob ADR-13

**Origem**: detectado pela sessão Opus principal 2026-04-28 ao iniciar o plan `pure-swinging-mitten` (FASE 3 §Onda 2 do prompt do dono).
**Prioridade**: P0 (bloqueia Onda 2 inteira).
**Onda**: 1 (revisão metodológica antes de Onda 2).
**Esforço estimado**: 2h (redigir reescritas) + ?h por sub-sprint subsequente.
**Depende de**: nenhuma.

## Problema

Conflito direto entre:

- **ADR-13** (Supervisor Artesanal via Claude Code) — vigente desde 2026-04 e atualizada em 2026-04-28: declara explicitamente que **NÃO HAVERÁ** dependência Python `anthropic`, que **`src/llm/` NÃO DEVE EXISTIR**, e que o supervisor é **Claude Code via browser** (sessão interativa).
- **Specs LLM-01..07 e AUDITOR-01** (criadas em 2026-04-29 com o plan): falam em `pip install anthropic`, `src/llm/supervisor.py`, `cost_tracker`, `ANTHROPIC_API_KEY`, cache LRU programático.

Aplicar literalmente as specs LLM-* da forma como estão **violaria ADR-13**, introduziria dependência externa paga, e contradiz o princípio de soberania humana sobre cada proposição.

## Hipótese

Reescrever cada uma das 8 specs (LLM-01..07 + AUDITOR-01) preservando **a intenção** (cobertura por LLM, proposições, auditoria, métricas de autossuficiência) mas trocando o **mecanismo** de "API programática" para "Claude Code interativo + arquivos versionados".

## Mapeamento da reescrita

### LLM-01 → LLM-01-V2 — Bootstrap de propostas via Claude Code

**Antes (refutado por ADR-13):**
- `src/llm/supervisor.py` + `cost_tracker.py` + `anthropic>=0.40` em pyproject.
- `Supervisor.chamar()` retorna resposta + custo SQLite.

**Depois:**
- Template Markdown `docs/propostas/_template.md` com frontmatter (id, tipo, hipotese, evidencia, decisao_humana).
- Script `scripts/supervisor_contexto.sh` (já previsto em ADR-13:51) que dumpa estado do projeto em formato legível para a sessão Claude Code começar pronta.
- Skill `/auditar-cobertura` (Claude Code) já permite invocar análise sob demanda.

**Acceptance:**
- Template publicado.
- Script executável e testado.
- Não introduz `anthropic` em deps.

### LLM-02 → LLM-02-V2 — Proposição de extrator via output Markdown

**Antes:**
- `supervisor.propor_extractor()` quando classifier=None → spec auto em backlog/.

**Depois:**
- Quando `make conformance-<tipo>` retornar exit 1 e o tipo não tem extrator, o Opus principal (sessão interativa) abre `docs/propostas/extracao_<tipo>_<data>.md` via Edit tool, com:
  - Hipótese de regex/layout.
  - Plano de extração.
  - Sub-spec sugerida em `backlog/sprint_doc_<X>_*.md`.
- Humano revisa e dispara `/sprint-ciclo sprint_doc_<X>_*.md` quando pronto.

### LLM-03 → LLM-03-V2 — Proposição de regra de categoria via Edit em mappings/proposicoes/

**Antes:**
- `supervisor.propor_regra()` cria YAML em `mappings/proposicoes/`.

**Depois:**
- Mesma rota mas escrita pelo Opus principal via Edit tool durante sessão. O diretório `mappings/proposicoes/` permanece (já é convenção de ADR-13:50).

### LLM-04 → LLM-04-V2 — Auditor via skill `/auditar-cobertura`

**Antes:**
- `supervisor.auditor()` Modo 2; relatório quinzenal automático.

**Depois:**
- Skill `/auditar-cobertura` (a criar em `.claude/skills/auditar-cobertura.md`) recebe um período como arg e dispara análise: lê `data/output/grafo.sqlite`, compara com `mappings/categorias.yaml`, gera relatório em `docs/auditorias/cobertura_<periodo>.md`.
- Humano roda manualmente quando quiser auditar (frequência discrição do dono).

### LLM-05 → LLM-05-V2 — Diff de proposições no Revisor 4-way

**Antes:**
- UI no Revisor para aceitar/rejeitar proposições LLM.

**Depois:**
- Adicionar tab "Proposições" no `revisor.py` listando arquivos `.md` em `mappings/proposicoes/` + `docs/propostas/`. Botões: aprovar (move para `mappings/<final>.yaml` ou `docs/sprints/backlog/`) e rejeitar (move para `docs/propostas/_rejeitadas/<id>.md` com motivo).

### LLM-06 → LLM-06-V2 — SHA-guard de propostas

**Antes:**
- Hash garante que proposta rejeitada com mesmo conteúdo não volta.

**Depois:**
- Mesma estratégia técnica, implementada como check em `scripts/check_propostas_rejeitadas.py`. Antes de gerar uma proposta nova, calcular sha256 do conteúdo principal (hipótese normalizada). Se matchar SHA já em `_rejeitadas/`, abortar.

### LLM-07 → LLM-07-V2 — Métricas de autossuficiência (ADR-09)

**Antes:**
- Métricas % determinístico vs LLM no dashboard.

**Depois:**
- Mesmo conceito, mas a fonte da métrica é diferente:
  - "% determinístico" = nodes do grafo cuja extração veio de classifier YAML.
  - "% via supervisor" = nodes que tiveram pelo menos uma aresta ou metadata vinda de proposta aprovada (campo `metadata.fonte: supervisor`).
- Dashboard mostra tendência ao longo do tempo: meta = 100% determinístico (= ADR-09).

### AUDITOR-01 → /auditar-cobertura (skill)

**Antes:**
- "Relatório de cobertura por pessoa" via subagent.

**Depois:**
- Já contemplado em LLM-04-V2 (skill `/auditar-cobertura`). Spec AUDITOR-01 absorvida.

## Implementação proposta

Esta sprint **NÃO IMPLEMENTA**. Ela apenas:

1. Cria 8 sub-specs (LLM-01-V2 a LLM-07-V2 + AUDITOR-01-V2) em `docs/sprints/backlog/` com o conteúdo descrito acima.
2. Move as 8 specs antigas (LLM-01..07 + AUDITOR-01) para `docs/sprints/arquivadas/` com nota "supersedida por LLM-XX-V2".
3. Atualiza `docs/SPRINTS_INDEX.md` mapeando a substituição.
4. Atualiza `~/.claude/plans/pure-swinging-mitten.md` substituindo as referências.

## Acceptance criteria

- 8 specs antigas em `arquivadas/`.
- 8 specs novas em `backlog/` com prefixo `_v2`.
- SPRINTS_INDEX.md atualizado.
- Plan ativo aponta para as novas.
- Aprovação humana via AskUserQuestion antes de aplicar (esta spec é de planejamento, não execução).

## Proof-of-work

`ls docs/sprints/backlog/sprint_llm_*_v2*.md | wc -l` → 7. `ls docs/sprints/arquivadas/sprint_llm_*` → 7+ specs antigas.

## Gate anti-migué

Para mover esta spec para `concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar (já feito: ADR-13 existe e contradiz; LLM-01 cita anthropic SDK).
2. Proof-of-work runtime real: contagem dos arquivos.
3. (não aplicável) `make conformance-<tipo>`.
4. `make lint` exit 0.
5. `make smoke` 10/10.
6. Pytest baseline mantida.
7. Achados colaterais viraram sprint-ID. Zero TODO.
8. **Aprovação humana via AskUserQuestion** confirmando reescrita correta.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.

## Por que não aplicar a reescrita agora

A reescrita das 8 specs é trabalho substancial (~2h só de redação). Mais importante, a aplicação altera o roadmap de uma onda inteira (Onda 2). É **decisão arquitetural** que precisa de aprovação humana antes de ser executada — não algo que o Opus principal deve fazer sozinho.

Por isso esta sprint entrega apenas o **plano de reescrita**. A execução fica para sprint subsequente, após confirmação humana.
