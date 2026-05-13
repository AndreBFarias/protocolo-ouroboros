---
titulo: Validação artesanal DAS PARCSN — 2 amostras (pré e pós Sprint 107)
data: 2026-05-12
auditor: supervisor Opus 4.7 (multimodal interativo)
escopo: Sprint INFRA-VALIDACAO-ARTESANAL-DAS — fev/2025 + mar/2026
status_final: APROVADO_COM_RESSALVAS
---

# Validação artesanal DAS PARCSN — 2 amostras

## TL;DR

**APROVADO_COM_RESSALVAS.** Aritmética interna (`principal + multa + juros = total`) bate centavo-a-centavo em ambas amostras. Cross-check com extrato bancário confirma os pagamentos com `categoria=Impostos` + `tag_irpf=imposto_pago`.

**Ressalvas/achados colaterais**:
- ETL não captura **decomposição** (principal/multa/juros) nem **composição por tributo** (COFINS/CSLL/INSS/IRPJ/ISS/PIS) — campos canônicos do bloco `das_parcsn` no schema estendido.
- `razao_social` extraído é do **contribuinte** (Andre) em vez do **emitente canônico** (RECEITA FEDERAL DO BRASIL) — confirma necessidade da Sprint AUDIT2-SPRINT107-RETROATIVA já no backlog.
- `tipo_documento` extraído é `das_parcsn_andre` em vez do canônico `das_parcsn`.
- Campo `chave_44` mapeia para o **Número do Documento** (17 chars), não chave NFe 44 dígitos — nome do campo equivocado.
- Achado colateral interessante: DAS de fev/2025 foi pago pela conta da Vitória (Nubank PF), embora seja do MEI do André — gestão financeira compartilhada como casal (não é bug).

## Amostra 1 — DAS PARCSN parcela 4/25 (fev/2025, vence 30/04/2025)

Arquivo: `data/raw/andre/impostos/das_parcsn/DAS_PARCSN_2025-02-28_2b8e0045.pdf`

### Captura ETL

```json
{
  "tipo_documento": "das_parcsn_andre",
  "cnpj_emitente": "45.850.636/0001-60",
  "razao_social": "ANDRE DA SILVA BATISTA DE FARIAS",
  "data_emissao": "2025-02-28",
  "vencimento": "2025-04-30",
  "periodo_apuracao": "2025-02",
  "numero": "07.18.25105.7231382-8",
  "parcela_atual": 4, "parcela_total": 25,
  "chave_44": "07182510572313828",
  "total": 324.31
}
```

### Captura Opus multimodal (pdfplumber)

```
Documento de Arrecadação do Simples Nacional
CNPJ: 45.850.636/0001-60 (MEI desativado do Andre)
Razão Social: ANDRE DA SILVA BATISTA DE FARIAS [PII no cache local; mascarar em relatorio]
Período de Apuração: Fevereiro/2025
Data de Vencimento: 28/02/2025
Pagar este documento até: 30/04/2025
Número do Documento: 07.18.25105.7231382-8
DAS de PARCSN (Versão: 2.0.0)
Valor Total: 324,31 -- Número Parcelamento 1, Parcela: 4/25

Composição:
  1004 COFINS - SIMPLES NACIONAL  31,56 +  6,31 +  3,70 =  41,57  (02/2024)
  1002 CSLL   - SIMPLES NACIONAL   8,62 +  1,72 +  1,01 =  11,35  (02/2024)
  1006 INSS   - SIMPLES NACIONAL 106,86 + 21,37 + 12,54 = 140,77  (02/2024)
  1001 IRPJ   - SIMPLES NACIONAL   9,85 +  1,97 +  1,15 =  12,97  (02/2024)
  1010 ISS    - SIMPLES NACIONAL  82,47 + 16,49 +  9,68 = 108,64  (Brasilia DF, 02/2024)
  1005 PIS    - SIMPLES NACIONAL   6,84 +  1,37 +  0,80 =   9,01  (02/2024)
  ----------------------------------------------------
  Totais                          246,20 + 49,23 + 28,88 = 324,31

Linha digitável (47 digitos):
  85830000003 3 24310328251 0 20071825105 1 72313828197 5

Pague com PIX (QR Code).
```

