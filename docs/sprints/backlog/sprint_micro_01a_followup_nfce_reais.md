# Sprint MICRO-01a-FOLLOWUP-NFCE-REAIS -- Validar drill-down com NFCe reais

> **Slug ASCII**: `micro_01a_followup_nfce_reais`. Texto livre: "MICRO-01a-FOLLOWUP-NFCE-REAIS".

**Origem**: achado da execução de MICRO-01a em 2026-04-30. Padrão (k) BRIEF: hipótese da spec original assumia que faltava criar mecanismo de linking, mas `src/graph/linking.py` (Sprint 48) já cobre `nfce_modelo_65`. Os 2 NFCe atuais no grafo são placeholders PoC sem transação correspondente.

**Prioridade**: P2
**Onda**: 4 (continuação MICRO)
**Esforço estimado**: 2h
**Depende de**:
  - MICRO-01a (resolver `obter_items_da_transacao` em `src/graph/drill_down.py`).
  - Existência de NFCe REAIS no inbox (não placeholders PoC).

## Problema

`src/graph/drill_down.py` entrega resolver de drill-down 2 saltos
(transação -> documento -> item). Em corpus real 2026-04-30:

- `transacoes_com_documento`: 25 (holerites/DAS, sem items granulares).
- `transacoes_com_items`: 0.
- `nfce_no_grafo`: 2 (PoC).
- `nfce_com_documento_de`: 0.

Logo, hoje 0 transações têm items granulares acessíveis. O motor de
linking (`linking.py`) e o resolver (`drill_down.py`) estão prontos,
mas faltam dados reais para validar o pipeline ponta-a-ponta.

## Critério de despertar

Abrir esta sprint quando:

- Dono coloca >=3 NFCe reais (não placeholders) em `data/inbox/`, OU
- `data/raw/<pessoa>/nfs_fiscais/nfce/` cresce com arquivos reais novos.

## Hipótese (a validar quando despertar)

Após `./run.sh --full-cycle` rodar com NFCe reais:

1. `linking.py` cria arestas `documento_de` automaticamente (config já
   cobre `nfce_modelo_65` em `mappings/linking_config.yaml` com
   janela_dias=1, diff_valor_percentual=0.01, confidence_minimo=0.85).
2. `obter_items_da_transacao(db, transacao_id)` retorna items reais
   para >=1 transação real.
3. `contar_drill_down(db)["transacoes_com_items"]` >= 1.

## Implementação proposta

Sem código novo. Apenas validação:

1. Confirmar que NFCe reais entraram no grafo após pipeline.
2. Rodar `python -c "from src.graph.db import *; from src.graph.drill_down import *; db=GrafoDB(caminho_padrao()); print(contar_drill_down(db)); db.fechar()"`.
3. Se `nfce_com_documento_de == 0` mas há NFCe reais, investigar por
   que `linking.py` não criou aresta -- propostas em
   `docs/propostas/linking/<chave>.md` devem ter sido geradas.
4. Se `transacoes_com_items >= 1`, escolher 1 amostra e rodar
   `obter_items_da_transacao` -- validar que items batem com PDF.

## Proof-of-work (runtime real)

Output esperado quando rodar com >=1 NFCe real linkado:

```
transacoes_com_documento: 26+ (25 atual + N reais)
transacoes_com_items: 1+ (era 0)
nfce_no_grafo: 5+ (2 PoC + 3 reais)
nfce_com_documento_de: 1+ (era 0)
```

## Acceptance criteria

- Estado em corpus real mostra `transacoes_com_items >= 1`.
- Pelo menos 1 walk completo (transação -> NFCe -> 3+ items) validado
  manualmente contra PDF original.
- Se houver propostas em `docs/propostas/linking/` para os NFCe não
  linkados, abrir sprint-filha de investigação ou aprovar manualmente.

## Gate anti-migué

(9 checks padrão -- ver CLAUDE.md.)

## Não-objetivos

- **Não fazer**: criar novo motor de linking. Reusar `linking.py`.
- **Não fazer**: forçar arestas via SQL manual.
- **Não fazer**: ajustar config de linking sem evidência empírica de
  que produz mais matches (refutar hipótese de tuning prematuro).

---

*"O grafo cresce por dados reais, não por placeholders."*
