---
concluida_em: 2026-04-29
---

# Sprint META-COBERTURA-TOTAL-01 -- Cobertura total como invariante operacional + lint

**Origem**: decisão D7 do dono em 2026-04-29 (registrada no plan `~/.claude/plans/glittery-munching-russell.md`).
**Prioridade**: P1 (estrutural -- bloqueia validação de qualidade de qualquer extrator novo)
**Onda**: independente (cross-cutting: aplica a Ondas 3 + 4 + 5 + 6)
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: estabelece princípio que ANTI-MIGUE-01 (gate 4-way) ainda não cobre

## Problema

Hoje extratores podem retornar `extrair() -> []` silenciosamente (caso conhecido: `src/extractors/danfe_pdf.py:224`, item 21 do plan mestre). Pipeline declara "0 transações extraídas" sem warning, sem gate, sem visibilidade. Conforme decisão D7 do dono em 2026-04-29:

> "A ideia é extrair tudo das imagens e pdfs, tudo mesmo, cada valor e catalogar tudo. Tudo."

Sem invariante explícito, cada extrator novo pode violar o princípio por amostragem implícita, filtro silencioso por valor mínimo, ou rejeição de campos não reconhecidos.

## Hipótese

Invariante operacional pode ser sustentado por 3 mecanismos combinados:

1. **Lint estático**: regex que detecta `return []` ou `return list()` em extratores sem `logger.warning(...)` na mesma função.
2. **Contrato runtime**: cada extrator declara em metadata `valores_extraidos: int` e `valores_esperados: int` (via heurística de campos visíveis no documento -- ex: contagem de linhas em tabela). Quando proporção `valores_extraidos / valores_esperados < 0.95`, gera warning + entrada em `data/output/cobertura_violacoes.md`.
3. **Auditoria periódica**: a cada N sprints fechadas (ex: 5), rodar `make auditar-cobertura-total` que compara extração ETL × leitura Opus (sessão interativa) × validação humana via VALIDAÇÃO-CSV-01.

## Como começar (operacional para o Opus que assumir esta sprint)

```bash
# Passo 1 -- validar baseline com grep
grep -rn "return \[\]" src/extractors/ | wc -l
grep -rn "return list()" src/extractors/ | wc -l

# Passo 2 -- listar extratores que retornam vazio sem warning
for f in src/extractors/*.py; do
  grep -L "logger.warning\|logger.error" "$f" | xargs -I{} grep -l "return \[\]" {}
done

# Passo 3 -- rodar pipeline em amostra controlada e capturar baseline
python -m src.pipeline --tudo --dry-run > /tmp/baseline_cobertura.log
```

## Implementação proposta

1. **Lint** (`scripts/check_cobertura_total.sh`):
   - Detecta `return []` em funções `def extrair*` sem `logger.warning` no escopo.
   - Detecta filtros por valor mínimo silenciosos (`if valor < N: continue` sem comentário justificativo).
   - Integrar em `make lint` como check adicional.

2. **Contrato runtime**: padronizar em `src/extractors/_base.py` (criar se não existir) interface `ResultadoExtracao` com:
   - `items: list[dict]`
   - `valores_extraidos: int`
   - `valores_potenciais: int` (heurística por tipo)
   - `cobertura_minima: float = 0.95`
   - método `validar()` que dispara warning + log estruturado se cobertura abaixo do mínimo.

3. **Auditoria periódica** (`scripts/auditar_cobertura_total.py`):
   - Roda em modo dry-run por padrão.
   - Para cada extrator, compara saída atual com snapshot anterior (em `data/output/cobertura_snapshots/<extrator>_<data>.json`).
   - Aponta regressões (campos que deixaram de ser extraídos) e progressões.
   - Gera relatório `docs/auditorias/cobertura_total_<data>.md` (apêndice, leniente).

4. **Skill `/auditar-cobertura-total`**: invoca o script + apresenta relatório no Revisor 4-way.

## Proof-of-work (runtime real)

- `make lint` falha exit 1 se algum extrator tem `return []` sem warning.
- `python -m src.pipeline --tudo` exibe linha `[COBERTURA] 22 extratores OK; 0 violações` ou lista violações.
- `python scripts/auditar_cobertura_total.py` gera relatório `docs/auditorias/cobertura_total_2026-04-29.md` com tabela "extrator × cobertura medida × cobertura esperada".

## Acceptance criteria

- Lint detecta `return []` silencioso em `src/extractors/`.
- Contrato `ResultadoExtracao` definido e adotado por ≥3 extratores como prova-de-conceito (DANFE, holerite, NFCe).
- Skill `/auditar-cobertura-total` rodável.
- Relatório baseline gerado em `docs/auditorias/cobertura_total_2026-04-29.md`.
- ≥6 testes (lint + contrato + auditoria).
- `make smoke` 10/10, `make lint` exit 0, baseline pytest crescida.

## Como saber que terminou

1. `make lint` (incluindo nova check de cobertura) exit 0.
2. `make smoke` 10/10.
3. Baseline pytest crescida em ≥6 testes.
4. Skill `/auditar-cobertura-total` retorna relatório legível.
5. Decisão D7 referenciada em CLAUDE.md como invariante (não só no plan glittery).
6. Frontmatter `concluida_em: <data>` adicionado.

## Achados colaterais durante execução

Conforme regra "zero TODO solto" (CLAUDE.md), achados durante esta sprint viram sprint-filha em backlog/, nunca TODO no código:

- Se descobrir extrator com violação grave de D7 → criar `sprint_retrabalho_<extrator>.md` na hora.
- Se descobrir que o lint precisa de novo check → criar `sprint_meta_lint_<check>.md`.
- Se descobrir que `_base.py` deveria existir mas não existe → criar `sprint_refactor_extractor_base.md`.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com grep antes de codar (Passo 1 de "Como começar").
2. Proof-of-work runtime real capturado em log (output do `make lint` + `auditar_cobertura_total.py`).
3. `make conformance-<tipo>` quando aplicável (não -- não é extrator novo).
4. `make lint` exit 0 (incluindo nova check).
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.

## Referências

- Decisão D7 em `~/.claude/plans/glittery-munching-russell.md`.
- ANTI-MIGUE-01 (gate 4-way) -- complementa este invariante.
- `docs/auditorias/linking_2026-04-29.md` -- evidência empírica do gap.
- Item 21 do plan `pure-swinging-mitten` (DANFE silencia falha).
- VALIDAÇÃO-CSV-01 (sprint irmã, ferramenta de validação humana).
- RETRABALHO-EXTRATORES-01 (sprint guarda-chuva que consome os artefatos desta).
