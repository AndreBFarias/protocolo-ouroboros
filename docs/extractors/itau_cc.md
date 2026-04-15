# Itaú Unibanco -- Extrato de Conta Corrente

## Formato

PDF protegido por senha, exportado pelo app/site Itaú.

## Estrutura

Cabeçalho na primeira página com dados da conta:
```
[NOME COMPLETO] [CPF] agência: [AGENCIA] conta: [CONTA]
saldo em conta: R$ XXX,XX
```

Tabela de lançamentos com formato:
```
DD/MM  HISTÓRICO                          VALOR
10/04  PIX QRS NEOENERGIA 10/04          -20,38
10/04  PAG BOLETO SESC                   -101,60
```

## Detecção

- Extensão: `.pdf`
- Requer senha: ver mappings/senhas.yaml (não rastreado pelo git)
- Contém "ITAÚ UNIBANCO" ou "agência: 6450"

## Pessoa

Sempre André (agência 6450, conta 006854-6).

## Mapeamento de forma de pagamento

| Pista no histórico | Forma |
|-------------------|-------|
| PIX QRS | Pix |
| PIX TRANSF | Pix |
| PAG BOLETO | Boleto |
| TED | Transferência |
| REND PAGO | Rendimento |
| DEB | Débito |

## Edge cases

- Valores no formato BR: 1.234,56 (ponto = milhar, vírgula = decimal)
- Linhas de "SALDO DO DIA" devem ser ignoradas
- Rendimentos de aplicação automática têm valor muito baixo (R$ 0,01)
- O PDF pode conter dados de múltiplos meses
- Nome do arquivo: `itau_extrato_012026.pdf` (MMYYYY)

## Deduplicação

Hash gerado via data + histórico + valor.
