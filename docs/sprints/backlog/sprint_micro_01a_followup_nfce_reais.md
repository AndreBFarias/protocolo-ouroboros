---
id: MICRO-01A-FOLLOWUP-NFCE-REAIS
titulo: Sprint MICRO-01a-FOLLOWUP-NFCE-REAIS -- Validar drill-down com NFCe reais
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-05-01'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint MICRO-01a-FOLLOWUP-NFCE-REAIS -- Validar drill-down com NFCe reais

> **Slug ASCII**: `micro_01a_followup_nfce_reais`. Texto livre: "MICRO-01a-FOLLOWUP-NFCE-REAIS".

**Origem**: achado da execução de MICRO-01a em 2026-04-30. Padrão (k) BRIEF: hipótese da spec original assumia que faltava criar mecanismo de linking, mas `src/graph/linking.py` (Sprint 48) já cobre `nfce_modelo_65`. Os 2 NFCe atuais no grafo são placeholders PoC sem transação correspondente.

## Atualização 2026-05-01 (validação executada)

Ciclo `./run.sh --full-cycle` rodado em 2026-05-01 com 3 PDFs em
`data/raw/andre/nfs_fiscais/nfce/`. Achados que invalidam parcialmente a
premissa original e geram o gap real:

1. **Os 2 NFCe nodes no grafo (id 7557 e 7558) NÃO são placeholders PoC.**
   `arquivo_origem` confirma: são `nfce_americanas_compra.pdf` (R$ 629.98)
   e `nfce_americanas_supermercado.pdf` (R$ 595.52), ambos com
   `data_emissao=2026-04-19`. Foram ingeridos pelo `ExtratorNfcePDF` na
   primeira execução real do pipeline com NFCe reais. A spec original
   classificou erradamente como PoC porque as chaves de acesso parecem
   sintéticas (`53260400776574016079653040000432601...`), mas o conteúdo
   é real (Americanas, valores plausíveis).
2. **Cada NFCe tem 33 items granulares** linkados via aresta `contem_item`.
   Drill-down 1 salto (NFCe -> item) funciona; o que falha é o segundo
   salto (`transacao` -> `documento_de` -> NFCe), porque...
3. **Não há transação bancária no extrato OFX/CSV** dentro da janela
   `linking.py` para nfce_modelo_65 (janela_dias=1, diff_valor_pct=0.01,
   confidence_minimo=0.85) com valor próximo de R$ 629.98 ou R$ 595.52
   em data próxima a 2026-04-19. Hipóteses não exclusivas:
   - Compra paga em dinheiro físico (não rastreável no OFX).
   - Compra paga via cartão de crédito que ainda não fechou fatura.
   - PIX/Picpay/voucher fora do extrato bancário importado.
4. **`fornecedor_cnpj` ficou `None`** nos 2 NFCe — extrator não conseguiu
   extrair via OCR/parser. Isso degrada chance de match mesmo se houvesse
   transação cadastrada com CNPJ Americanas.
5. **Achado colateral** (não-MICRO-01a, mas relacionado): o 3º PDF
   `NFCE_2026-04-19_6c1cc203.pdf` foi capturado pelo `ExtratorCupomGarantiaEstendida`
   e gerou "2 bilhete(s) ingerido(s)" em vez de 1 NFC-e. O classificador
   de extrator confundiu NFCe consumidor com bilhete de garantia
   estendida SUSEP. Sub-sprint sucessora candidata:
   `MICRO-01a-FOLLOWUP-2_NFCE_VS_GARANTIA_CLASSIFICADOR` -- não aberta
   ainda; aguarda decisão do dono se quer atacar agora ou registrar
   como achado solto.

**Estado pós-validação**: `transacoes_com_documento=25`, `transacoes_com_items=0`,
`nfce_no_grafo=2 (REAIS)`, `nfce_com_documento_de=0`. Acceptance criteria
desta spec (`transacoes_com_items >= 1`) NÃO cumprida -- não por falha
do código, mas por ausência de dado bancário casável. Spec **permanece
em backlog** com escopo refinado: aguarda compra-amostra paga via OFX
rastreável (cartão de débito ou PIX dentro da janela) para validar
walk completo.

A spec proíbe explicitamente "ajustar config de linking sem evidência
empírica de que produz mais matches" -- mantemos a configuração estrita
(janela 1d, diff 1%, confidence 85%) para preservar precisão sobre
recall em NFCe.



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
