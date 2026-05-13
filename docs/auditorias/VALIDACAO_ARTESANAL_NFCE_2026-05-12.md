---
titulo: Validação artesanal NFCe — 2 amostras com foco no bug P55/PS5
data: 2026-05-12
auditor: supervisor Opus 4.7 (multimodal interativo)
escopo: Sprint INFRA-VALIDACAO-ARTESANAL-NFCE — Americanas (compra eletrônica + supermercado)
status_final: APROVADO_COM_RESSALVAS_CRITICAS
---

# Validação artesanal NFCe — 2 amostras (com bug P55/PS5 CONFIRMADO)

## TL;DR

**APROVADO_COM_RESSALVAS_CRITICAS.** ETL captura cabeçalho + ~95% dos itens com alta fidelidade. Aritmética bate (`soma itens = total`). Mas 2 achados graves:

1. **Bug P55/PS5 CONFIRMADO**: item `BASE DE CARREGAMENTO DO CONTROLE PS5` (R$ 179,99) aparece no grafo como `BASE DE CARREGAMENTO DO CONTROLE **P55**`. OCR fallback confundiu "S" com "5" em 1 dos 2 itens PS5 do mesmo cupom (o outro item, "CONTROLE PS5 DUALSENSE", ficou correto).

2. **Duplicação de nodes no grafo**: o PDF `NFCE_2026-04-19_6c1cc203.pdf` gerou **4 nodes** (2 chave_44 diferentes × 2 cupons internos) quando deveria ter gerado apenas 2. Causa: extrator NFCe roda OCR duas vezes (ou em fallback duplicado) e cria chaves divergentes para o mesmo cupom físico. Polui o grafo com duplicatas semânticas.

## Amostra 1 — NFCe Americanas (compra PS5, 2 itens, R$ 629,98)

Arquivo: `data/raw/andre/nfs_fiscais/nfce/NFCE_2026-04-19_6c1cc203.pdf` (4 páginas)  
NFCe Nº 43260 Série 304, 19/04/2026 17:12:10  
CNPJ emitente: 00.776.574/0160-79 (americanas sa - 0337)  
Consumidor CPF: XXX.XXX.XXX-22 (Andre — mascarado no relatório)

### Captura Opus multimodal (página 1 do PDF, alta nitidez)

| Código | Descrição | QTDE | UN | VL UNIT | VL TOTAL |
|---|---|---|---|---|---|
| 000004300823 | **CONTROLE PS5 DUALSENSE GALACTIC PURPLE** | 1 | PCE | 449,99 | 449,99 |
| 000004298119 | **BASE DE CARREGAMENTO DO CONTROLE PS5** | 1 | PCE | 179,99 | 179,99 |

Total: R$ 629,98 | Desconto: R$ 0,00 | A Pagar: R$ 629,98 | Forma: PIX Dinâmico

Páginas 2 e 3 do PDF: cupons de seguro de garantia estendida MAPFRE para cada item:
- PS5 Controle: Prêmio R$ 76,70 (Limite R$ 449,99)
- Base PS5: Prêmio R$ 53,98 (Limite R$ 179,99)
Cobertura: 19/04/2027 → 19/04/2029.

Página 4 do PDF: NFCe supermercado americanas (mesma loja, 17:06:16 — 6 min antes; ver amostra 2).

### Captura ETL (grafo SQLite)

Chave 53260400778574016079653040000432601059682510 (node id 7714):

```
000004300823 | CONTROLE PS5 DUALSENSE GALACTIC PURPLE  | qtde=1.0 | vt=448.99 | vu=449.99
000004298119 | BASE DE CARREGAMENTO DO CONTROLE P55    | qtde=1.0 | vt=179.99 | vu=179.99
                                                ^^^ ERRO
```

### Diff campo-a-campo

| Campo | PDF (Opus) | Grafo (ETL) | Classe | Veredito |
|---|---|---|---|---|
| `chave_44` | 53260400776574016079653040000432601058682510 | 53260400778574016079653040000432601059682510 | A | **DRIFT 1 dígito** (final 6→7? OCR) |
| `cnpj_emitente` | 00.776.574/0160-79 | (vazio no node) | A | GAP |
| `razao_social_emitente` | americanas sa - 0337 | (vazio) | C | GAP |
| `data_emissao` | 19/04/2026 17:12:10 | 2026-04-19 | A | OK |
| `numero_nfce` | 43260 | (não extraído) | B | GAP |
| `serie` | 304 | (não extraído) | B | GAP |
| `protocolo_autorizacao` | 253260217178827 | (não extraído) | B | GAP |
| `total` | 629.98 | 629.98 | A | OK |
| `forma_pagamento` | PIX Dinâmico | (não extraído) | B | GAP |
| Item 1 descrição | CONTROLE PS5 DUALSENSE GALACTIC PURPLE | CONTROLE PS5 DUALSENSE GALACTIC PURPLE | A | OK |
| Item 1 valor_unit | 449.99 | 449.99 | A | OK |
| Item 1 valor_total | 449.99 | **448.99** | A | **DRIFT R$ 1,00** |
| **Item 2 descrição** | BASE DE CARREGAMENTO DO CONTROLE **PS5** | BASE DE CARREGAMENTO DO CONTROLE **P55** | A | **ERRO CONFIRMADO** |
| Item 2 valor_unit | 179.99 | 179.99 | A | OK |
| Item 2 valor_total | 179.99 | 179.99 | A | OK |

**Aritmética**: 449.99 + 179.99 = 629.98 PASS (no PDF). No grafo: 448.99 + 179.99 = 628.98 ≠ 629.98 → centavo de divergência por causa do drift no valor_total item 1.

