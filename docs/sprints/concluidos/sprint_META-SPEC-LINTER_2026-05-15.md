---
id: META-SPEC-LINTER
titulo: Linter de specs com estrutura mandatória (`scripts/check_spec.py`)
status: concluída
concluida_em: 2026-05-15
prioridade: P1
data_criacao: 2026-05-15
fase: DX
epico: 8
depende_de: []
esforco_estimado_horas: 2
origem: "auditoria 2026-05-15. 122 specs em `docs/sprints/backlog/` sem validação automática. VALIDATOR_BRIEF padrões `(s/t/u)` exigem 'Validação ANTES', 'Não-objetivos', 'Proof-of-work runtime real'. Sem linter, próximo executor pode receber spec frágil. Padrão (ff) descoberto em 2026-05-12: auditoria automática vs supervisor — discrepância de ~30%."
---

# Sprint META-SPEC-LINTER

## Contexto

Specs viraram a unidade de trabalho do projeto. Cada sprint nova nasce com expectativa de:
- Frontmatter (id, status, prioridade, esforco_estimado_horas, data_criacao, origem)
- Seção "## Contexto"
- Seção "## Hipótese e validação ANTES" com comando grep/sql/python
- Seção "## Objetivo"
- Seção "## Não-objetivos"
- Seção "## Proof-of-work runtime-real" com comando executável
- Seção "## Acceptance"
- Seção "## Padrões aplicáveis"

Hoje umas 30% das specs no backlog não têm essa estrutura completa. Executor que recebe spec frágil produz código frágil.

## Hipótese e validação ANTES

H1: 122 specs com estruturas heterogêneas:

```bash
ls docs/sprints/backlog/sprint_*.md | wc -l
# Esperado: ~122

# Specs sem "Proof-of-work"
grep -L "Proof-of-work\|proof-of-work\|## Proof" docs/sprints/backlog/sprint_*.md | wc -l
# Esperado: 30+

# Specs sem "Não-objetivos"
grep -L "Não-objetivos\|nao-objetivos\|## Não objetivos" docs/sprints/backlog/sprint_*.md | wc -l
# Esperado: 40+
```

H2: ausência de validador automatizado:

```bash
ls scripts/check_spec*.py scripts/lint_spec*.py 2>/dev/null
# Esperado: 0 hits
```

## Objetivo

1. Criar `scripts/check_spec.py`:
   - Argumento: 1 path ou glob (`docs/sprints/backlog/`).
   - Valida frontmatter YAML: campos mandatórios `id`, `titulo`, `status`, `prioridade`, `data_criacao`, `esforco_estimado_horas`, `origem`.
   - Valida seções mandatórias (regex): `## Contexto`, `## Hipótese.*ANTES` OU `## Validação ANTES`, `## Objetivo` OU `## Implementação`, `## Não-objetivos`, `## Proof-of-work`, `## Acceptance`.
   - Valida que cada seção tem ≥1 linha de conteúdo (não-vazia).
   - Output: para cada spec, linha `OK` ou `FALHA: <id> [seção_faltante, frontmatter_campo_faltante]`.
   - Exit code: 0 se todas OK, 1 se alguma falha.
2. Integrar em `make lint`:
   ```makefile
   lint: ...
       $(PYTHON) scripts/check_spec.py docs/sprints/backlog/
   ```
3. Modo `--auto-completar` que insere `## Não-objetivos\n(preencher)\n` em specs que faltam (não-destrutivo, append no fim).
4. Hook pre-commit que valida APENAS specs modificadas no commit.

## Não-objetivos

- Não validar SEMÂNTICA da spec (executor humano + supervisor decidem).
- Não tocar `docs/sprints/concluidos/` (histórico imutável).
- Não criar UI gráfica.

## Proof-of-work runtime-real

```bash
# 1. Lint roda
.venv/bin/python scripts/check_spec.py docs/sprints/backlog/sprint_FIX-REGREDINDO-SEMANTICA_2026-05-15.md
# Esperado: "OK" (esta spec atende ao padrão)

# 2. Detecta falha
.venv/bin/python scripts/check_spec.py docs/sprints/backlog/sprint_FASE-A-AGUARDA-AMOSTRAS-2026-05-14.md
# Esperado: "OK" ou lista faltantes (verificar manualmente)

# 3. Lint geral
.venv/bin/python scripts/check_spec.py docs/sprints/backlog/ | grep "FALHA" | wc -l
# Esperado: count atual de specs frágeis (baseline)

# 4. Make lint integrado
make lint
# Esperado: exit 0 OU falha clara com path do arquivo
```

## Acceptance

- `scripts/check_spec.py` criado.
- 5 testes (cada seção/campo, modo auto-completar, exit code).
- `make lint` invoca o linter.
- Hook pre-commit configurado.
- Relatório baseline gerado em `docs/auditorias/specs_linter_baseline_2026-05-15.md` com count de falhas existentes.
- Pytest > 3019. Smoke 10/10. Lint exit 0 (após auto-completar opcional).

## Padrões aplicáveis

- (s) Validação ANTES — linter cobra exatamente isso.
- (n) Defesa em camadas — linter + revisor humano.
- (ff) Auditoria automática vs supervisor — linter limita-se a forma; supervisor cuida da substância.

---

*"Spec sem forma é convite ao caos; spec com forma é convite ao mérito." — princípio do template canônico*
