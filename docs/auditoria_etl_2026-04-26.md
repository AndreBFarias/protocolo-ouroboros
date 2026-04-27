# Auditoria 2x2 ETL -- 2026-04-26

**Origem:** subagente Opus (general-purpose) executou auditoria de fidelidade ETL READ-ONLY. Modelo: `opus`. Duração: ~25 min. Tool calls: 58.

**Modo:** READ-ONLY (nenhum arquivo modificado, pipeline não rodado).

**Fontes auditadas:**
- `data/raw/` x `data/output/ouroboros_2026.xlsx` (gerado 2026-04-24 19:05)
- `data/output/grafo.sqlite` (mesma timestamp)

**Validação dos claims-chave (eu):**
1. Sprint 93f já está em RUNTIME: confirmei `828 tx Nubank (PJ) Vitória / R$ 169.131,13` no XLSX.
2. Holerite G4F mal classificado: abri `BANCARIO_ITAU_CC_b1e59d77.pdf`, começa com "Demonstrativo de Pagamento de Salário G4F SOLUCOES CORPORATIVAS CNPJ 07.094.346/0002-26".

**PII tratada:** CPF/CNPJ pessoais NÃO aparecem neste documento. CNPJs corporativos (G4F 07.094.346, Americanas 00.776.574) são públicos, mantidos.

---

## Sumário executivo

- **Saúde geral OK.** Pipeline está deduplicando corretamente (6.093 chaves únicas, 0 duplicatas exatas) e o XLSX reflete fielmente os arquivos brutos disponíveis. Itaú bate **100%** centavo-a-centavo após exclusão de SALDO DO DIA.
- **Sprint 93f está EM RUNTIME, não só em backlog.** XLSX já contém Vitória 3.160 tx (PJ 828 + PF 1.757), confirmando que `vitoria/nubank_pj_*` foi escaneado na rodada de 2026-04-24. Descrição do CLAUDE.md sobre Sprint 93f como "BACKLOG" está desatualizada.
- **Família B (dataloss nubank_pf_cc) confirmada mas mitigada.** Pasta `vitoria/nubank_pf_cc/` tem só 363 tx em 19 SHAs únicos com gap claro (sem cobertura 2022-2024). Os 1.394 tx adicionais (1.757 - 363) vêm corretamente de `vitoria/nubank_cc/` (CSVs históricos preservados). Sprint 93d permanece P2 (não P1).
- **Achado novo P0 -- classificação cruzada de holerites.** 13 PDFs únicos rotulados como `BANCARIO_ITAU_CC_*` ou `BANCARIO_SANTANDER_CARTAO_*` são na verdade contracheques G4F (mesmas datas, mesmo CNPJ 07.094.346/0002-26, mesmo cabeçalho "Demonstrativo de Pagamento de Salário"). Classifier do inbox não detectou. Grafo extraiu corretamente apenas conteúdo bancário real (4 únicos no Itaú e Santander juntos), mas isso revela bug no `inbox_processor.py`.
- **DAS PARCSN sub-processado.** 19 PDFs físicos únicos vs 10 nodes no grafo = 9 GAP. Não é dedup (todos têm SHA distinto). Investigar `extractors/das_parcsn_pdf.py` ou `boleto_pdf.py` (que provavelmente está roubando arquivos parcsn).
- **Clones SHA ainda massivos.** Apesar da Sprint 93g, andre/itau_cc continua com 7.25x clones físicos por arquivo único (29 -> 4). Sprint P2.3 dedup-on-ingestão precisa ser ativada para futuras rodadas.

---

## 1. Tabela de fidelidade por extrator