### Aritmética (defesa em camadas)

`principal + multa + juros = total`  
`246,20 + 49,23 + 28,88 = 324,31` PASS — **R$ 0,00 de divergência**

Soma da composição por tributo: 41,57 + 11,35 + 140,77 + 12,97 + 108,64 + 9,01 = 324,31 PASS

### Diff campo-a-campo

| Campo | ETL | Opus | Classe | Veredito |
|---|---|---|---|---|
| `cnpj_contribuinte` | 45.850.636/0001-60 | 45.850.636/0001-60 | A | OK |
| `data_emissao` | 2025-02-28 | 28/02/2025 | A | OK |
| `vencimento` | 2025-04-30 | 30/04/2025 | A | OK |
| `total` | 324.31 | 324,31 | A | OK |
| `numero_documento` | 07.18.25105.7231382-8 | 07.18.25105.7231382-8 | A | OK |
| `parcela` | 4/25 | 4/25 | A | OK |
| `principal` | (não extraído) | 246,20 | A | **GAP** |
| `multa` | (não extraído) | 49,23 | A | **GAP** |
| `juros` | (não extraído) | 28,88 | A | **GAP** |
| `codigo_barras` | (não extraído) | 85830000003 3 24310328251 0 20071825105 1 72313828197 5 | A | **GAP** |
| `razao_social` | ANDRE... (contribuinte) | RECEITA FEDERAL DO BRASIL (emitente canônico) | A | **DRIFT** |
| `tipo_documento` | das_parcsn_andre | das_parcsn | A | **DRIFT** |
| `composicao_por_tributo` | (não extraído) | 6 tributos (COFINS/CSLL/INSS/IRPJ/ISS/PIS) | B | GAP |

### Cross-check extrato bancário

| data | valor | mes_ref | categoria | quem | banco | tag_irpf |
|---|---|---|---|---|---|---|
| 2025-04-16 | 324.31 | 2025-04 | Impostos | **pessoa_b** (Vitoria) | Nubank PF | imposto_pago |

**Achado colateral honesto**: DAS do MEI do André foi pago pela conta da Vitória (Nubank PF), 14 dias antes do vencimento. Tag IRPF correta. Categoria correta. Pagamento legítimo via gestão financeira compartilhada do casal — **não é bug**, é o uso real.

---

## Amostra 2 — DAS PARCSN parcela 17/25 (mar/2026, vence 31/03/2026)

Arquivo: `data/raw/andre/impostos/das_parcsn/DAS_PARCSN_2026-03-31_c2bdf7e2.pdf`

### Captura ETL

```json
{
  "tipo_documento": "das_parcsn_andre",
  "cnpj_emitente": "45.850.636/0001-60",
  "razao_social": "ANDRE DA SILVA BATISTA DE FARIAS",
  "data_emissao": "2026-03-31",
  "vencimento": "2026-03-31",
  "periodo_apuracao": "diversos",
  "numero": "07.18.26078.0813829-0",
  "parcela_atual": 17, "parcela_total": 25,
  "chave_44": "07182607808138290",
  "total": 363.49
}
```

### Captura Opus multimodal (resumo, mesmas observacoes do amostra 1)