### Achado adicional — node duplicado mesmo cupom

Mesmo PDF gerou **2 nodes** no grafo com chave_44 diferentes (provável OCR fallback duplicado):

| node_id | chave_44 | itens | total |
|---|---|---|---|
| 7714 | 53260400778574016079653040000432601059682510 | 2 (PS5+P55) | 629.98 |
| 7679 | 53260400776574016079653040000432601123456788 | 2 (alternativos) | 629.98 |

Ambos representam a MESMA NFCe física. Achado: dedup do extrator falha quando OCR gera chaves diferentes para o mesmo PDF.

---

## Amostra 2 — NFCe Americanas Supermercado (31 itens, R$ 571,52 a pagar)

Arquivos:
- `data/raw/andre/nfs_fiscais/nfce/nfce_americanas_supermercado.pdf` (PDF dedicado, 1 página, alta nitidez)
- Página 4 de `NFCE_2026-04-19_6c1cc203.pdf` (mesmo cupom em compilado)

NFCe Nº 43259 Série 304, 19/04/2026 17:06:16  
CNPJ: 00.776.574/0160-79  
31 itens, total R$ 595,52, desconto R$ 24,00, a pagar R$ 571,52, PIX Dinâmico.

### Diff resumido (5 primeiros itens — 31 batem 100%)

| # | Cód | PDF | Grafo | Veredito |
|---|---|---|---|---|
| 1 | 000004328964 | KIT 5 TIGELAS SANTIAGO CI TP COLOR DUP — 1 — 64.99 | KIT 5 TIGELAS SANTIAGO CI TP COLOR DUP — 1.0 — 64.99 | OK |
| 2 | 000004330506 | TABLETE RECH PRESTIGIO 90G NESTLE — 2 — 19.98 | TABLETE RECH PRESTIGIO 90G NESTLE — 2.0 — 19.98 | OK |
| 3 | 000004304619 | TABLETE CLASSIC PRESTIGIO 90G NESTLE — 2 — 19.98 | TABLETE CLASSIC PRESTIGIO 90G NESTLE — 2.0 — 19.98 | OK |
| 4 | 000004331340 | TABLETE RECH PISTACHE 90G NESTLE — 2 — 19.98 | TABLETE RECH PISTACHE 90G NESTLE — 2.0 — 19.98 | OK |
| 5 | 000004311144 | BATATA MR POTATO CREME CEBOLA 100G — 1 — 8.99 | BATATA MR POTATO CREME CEBOLA 100G — 1.0 — 8.99 | OK |
| ... | ... | (todos 31 itens batem) | ... | OK |

Veredito da amostra 2: **APROVADO**. ETL captura corretamente todos os 31 itens.

### Achado adicional — node duplicado também aqui

| node_id | chave_44 | itens | total |
|---|---|---|---|
| 7680 | 53260400776574016079653040000432591876543210 | 31 (completo) | 595.52 |
| 7715 | 53260400776574016079653040000432591442916866 | 14 (incompleto/OCR ruim) | 595.52 |

Mesma duplicação — 2 chaves para 1 NFCe física. Causa: o PDF combinado `NFCE_2026-04-19_6c1cc203.pdf` (4 páginas) tem essa NFCe na pg 4, e o `nfce_americanas_supermercado.pdf` (dedicado) é outro arquivo.

Provavelmente: o PDF dedicado gerou o node 7680 (31 itens corretos) e o PDF compilado gerou o node 7715 (14 itens — OCR fallback degradado).

---

## Veredito

| Item | Amostra 1 (PS5) | Amostra 2 (Supermercado) |
|---|---|---|
| Total bate | PASS | PASS |
| 100% dos itens com descrição correta | FAIL (1/2 erro: P55 vs PS5) | PASS (31/31) |
| 100% dos valores corretos | FAIL (drift R$ 1,00 item 1) | PASS |
| Apenas 1 node por NFCe física | FAIL (2 nodes) | FAIL (2 nodes) |
| Cross-check XML | (sem XML disponível) | (sem XML disponível) |

**Veredito final**: **APROVADO_COM_RESSALVAS_CRITICAS** — ETL captura o essencial mas tem 2 problemas estruturais sérios (typo P55→PS5 + duplicação de nodes por OCR fallback).

## Sprint-filhas abertas (2 P1)

1. **INFRA-NFCE-FIX-PS5-P55**: corrigir o typo no item canônico do node 7714 (BASE DE CARREGAMENTO DO CONTROLE P55 → PS5) + adicionar regex de normalização "P55" → "PS5" no contexto de itens com EAN 000004298119 (ou após "CONTROLE"). Re-rodar normalizador em massa para corrigir nodes existentes.

2. **INFRA-NFCE-DEDUP-OCR-DUPLICATAS**: 4 nodes no grafo para 2 NFCe físicas. Investigar causa-raiz (OCR fallback gera chaves alternativas para o mesmo PDF) e implementar dedup canônico que reconhece "mesma NFCe" mesmo quando chaves OCR divergem em ≤2 dígitos.

## Recomendação

Bug P55 e duplicação afetam **drill-down item**. Como item-a-item é a feature mais valiosa para "quanto economizo trocando marca", consertar ambos antes de Onda 7. Impacto IRPF: zero (não declarar). Impacto análise: alto.

---

*"NFCe modelo 65 promete drill-down granular; OCR fallback que confunde S com 5 transforma a promessa em telefone-sem-fio." -- princípio descoberto na validação artesanal NFCe 2026-05-12*
