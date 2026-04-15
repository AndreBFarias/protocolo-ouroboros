# Nubank -- Fatura de Cartão de Crédito

## Formato

CSV exportado pelo app Nubank (seção Fatura > Exportar CSV).

## Estrutura

```csv
date,title,amount
2026-04-02,Juros por fatura atrasada - Pix no crédito - 5/10,29.44
2025-05-29,Dl *Google Crunchyroll,19.99
```

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| date | YYYY-MM-DD | Data da compra (ISO 8601) |
| title | str | Descrição da transação |
| amount | float | Valor (sempre positivo, ponto decimal) |

## Detecção

- Headers: `date,title,amount`
- Nome do arquivo: geralmente `Nubank_YYYY-MM-DD.csv`

## Pessoas

- `andre/nubank_cartao/` = André
- `vitoria/nubank_pj_cartao/` = Vitória (PJ)

## Mapeamento para schema

| Campo origem | Campo destino |
|-------------|---------------|
| date | data |
| amount | valor (abs) |
| title | descricao / local | <!-- noqa: accent -->
| -- | forma_pagamento = "Crédito" |
| -- | tipo = "Despesa" (padrão) |

## Edge cases

- Parcelas aparecem como "Descrição - Parcela X/Y"
- Juros, multas e IOF de fatura atrasada aparecem misturados
- Transações com nome de pessoa (ex: "André da Silva") = Transferência Interna
- Datas podem ser futuras (parcelas de compras parceladas)

## Deduplicação

Sem UUID nativo. Hash gerado via SHA-256(data + titulo + valor).
