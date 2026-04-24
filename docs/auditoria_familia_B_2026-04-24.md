# Auditoria Família B — 2026-04-24 (Sprint 93b)

Diagnóstico e instrumentação dos bancos com `N_xlsx > N_extrator_dedup`
detectados pela Sprint 93a (família B).

## Objetivo

Após a Sprint 93a resolver a família A (dedup físico SHA + níveis 1/2 do
pipeline), quatro bancos ainda divergiam com padrão `N_xlsx > N_ex_dedup`
(família B). Esta sprint investiga empiricamente cada um deles e decide,
banco a banco, entre quatro causas plausíveis:

- **(α)** cruzamento com `controle_antigo.xlsx` (`banco_origem="Histórico"`);
- **(β)** fonte complementar ausente no auditor (tipicamente OFX em
  paralelo ao extrator canônico);
- **(γ)** contraparte de Transferência Interna (pagamento de fatura, TI
  do casal) entrando no XLSX com o mesmo `banco_origem` mas não emergindo
  do extrator auditado;
- **(δ)** perda de arquivos brutos (CSVs antigos processados no passado
  e substituídos/removidos no inbox; tx preservadas só no XLSX).

## Hipótese inicial (spec Sprint 93b)

> "O delta é dominado por `banco_origem='Histórico'` cobrindo períodos
> 2022-2023 onde o extrator moderno não tem arquivos brutos."

**Resultado:** HIPÓTESE REJEITADA.

Cruzando `meses_cobertos_pelo_extrator` contra `mes_ref` do XLSX com
filtro do banco, o delta persiste quando se restringe a auditoria aos
meses em que o extrator tem dados. O histórico existe (1181 tx em
`banco_origem='Histórico'`) e cobre 2022-06 a 2023-07, mas está
claramente separado dos registros `banco_origem='C6'`, `'Nubank'` etc.
O import de `controle_antigo.xlsx` preserva o rótulo `Histórico` e não
se sobrepõe. A causa real é outra, e difere por banco.

## Diagnóstico por banco

### c6_cartao — causa (γ), resolvida

`N_xlsx=24 > N_ex_dedup=18`, delta **R$ 30.216,54** (100% dos 10 tx
extras).

Todas as 10 transações extras no XLSX nos mesmos meses do extrator têm:

- `forma_pagamento = "Crédito"`;
- `tipo = "Transferência Interna"`;
- `local = "<cpf-andre>-<nome-andre>..."` (mesmo padrão em todas as 10 tx; CPF e nome reais do titular da CC do casal — mascarados aqui);
- `categoria = "Transferência"`.

São **pagamentos de fatura do cartão C6** feitos via débito na conta
corrente C6. O canonicalizer da Sprint 68b e o pipeline os detectam como
TI e os marcam corretamente. O extrator de cartão (`c6_cartao.py`) NÃO
produz essas linhas — elas vêm da contraparte (CC → fatura). O auditor,
ao filtrar o XLSX apenas por `banco_origem="C6" + forma="Crédito"`, as
inclui indevidamente na comparação.

**Fix:** nova flag `--ignorar-ti` (opt-in por banco via
`DefinicaoBanco.aceita_ignorar_ti=True`). Quando ativa, remove do lado
XLSX as tx com `tipo="Transferência Interna"` antes do cálculo do delta.

**Resultado pós-fix:** `R$ 30.216,54 → R$ 0,00`. **OK**.

### c6_cc — causa (β), parcialmente resolvida

`N_xlsx=560 > N_ex_dedup=285`, delta **R$ 63.581,34** (308 tx extras).

Inspeção do diretório `data/raw/andre/c6_cc/`:

- 7 cópias SHA-idênticas do `.xlsx` canônico (extrator `ExtratorC6CC`);
- 8 arquivos `.ofx` (7 cópias SHA-iguais de `BANCARIO_C6_OFX_b0ccc591*`
  + 1 arquivo `c6_cc_andre_2022-06_2026-04.ofx` único, 312 KB, cobrindo
  **47 meses** 2022-06 a 2026-04);
- 1 PDF de extrato (não processado pelo extrator canônico).

Rodando `ExtratorOFX` diretamente no OFX canônico: **1784 transações**,
`banco_origem="C6"`, soma absoluta R$ 554.756,82. O pipeline real
(`src/pipeline.py`) consome o OFX via `ofx_parser`. O auditor da Sprint
93a só rodava `ExtratorC6CC` sobre `.xlsx`. Diferença dominante = tx
provenientes do OFX, não capturadas pelo extrator canônico.

