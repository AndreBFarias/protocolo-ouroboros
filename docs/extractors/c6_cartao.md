# C6 Bank -- Fatura de Cartão de Crédito

## Formato

XLS (Excel 97-2003) exportado pelo app/site C6. Criptografado (senha: 051273).

## Estrutura

```
Linha 0: "Nome: ANDRE DA SILVA BATISTA DE FARIAS     Cartão C6"
Linha 1: Headers
Linha 2+: Transações
```

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| Data de compra | DD/MM/YYYY | Data da compra |
| Nome no cartão | str | Nome do titular |
| Final do Cartão | int | Últimos 4 dígitos (4828) |
| Categoria | str | Categoria do C6 (ex: "Supermercados / Mercearia") |
| Descrição | str | Nome do estabelecimento |
| Parcela | str | "Única" ou "X/Y" |
| Valor (em US$) | float | Valor em dólar (compras internacionais) |
| Cotação (em R$) | float | Cotação do dólar usada |
| Valor (em R$) | float | Valor em reais |

## Detecção

- Extensão: `.xls`
- Requer descriptografia via msoffcrypto + leitura via xlrd
- Nome contém "Fatura-CPF" ou conteúdo contém "Cartão C6"

## Pessoa

Sempre André (cartão final 4828).

## Edge cases

- Compras internacionais: valor em US$ com cotação separada (ex: XAI LLC)
- Se Valor (em R$) está vazio mas Valor (em US$) existe = compra nacional sem conversão, usar US$
- Mês da fatura extraído do nome do arquivo ("janeiro", "fevereiro", "marco")
- Arquivo "marco" (sem acento) = março

## Deduplicação

Hash gerado via data + descrição + valor.
