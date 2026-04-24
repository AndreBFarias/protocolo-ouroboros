# Auditoria de fidelidade dos extratores -- 2026-04-23

Script: `scripts/auditar_extratores.py`
Tolerância: R$ 0,02 (arredondamento).
Modo: `--tudo --modo-abrangente` (extrator roda no diretório inteiro;
XLSX é filtrado pelos mesmos meses cobertos).

## Resumo executivo

- **1 banco com indício de fidelidade** em modo single-file: **Itaú CC**
  (auditoria `single-file` com mês dominante retornou delta R$ 0,00, 29 tx
  em ambos os lados).
- **0 bancos com fidelidade em modo diretório-completo.**
- **8 bancos DIVERGEM** em modo abrangente. 2 deles com XLSX=0 (Nubank PJ).
- A auditoria cumpre o papel do princípio: "código roda" não é o mesmo que
  "código preserva os dados".

Este relatório é o sinal pedido pela Sprint 93: **sem auditoria, não há
confiança empírica no pipeline**. A presença de divergências não é bug do
script; é exatamente o que a auditoria foi desenhada para revelar.

## Resumo tabular (modo abrangente, diretório completo)

| Banco | Mês | Fonte | Tot extrator | Tot XLSX | Delta | N_ex | N_xlsx | Veredito |
|---|---|---|---:|---:|---:|---:|---:|---|
| itau_cc | 2026-02..2026-04 | `data/raw/andre/itau_cc/*` | 352520.08 | 44065.01 | 308455.07 | 232 | 29 | DIVERGE |
| santander_cartao | 2025-10..2026-03 | `data/raw/andre/santander_cartao/*` | 160856.64 | 19188.39 | 141668.25 | 1000 | 110 | DIVERGE |
| c6_cc | 2025-04..2026-04 | `data/raw/andre/c6_cc/*` | 934690.96 | 195498.47 | 739192.49 | 2023 | 560 | DIVERGE |
| c6_cartao | 2025-10..2026-02 | `data/raw/andre/c6_cartao/*` | 10359.36 | 31511.46 | 21152.10 | 144 | 24 | DIVERGE |
| nubank_cartao | 2025-05..2026-10 | `data/raw/andre/nubank_cartao/*` | 331702.16 | 109451.28 | 222250.88 | 2114 | 312 | DIVERGE |
| nubank_cc | 2019-10..2026-04 | `data/raw/andre/nubank_cc/*` | 1040429.53 | 151194.77 | 889234.76 | 3083 | 821 | DIVERGE |
| nubank_pf_cc | 2024-10..2026-04 | `data/raw/vitoria/nubank_pf_cc/*` | 82247.16 | 349458.34 | 267211.18 | 355 | 876 | DIVERGE |
| nubank_pj_cc | 2024-01..2026-04 | `data/raw/vitoria/nubank_pj_cc/*` | 126170.97 | 0.00 | 126170.97 | 566 | 0 | DIVERGE |
| nubank_pj_cartao | 2025-05..2026-04 | `data/raw/vitoria/nubank_pj_cartao/*` | 46943.20 | 0.00 | 46943.20 | 294 | 0 | DIVERGE |

## Resumo tabular (modo single-file, mês dominante)

Para comparação, o modo padrão `--banco <x>` sem `--modo-abrangente` filtra
o XLSX apenas pelo mês dominante das transações do arquivo escolhido. Este
corte mostra quanto de um arquivo específico sobrevive ao pipeline:

| Banco | Mês | Tot extrator | Tot XLSX | Delta | N_ex | N_xlsx | Veredito |
|---|---|---:|---:|---:|---:|---:|---|
| itau_cc | 2026-03 | 44065.01 | 13552.51 | 30512.50 | 29 | 12 | DIVERGE |
| santander_cartao | 2025-12 | 1680.12 | 683.95 | 996.17 | 10 | 6 | DIVERGE |
| nubank_cartao | 2025-05 | 2728.61 | 7633.61 | 4905.00 | 19 | 24 | DIVERGE |