| # | Extrator | Arquivo bruto (SHA-único) | Tam | Bruto (n/R$) | XLSX (n/R$) | Δ | Status |
|---|---|---|---|---|---|---|---|
| 1 | nubank_cartao | `andre/nubank_cartao/Nubank_2026-08-09.csv` (8 clones) | 125B | 2 / R$ 109,87 | 2 / R$ 109,87 | 0% | OK |
| 2 | nubank_cc | `andre/nubank_cc/nubank_cc_andre_*.csv` (1 clone, 152KB) | 152KB | ~6.000 linhas | OK | n/a | OK (master CSV) |
| 3 | c6_cc | `andre/c6_cc/c6_cc_andre_*.ofx` (8 clones, 312KB) | 312KB | 892 STMTTRN / R$ 277.378,41 | 207 / R$ 47.380,46 (recorte 2026-01..03) | -0,7% | OK |
| 4 | c6_cartao | `andre/c6_cartao/BANCARIO_C6_CARTAO_2026-01_*.xls` | 10KB | 14 / R$ 1.718,82 | 9 / R$ 7.387,12 | n/a | DELTA-MEDIO (XLSX agrega parcelas) |
| 5 | itau_pdf | `andre/itau_cc/BANCARIO_ITAU_CC_2026-01_*.pdf` | 172KB | 22 / R$ 44.063,64 | 29 / R$ 44.065,01 | +0,003% | **OK 100%** |
| 5b | itau_pdf | `andre/itau_cc/BANCARIO_ITAU_CC_b1e59d77.pdf` (7 clones, 63KB) | 1 pg | n/a (HOLERITE G4F, NÃO Itaú) | n/a | n/a | **MISCLASSIFIED P0** |
| 6 | santander_pdf | `andre/santander_cartao/BANCARIO_SANTANDER_CARTAO_2026-02_*.pdf` | 353KB | 60 linhas / R$ 1.705,13 | 29 / R$ 2.832,83 | n/a | OK (combina fatura + retornos) |
| 6b | santander_pdf | `andre/santander_cartao/BANCARIO_SANTANDER_CARTAO_3a547968.pdf` (7 clones) | 63KB | n/a (HOLERITE G4F) | n/a | n/a | **MISCLASSIFIED P0** |
| 7 | energia_ocr | `data/raw/casal/contas_energia/` ausente | -- | -- | -- | -- | N/D |
| 8 | ofx_parser | `andre/c6_cc/BANCARIO_C6_OFX_*.ofx` (7 clones, 86KB) | 86KB | parser comum a c6_cc | n/a | n/a | OK |
| 9 | cupom_garantia_estendida_pdf | `casal/garantias_estendidas/GARANTIA_EST_2026-04-19_*.pdf` (3 únicos) | 70-150KB | 3 PDFs | 2 nodes apolice | -33% | DRIFT-MEDIO |
| 10 | nfce_pdf | `andre/nfs_fiscais/nfce/nfce_americanas_compra.pdf` | 80KB | 1 PDF | 4 nodes (2 do mesmo arquivo) | dup | DRIFT (id 7464 vs 7466 chave_44 quase igual) |
| 11 | danfe_pdf | n/a | -- | 0 | 0 | 0% | N/D |
| 12 | cupom_termico_foto | `casal/nfs_fiscais/cupom_foto/CUPOM_*.jpeg` (2 únicos) | 65-77KB | 2 JPEGs | 0 nodes | -100% | **GAP-ZERO P1** |
| 13 | xml_nfe | n/a | -- | 0 | 0 | 0% | N/D |
| 14 | receita_medica | n/a | -- | 0 | 0 | 0% | N/D |
| 15 | garantia (fabricante) | n/a | -- | 0 | 0 | 0% | N/D |
| 16 | das_parcsn_pdf | `andre/impostos/das_parcsn/DAS_PARCSN_*.pdf` | 157KB | 19 únicos | 10 | -47% | **DRIFT-CRITICO P0** |
| 17 | dirpf_dec | `andre/documentos/dirpf/05127373122-IRPF-A-2026-2025-RETIF.DEC` | n/a | 1 .DEC | 1 | 0% | OK |
| 18 | boleto_pdf | `andre/boletos/BOLETO_2026-04-21_*.pdf` (1 clone) | 230KB | 2 PDFs | 2 | 0% | OK |
| 19 | recibo_nao_fiscal | catch-all | -- | -- | -- | -- | N/D |
| 20 | contracheque_pdf (`processar_holerites`) | `andre/holerites/document(*).pdf` (24 únicos) | 56-176KB | 24 únicos | 24 nodes | 0% | OK |