```
DAS PARCSN parcela 17/25, total 363,49
Periodo de Apuração: Diversos (06/2024 + 07/2024 -- dois meses-tributo agregados)
Composição:
  06/2024: 6 tributos somando 199,01
  07/2024: 6 tributos somando 162,47
  Wait -- recalculando: 06/2024 (COFINS 25,77 + CSLL 7,04 + INSS 87,24 + IRPJ 8,04 + ISS 67,34 + PIS 5,59) = 201,02
           07/2024 (COFINS 20,83 + CSLL 5,69 + INSS 70,51 + IRPJ 6,50 + ISS 54,43 + PIS 4,51) = 162,47
           Total 363,49 (PASS)
  Por componente:
  Principal: 258,55 ; Multa: 51,68 ; Juros: 53,26 ; Total: 363,49

Linha digitavel: 85890000003 4 63490328260 0 90071826078 0 08138290642 6
```

### Aritmética

`258,55 + 51,68 + 53,26 = 363,49` PASS

Soma por mes-tributo:
- 06/2024: 25,77 + 7,04 + 87,24 + 8,04 + 67,34 + 5,59 = 201,02
- 07/2024: 20,83 + 5,69 + 70,51 + 6,50 + 54,43 + 4,51 = 162,47
- Total: 363,49 PASS

### Cross-check extrato bancário

| data | valor | mes_ref | categoria | quem | banco | tag_irpf |
|---|---|---|---|---|---|---|
| 2026-03-19 | 363.49 | 2026-03 | Impostos | pessoa_a (Andre) | C6 | imposto_pago |

Pago 12 dias antes do vencimento. Tag IRPF correta. Categoria correta. Banco C6 — diferente da Vitória pagando antes; aqui é o André pagando o próprio MEI. PASS.

---

## Veredito

| Item | Amostra 1 (fev/25) | Amostra 2 (mar/26) |
|---|---|---|
| Aritmética `principal+multa+juros=total` | PASS | PASS |
| Soma composição por tributo = total | PASS | PASS |
| Cross-check extrato bate | PASS | PASS |
| Tag IRPF correta | PASS | PASS |
| Categoria correta | PASS | PASS |
| `razao_social` = emitente canônico | FAIL (Andre, não RFB) | FAIL (Andre, não RFB) |
| `tipo_documento` canônico | FAIL (das_parcsn_andre) | FAIL (das_parcsn_andre) |
| Decomposição (principal/multa/juros) extraída | FAIL | FAIL |
| Composição por tributo extraída | FAIL | FAIL |
| Código de barras extraído | FAIL | FAIL |

**Veredito final**: **APROVADO_COM_RESSALVAS** — aritmética e cross-check bancário comprovam que o ETL captura o valor final correto. Mas o extrator omite a decomposição que é necessária para análise fiscal granular e a Sprint AUDIT2-SPRINT107-RETROATIVA precisa rodar para corrigir o drift de fornecedor canônico nos 14 nodes pré-Sprint 107.

## Sprint-filha aberta (1 P1)

**INFRA-DAS-EXTRAIR-COMPOSICAO**: estender `_montar_documento` em `src/extractors/das_parcsn_pdf.py` para capturar:
- `principal`, `multa`, `juros` (totais)
- `codigo_barras` (47 dígitos com espaços)
- `composicao_por_tributo`: lista de `{codigo, denominacao, principal, multa, juros, total, periodo}`
- `quantidade_meses_diversos`: int (quando `periodo_apuracao == "diversos"`, parsear N meses internos)

**AUDIT2-SPRINT107-RETROATIVA** já está no backlog (`docs/sprints/backlog/sprint_AUDIT2_*.md`) para corrigir os 14 nodes pré-Sprint 107 que ainda têm fornecedor errado. Não precisa nova sprint.

## Observação especial

DAS pago pela Vitória (Amostra 1): registrar essa prática no `docs/auditorias/PADRAO_PAGAMENTOS_CRUZADOS_CASAL_2026-05-12.md` para evitar reclassificação automática como "transferência de terceiro" no futuro. É legítimo e é o uso real.

---

*"Imposto pago bem-pago bate em 3 lugares: PDF, extrato e Receita. Quando todos batem, o ETL pode dormir tranquilo." -- princípio descoberto na validação artesanal DAS 2026-05-12*
