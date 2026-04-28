# Automacoes Opus (Sprint 108)

A fase Opus da Sprint 103 entregou 5 achados materiais que viraram
automacoes individuais (Sprints INFRA-DEDUP-CLASSIFICAR, 98a, 105, 106, 107).
A Sprint 108 amarra todas em fluxos canonicos do `run.sh`, eliminando
operação manual recorrente.

## Cadeia em `--full-cycle`

```
[passo 0] inbox processing (--inbox)
[passo 1] run_passo dedup_classificar          --executar  # Sprint INFRA-DEDUP
[passo 2] run_passo migrar_pessoa_via_cpf      --executar  # Sprint 105
[passo 3] run_passo backfill_arquivo_origem    --executar  # Sprint 98a
[passo 4] python -m src.pipeline --tudo                     # gera XLSX, relatorios
```

## Cadeia em `--reextrair-tudo`

```
[confirmacao humana] -- "Tem certeza? (operação irreversivel)"
[passo 1] run_passo dedup_classificar          --executar
[passo 2] run_passo migrar_pessoa_via_cpf      --executar
[passo 3] run_passo backfill_arquivo_origem    --executar
[passo 4] python -m scripts.reprocessar_documentos --forcar-reextracao
```

Sprint 106 (OCR fallback similar) **não** esta encadeada por padrao porque
o criterio de legibilidade atual ainda não detecta garbage Tesseract
adequadamente -- aguarda sub-sprint 106a com criterio refinado. Pode ser
invocada manualmente:

```bash
.venv/bin/python -m src.intake.ocr_fallback_similar --reanalisar-conferir --executar
```

Sprint 107 (fornecedor sintetico) opera **passivamente** durante ingestao
(quando `tipo_documento` casa com `mappings/fornecedores_sinteticos.yaml`).
Migração de nodes existentes acontece via `--reextrair-tudo`.

## Caracteristicas de cada passo

| Passo | Sprint | Idempotencia | Falha-modo | Flag para desativar |
|---|---|---|---|---|
| dedup_classificar | INFRA-DEDUP | Sim (sha256 valida) | Soft (log + segue) | omitir flag --executar |
| migrar_pessoa_via_cpf | 105 | Sim (arquivos ja migrados saem da varredura) | Soft | --dry-run |
| backfill_arquivo_origem | 98a | Sim (paths corrigidos passam Path.exists) | Soft | --dry-run |
| pipeline --tudo | -- | Sim | Hard (smoke aritmetico final captura) | -- |

## Helper `run_passo`

```bash
run_passo() {
    local nome="$1"
    shift
    local inicio
    inicio=$(date +%s)
    msg_info "[Sprint 108] ${nome}..."
    mkdir -p logs
    if "$@" >> logs/auditoria_opus.log 2>&1; then
        local dur=$(($(date +%s) - inicio))
        msg_ok "[Sprint 108] ${nome} OK (${dur}s)"
        return 0
    else
        msg_aviso "[Sprint 108] ${nome} falhou; seguindo"
        return 1
    fi
}
```

Cada passo loga inicio/fim/duracao em `logs/auditoria_opus.log` para
auditoria pos-fato.

## Menu interativo (opção 7)

```
7 - Auditoria Opus completa (cleanup + reextração) [Sprint 108]
```

Delega para `./run.sh --reextrair-tudo` que ja inclui a cadeia.

## Linha do tempo da entrega

- 2026-04-28: Sprint INFRA-DEDUP -> 98a -> 105 -> 107 -> 106 -> 108 mergeadas em sequencia.
- Volume real: 3 fosseis Americanas removidos (INFRA-DEDUP), 24 paths quebrados
  corrigidos (98a), 3 arquivos casal->andre (105), 13 DAS PARCSN apontariam para
  Receita Federal apos `--reextrair-tudo` (107).
- Sprint 106 ativa em código, aguarda criterio de legibilidade refinado (106a).
