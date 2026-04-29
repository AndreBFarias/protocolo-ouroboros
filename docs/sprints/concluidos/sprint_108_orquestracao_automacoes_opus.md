---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 108
  title: "Orquestracao das 5 automacoes Opus em --full-cycle e --reextrair-tudo"
  prioridade: P1
  estimativa: ~2h
  origem: "fase Opus Sprint 103 entregou achados que precisam virar parte automatica do pipeline -- nao operação manual eventual"
  touches:
    - path: run.sh
      reason: "encadear as 5 automacoes em --full-cycle (default) e --reextrair-tudo"
    - path: scripts/menu_interativo.py
      reason: "opção 7: 'Auditoria Opus completa' que dispara o ciclo de automacoes"
    - path: src/pipeline.py
      reason: "passo final do pipeline padrao: --auditoria-opus que invoca as automacoes em sequencia"
    - path: docs/AUTOMACOES_OPUS.md
      reason: "novo doc: descreve a cadeia + ordem + idempotencia + flags"
    - path: tests/test_orquestracao_automacoes_opus.py
      reason: "regressao: cada automacao corre em ordem; falhas individuais nao abortam o pipeline; resumo agregado"
  forbidden:
    - "Mudar comportamento de --inbox / --tudo isolados (preservar isolamento)"
    - "Rodar automacoes destrutivas sem confirmacao explicita do dono no menu interativo"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_orquestracao_automacoes_opus.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "./run.sh --full-cycle roda em ordem: inbox -> dedup_classificar -> migrar_pessoa_via_cpf -> backfill_arquivo_origem -> ocr_fallback_similar -> pipeline-tudo"
    - "./run.sh --reextrair-tudo roda: cleanup automacoes + --forcar-reextracao + reprocessamento (Sprint 104)"
    - "Cada automacao falha-soft: erro em uma nao aborta as proximas (smoke aritmetico final captura)"
    - "Novo helper run_passo() loga inicio/fim/duracao/erro de cada automacao em logs/auditoria_opus.log"
    - "Menu interativo opção 7 'Auditoria Opus completa' chama --reextrair-tudo + automacoes via run.sh"
    - "docs/AUTOMACOES_OPUS.md documenta a ordem fixa e a idempotencia esperada de cada passo"
  proof_of_work_esperado: |
    ./run.sh --full-cycle 2>&1 | grep -E "(dedup_classificar|migrar_pessoa|backfill|ocr_fallback)"
    # Esperado: 4 linhas com OK ou Aviso para cada automacao
    
    ./run.sh --reextrair-tudo
    # Esperado: passos automacoes + reextracao todos rodam idempotentes
```

---

# Sprint 108 -- Orquestracao das automacoes Opus

**Status:** BACKLOG (P1, criada 2026-04-28 como sprint-mae das 5 automacoes Opus)

## Motivação

A fase Opus da Sprint 103 entregou 5 achados materiais que viraram sprints individuais (INFRA-DEDUP-CLASSIFICAR, 98a, 105, 106, 107). Mas se cada uma fica como script avulso, o usuario precisa lembrar de rodar todas, na ordem certa, todo mes.

Sprint 108 orquestra: as automacoes correm sozinhas dentro de `--full-cycle` (rota canônica) e `--reextrair-tudo` (rota administrativa). Resultado: re-classificação **ja vem limpa** sem operação manual.

## Ordem fixa de execução

```
[passo 0] inbox processing (--inbox)
[passo 1] dedup_classificar_lote --executar     # Sprint INFRA-DEDUP
[passo 2] migrar_pessoa_via_cpf --executar      # Sprint 105
[passo 3] backfill_arquivo_origem --executar    # Sprint 98a
[passo 4] ocr_fallback_similar --reanalisar-conferir --executar  # Sprint 106
[passo 5] pipeline --tudo (gera XLSX, relatorios, etc.)
```

Cada passo eh **idempotente** -- rodar 2x não corrompe.
Cada passo tem **falha-soft** -- log warning + segue.
Smoke aritmetico final (Sprint 56) eh o gate de qualidade.

## Implementação

### 1. `run.sh --full-cycle` estendido

```bash
--full-cycle)
    msg_info "Rota completa: inbox + automacoes Opus + tudo (Sprint 108)..."
    backup_xlsx
    run_passo "inbox" python -m src.inbox_processor || abort
    run_passo "dedup_classificar" python -m src.intake.dedup_classificar --executar
    run_passo "migrar_pessoa_cpf" python -m scripts.migrar_pessoa_via_cpf --executar
    run_passo "backfill_arquivo_origem" python -m src.graph.backfill_arquivo_origem --executar
    run_passo "ocr_fallback_similar" python -m src.intake.ocr_fallback_similar --reanalisar-conferir --executar
    run_passo "pipeline_tudo" python -m src.pipeline --tudo
    msg_ok "Rota completa concluida."
    ;;
```

### 2. `run.sh --reextrair-tudo` estendido

Antes da `--forcar-reextracao` (Sprint 104), roda automacoes 1-4. Depois reextrai tudo limpo.

### 3. Helper `run_passo`

```bash
run_passo() {
    local nome="$1"; shift
    local inicio=$(date +%s)
    msg_info "[Sprint 108] $nome..."
    if "$@" >> logs/auditoria_opus.log 2>&1; then
        local dur=$(($(date +%s) - inicio))
        msg_ok "[Sprint 108] $nome OK (${dur}s)"
    else
        msg_aviso "[Sprint 108] $nome falhou; seguindo (smoke aritmetico final captura regressao)"
    fi
}
```

### 4. Menu interativo opção 7

```python
"7": "Auditoria Opus completa (--reextrair-tudo + automacoes)",
```

Dispatcher chama `_acao_auditoria_opus()` que delega para `./run.sh --reextrair-tudo`.

### 5. Doc `docs/AUTOMACOES_OPUS.md`

Tabela com:
- Passo, sprint origem, idempotencia, falha-modo, flag para desativar.

## Testes regressivos

1. `--full-cycle` end-to-end com fixtures sinteticas: 5 passos rodam em ordem.
2. Falha em `dedup_classificar` (mock raise) -> proximos passos rodam.
3. Idempotencia: rodar `--full-cycle` 2x não corrompe estado.
4. Logs em `logs/auditoria_opus.log` tem 5 entradas (uma por passo).
5. Smoke aritmetico continua 8/8 + 23/23.

## Dependências

- Sprint INFRA-DEDUP-CLASSIFICAR (passo 1) -- pre-requisito.
- Sprint 105 (passo 2) -- pre-requisito.
- Sprint 98a (passo 3) -- pre-requisito.
- Sprint 106 (passo 4) -- pre-requisito.
- Sprint 107 (passo 5 implicito via re-extração) -- não bloqueia mas potencializa.
- Sprint 101 (--full-cycle) ja em main.
- Sprint 104 (--forcar-reextracao) ja em main.

Ordem sugerida de execução:
```
1. INFRA-DEDUP-CLASSIFICAR (~1.5h)
2. 98a (~2h)
3. 105 (~2h)
4. 107 (~1.5h)   [nao bloqueante para 108, pode ser depois]
5. 106 (~3-4h)
6. 108 (~2h)     [esta sprint -- amarra tudo]
```

Total: ~12-13h em sprints novas + 1 rodada de --reextrair-tudo no fim para migrar nodes pre-existentes.
