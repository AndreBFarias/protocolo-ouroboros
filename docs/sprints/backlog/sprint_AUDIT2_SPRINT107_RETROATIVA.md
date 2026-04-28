# Sprint AUDIT2-SPRINT107-RETROATIVA -- Backfill fornecedor sintetico em nodes antigos

**Origem**: Auditoria self-driven 2026-04-29, achado A1.
**Prioridade**: P1 (bug visivel em runtime).
**Estimado**: 1h.

## Problema

Sprint 107 introduziu o fornecedor sintetico (`mappings/fornecedores_sinteticos.yaml`)
para que DAS PARCSN aponte para `RECEITA_FEDERAL` em vez do contribuinte
(`ANDRE DA SILVA BATISTA DE FARIAS`). A logica funciona apenas em ingestoes
**posteriores** a 2026-04-28; os 14 nodes antigos (ids 7429-7489) gravados
antes mantem `metadata.razao_social = "ANDRE DA SILVA BATISTA DE FARIAS"`
incorreto, ou tem `razao_social` vazia + edge `fornecido_por` ausente.

Evidencia: query SQL no grafo

```sql
SELECT id, json_extract(metadata, '$.razao_social') FROM node
WHERE tipo='documento' AND json_extract(metadata, '$.tipo_documento') LIKE 'das_parcsn%'
ORDER BY id;
```

Mostra ids 7429-7489 com razao_social do contribuinte (errado) vs ids
7490+ com razao_social = "Receita Federal do Brasil" (correto pos-Sprint 107).

## Hipotese principal

Rerodar `./run.sh --reextrair-tudo` aciona Sprint 108 que encadeia o
ingestor de documento atualizado e re-grava metadata.razao_social com o
sintetico aplicado para todos. Verificar se o pipeline NÃO preserva nodes
antigos quando o arquivo origem não mudou.

## Implementação sugerida

1. Diagnostico (15min): rodar `./run.sh --reextrair-tudo`. Verificar se
   nodes antigos são deletados+recriados ou se ficam como estao.
2. Se ficam: criar script `scripts/backfill_fornecedor_sintetico.py` que
   itera nodes documento e re-aplica `_resolver_fornecedor_sintetico`
   conforme `tipo_documento`.
3. Adicionar teste cobrindo nodes pre-Sprint 107 + chamada idempotente.
4. Documentar no rodape do VALIDATOR_BRIEF como padrao (v) "Sprints
   retroativas".

## Proof-of-work esperado

```sql
SELECT COUNT(*) FROM node
WHERE tipo='documento'
  AND json_extract(metadata, '$.tipo_documento') LIKE 'das_parcsn%'
  AND json_extract(metadata, '$.razao_social') = 'Receita Federal do Brasil';
```

Esperado: 33 (todos os DAS PARCSN, antigos + novos).

## Acceptance

- 0 nodes DAS PARCSN com `razao_social = "ANDRE DA SILVA BATISTA DE FARIAS"`.
- Rerun do popular_valor_grafo_real preenche fornecedor para todos os DAS.
- Coluna `revisao.valor_grafo_real` sai de 14 vazios para 14 preenchidos.
