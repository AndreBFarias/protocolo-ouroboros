---
id: META-FINISH-SPRINT-GATE-COMPLETO
titulo: Estender `finish_sprint.sh` para rodar gate completo de 9 checks
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-15
fase: DX
epico: 8
depende_de: []
esforco_estimado_horas: 1
origem: auditoria 2026-05-15. `scripts/finish_sprint.sh` cobre 2 de 9 checks do VALIDATOR_BRIEF (valida estrutura MD + smoke aritmético). Não roda: make lint, pytest, schema-grafo, frontmatter `concluida_em`. Sprint "concluída" pode ter regressão silenciosa.
---

# Sprint META-FINISH-SPRINT-GATE-COMPLETO

## Contexto

VALIDATOR_BRIEF Fase DEPOIS lista 9 checks que toda sprint deve passar antes de virar CONCLUÍDA:

1. Hipótese declarada validada com grep (humano)
2. Proof-of-work runtime real capturado em log (humano)
3. Gate 4-way ≥3 amostras quando aplicável (`make conformance-<tipo>`)
4. `make lint` exit 0
5. `make smoke` 10/10
6. `pytest tests/ -q` baseline mantida ou crescida
7. Achados colaterais viraram sprint-ID OU Edit-pronto (humano)
8. Validador aprovou (humano)
9. Spec movida com `concluida_em` (script)

Checks 1, 2, 7, 8 dependem de humano. Checks 4, 5, 6, 9 podem ser automáticos. Check 3 condicional (só se aplicável).

Hoje `finish_sprint.sh` cobre:
- Check 9 (move + atualiza concluida_em)
- ~Check 5 (smoke aritmético, mas só 1 dos 2 smokes)

Falta cobrir 4, 6, 9-completo.

## Hipótese e validação ANTES

H1: script atual:

```bash
cat scripts/finish_sprint.sh | wc -l
# Esperado: ~76 linhas

grep -E "make lint|pytest|make smoke" scripts/finish_sprint.sh
# Esperado: 1 hit (smoke), falta lint e pytest
```

## Objetivo

1. Estender `scripts/finish_sprint.sh`:
   ```bash
   echo "=== Gate 9 checks ==="
   
   echo "[4/9] make lint..."
   if ! make lint; then echo "FALHA: lint" && exit 1; fi
   
   echo "[5/9] make smoke..."
   if ! make smoke; then echo "FALHA: smoke" && exit 1; fi
   
   echo "[6/9] pytest..."
   if ! .venv/bin/pytest tests/ -q --tb=no > /tmp/pytest.log 2>&1; then
       echo "FALHA: pytest"; tail -20 /tmp/pytest.log; exit 1
   fi
   N=$(grep -oE "[0-9]+ passed" /tmp/pytest.log | head -1 | grep -oE "[0-9]+")
   BASELINE_FILE=".ouroboros/pytest_baseline.txt"
   if [ -f "$BASELINE_FILE" ]; then
       OLD=$(cat "$BASELINE_FILE")
       if [ "$N" -lt "$OLD" ]; then
           echo "FALHA: pytest regrediu de $OLD para $N"; exit 1
       fi
   fi
   echo "$N" > "$BASELINE_FILE"
   
   echo "[3/9] (condicional) conformance se sprint toca extrator..."
   # Detectar via git diff em `src/extractors/`
   if git diff HEAD~1 HEAD --stat | grep -q "src/extractors/"; then
       echo "Sprint toca extrator; rodar manualmente: make conformance-<tipo>"
   fi
   
   echo "=== Gate OK ==="
   ```
2. Adicionar opção `--skip-pytest` para acelerar quando dono já rodou.
3. Manter compatibilidade: rodar sem args continua movendo spec; com `--gate-only` só roda checks.

## Não-objetivos

- Não substituir validador humano (checks 1, 2, 7, 8 ficam humanos).
- Não auto-rodar `make conformance-<tipo>` (escolha do tipo é decisão humana).
- Não tocar `make anti-migue` (que já faz parte do anti-migue gauntlet).

## Proof-of-work runtime-real

```bash
# 1. Gate passa em estado verde
./scripts/finish_sprint.sh --gate-only
# Esperado: "Gate OK" + exit 0

# 2. Gate falha se pytest regredido (simular)
# (não dá pra testar destrutivamente; documentar manual)

# 3. Baseline atualiza
cat .ouroboros/pytest_baseline.txt
# Esperado: número atual (3019+)
```

## Acceptance

- `finish_sprint.sh` cobre checks 4, 5, 6, 9.
- Baseline pytest persistido.
- Opção `--gate-only`.
- 3 testes em `tests/test_finish_sprint_gate.py` (via subprocess + mock).
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (n) Defesa em camadas — gate complementa make anti-migue.
- (u) Proof-of-work runtime-real — checks rodam contra estado atual.

---

*"Fechar sprint é cerimônia; cerimônia mal-feita acumula débito invisível." — princípio do encerramento honesto*
