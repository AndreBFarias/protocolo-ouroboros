# C6 Bank -- Extrato de Conta Corrente

## Formato

XLSX exportado pelo app/site C6 Bank. Pode estar criptografado (senha: [SENHA]).

## Estrutura

Planilha com cabeçalho na primeira linha funcional e transações nas linhas seguintes.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| Data Lançamento | date | Data do lançamento |
| Data Contábil | date | Data contábil |
| Título | str | Tipo da operação (Pix enviado, Compra no débito, etc.) |
| Descrição | str | Detalhes (beneficiário, CNPJ) |
| Entrada | float | Valor de entrada (positivo) |
| Saída | float | Valor de saída (negativo) |
| Saldo | float | Saldo após a transação |

## Detecção

- Extensão: `.xlsx`
- Cabeçalho contém "EXTRATO DE CONTA CORRENTE C6 BANK" ou colunas Entrada/Saída

## Pessoa

Sempre André (único titular C6).

## Edge cases

- Arquivo pode precisar de descriptografia via msoffcrypto
- Pagamento de fatura do cartão C6 = "PGTO FAT CARTAO C6" (Transferência Interna)
- Pix para Vitória = Transferência Interna
- Rendimentos de aplicação automática = Receita

## Deduplicação

Sem UUID. Hash gerado via data + descrição + valor.
