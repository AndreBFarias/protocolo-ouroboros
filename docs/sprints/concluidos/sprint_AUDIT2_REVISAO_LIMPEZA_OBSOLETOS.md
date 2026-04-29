# Sprint AUDIT2-REVISAO-LIMPEZA-OBSOLETOS -- Limpar item_ids orfaos pos-reextracao

**Origem**: Auditoria self-driven 2026-04-29, achado B4.
**Prioridade**: P2.
**Estimado**: 30min.
**concluida_em**: 2026-04-28
**Commit**: `9f52372`

## Problema

`data/output/revisao_humana.sqlite` acumula marcacoes de sessoes anteriores
referenciando `item_id = "node_<id>"` onde o node ja foi deletado pela
reextracao (Sprint 108 truncates+recria nodes). 23 item_ids orfaos hoje
(node_7383..7489), totalizando 115 marcacoes invisiveis no Revisor.

Impacto: Revisor mostra apenas pendencias atuais; marcacoes orfas viram
dado morto e poluem o ground_truth_csv exportado.

## Implementação sugerida

1. Criar `scripts/limpar_revisao_orfaos.py` que:
   - Cruza item_ids `node_<id>` com tabela `node` no grafo
   - Deleta marcacoes onde node não existe
   - Modo `--dry-run` por padrao + `--executar` explicito (CLAUDE.md)
2. Encadear a limpeza no `--full-cycle` ou `--reextrair-tudo` (Sprint 108).
3. Logar quantas foram removidas com timestamps preservados em log de
   auditoria.

## Proof-of-work esperado

```sql
-- Antes: 23 item_ids orfaos (115 marcacoes)
SELECT COUNT(DISTINCT item_id) FROM revisao
WHERE item_id LIKE 'node_%'
  AND CAST(substr(item_id, 6) AS INTEGER) NOT IN (
    SELECT id FROM grafo.node WHERE tipo='documento'
  );

-- Depois: 0
```

## Acceptance

- 0 item_ids orfaos apos rodar o script.
- Log de auditoria registra os ids removidos.
- Encadeado em automacao --reextrair-tudo (proxima reextracao limpa
  automaticamente).
