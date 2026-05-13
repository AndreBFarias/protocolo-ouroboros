---
titulo: Validação artesanal HOLERITE — G4F + Infobase fev/2026 (ETL × Opus + cross-check extrato)
data: 2026-05-12
auditor: supervisor Opus 4.7 (multimodal interativo)
escopo: Sprint INFRA-VALIDACAO-ARTESANAL-HOLERITE — 2 amostras (1 G4F + 1 Infobase)
status_final: APROVADO_COM_RESSALVAS
---

# Validação artesanal HOLERITE — fev/2026 (G4F + Infobase)

## TL;DR

**APROVADO_COM_RESSALVAS.** ETL extrai corretamente os 5 campos críticos classe A (bruto, INSS, IRRF, VR/VA, líquido) em ambos empregadores. Aritmética bate centavo-a-centavo. Cross-check com extrato bancário confirma R$ 0,00 de divergência no líquido.

**3 ressalvas/achados colaterais** (3 sprint-filhas abertas):
- ETL **não extrai bases fiscais** (base_inss, base_irrf, FGTS, dependentes) que estão visíveis no PDF — impacto direto em IRPF.
- **Drift de categorização**: salário G4F aparece como `Transferência` (não `Salário`) no extrato C6.
- **Lançamento duplicado** R$ 6.381,14 G4F no C6 em 06/03/2026 (2 ocorrências idênticas).

## Amostra 1 — HOLERITE G4F fev/2026

Arquivo: `data/raw/andre/holerites/HOLERITE_2026-02_G4F_6381.pdf`

### Captura ETL (`_parse_g4f`)

```json
{
  "mes_ref": "2026-02", "fonte": "G4F",
  "bruto": 8657.25, "inss": 988.07, "irrf": 1200.29,
  "vr_va": 87.75, "liquido": 6381.14, "banco": ""
}
```

### Captura Opus multimodal (texto bruto do PDF)

```
Demonstrativo de Pagamento de Salário: 02/26 Seg: 695
Empresa: G4F SOLUCOES CORPORATIVAS LTDA, CNPJ: 07.094.346/0002-26
Colaborador: ANDRE DA SILVA BATISTA DE FARIAS, Matrícula: 16769, CBO: 212405
CPF: XXX.XXX.XXX-22  [PII mascarada no relatório]
Cargo: ANALISTA DE BUSINESS INTELLIGENCE
Data de admissão: 08/05/2025
Data de pagamento: 06/03/2026
Conta: Banco 33 - Santander S.A., Agência 2327, CC 71018701-1

Proventos:
  + Horas Normais  200,00  R$ 8.657,25
Descontos:
  - IRRF           27,50  (R$ 1.200,29)
  - INSS           14,00  (R$ 988,07)
  - Desc.Vale Alimentação 20,00 (R$ 87,75)
Total: R$ (2.276,11)  R$ 8.657,25
Valor líquido a receber: R$ 6.381,14

Nº de dependentes IR: 0, Nº dependentes Salário Família: 0
Salário base: R$ 8.657,25
Base de cálculo INSS: R$ 8.475,55
Base de cálculo IR: R$ 8.657,25
Base de cálculo FGTS: R$ 8.657,25
FGTS do mês: R$ 692,58
```

### Diff campo-a-campo