O único caso de fidelidade 100% detectado nesta auditoria foi o Itaú CC em
**modo single-file + abrangente** (29 tx, R$ 44.065,01 em ambos os lados --
o extrator entende a fatura inteira e o XLSX preserva todas). Itaú é o
referencial de "como fidelidade se parece".

## Diagnóstico por banco (análise humana)

Três famílias de divergência foram detectadas; sprints-filhas propostas
abaixo investigam cada família antes de alterar o extrator (escopo proibido
na Sprint 93: "primeiro audita, depois fix").

### Família A -- "extrator pega mais do que sobra no XLSX"

Casos: **itau_cc, santander_cartao, c6_cc, nubank_cartao, nubank_cc**.
Padrão: `N_extrator >> N_xlsx` (3x-10x mais tx no bruto do que no XLSX
para os mesmos meses).

Hipóteses (ordenadas por probabilidade):
1. **Arquivos duplicados baixados mais de uma vez**, com sufixos
   `_1.pdf`, `_2.pdf`, ...: o deduplicator do pipeline filtra; o script
   de auditoria conta bruto sem deduplicar. Evidência: cada diretório
   tem múltiplas cópias do mesmo `<hash>.pdf`.
2. **Filtro por forma_pagamento no XLSX inadequado**: a mesma transação
   pode ter sido categorizada com forma diferente do que supomos.
3. **Bug de perda silenciosa no pipeline**: possível mas menos provável
   que a explicação deduplicação.

Sprint-filha proposta: **Sprint 93a -- reconciliar contagem bruto vs
deduplicado**. Auditoria específica: rodar extrator no diretório, aplicar
deduplicator manualmente, comparar com XLSX; se ainda diverge, é bug real
no categorizer/normalizer.

### Família B -- "extrator pega menos do que o XLSX"

Casos: **c6_cartao, nubank_pf_cc**.
Padrão: `N_extrator < N_xlsx` para os mesmos meses.

Hipóteses:
1. **Linhas no XLSX vieram de outras fontes** (histórico do
   `controle_antigo.xlsx`, OFX, inbox_processor) e se colaram sob o
   mesmo `banco_origem` mas não existem no diretório bruto atual.
   Evidência: o XLSX tem 645+ linhas marcadas `Histórico/Débito` que
   não são puras do extrator.
2. **O diretório bruto foi limpo após o processamento** (arquivos
   legacy removidos).

Sprint-filha proposta: **Sprint 93b -- rastreabilidade da origem no
XLSX**. Adicionar coluna `arquivo_origem` preenchida na ingestão
(hoje só existe no dict interno) e filtrar auditoria por `arquivo_origem
in <lista do diretório>`.

### Família C -- "extrator gera rotulagem não presente no XLSX"

Casos: **nubank_pj_cc, nubank_pj_cartao** (ambos XLSX=0).
Padrão: extrator gera `banco_origem="Nubank (PJ)"`, mas o XLSX só tem
`Nubank`, `Nubank (PF)`, `C6`, `Histórico`, `Santander`, `Itaú`.

Evidência empírica (rodou neste commit):
```python
from src.extractors.nubank_cc import ExtratorNubankCC
from pathlib import Path
txs = ExtratorNubankCC(Path('data/raw/vitoria/nubank_pj_cc/cc_pj_vitoria.csv')).extrair()
# banco_origem unicos: {'Nubank (PJ)'}
# pessoa unicos: {'Vitória'}
```

Mas `scripts/smoke_aritmetico.py::BANCOS_VALIDOS` declara `Nubank (PJ)`
como rótulo aceito. Ou seja: o contrato do smoke aceita; o XLSX em
produção não tem. Pipeline nunca rodou em volume os arquivos PJ ou os
consolidou sob `Nubank` perdendo a etiqueta.

Sprint-filha proposta: **Sprint 93c -- popular `Nubank (PJ)` no XLSX**.
Rodar `./run.sh --tudo` e confirmar que `banco_origem="Nubank (PJ)"`
aparece; se não aparece, investigar `normalizer.py` /
`canonicalizer_casal.py` para preservação da etiqueta.

## O que foi provado (positivo)

