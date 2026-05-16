---
id: META-FIX-FRONTMATTER-YAML-INVALIDO
titulo: Aspas duplas em 11 specs com frontmatter YAML inválido por `:` não escapado
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de:
  - META-SPEC-LINTER (concluída — detectou via baseline)
esforco_estimado_horas: 0.5
origem: achado colateral da sprint META-SPEC-LINTER (executor `ac4b5956`, 2026-05-15). Baseline em `docs/auditorias/specs_linter_baseline_2026-05-15.md` lista 11 specs com YAML inválido — campo `titulo` ou `origem` contém `:` interno (geralmente seguido de `<!-- noqa: accent -->` que YAML interpreta como mapping) sem aspas duplas.
---

# Sprint META-FIX-FRONTMATTER-YAML-INVALIDO

## Contexto

YAML interpreta `: ` (dois pontos seguidos de espaço) como separador de mapping. Quando o título tem `:` no meio (ex: "Sprint: refatorar X"), o parser YAML quebra. Solução canônica: envolver o valor em aspas duplas.

11 specs identificadas no baseline. Sprint mecânica.

## Hipótese e validação ANTES

```bash
grep -l "titulo:.*:" docs/sprints/backlog/sprint_*.md | head -15
# Esperado: 11 paths

# Confirmar com tentativa de parse YAML:
.venv/bin/python -c "
import yaml
from pathlib import Path
falhas = []
for p in Path('docs/sprints/backlog').glob('sprint_*.md'):
    t = p.read_text()
    if t.startswith('---'):
        try:
            yaml.safe_load(t.split('---')[1])
        except Exception as e:
            falhas.append((p.name, str(e)[:60]))
for f in falhas[:15]:
    print(f)
print(f'Total: {len(falhas)}')
"
# Esperado: 11 falhas listadas
```

## Objetivo

Para cada uma das 11 specs:
1. Localizar linha do `titulo:` ou `origem:` problemática.
2. Envolver valor em aspas duplas.
3. Validar parse YAML retorna OK.

## Não-objetivos

- Não tocar outros campos do frontmatter.
- Não tocar specs em `concluidos/`.

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/check_spec.py docs/sprints/backlog/ 2>&1 | grep -c "FALHA.*frontmatter_invalido"
# Esperado: 0

.venv/bin/python -c "
import yaml
from pathlib import Path
problemas = 0
for p in Path('docs/sprints/backlog').glob('sprint_*.md'):
    t = p.read_text()
    if t.startswith('---'):
        try:
            yaml.safe_load(t.split('---')[1])
        except Exception:
            problemas += 1
print(f'Frontmatter inválido: {problemas}')
"
# Esperado: 0
```

## Acceptance

- 11 specs com frontmatter YAML válido.
- `scripts/check_spec.py` reporta 0 falhas de frontmatter inválido.
- Pytest > 3046. Lint exit 0.

## Padrões aplicáveis

- (a) Edit incremental.

---

*"Forma quebrada confunde mais do que ajuda." — princípio do parser feliz*
