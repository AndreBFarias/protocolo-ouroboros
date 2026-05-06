---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-01
  title: "Restaurar make lint exit 0 corrigindo 11 acentuações em .md"
  prioridade: P1
  estimativa: 1h
  onda: C1
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §2.1 (lint quebrou na branch ux/redesign-v1)"
  depende_de: []
  bloqueia: []
  touches:
    - path: docs/sprints/backlog/sprint_micro_01a_followup_nfce_reais.md
      reason: "linha 23: 'transacao' -> 'transação'"
    - path: docs/sprints/concluidos/sprint_garantia_expirando_01_warning_intermediario.md
      reason: "linha 3: 'migracao' -> 'migração'; 'nao' (2 ocorrências) -> 'não'"
    - path: novo-mockup/README.md
      reason: "linhas 34, 38: 'validacao' -> 'validação'; 'analise' -> 'análise'"
    - path: novo-mockup/docs/MAPA_FEATURES_MOBILE_DESKTOP.md
      reason: "linhas 79, 89, 103, 134, 136: 'validacao'/'execucao'/'analise'/'relatorios'/'Analise' acentuados"
  forbidden:
    - "Adicionar exceção em scripts/check_acentuacao.py para esconder o problema; corrigir o conteúdo é obrigatório"
    - "Mudar texto além do estritamente necessário"
  hipotese:
    - "make lint exit 1 hoje. Saída atual lista exatamente 11 erros em 4 arquivos .md. Corrigir os 11 sem afetar nenhum outro lint check."
  tests:
    - cmd: "make lint"
      esperado: "exit 0; 'All checks passed!' (ruff) + 'Acentuação: 0 problema(s) encontrado(s)' (check_acentuacao)"
    - cmd: "make smoke"
      esperado: "10/10 contratos OK"
    - cmd: ".venv/bin/pytest tests/ -q --no-header --tb=no"
      esperado: "baseline mantida (>=2520 passed)"
  acceptance_criteria:
    - "make lint retorna exit 0 sem warnings"
    - "Os 11 ocorrências exatas listadas em §3 corrigidas; nenhuma adicional"
    - "git diff --stat mostra apenas os 4 arquivos .md modificados"
    - "Texto preservado: a frase original mantém o sentido"
  proof_of_work_esperado: |
    make lint 2>&1 | tee /tmp/proof_fix_01.log | tail -5
    grep "Acentuação:" /tmp/proof_fix_01.log
    git diff --stat ux/redesign-v1..HEAD
```

---

# Sprint UX-RD-FIX-01 — Lint acentuação 11 .md

**Status:** BACKLOG — Onda C1 (higiene crítica).

## 1. Contexto

A branch `ux/redesign-v1` deixou `make lint` com exit 1 (auditoria 2026-05-05 §2.1). O `ruff` passa, mas `scripts/check_acentuacao.py` encontra 11 erros em 4 arquivos .md. Nenhum em código `.py`. Esta sprint corrige conteúdo (não a regra).

## 2. Hipótese verificável (Fase ANTES)

Antes de mudar qualquer arquivo, executar:

```bash
make lint 2>&1 | grep -E '\.md:[0-9]+' | tee /tmp/lint_baseline.txt
wc -l /tmp/lint_baseline.txt   # esperado: 11
```

Se `wc -l` não der **11**, parar e revisar. A hipótese-base mudou; consultar dono.

## 3. Lista exata das correções

```
docs/sprints/backlog/sprint_micro_01a_followup_nfce_reais.md:23: 'transacao' -> 'transação'
docs/sprints/concluidos/sprint_garantia_expirando_01_warning_intermediario.md:3: 'migracao' -> 'migração'
docs/sprints/concluidos/sprint_garantia_expirando_01_warning_intermediario.md:3: 'nao' (2 ocorrências) -> 'não'
novo-mockup/README.md:34: 'validacao' -> 'validação'
novo-mockup/README.md:38: 'analise' -> 'análise'
novo-mockup/docs/MAPA_FEATURES_MOBILE_DESKTOP.md:79: 'relatorios' -> 'relatórios'
novo-mockup/docs/MAPA_FEATURES_MOBILE_DESKTOP.md:89: 'Analise' -> 'análise'
novo-mockup/docs/MAPA_FEATURES_MOBILE_DESKTOP.md:103: 'validacao' -> 'validação'
novo-mockup/docs/MAPA_FEATURES_MOBILE_DESKTOP.md:134: 'execucao' -> 'execução'
novo-mockup/docs/MAPA_FEATURES_MOBILE_DESKTOP.md:136: 'validacao' -> 'validação'
```

## 4. Tarefas

1. Rodar hipótese (§2). Confirmar 11 erros.
2. Para cada item: `Read` o arquivo na linha indicada, `Edit` substituindo o token. Use 30+ chars de contexto em `old_string` para garantir unicidade.
3. Re-rodar `make lint`. Esperado: exit 0.
4. Re-rodar `make smoke` (10/10) e `pytest tests/ -q` (baseline).
5. Capturar proof-of-work.

## 5. Anti-débito

Se `make lint` ainda mostrar erros depois das 11 correções: rodar diff novo, listar adicionais com path:linha, criar **sprint UX-RD-FIX-01.B** (achado colateral). Zero escopo creep.

## 6. Validação visual

Não aplicável (não toca UI).

## 7. Gauntlet

```bash
make lint                                          # exit 0
make smoke                                         # 10/10
.venv/bin/pytest tests/ -q --tb=no -p no:warnings  # baseline >=2520
git diff --stat ux/redesign-v1..HEAD               # apenas 4 .md
```

---

*"As palavras são pesos exactos: a falta de um acento desequilibra o sentido." -- Mário Quintana (paráfrase)*