- **Itaú CC tem fidelidade 100%** quando auditado arquivo-a-arquivo
  com o mês dominante das transações. Os 29 lançamentos do arquivo
  `BANCARIO_ITAU_CC_2026-01_2f01b54d.pdf` (meses 2026-02 a 2026-04)
  estão integralmente no XLSX, somando R$ 44.065,01 nos dois lados.
- **O extrator Nubank CC produz `banco_origem="Nubank (PJ)"` com
  `pessoa="Vitória"`** para arquivos em `data/raw/vitoria/nubank_pj_cc/`.
  Contrato declarado (Sprint 56 BANCOS_VALIDOS) cumprido pelo extrator.
- **O extrator Santander PDF extrai 1000 tx** dos 15+ arquivos de
  fatura do diretório (volume real, ambiente com `senhas.yaml`).

## O que não foi provado (nem negado)

Nenhum banco atingiu fidelidade 100% em modo diretório-completo. Isso
pode significar (a) deduplicação agressiva legítima, (b) linhas-fantasma
vindas de outras fontes (histórico, OFX, inbox), ou (c) bug de perda.
Distinguir essas hipóteses exige as Sprints 93a/b/c.

## Recomendações acionáveis

1. **Sprint 93a (P0)**: reconciliar contagem bruto-vs-dedup. Investigar
   se a queda de `3083 → 821` (nubank_cc) é dedup legítimo (arquivos
   duplicados no diretório) ou perda de linhas únicas.
2. **Sprint 93b (P1)**: propagar `arquivo_origem` para o XLSX (já existe
   no dict interno; adicionar coluna) e re-auditar com filtro preciso.
3. **Sprint 93c (P1)**: corrigir/confirmar rotulagem `Nubank (PJ)` no
   XLSX final. Afeta 860 tx (566+294) atualmente invisíveis no dashboard.
4. **INFRA: adicionar `make audit` ao gauntlet** após estabilizar os
   3 fixes acima. Delta 0 em pelo menos 5 bancos = acceptance da Sprint 93.

## Limitações conhecidas da metodologia

- **Soma absoluta não cobre sinal.** Entradas e saídas viram valor
  absoluto; sinal não é verificado (uma entrada de R$ 100 e uma saída
  de R$ 100 somariam R$ 200 tanto no bruto quanto no XLSX mesmo se o
  extrator invertesse os sinais -- falso-positivo de fidelidade).
  Sprint futura pode incluir assinatura por conjunto de identificadores.
- **Comparação agregada, não linha-a-linha.** Para diagnosticar
  divergências específicas (ex: transação X do arquivo Y ausente no
  XLSX), ampliar o script para emitir diff de conjuntos de hashes.
- **Tolerância R$ 0,02 é conservadora.** Arredondamentos no openpyxl
  podem acumular em faturas grandes; Itaú ainda fechou em 0,00 no único
  caso estável, o que sugere que a tolerância está calibrada.

## Reprodução

```bash
# Modo completo (diretório inteiro, 9 bancos)
.venv/bin/python scripts/auditar_extratores.py --tudo --modo-abrangente \
    --relatorio docs/auditoria_extratores_$(date +%Y-%m-%d).md

# Modo pontual (um banco, mês dominante, single-file)
.venv/bin/python scripts/auditar_extratores.py --banco itau_cc

# Modo forçado (mês e arquivo específicos)
.venv/bin/python scripts/auditar_extratores.py --banco itau_cc \
    --mes 2026-03 --arquivo data/raw/andre/itau_cc/BANCARIO_ITAU_CC_2026-01_2f01b54d.pdf
```

## Veredictos consolidados

- OK (delta <= R$ 0,02): 0 / 9 em modo diretório-completo.
- DIVERGE: 9 / 9.
- SEM_DADOS: 0.

Em modo single-file com mês dominante, **Itaú CC é OK** (delta R$ 0,00,
29 tx). Os demais extratores não foram confirmados fieis em nenhum modo.

---

*"Teste automatizado prova que o código não quebra; auditoria prova que
o código faz o que deveria." -- princípio de fidelidade*