| Campo | ETL | Opus | Classe | Veredito |
|---|---|---|---|---|
| `mes_ref` | 2026-02 | 2026-02 | A | OK |
| `cnpj_empresa` | (não extraído) | 07.094.346/0002-26 | A | **GAP** (ressalva 1) |
| `razao_social` | (não extraído) | G4F SOLUCOES CORPORATIVAS LTDA | C | GAP cosmético |
| `bruto` | 8657.25 | 8.657,25 | A | OK |
| `inss` | 988.07 | 988,07 | A | OK |
| `irrf` | 1200.29 | 1.200,29 | A | OK |
| `vr_va` | 87.75 | 87,75 | A | OK |
| `liquido` | 6381.14 | 6.381,14 | A | OK |
| `base_inss` | (não extraído) | 8.475,55 | A | **GAP** (ressalva 1) |
| `base_irrf` | (não extraído) | 8.657,25 | A | **GAP** (ressalva 1) |
| `base_fgts` | (não extraído) | 8.657,25 | A | **GAP** (ressalva 1) |
| `fgts_mes` | (não extraído) | 692,58 | B | GAP |
| `data_pagamento` | (não extraído) | 06/03/2026 | B | GAP |
| `banco_credito` | "" | Santander 33 / Ag 2327 / CC 71018701-1 | B | **GAP** |
| `dependentes_ir` | (não extraído) | 0 | C | GAP |

### Aritmética (defesa em camadas)

`bruto - inss - irrf - vr_va = liquido`  
`8657.25 - 988.07 - 1200.29 - 87.75 = 6381.14` PASS — **R$ 0,00 de divergência**

### Cross-check extrato bancário

Busca em `data/output/ouroboros_2026.xlsx` por valor próximo a 6.381,14 em mes_ref 2026-02 ou 2026-03:

| data | valor | mes_ref | categoria | quem | banco |
|---|---|---|---|---|---|
| 2026-03-06 | 6.381,14 | 2026-03 | **Transferência** | pessoa_a | C6 |
| 2026-03-06 | 6.381,14 | 2026-03 | **Transferência** | pessoa_a | C6 |

**Ressalva crítica 2**: salário G4F está classificado como `Transferência` (não `Salário`) — provável fluxo "Santander recebe → transferência para C6". O banco Santander declarado no holerite não aparece no extrato (conta não importada?). Tag IRPF: vazia (deveria ser `rendimento_tributavel`).

**Ressalva crítica 3**: 2 lançamentos idênticos R$ 6.381,14 em 06/03/2026 no C6 — duplicação silenciosa.

---

## Amostra 2 — HOLERITE INFOBASE fev/2026

Arquivo: `data/raw/andre/holerites/HOLERITE_2026-02_INFOBASE_7442.pdf`

### Captura ETL (`_parse_infobase`)

```json
{
  "mes_ref": "2026-02", "fonte": "Infobase",
  "bruto": 10000.00, "inss": 988.07, "irrf": 1569.55,
  "vr_va": 0.0, "liquido": 7442.38, "banco": ""
}
```

### Captura Opus multimodal (texto bruto do PDF)

```
INFOBASE CONSULTORIA E INFORMATICA LTDA
CNPJ: 02.800.463/0001-63, CC: GERAL, Folha Mensal Fevereiro 2026
Mensalista
440 — ANDRE DA SILVA BATISTA DE FARIAS (CBO 212410)
Cargo: ANALISTA DE DADOS, Admissão: 02/06/2025

Vencimentos:
  8781 | DIAS NORMAIS       30,00   10.000,00
Descontos:
   998 | I.N.S.S.            9,88        988,07
   999 | IMPOSTO DE RENDA   27,50      1.569,55

Total vencimentos: 10.000,00, Total descontos: 2.557,62
Valor líquido: 7.442,38

Rodapé bases:
  Sal_Base 10.000,00, Base_INSS 8.475,55, Base_IRRF 10.000,00,
  FGTS 800,00, Base_FGTS 9.011,93, Aliq_IRRF 27,50%
```

### Diff campo-a-campo