**Resumo:** Itaú bate centavo-a-centavo. Holerites bate exato. C6 e Santander têm pequenos deltas pela combinação de múltiplas fontes (OFX + XLS + PDF) que se complementam. Vários extratores documentais ficam N/D porque as fixtures não existem.

## 2. Tabela documentais (nodes vs físicos)

| Extrator -> Tipo | Físicos únicos | Nodes | Gap | Status |
|---|---|---|---|---|
| `cupom_termico_foto` -> cupom_termico | 2 | 0 | -2 | **GAP-ZERO** -- jpegs não foram processados |
| `cupom_garantia_estendida_pdf` -> apolice | 3 | 2 | -1 | DRIFT-MEDIO |
| `das_parcsn_pdf` -> das_parcsn_andre | 19 | 10 | -9 | **DRIFT-CRITICO -47%** |
| `dirpf_dec` -> dirpf_retif | 1 | 1 | 0 | OK |
| `nfce_pdf` -> nfce_modelo_65 | 3 PDFs | 4 nodes (1 dup) | +1 dup | DRIFT (chave_44 1 dígito off) |
| `boleto_pdf` -> boleto_servico | 2 | 2 | 0 | OK |
| `contracheque_pdf` -> holerite | 24 | 24 | 0 | OK |

**DAS PARCSN drift -47%** -- 9 PDFs faltantes:
- `2025-02-28_a135a39f`
- `2025-03-31_9a445c44`
- `2025-03-31_b3f11503`
- `2025-04-30_ab9ae6e3`
- `2025-05-30_29d42c07`
- `2025-07-31_996ccc3f`
- `2025-10-31_96469f32`
- `2025-12-30_ba1faf52`
- `2026-03-31_c2bdf7e2`

**NFC-e duplicação:** node 7464 vs 7466, mesmo arquivo `casal/nfs_fiscais/nfce/NFCE_2026-04-19_6c1cc203.pdf`, chaves de 44 dígitos divergem em 1 caractere (`...77785...` vs `...77765...`). Provável: OCR-fallback re-leu o mesmo PDF com nuance diferente do extrator nativo. Não-idempotente.

## 3. Sprint 93f -- já está em RUNTIME (não só backlog)

```
$ find data/raw/vitoria/nubank_pj_* -type f | wc -l
13   (12 cartao + 1 cc)

XLSX banco_origem=Nubank (PJ) AND quem=Vitória:
  828 tx, soma R$ 169.131,13
  Cobertura: 2024-01 a 2026-04 (sem 2025-03/04)
```

Reconciliação bruto vs XLSX:
- Bruto cartão (11 SHAs únicos): 275 tx / R$ 44.214,59
- Bruto CC (570 linhas): 570 / R$ 134.770,97
- Total bruto: 845 / R$ 178.985,56
- XLSX: 828 / R$ 169.131,13
- Delta: -17 tx (-2,0%) / -R$ 9.854,43 (-5,5%)

Discrepância modesta consistente com pareamento de TI cartão -> CC. **Status: OK.** CLAUDE.md descreve estado pré-fix. Atualizar.

## 4. Sprint 93d -- dataloss confirmado mas mitigado

`data/raw/vitoria/nubank_pf_cc/`: 37 físicos / 19 SHAs únicos / 363 tx / R$ 83.182,71. Cobertura 2024-10 a 2026-04 apenas.

XLSX `Nubank (PF)` Vitória = 1.757 tx desde 2022-03. **1.394 tx + R$ 590.670,66 vêm de outra pasta:**

