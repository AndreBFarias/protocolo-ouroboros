---
data: 2026-05-15
sprint: META-SPEC-LINTER
ferramenta: scripts/check_spec.py
escopo: docs/sprints/backlog/
total_specs: 137
specs_com_falhas: 129
percentual_fragilidade: 94%
---

# Baseline do linter de specs — 2026-05-15

## Contexto

A Sprint META-SPEC-LINTER (2026-05-15) introduziu `scripts/check_spec.py`,
linter que verifica:

- **Frontmatter YAML** com campos `id`, `titulo`, `status`, `prioridade`,
  `data_criacao`, `esforco_estimado_horas`, `origem`.
- **Seções mandatórias** `## Contexto`, `## Hipótese ... ANTES` (ou
  `## Validação ANTES`), `## Objetivo` (ou `## Implementação`),
  `## Não-objetivos`, `## Proof-of-work`, `## Acceptance`, cada uma com
  conteúdo não-vazio.

Este relatório registra o estado do backlog no momento de instalação do
linter. Padrões VALIDATOR_BRIEF cobertos: `(s)` Validação ANTES, `(t)`
Não-objetivos explícitos, `(u)` Proof-of-work runtime real.

## Comando reproduzível

```bash
.venv/bin/python scripts/check_spec.py docs/sprints/backlog/
```

## Resumo agregado

- 137 specs varridas em `docs/sprints/backlog/`
- 129 com pelo menos um problema (94%)
- 8 specs em conformidade total

## Tipos de falha (ranking)

| Tipo | Ocorrências | % do backlog |
|---|---|---|
| `secao_ausente:hipotese_ou_validacao_antes` | 98 | 71% |
| `campo_faltante:origem` | 97 | 71% |
| `secao_ausente:nao_objetivos` | 96 | 70% |
| `secao_ausente:contexto` | 96 | 70% |
| `campo_faltante:esforco_estimado_horas` | 95 | 69% |
| `secao_ausente:acceptance` | 35 | 26% |
| `secao_ausente:proof_of_work` | 34 | 25% |
| `secao_ausente:objetivo_ou_implementacao` | 26 | 19% |

## Padrões secundários detectados

- 11 specs com **frontmatter YAML inválido**: campo `titulo` contém comentário
  HTML embutido (`<!-- noqa: accent -->`) sem aspas; o token `:` em coluna
  arbitrária quebra o parser YAML.
- 1 spec com **bloco frontmatter sem fechamento `---`** (parser registra
  `expected <block end>`).
- Vários campos `origem` longos com `:` interno sem aspas (mesma classe de
  problema do frontmatter da spec META-SPEC-LINTER antes do fix aplicado
  durante a própria sprint).

## Estratégia de integração

- `make lint` invoca o linter com flag `--soft`: reporta sem travar suite
  global. Permite descoberta gradual enquanto o backlog histórico é saneado.
- Hook pre-commit `check-spec` é estrito (`--files`, sem `--soft`) e atinge
  APENAS specs modificadas no commit. Sprints novas nascem em conformidade;
  débito histórico é purgado em sprint-filha dedicada.

## Próximas sprints sugeridas

1. **Sprint dedicada de saneamento de backlog** — varre as 129 specs frágeis
   e aplica `--auto-completar` + revisão manual de seções essenciais.
2. **Sprint de fix de frontmatter YAML** — escapa `:` em campos `titulo` e
   `origem` das 11 specs detectadas como YAML inválido.
3. **Endurecer linter para Padrão (ii)** — verificar ausência de comandos
   git banidos no corpo da spec (`git stash`, `git reset --hard`, etc.) em
   exemplos de comando.

## Observação operacional

Reduzir a fragilidade do backlog é trabalho de mais de uma sprint. O
benefício imediato é que **toda spec nova ou modificada já é validada
automaticamente** pelo hook pre-commit, evitando crescimento da dívida.

---

*"Aquilo que medimos, melhora; aquilo que não medimos, decai." — princípio do baseline*