| Campo | ETL | Opus | Classe | Veredito |
|---|---|---|---|---|
| `mes_ref` | 2026-02 | 2026-02 | A | OK |
| `cnpj_empresa` | (não extraído) | 02.800.463/0001-63 | A | GAP |
| `razao_social` | (não extraído) | INFOBASE CONSULTORIA E INFORMATICA LTDA | C | GAP |
| `bruto` | 10000.00 | 10.000,00 | A | OK |
| `inss` | 988.07 | 988,07 | A | OK |
| `irrf` | 1569.55 | 1.569,55 | A | OK |
| `vr_va` | 0.00 | (sem VA neste mês) | A | OK |
| `liquido` | 7442.38 | 7.442,38 | A | OK |
| `base_inss` | (não extraído) | 8.475,55 | A | GAP |
| `base_irrf` | (não extraído) | 10.000,00 | A | GAP |
| `fgts_mes` | (não extraído) | 800,00 | B | GAP |
| `base_fgts` | (não extraído) | 9.011,93 | B | GAP |
| `cargo` | (não extraído) | ANALISTA DE DADOS | C | GAP |
| `data_admissao` | (não extraído) | 02/06/2025 | C | GAP |

### Aritmética

`10000 - 988.07 - 1569.55 = 7442.38` PASS — **R$ 0,00 de divergência**

### Cross-check extrato bancário

| data | valor | mes_ref | categoria | quem | banco | tag_irpf |
|---|---|---|---|---|---|---|
| 2026-02-06 | 7.442,38 | 2026-02 | **Salário** | pessoa_a | Itaú | rendimento_tributavel |
| 2026-03-06 | 7.442,38 | 2026-03 | **Salário** | pessoa_a | Itaú | rendimento_tributavel |
| 2026-04-08 | 7.442,38 | 2026-04 | **Salário** | pessoa_a | Itaú | rendimento_tributavel |

**Bate centavo-a-centavo** PASS. Categoria correta. Tag IRPF correta. Banco Itaú importado. Padrão de pagamento mensal regular.

---

## Veredito

| Item | G4F | Infobase |
|---|---|---|
| Aritmética bruto-descontos=líquido | PASS | PASS |
| Campos críticos classe A extraídos | 5/5 | 5/5 |
| Cross-check extrato bate | PASS (em Transferência) | PASS (em Salário) |
| Tag IRPF correta | FAIL (vazia) | PASS |
| Categoria correta | FAIL (Transferência) | PASS |
| Bases fiscais extraídas | FAIL (3/3 ausentes) | FAIL (3/3 ausentes) |
| Dados bancários extraídos | FAIL | FAIL |

**Veredito final**: **APROVADO_COM_RESSALVAS** — extrator captura o essencial (bruto + descontos + líquido) mas omite metadata fiscal importante para IRPF.

## Sprint-filhas abertas (3 P1)

1. **INFRA-CONTRACHEQUE-EXTRAIR-BASES**: estender `_parse_g4f` e `_parse_infobase` para capturar `base_inss`, `base_irrf`, `base_fgts`, `fgts_mes`, `dependentes_ir`, `dependentes_salfam`, `cnpj_empresa`, `razao_social`, `cargo`, `data_admissao`, `data_pagamento`, `banco_credito`. Impacto IRPF: alto.

2. **INFRA-CATEGORIZAR-SALARIO-G4F-C6**: salário G4F (R$ 6.381,14) está categorizado como `Transferência` no extrato C6 em vez de `Salário`. Tag IRPF vazia. Investigar: (a) conta Santander declarada no holerite não está sendo importada? (b) categorizador não reconhece padrão G4F → C6 como salário? (c) regra de override falta?

3. **INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F**: 2 lançamentos R$ 6.381,14 em 06/03/2026 no C6 pessoa_a — duplicação silenciosa. Investigar sha8 + identificador para confirmar duplicata vs lançamentos legítimos diferentes.

## Recomendação

Antes de declarar Onda 6 completa, executar as 3 sprint-filhas em sequência. Impacto IRPF do gap nas bases é alto (base_inss e base_irrf são campos canônicos da declaração).

---

*"Cross-check com extrato bancário é o juiz final do holerite: aritmética interna pode bater por acaso, mas dinheiro na conta não mente." — princípio descoberto na validação artesanal HOLERITE 2026-05-12*
