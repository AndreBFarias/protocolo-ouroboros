---
id: META-FIX-CONCLUIDA-EM-FALTANTES  # noqa: accent
titulo: Adicionar `concluida_em` em 16 specs de `docs/sprints/concluidos/` sem o campo
status: concluída
concluida_em: 2026-05-15
prioridade: P3
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.5
origem: "achado colateral da sprint META-SPEC-LINTER (executor `ac4b5956`, 2026-05-15). `scripts/check_concluida_em.py` detectou 16 specs em `docs/sprints/concluidos/` sem frontmatter `concluida_em`. Exemplos: `sprint_DASH_pagamentos_cruzados_casal.md`, `sprint_INFRA_categorizar_salario_g4f_c6.md`."
---

# Sprint META-FIX-CONCLUIDA-EM-FALTANTES <!-- noqa: accent -->

## Contexto

`make anti-migue` (que invoca `scripts/check_concluida_em.py`) flagra specs concluídas sem data de conclusão. Padrão `(v)` "Spec retroativa" exige frontmatter `concluida_em: YYYY-MM-DD + link commit`. 16 specs históricas não têm esse campo.

Sprint mecânica: para cada uma, encontrar o commit que a moveu para `concluidos/` via `git log --follow` e usar essa data. Edit cirúrgico no frontmatter.

## Hipótese e validação ANTES

```bash
.venv/bin/python scripts/check_concluida_em.py 2>&1 | tail -20
# Esperado: lista de 16 specs sem o campo
```

## Objetivo

1. Listar as 16 paths.
2. Para cada uma:
   - `git log --diff-filter=A --follow --format="%cI" -- <path> | head -1` retorna a data do primeiro commit que tocou ela em `concluidos/` (ou usar data do último commit como aproximação).
   - Edit no frontmatter: `concluida_em: <data ISO>`.
3. Rodar `scripts/check_concluida_em.py` exit 0.

## Não-objetivos

- Não inventar datas (usar git log).
- Não tocar specs em `backlog/`.
- Não tocar outros campos do frontmatter.

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/check_concluida_em.py
# Esperado: exit 0, "todas as specs concluídas têm concluida_em"

git diff --stat docs/sprints/concluidos/ | tail -3
# Esperado: 16 arquivos com 1 linha modificada cada
```

## Acceptance

- 16 specs com `concluida_em` populado.
- `make anti-migue` exit 0.
- Pytest > 3046. Lint exit 0.

## Padrões aplicáveis

- (v) Spec retroativa.
- (a) Edit incremental.

---

*"Data de fechamento é prova de fechamento." — princípio da assinatura datada*