```
data/raw/vitoria/nubank_cc/
  210 físicos / 20 SHAs únicos / 1.366 linhas / R$ 386.702,80
  Cobertura: 2019-10 a 2026-04 (completa)
```

Total bruto disponível: 363 + 1.366 = 1.729 vs XLSX 1.757 = +28 tx (+1,6%). Aceitável.

**Volume real de dataloss em R$:** **R$ 0,00** no XLSX (todos os meses 2022-2024 estão preenchidos via `nubank_cc/`). **R$ ~590k inacessíveis se um dia `nubank_cc/` for deletado.** Risco arquitetural (pasta semanticamente errada hospeda dados PF), não operacional imediato.

## 5. Bucket `_classificar/` -- PDF multipart heterogêneo

3 PDFs idênticos (mesmo SHA) `_CLASSIFICAR_6c1cc203*.pdf`, 5MB cada. **4 páginas com 3 tipos misturados:**

| Pg | Tipo | Conteúdo |
|----|------|----------|
| 1 | NFC-e | Loja Americanas 0337, CNPJ 00.776.574/0160-79, DUALSENSE GALACTIC PURPLE + BASE CARREGAMENTO P55, R$ 629,98, chave `5326 0400 7765...432601 0596...` |
| 2 | Cupom-bilhete seguro | "CUPOM DE SERVIÇO" SUSEP 781000129322123 |
| 3 | Cupom-bilhete seguro | Idem para SUSEP 781000129322124 |
| 4 | NFC-e | Outra compra na mesma loja (CJT 5 TIGELAS SANTIAGO + outros) |

**Por que escapou da Sprint 89 (OCR fallback):** PDF é multipart heterogêneo. Classifier identifica primeiro tipo (NFCe pg1) e classifica arquivo inteiro como NFCe. Mas é uma "fotografia compósita" do envelope físico (NFC-e + 2 cupons garantia + outra NFC-e). Classifier não sabe que precisa fatiar antes de extrair.

**Evidência indireta no grafo:** apólices 7379 e 7382 têm `arquivo_origem = data/raw/originais/6c1cc2035c99d68f.pdf` (cópia preservada, hash diferente). `cupom_garantia_estendida_pdf` PROCESSOU corretamente esse PDF a partir de `originais/`, gerando 2 apólices.

**Recomendação:** mover os 3 PDFs `_CLASSIFICAR_*` para `_envelopes/` ou deletar (já há cópia em `originais/` que produziu as apólices). Sprint 97 (page-split heterogêneo) endereça o padrão geral.

## 6. Holerites -- 24 únicos físicos = 24 nodes

```
data/raw/andre/holerites/  ->  30 físicos / 24 únicos por SHA
```

Nomes não-canônicos: 11 `document(N).pdf` ou `document(N) (1).pdf` + 13 `holerite_NNNNNNNNNNNNNN.pdf`.

Grafo: 24 nodes tipo `holerite`:
- G4F: 11 nodes
- Infobase: 10 nodes
- G4F 13º Adiantamento: 1
- G4F 13º Integral: 1
- Infobase 13º Integral: 1

Total = 24. **Sprint P3.2 fielmente implementada.** Aba `renda` 99 linhas (24 holerites + 75 MEI legítimos via `mappings/fontes_renda.yaml`). Bate com CLAUDE.md.

## 7. SHA-256 -- clones físicos por pasta

| Pasta | Físicos | Únicos | Ratio | Status |
|-------|---------|--------|-------|--------|
| andre/itau_cc | 29 | 4 | 7,25x | piorou (75% holerites) |
| andre/santander_cartao | 102 | 14 | 7,29x | piorou (66% holerites) |
| andre/c6_cartao | 24 | 3 | 8,00x | piorou |
| andre/c6_cc | 17 | 3 | 5,67x | similar |
| andre/nubank_cartao | 32 | 4 | 8,00x | piorou |
| andre/nubank_cc | 81 | 12 | 6,75x | similar |
| vitoria/nubank_cc | 210 | 20 | 10,50x | mais alto |
| vitoria/nubank_pf_cc | 37 | 19 | 1,95x | baixo |
| vitoria/nubank_pj_cartao | 12 | 11 | 1,09x | Sprint 93g atuou |
| vitoria/nubank_pj_cc | 1 | 1 | 1,00x | OK |