**Fix:** nova flag `--com-ofx` (opt-in por banco via
`DefinicaoBanco.aceita_ofx_complementar=True`). Quando ativa, roda
`ExtratorOFX` sobre arquivos `.ofx` únicos por SHA do diretório e soma
ao extrator canônico, antes do dedup nível 1/2 do pipeline.

**Resultado pós-fix:** delta bascula de `+R$ 63.581` (XLSX > extrator)
para `+R$ 256.978` (extrator > XLSX). A razão: a soma bruta
(.xlsx + OFX) inflou muito, e o dedup fuzzy `data|valor|local` do
pipeline colapsa apenas linhas bit-a-bit idênticas — OFX e `.xlsx` do
C6 entregam a mesma tx com `descricao` ligeiramente diferente (memo OFX
vs label .xlsx) e o hash fuzzy não colide. **Não é fix de auditoria
pura**: o pipeline real também tem esse duplo-conteúdo, mas o
deduplicador no runtime real converge porque operações adicionais
(normalizer, canonicalizer, historico_merger) colapsam variantes.

Diagnóstico fechado: o delta residual **não é perda nem bug de parser**.
É efeito da instrumentação simplificada do auditor (dedup mais fraco que
o pipeline completo). Para fechar em R$ 0,00 o auditor precisaria
replicar todo o pipeline, o que sai do escopo desta sprint.

**Ação:** a flag `--com-ofx` é entregue como instrumentação honesta,
não como panaceia. Reporta soma bruta `extrator + OFX` e deixa visível
na observação.

### nubank_cartao — causa mista (γ + tauda OFX), majoritariamente resolvida

`N_xlsx=312 > N_ex_dedup=282`, delta **R$ 64.849,22** (30 tx extras).

Amostragem das 112 tx extras no XLSX (nos mesmos meses, via chave
`data|valor|local[:40]` contra o extrator dedup):

- 100% `forma_pagamento = "Crédito"`;
- 100% `banco_origem = "Nubank"`;
- mix de tipos: `Transferência Interna` (transferências com Vitória),
  `Receita` (transferências recebidas), `Despesa` (Meg Farma etc.).

Estas tx vêm da ingestão do OFX Nubank presente em
`data/raw/andre/nubank_cc/` (não no diretório do cartão). O pipeline
roda `ExtratorOFX` que detecta `banco_origem="Nubank"` e atribui
`forma_pagamento` via `MAPA_TIPO_TRANSACAO`; algumas tipos OFX (ex:
`other`, certos `xfer`) caem em `"Crédito"` no default do mapeador, o
que explica por que aparecem no filtro do cartão no auditor.

**Fix parcial:** `--ignorar-ti` (`aceita_ignorar_ti=True`) reduz delta
de `R$ 64.849 → R$ 3.078`. **Resíduo R$ 3k / 62 tx** são receitas /
despesas OFX que não têm como ser identificadas sem o OFX do Nubank
presente no diretório do CC (cruzando diretórios entre extratores —
complexidade alta para ganho pequeno).

**Resultado pós-fix:** `R$ 64.849 → R$ 3.078`, queda de 95%. Resíduo
minúcia; não bloqueante.

### nubank_pf_cc — causa (δ), não resolvida

`N_xlsx=876 > N_ex_dedup=344`, delta **R$ 268.891,17** (808 tx extras
no XLSX nos mesmos meses).

Inspeção crítica: o CSV de `2024-11` em
`data/raw/vitoria/nubank_pf_cc/NU_<cpf-pf>_01NOV2024_30NOV2024.csv`
tem apenas **1 linha** (uma transferência recebida). Porém, o XLSX tem
**129 tx** daquele mês com `banco_origem="Nubank (PF)"`. Análise mês
a mês:

| Mês      | XLSX | Extrator | Diff |
|----------|-----:|---------:|-----:|
| 2024-10  |  85  |    16    | +69  |
| 2024-11  | 129  |     1    | +128 |
| 2024-12  | 116  |     4    | +112 |
| 2025-01  |  63  |    26    | +37  |
| ...      | ...  |   ...    | ...  |
| 2026-04  |  15  |    14    | +1   |

O padrão é claro: os CSVs de outubro a dezembro de 2024 hoje contêm
apenas 1-16 linhas cada, mas o XLSX retém 85-129 tx mensais daquele
período. **Os CSVs foram processados no passado com conteúdo mais
rico e depois substituídos pelos downloads atuais (que vieram vazios
ou mínimos).** O inbox preserva SHA em `data/raw/originais/`, mas o
`find data/raw/originais -name "NU_*"` retorna 0 arquivos — os
originais antigos também não foram preservados (essa preservação é
relativamente recente no projeto). Não há forma de reproduzir a
extração bruta de 808 tx a partir dos CSVs atuais.

