# Nubank -- Extrato de Conta Corrente

## Formato

CSV exportado pelo app Nubank (seção Conta > Extrato > Exportar).

## Estrutura

```csv
Data,Valor,Identificador,Descrição
01/04/2026,80.00,69cdbd59-ba55-...,Transferência Recebida - NOME CPF - CNPJ - BANCO
01/04/2026,-54.93,69cdbd92-efdf-...,Transferência enviada pelo Pix - DROGARIA X
```

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| Data | DD/MM/YYYY | Data da transação (formato BR) |
| Valor | float | Positivo = entrada, negativo = saída |
| Identificador | UUID v4 | Identificador único da transação |
| Descrição | str | Descrição longa com CNPJ, banco, agência |

## Detecção

- Headers: `Data,Valor,Identificador,Descrição`
- Nome do arquivo: `NU_977370681_01MES2026_31MES2026.csv` (PF Vitória) ou `cc_pj_vitoria.csv` (PJ)

## Pessoas e subtipos

- `vitoria/nubank_pf_cc/` = Vitória PF (conta 97737068-1)
- `vitoria/nubank_pj_cc/` = Vitória PJ (conta 96470242-3, CNPJ 52.488.753)

## Mapeamento para schema

| Campo origem | Campo destino |
|-------------|---------------|
| Data | data (parse DD/MM/YYYY) |
| Valor | valor |
| Identificador | _identificador (UUID) |
| Descrição | descricao / local (extraído) |

## Edge cases

- HTML entities: `&amp;` precisa ser convertido para `&`
- Reembolsos aparecem como valor positivo com "Reembolso recebido pelo Pix"
- Transferências entre contas PF e PJ da Vitória = Transferência Interna
- Recebimentos do André (agência 6450 ou nome "ANDRE") = Transferência Interna
- "Valor adicionado na conta por cartão de crédito" = Transferência Interna
- Arquivos com sufixo "(1)", "(2)" = downloads duplicados do navegador

## Deduplicação

UUID nativo no campo Identificador. Deduplicação exata.
