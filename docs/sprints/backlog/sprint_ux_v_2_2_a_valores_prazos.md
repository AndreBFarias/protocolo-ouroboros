---
id: UX-V-2.2.A
titulo: Enriquecer prazos com valores reais (cruzamento boletos x prazos)
status: backlog
prioridade: media
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-2.2]
origem: achado colateral durante execução UX-V-2.2 (executor sprint)
---

# Sprint UX-V-2.2.A — Valores reais nas pílulas do calendário Pagamentos

## Contexto

Durante execução de UX-V-2.2 ficou evidente que a aba `prazos` do XLSX
(`data/output/ouroboros_2026.xlsx`) tem apenas 4 colunas:

```
conta · dia_vencimento · banco_pagamento · auto_debito
```

NÃO há coluna `valor`. Resultado: pílulas no calendário mostram R$ 0,00
e legenda mostra "6 pagamentos no mês · R$ 0.00". Visualmente legível,
mas semanticamente vazio.

A spec de UX-V-2.2 explicitamente proibiu inventar dados, então o
executor manteve fidelidade. Esta sprint endereça o gap real.

## Objetivo

1. Cruzar cada prazo (conta + dia_vencimento) com a média histórica de
   débitos correspondentes no `extrato`.
2. Para fornecedores ambíguos (Nubank, C6) que viram fatura, usar último
   valor de fatura conhecido em `boletos`.
3. Adicionar coluna sintética `valor_estimado` ao DataFrame de prazos
   antes de passar para `_pagamentos_por_data`.
4. Não modificar XLSX em disco — enriquecimento é runtime apenas
   (dashboard) e marca origem como "estimado" no tooltip.

## Não-objetivos

- NÃO atualizar a aba `prazos` do XLSX (é snapshot histórico, conforme
  CLAUDE.md armadilha #15).
- NÃO inventar valor quando não há histórico (mantém R$ 0,00 nesse caso).

## Validação ANTES (grep)

```bash
grep -n "valor" /home/andrefarias/Desenvolvimento/protocolo-ouroboros/data/output/ouroboros_2026.xlsx 2>&1 | head
python3 -c "
from openpyxl import load_workbook
wb = load_workbook('data/output/ouroboros_2026.xlsx', read_only=True)
print(list(wb['prazos'].iter_rows(values_only=True))[1])  # cabeçalho
"
```

## Critério de aceitação

1. Pílulas mostram valor real (R$ 1.280,00 para Aluguel, etc) quando há histórico.
2. Legenda mostra "N pagamentos no mês · R$ X" com X != 0.
3. Tooltip da pílula indica origem ("histórico 12m" / "última fatura" / "sem dado").
4. Lint OK + smoke 10/10.

## Referência

- Sprint pai: UX-V-2.2.
- Mockup: `novo-mockup/mockups/04-pagamentos.html`.