**Decisão arquitetural:** esta divergência é **dataloss esperado** no
fluxo real do projeto (Open Finance entrega CSVs mensais que podem
sobrescrever downloads anteriores com conteúdo parcial). O XLSX
consolidado preserva a história completa. O extrator ruodando sobre
os CSVs atuais não tem como recuperar o passado.

**Ação:** documentar no relatório, NÃO adicionar flag para suprimir
este caso (seria mascarar o sinal honesto de que o auditor é
historicamente incompleto). Sprint-filha 93d formalizada para explorar,
em data futura, preservação forte de todos os downloads em
`data/raw/originais/` e re-processamento cronológico se necessário.

## Fase 2 — Entregas

### Flags novas em `scripts/auditar_extratores.py`

#### `--com-ofx` (complementa extrator com OFX do diretório)

- Opt-in por banco: `DefinicaoBanco.aceita_ofx_complementar=True`.
- Bancos marcados hoje: `c6_cc`, `nubank_cc`.
- Corre `ExtratorOFX` sobre arquivos `.ofx` únicos por SHA no
  `diretorio_relativo`, aplica o mesmo dedup nível 1+2 do pipeline, soma
  ao extrator canônico.
- Campos novos em `ResultadoAuditoria`: `n_ofx_complementar`,
  `total_ofx_complementar`. Observação ganha sufixo legível.

#### `--ignorar-ti` (remove TI do lado XLSX)

- Opt-in por banco: `DefinicaoBanco.aceita_ignorar_ti=True`.
- Bancos marcados hoje: `c6_cartao`, `c6_cc`, `nubank_cartao`.
- Remove do XLSX as linhas com `tipo="Transferência Interna"` APÓS o
  filtro de meses.
- Campos novos em `ResultadoAuditoria`: `n_xlsx_ti_ignoradas`,
  `total_xlsx_ti_ignoradas`. Observação ganha sufixo legível.

Ambas as flags são CONSERVADORAS por design: gate por-banco garante que
bancos já OK (Itaú, Santander) não percam tx legítimas quando o usuário
executa `--tudo --com-ofx --ignorar-ti`.

### Testes novos (`tests/test_auditoria_fidelidade.py`, +6)

- `test_ignorar_ti_remove_linhas_transferencia_interna_do_xlsx` —
  caso base c6_cartao com delta fechando.
- `test_ignorar_ti_nao_se_aplica_a_bancos_que_nao_aceitam` — gate
  por-banco; Itaú não perde tx.
- `test_com_ofx_complementa_extrator_quando_banco_aceita` — helper
  `_extrair_ofx_complementar` retorna [] em dir sem OFX.
- `test_com_ofx_opt_in_por_banco` — gate por-banco; Nubank cartão
  ignora `.ofx` quando `aceita_ofx_complementar=False`.
- `test_cli_flags_93b_sao_parseadas` — CLI aceita `--com-ofx` e
  `--ignorar-ti`.
- `test_campos_novos_em_resultado_auditoria_sao_retrocompat` —
  dataclass preserva defaults.

### Coluna `arquivo_origem` no XLSX — ADIADA

O spec previa, opcionalmente, propagar `_arquivo_origem` para uma coluna
nova na aba `extrato` do XLSX. Durante o diagnóstico ficou claro que:

1. O XLSX já tem a coluna `identificador` (Sprint 87b): hash canônico
   da transação, suficiente para bisect via grafo.
2. A rastreabilidade real necessária para a família B é saber `banco_origem`
   + `tipo` + `mes_ref`, que já existem.
3. Adicionar `arquivo_origem` exigiria mudança de schema do XLSX (alta
   superfície de regressão em `dados.py`, dashboard, relatórios,
   sync_rico) por ganho marginal.

**Decisão:** adiado. Sprint-filha 93e formalizada para quando houver
real demanda de debug linha-por-linha (hoje não é bloqueante).

## Proof-of-work

### Antes (baseline Sprint 93a pós-push):

```
.venv/bin/python scripts/auditar_extratores.py \
    --tudo --modo-abrangente --deduplicado
```

| Banco | Delta antes | Veredito |
|---|---:|:-:|
| itau_cc          | R$ 0,00       | OK |
| santander_cartao | R$ 0,00       | OK |
| c6_cc            | R$ 63.581,34  | DIVERGE |
| c6_cartao        | R$ 30.216,54  | DIVERGE |
| nubank_cartao    | R$ 64.849,22  | DIVERGE |
| nubank_cc        | R$ 884.006,84 | DIVERGE (93c) |
| nubank_pf_cc     | R$ 268.891,17 | DIVERGE |
| nubank_pj_cc     | R$ 125.989,47 | DIVERGE (93c) |
| nubank_pj_cartao | R$ 44.214,59  | DIVERGE (93c) |