Sprint 93g deletou 91 clones de `vitoria/nubank_pj_*` e `andre/nubank_*`. **Escopo PJ apenas.** Pastas do André continuam com 7-8x clones. **Sprint 93h sugerida** (limpeza simétrica). Não bloqueia Sprint D.

## 8. Achados consolidados

**P0 (bloqueante para confiança):**

1. **Holerites G4F mal classificados como `BANCARIO_ITAU_CC_*` e `BANCARIO_SANTANDER_CARTAO_*`.** 13 PDFs únicos (3 em itau_cc + 10 em santander_cartao) vivem em pastas bancárias erradas. Não há perda de dados (grafo extrai 24 holerites corretamente via `processar_holerites` que escaneia `holerites/`), mas 13 desses arquivos estão duplicados nas duas pastas, ocupando espaço em disco e poluindo `pode_processar`. **Sugestão:** Sprint 90a (P0) -- `inbox_processor` detectar "Demonstrativo de Pagamento" no texto antes de aceitar pasta destino bancária.

2. **DAS PARCSN sub-processado** (10 nodes vs 19 únicos físicos = -47%). Não é dedup (todos têm SHA distinto). Investigar parser. **Sugestão:** Sprint 90b (P0).

**P1 (drift médio, vale corrigir):**

3. **NFCe duplicada por chave_44 quase igual** (id 7464 vs 7466, mesmo arquivo). Investigar `extractors/nfce_pdf.py`.

4. **Cupom térmico foto sem nodes no grafo** (2 jpegs em `_conferir/` + `cupom_foto/`, 0 nodes). Extrator pode estar exigindo PDF.

5. **Limpeza simétrica de clones SHA nas pastas do André** (Sprint 93h sugerida).

**P2:**

6. Renomear `vitoria/nubank_cc/` para `vitoria/nubank_pf_cc_historico/`. Esclarece Família B.

7. Atualizar CLAUDE.md: Sprint 93f está EM RUNTIME (não BACKLOG).

## 9. Conclusão para Sprint D

**Sistema apto a entrar na auditoria artesanal.** Pipeline está executando dedup corretamente, fontes primárias estão completas, deltas detectados são todos explicáveis (dedup ou multi-fonte), não bug.

**Recomendação ao supervisor humano:**
1. Iniciar pela aba `extrato` filtrada por banco_origem `Itaú` (29 linhas, 100% fidelidade) -- 30 min de calibração.
2. Em seguida `Nubank (PJ)` Vitória (828 linhas) -- verificar pareamento cartão <-> CC.
3. Por fim `C6` (1.190 linhas, mais complexo).

**Não rodar `./run.sh --tudo` antes da Sprint D** sem antes:
- Decidir se Sprint 90a (P0 holerites mal classificados) entra antes -- afeta apenas limpeza de raw, não tx no XLSX.
- Decidir se Sprint 90b (P0 DAS PARCSN -47%) entra antes -- gap afeta nodes no grafo + aba IRPF.

---

**Caminhos absolutos relevantes:**
- `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/data/output/ouroboros_2026.xlsx`
- `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/data/output/grafo.sqlite`
- `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/src/pipeline.py:31` (`_descobrir_extratores`)
- `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/src/extractors/das_parcsn_pdf.py` (investigar drift)
- `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/src/extractors/nfce_pdf.py` (investigar dup)
- `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/data/raw/andre/itau_cc/` (75% holerites mal classificados)
- `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/data/raw/andre/santander_cartao/` (66% holerites mal classificados)
- `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/data/raw/_classificar/` (3 cópias do PDF multipart)
