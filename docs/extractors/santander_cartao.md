# Santander -- Fatura de Cartão de Crédito (Black Way / Elite Visa)

## Formato

PDF exportado pelo app/site Santander. Sem proteção por senha.

## Estrutura

Fatura com 2-4 páginas:
- Página 1: Proposta de parcelamento de fatura (pode ser ignorada)
- Página 2: Resumo da fatura + detalhamento
- Página 3+: Continuação do detalhamento (se houver)

### Cabeçalho (página 2)

```
SANTANDER ELITE ANDRE DA SILVA BATISTA DE FARI - 4220 XXXX XXXX 7342
Total a Pagar: R$ 1.184,60    Vencimento: 10/02/2026
```

### Detalhamento

```
Compra Data   Descrição              Parcela  R$        US$
05/12  PAGAMENTO DE FATURA                   -281,20
20/10  SHOPEE *RICLI               03/09      64,44
30/12  XAI LLC                                177,24   30,00
```

## Detecção

- Extensão: `.pdf`
- Contém "SANTANDER" + "4220" ou "7342"

## Pessoa

Sempre André (cartão final 7342).

## Edge cases

- Seções separadas: Pagamentos e Créditos, Parcelamentos, Despesas
- Compras internacionais: valor em US$ + cotação + IOF separado
- PAGAMENTO DE FATURA = Transferência Interna (crédito negativo)
- IOF DESPESA NO EXTERIOR = Imposto
- ANUIDADE DIFERENCIADA R$ 0,00 = ignorar
- Layout pode ter duas colunas (dois cartões lado a lado)
- Mês/ano da transação inferido pelo vencimento da fatura

## Faturas encontradas

| Arquivo | Mês | Valor | Vencimento |
|---------|-----|-------|-----------|
| fatura-1776093934172.pdf | Janeiro | R$ 109,38 | 10/01/2026 |
| fatura-1776093953160.pdf | Fevereiro | R$ 1.184,60 | 10/02/2026 |
| fatura-1776093969815.pdf | Março | R$ 2.155,72 | 10/03/2026 |
| fatura-1776093983468.pdf | Abril | R$ 707,77 | 10/04/2026 |