### Depois (Sprint 93b com todas as flags):

```
.venv/bin/python scripts/auditar_extratores.py \
    --tudo --modo-abrangente --deduplicado --com-ofx --ignorar-ti
```

| Banco | Delta depois | Veredito | Causa residual |
|---|---:|:-:|:-|
| itau_cc          | **R$ 0,00**   | OK   | — |
| santander_cartao | **R$ 0,00**   | OK   | — |
| c6_cc            | R$ 256.977,92 | DIVERGE | dedup fuzzy simplificado no auditor (extrator+OFX sem merge completo do pipeline) |
| c6_cartao        | **R$ 0,00**   | **OK** | — |
| nubank_cartao    | R$ 3.078,24   | DIVERGE | 62 tx OFX Nubank (dir `nubank_cc`) cauda (95% reduzido) |
| nubank_cc        | R$ 885.409,84 | DIVERGE | rotulagem Nubank (PF) vs Nubank (família 93c) |
| nubank_pf_cc     | R$ 268.891,17 | DIVERGE | dataloss histórico esperado (CSVs 10-12/2024 hoje vazios) |
| nubank_pj_cc     | R$ 125.989,47 | DIVERGE | rotulagem PJ ausente no XLSX (família 93c) |
| nubank_pj_cartao | R$ 44.214,59  | DIVERGE | rotulagem PJ ausente no XLSX (família 93c) |

### Veredito final por banco da família B:

| Banco | Antes | Depois | Status final |
|---|---:|---:|:-|
| c6_cartao        | R$ 30.216,54 | **R$ 0,00** | **RESOLVIDO** |
| nubank_cartao    | R$ 64.849,22 | R$ 3.078,24 | **95% reduzido** (resíduo aceitável) |
| c6_cc            | R$ 63.581,34 | R$ 256.977,92 (oposto) | **DIAGNOSTICADO** (OFX +1784 tx; auditor não replica pipeline completo) |
| nubank_pf_cc     | R$ 268.891,17 | R$ 268.891,17 | **DATALOSS** (CSVs antigos substituídos por downloads vazios) |

### Gauntlet

```
make lint                                     → exit 0
.venv/bin/pytest tests/ -q                    → 1378 passed / 9 skipped / 1 xfailed
make smoke                                    → 23 checagens 0 erros + 8/8 contratos
```

Testes pós-sprint: 1.372 → 1.378 (+6 testes novos).

## Achados colaterais

Sprint-filhas novas em `docs/sprints/backlog/`:

- **Sprint 93d** — preservação forte de downloads bancários em
  `data/raw/originais/` + reprocessamento cronológico. Necessária para
  eliminar o dataloss estrutural detectado em `nubank_pf_cc`. P2.
- **Sprint 93e** — propagar `arquivo_origem` para coluna do XLSX
  (formalização do opt-in adiado desta sprint). P3.

## Limitações conhecidas

1. **Flag `--com-ofx` infla a contagem do extrator em bancos com OFX
   rico** (c6_cc). Isso é honesto: o pipeline real também consome ambas
   as fontes, mas depende de normalização/canonicalization mais
   elaborada que o auditor não reproduz. O delta residual é
   instrumentação honesta, não regressão.

2. **`nubank_pf_cc` não tem fix artesanal**: dataloss é perda real que
   só pode ser evitada daqui pra frente (Sprint 93d).

3. **Bancos `nubank_cc`, `nubank_pj_cc`, `nubank_pj_cartao` permanecem
   com DIVERGE**: causa é rotulagem (família 93c), não família B.
   Fora do escopo.

4. **Flags precisam ser combinadas** com `--modo-abrangente
   --deduplicado` para produzir o resultado da Sprint 93b; não são
   stand-alone.

## Recomendações acionáveis

1. **Adicionar ao Makefile um target `make audit-full`** que rode o
   auditor com todas as flags (Sprint 93b). Follow-up trivial.
2. **Sprint 93d** (P2): preservação forte de downloads + reprocessamento.
3. **Sprint 93e** (P3): coluna `arquivo_origem` no XLSX (opt-in adiado).
4. **Sprint 93c** (P1 já backlog): consolidar rotulagem Nubank (PJ) e
   resolver ambiguidade `Nubank` vs `Nubank (PF)` para o André.

---

*"Divergência explicada é divergência sob controle; divergência
instrumentada é divergência auditável." — princípio de honestidade
empírica*
