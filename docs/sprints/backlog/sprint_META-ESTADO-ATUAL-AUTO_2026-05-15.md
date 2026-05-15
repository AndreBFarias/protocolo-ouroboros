---
id: META-ESTADO-ATUAL-AUTO
titulo: Regenerar seção "Versão + saúde" do ESTADO_ATUAL.md automaticamente
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 2
origem: auditoria 2026-05-15. `contexto/ESTADO_ATUAL.md` (canônico no PROMPT_NOVA_SESSAO) declara VERSAO 5.11, pytest "2.018 passed", smoke "8/8 (declarado, só 6 implementados)". Realidade atual: VERSAO 5.14 (memória), pytest 3019, smoke 10/10. Documento que serve de onboarding canônico está enganando próxima IA.
---

# Sprint META-ESTADO-ATUAL-AUTO

## Contexto

`contexto/ESTADO_ATUAL.md` tem 600+ linhas. A maioria é histórico narrativo de sessões (válido para preservar). Mas a seção "Versão + saúde geral" (linhas 292-305) tem métricas que envelhecem em dias:

```
VERSAO: 5.11 | TRANSACOES: 6.094 | MESES: 82 | EXTRATORES: 22
GRAFO: 7.494+ nodes + 24.732+ edges
TESTES: 2.018 passed / 9 skipped / 1 xfailed
SMOKE: 8/8 contratos aritmeticos OK
```

Snapshot de 2026-04-29 vs realidade 2026-05-15: pytest cresceu de 2018 para 3019 (+50%). Onboarding cita "≥1.971" como gate — gate inválido.

## Hipótese e validação ANTES

H1: scripts/auditar_estado.py existe mas só valida pendências:

```bash
.venv/bin/python scripts/auditar_estado.py
# Esperado: "Nenhuma pendencia [A FAZER]/[EM CURSO]" (não reporta métricas)

wc -l scripts/auditar_estado.py
# Esperado: ~200L
```

H2: bloco "Versão + saúde geral" é estático no MD:

```bash
grep -n "VERSAO:.*5\.\|TRANSACOES:.*6\.\|TESTES:.*2\.0" contexto/ESTADO_ATUAL.md
# Esperado: 1+ hit
```

## Objetivo

1. Estender `scripts/auditar_estado.py` com flag `--metricas`:
   - Lê: pytest count via `pytest --collect-only -q`, smoke via `make smoke`, lint via `make lint`, git HEAD, count de transações via grafo, count de extratores via `src/extractors/`, contagem dos status em `graduacao_tipos.json`.
   - Gera bloco markdown idêntico ao formato atual.
2. Adicionar marker no `ESTADO_ATUAL.md`:
   ```markdown
   <!-- BEGIN_AUTO_METRICAS -->
   ... bloco gerado ...
   <!-- END_AUTO_METRICAS -->
   ```
3. Script `scripts/regenerar_estado_atual.py` substitui o conteúdo entre markers.
4. Hook `pre-push` invoca o regenerador. Falha-soft (não bloqueia push).
5. Adicionar `make estado-atual-atualizar` no Makefile.

## Não-objetivos

- Não regenerar o restante do MD (narrativa histórica fica intacta).
- Não tocar `contexto/POR_QUE.md` ou `COMO_AGIR.md` (estáveis).
- Não criar Versão semântica automática (versão é manual: dono incrementa em releases).

## Proof-of-work runtime-real

```bash
# 1. Regenerador roda
.venv/bin/python scripts/regenerar_estado_atual.py --dry-run | head -20
# Esperado: mostra bloco proposto sem aplicar

# 2. Aplicar
.venv/bin/python scripts/regenerar_estado_atual.py --apply
grep -A 1 "VERSAO:" contexto/ESTADO_ATUAL.md | head -2
# Esperado: versão atual (não mais 5.11)

grep -A 1 "TESTES:" contexto/ESTADO_ATUAL.md | head -2
# Esperado: 3019+ (não mais 2018)

# 3. Idempotente
.venv/bin/python scripts/regenerar_estado_atual.py --apply
git diff contexto/ESTADO_ATUAL.md | wc -l
# Esperado: 0 (rerun não muda nada)
```

## Acceptance

- `scripts/regenerar_estado_atual.py` criado.
- Markers `<!-- BEGIN_AUTO_METRICAS -->` em `ESTADO_ATUAL.md`.
- `make estado-atual-atualizar` funciona.
- Hook pre-push wireado em `hooks/` ou `.git/hooks/pre-push`.
- 3 testes: (a) regenerador determinístico; (b) markers preservados; (c) idempotência.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (s) Validação ANTES — grep no MD atual.
- (y) Validação cosmética é antipattern — métricas precisam vir do runtime.

---

*"Documento que precisa ser atualizado à mão envelhece à mão. Documento gerado envelhece com o repositório." — princípio do snapshot vivo*
