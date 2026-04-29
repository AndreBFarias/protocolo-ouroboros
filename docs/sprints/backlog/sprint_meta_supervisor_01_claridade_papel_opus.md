---
concluida_em: 2026-04-29
---

# Sprint META-SUPERVISOR-01 — Claridade interpretativa do papel do Opus

**Origem**: pedido explícito do dono em sessão de 2026-04-29 ("anthropic está instável, melhora as sprints antes de cair").
**Prioridade**: P0 (sessão a sessão pode trocar de Opus; ambiguidade vira retrabalho).
**Onda**: 1 (anti-migué metodológico).
**Esforço estimado**: 2h.
**Depende de**: REVISAO-LLM-ONDA-01 já feita.

## Problema

Várias specs em `backlog/` mencionam "LLM", "IA" ou "supervisor" sem deixar explícito que **o supervisor sou EU** (Opus principal, sessão Claude Code interativa, conforme ADR-13). Risco real:

- Anthropic está instável; sessão pode cair a qualquer momento.
- Próximo Opus que pegar a sessão pode interpretar "supervisor LLM" como "implementar `src/llm/supervisor.py` chamando API" — exatamente o que ADR-13 PROÍBE.
- Já aconteceu uma vez: as 7 specs LLM-* originais previam SDK programático e foram reescritas via REVISAO-LLM-ONDA-01.

Inventário concreto (2026-04-29):
- **2 specs com linguagem Anthropic programática explícita** (`sprint_34_supervisor_auditor`, `sprint_36_metricas_ia_dashboard`) — superseded por LLM-04-V2 e LLM-07-V2 respectivamente, mas ainda em backlog.
- **18 specs DOC-* ambíguas** mencionando "LLM" sem citar ADR-13.

## Hipótese

Resolver via 3 camadas:

1. **Doc canônico permanente** `docs/SUPERVISOR_OPUS.md` (novo). Manifesto único: quem sou eu, fluxo padrão, comparação OCR vs ETL determinístico, quando disparar agentes Opus via Agent tool, quando marcar amostras 4-way.
2. **Bloco fixo nas DOC-* ambíguas**: seção "## Papel do supervisor (Opus Claude Code)" com instruções padronizadas para o extrator novo.
3. **Mover specs duplicatas** Sprint 34 e 36 para `arquivadas/` com nota `superseded_by`.

## Implementação proposta

### A. Criar `docs/SUPERVISOR_OPUS.md`

Manifesto cobrindo:
- Quem é o supervisor: o Opus principal **desta sessão** Claude Code interativa.
- Por que não é programático: ADR-13.
- Fluxo padrão por extrator novo:
  1. Eu leio o arquivo bruto via Read tool (PDF/imagem) — meu OCR/visão.
  2. Rodo o pipeline determinístico (`scripts/reprocessar_documentos.py --dry-run`) — output ETL.
  3. Comparo MEU output com o do pipeline campo a campo.
  4. Achados de divergência viram proposta via `/propor-extrator` ou regra YAML via `/propor-regra` (LLM-03-V2 futura).
  5. Marco amostras 4-way no Revisor quando humano confirmar.
  6. Disparo agente Opus via Agent tool quando refactor pesado (>5min, isolado, verificável).
  7. Integro o código do agente após validar 2-3 claims com grep.
- Lista de skills disponíveis: `/propor-extrator`, `/auditar-cobertura`, `/sprint-ciclo`, `/validar-sprint`.
- Cláusula de continuidade: "Se você for outro Opus que pegou esta sessão após queda, leia este doc primeiro."

### B. Bloco padrão nas 18 DOC-* + outras ambíguas

Ao final de cada spec, adicionar:

```markdown
## Papel do supervisor (Opus Claude Code)

Conforme ADR-13 e `docs/SUPERVISOR_OPUS.md`, eu (Opus principal nesta sessão interativa) executo este extrator novo seguindo:

1. Leio amostra bruta (`Read` tool sobre PDF/foto).
2. Comparo meu OCR/parse com output do extrator candidato (`scripts/reprocessar_documentos.py --dry-run --raiz <pasta>`).
3. Diferenças viram regex/regra ajustada na implementação ou Edit-pronto.
4. Marco >=3 amostras 4-way no Revisor (gate ANTI-MIGUE-01).
5. Para refactor substancial despacho `executor-sprint` em worktree isolado.

NÃO há chamada Anthropic API. Regra inviolável.
```

### C. Arquivar Sprint 34 e Sprint 36

Mover para `docs/sprints/arquivadas/` adicionando frontmatter `superseded_by`.

## Acceptance criteria

- `docs/SUPERVISOR_OPUS.md` publicado com >=150 linhas.
- 18 specs DOC-* com bloco "## Papel do supervisor (Opus Claude Code)".
- Sprint 34 e 36 em `arquivadas/`.
- CLAUDE.md §referências rápidas linka SUPERVISOR_OPUS.md.
- `grep -L "ADR-13\|Opus interativo\|Claude Code interativo\|SUPERVISOR_OPUS" docs/sprints/backlog/sprint_doc_*.md docs/sprints/backlog/sprint_*llm*.md` retorna 0 arquivos (todos têm a referência).

## Proof-of-work

Inventário pré-fix (executado em 2026-04-29):
- 2 specs com linguagem Anthropic programática explícita.
- 18 DOC-* ambíguas.

Inventário pós-fix esperado: 0 ambíguas.

## Gate anti-migué

9 checks padrão.
