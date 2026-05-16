---
id: META-HOOK-SESSION-DINAMICO
titulo: SessionStart hook injeta baseline runtime + métricas vivas
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-15
fase: DX
epico: 8
depende_de:
  - META-ROADMAP-METRICAS-AUTO (reusa metricas_prontidao.json)
esforco_estimado_horas: 1.5
origem: "auditoria 2026-05-15. `.claude/hooks/session-start-projeto.py` injeta texto + `_bloco_graduacao` (lê JSON, OK) mas NÃO injeta: pytest count atual, smoke status, último commit, métricas linking/Outros, contagem de specs PRONTAS no backlog, working tree dirty, branches *-rebase mergeadas pendentes de delete. Próxima IA perde baseline para detectar regressão e age sem contexto vivo."
---

# Sprint META-HOOK-SESSION-DINAMICO

## Contexto

O hook SessionStart é o "olá mundo" da nova sessão IA. Hoje produz:
- Lista de 3 docs canônicos a ler
- Bloco de graduação (lê JSON)
- Bloco do épico ativo (lê ROADMAP)
- 1 linha de inventário

Falta:
- Baseline pytest (pra IA saber se regrediu durante sessão)
- Status smoke/lint (pra IA confiar que parte de estado verde)
- Working tree dirty (pra IA notar resíduo antes de novo trabalho)
- Branches/worktrees órfãos (pra IA propor GC se aplicável)

## Hipótese e validação ANTES

H1: hook atual tem 4 blocos:

```bash
grep -E "^def _bloco_" .claude/hooks/session-start-projeto.py
# Esperado: _bloco_graduacao, _bloco_epico_ativo (e talvez outros)
```

H2: hook tem timeout 5s no settings:

```bash
grep -A 1 "timeout" .claude/settings.json
# Esperado: timeout: 5
```

## Objetivo

1. Estender `montar_contexto_inicial()` com:
   - `_bloco_baseline_runtime()`: lê `data/output/metricas_prontidao.json` (gerado por META-ROADMAP-METRICAS-AUTO). Cache de 30min em `.claude/cache/baseline.json` para não estourar timeout.
   - `_bloco_working_tree()`: `git status --porcelain` count + 3 primeiros arquivos.
   - `_bloco_branches_orfas()`: count `git branch --merged main | grep -E "^\s+(worktree-agent-|sprint/|ux/)" | wc -l`.
   - `_bloco_specs_prontas()`: count `ls docs/sprints/backlog/sprint_*_2026-05*.md` (recentes).
   - `_bloco_alertas()`: lista tipos REGREDINDO ou propostas pendentes sem decisão >7 dias.
2. Output formato curto (1 linha por bloco para não estourar timeout 5s).
3. Cache estratégico para métricas pesadas (pytest count, smoke run).
4. Falha-soft em qualquer bloco (já garantido pelo try/except existente).

## Não-objetivos

- Não rodar `make smoke` no hook (custo ~5s, estoura timeout). Ler último resultado de `logs/`.
- Não rodar pytest no hook. Ler de `data/output/metricas_prontidao.json`.
- Não tocar o hook GLOBAL do dono (`~/.claude/hooks/session-start-briefing.py`).

## Proof-of-work runtime-real

```bash
# 1. Simular invocação do hook
echo '{}' | .venv/bin/python .claude/hooks/session-start-projeto.py | python -c "
import json, sys
out = json.load(sys.stdin)
ctx = out['additionalContext']
print('=== contexto gerado ===')
print(ctx[:800])
# Verificar blocos presentes
assert 'Baseline runtime' in ctx or 'pytest' in ctx.lower(), 'baseline ausente'
assert 'Working tree' in ctx or 'dirty' in ctx.lower(), 'working tree ausente'
print('OK blocos presentes')
"

# 2. Timeout (deve completar em <5s)
time echo '{}' | .venv/bin/python .claude/hooks/session-start-projeto.py > /dev/null
# Esperado: real < 1.5s (cache aquecido) ou < 4s (cache frio)
```

## Acceptance

- 5 novos `_bloco_*` funções.
- Cache em `.claude/cache/baseline.json` (TTL 30min).
- Hook completa em <4s wall clock.
- Contexto injetado mostra: pytest count, smoke status, lint status, working tree dirty, branches órfãs count.
- 4 testes em `tests/test_session_start_hook.py`.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (u) Proof-of-work runtime-real — wall clock medido.
- (n) Defesa em camadas — cache evita timeout, falha-soft evita travar boot.

---

*"A primeira frase ao acordar decide o tom do dia inteiro." — princípio do briefing diário*
