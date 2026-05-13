---
id: INFRA-LINKING-DIRPF-TOTAL-ZERO
titulo: DIRPF com total=0.0 entra no linking heurístico por valor e casa transações aleatórias
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-13
fase: SANEAMENTO
depende_de: []
esforco_estimado_horas: 2
origem: auditoria pós-./run.sh --tudo em 2026-05-13 -- 3 propostas conflito (007462, 007583, 007768) todas para DIRPF|05127373122|2025_RETIF com total=0.0 e candidatas casadas via diff_valor=0.01.
---

# Sprint INFRA-LINKING-DIRPF-TOTAL-ZERO

## Contexto

Pipeline `./run.sh --tudo` (HEAD c3aca7b, executado 2026-05-13 00:30) gerou 21 conflitos de linking. Padrão identificado:

- Documento `DIRPF|05127373122|2025_RETIF` (id grafo 7768) tem `total: 0.0`.
- Heurística `data_valor_aproximado` casa-o contra 3 transações (rank 1-3) com `diff_valor: 0.01` e `diff_dias: -20/-45/-48`.
- Como o total é zero, qualquer transação pequena (R$ 0.01) bate proporcionalmente.

Conflitos identificados: 3 propostas distintas (007462, 007583, 007768) — provavelmente 3 versões da mesma DIRPF acumuladas no grafo. Antes de filtrar, conferir se são retificações legítimas ou lixo.

## Objetivo

Filtrar documentos com `total <= 0.01` ou `total IS NULL` ANTES de aplicar heurística `data_valor_aproximado`. DIRPF e similares geralmente não têm total monetário direto (retificadora pode até ter restituição a receber, mas o ARQUIVO em si não tem total movimento).

## Proof-of-work esperado

```bash
.venv/bin/python -c "
from src.graph.linking import linking_documento_transacao
result = linking_documento_transacao(dry_run=True)
assert result['conflitos'] < 21, f'Conflitos pós-fix: {result[\"conflitos\"]} (era 21)'
print(f'DIRPF conflitos: {result.get(\"dirpf_filtrados\", \"sem flag\")}')
"
```

## Padrão canônico aplicável

(s) Validação ANTES, (gg) Cache sintético/dado vazio não pode virar gabarito.

---

*"Linkar dado vazio é ato de fé; ato de fé não reduz incerteza." -- princípio anti-magia do arquivista*
