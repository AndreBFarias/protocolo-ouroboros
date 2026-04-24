# Auditoria Família A — 2026-04-24 (Sprint 93a)

Diagnóstico e fix da dedup agressiva nos 5 extratores bancários sinalizados
pela Sprint 93 (`docs/auditoria_extratores_2026-04-23.md` §Família A).

## Objetivo

Distinguir empiricamente três causas possíveis para `N_extrator >> N_xlsx`
observado no modo diretório-completo (`--modo-abrangente`):

- **(a)** dedup legítimo de duplicatas físicas (mesmo SHA-256 binário);
- **(b)** dedup legítimo de transações similares via hash `data|valor|local`;
- **(c)** bug de parser (hash composto colidente com conteúdo distinto);
- **(d)** perda de linha silenciosa no pipeline;
- **(e)** N_xlsx > N_extrator após dedup — famílias B/C desta Sprint 93.

## Hipótese testada

A Sprint 93 propôs que a maior parte do delta seria causa (a): arquivos
baixados várias vezes no inbox, renomeados pelo inbox_processor como
`<hash>_1.pdf`, `<hash>_2.pdf`, ... com conteúdo binário idêntico; o pipeline
real descarta via fluxo inbox-processor + dedup nível 1/2; o script de
auditoria contava bruto sem deduplicar.

## Fase 1 — Diagnóstico empírico

### Cópias físicas por SHA-256 nos diretórios bancários

Contagem real em `data/raw/<pessoa>/<banco>`:

| Banco | Arquivos físicos | SHA únicos | Duplicatas | % redundância |
|---|---:|---:|---:|---:|
| `itau_cc`          |  29 |  4 | 25 | 86% |
| `santander_cartao` | 102 | 14 | 88 | 86% |
| `c6_cc`            |   7 |  1 |  6 | 86% |
| `nubank_cartao`    | 116 | 15 | 101 | 87% |
| `nubank_cc`        |  69 | 11 | 58 | 84% |

Amostra direta (itau_cc, SHA `2f01b54d…`) — 8 cópias do mesmo PDF:

```
BANCARIO_ITAU_CC_2026-01_2f01b54d.pdf
BANCARIO_ITAU_CC_2026-01_2f01b54d_1.pdf
BANCARIO_ITAU_CC_2026-01_2f01b54d_2.pdf
BANCARIO_ITAU_CC_2026-01_2f01b54d_3.pdf
BANCARIO_ITAU_CC_2026-01_2f01b54d_4.pdf
BANCARIO_ITAU_CC_2026-01_2f01b54d_5.pdf
BANCARIO_ITAU_CC_2026-01_2f01b54d_6.pdf
itau_extrato_012026.pdf  # mesmo SHA, nome original do download
```

Confirma a hipótese (a) como dominante. 86% do bruto é redundância física.

### Como o extrator trata o diretório

Inspeção do código mostra que todos os 5 extratores, quando recebem um
diretório via `__init__`, fazem:

```python
return sorted(f for f in self.caminho.glob("*.<ext>")
              if self.pode_processar(f))
```

— ou seja, processam CADA arquivo físico, sem deduplicar por SHA. Como
o `scripts/auditar_extratores.py --modo-abrangente` passa o diretório
como caminho do extrator, ele multiplica as tx por ~7x. O pipeline
real é protegido porque o `inbox_processor` descarta cópias idênticas
antes de movê-las para `raw/`, e o `deduplicator` remove colisões
residuais por identificador/hash.

### Diagnóstico pós-dedup por banco

Comparando (i) N_extrator com diretório cru, (ii) após dedup SHA-256
do arquivo e (iii) após dedup nível 1+2 do pipeline, sempre contra o
total filtrado do XLSX em `data/output/ouroboros_2026.xlsx` para os
mesmos meses cobertos:

| Banco | N dir-cru | N pós-SHA | N pós-dedup | N XLSX | Delta pós-dedup | Causa |
|---|---:|---:|---:|---:|---:|:-:|
| `itau_cc`          |  232 |   29 |   29 |   29 | **R$ 0,00**    | (a) |
| `santander_cartao` | 1000 |  125 |  110 |  110 | **R$ 0,00**    | (a)+(b) |
| `c6_cc`            | 2023 |  289 |  285 |  560 | R$ 63.581,34   | (e) |
| `nubank_cartao`    | 2114 |  282 |  282 |  312 | R$ 64.849,22   | (e) |
| `nubank_cc`        | 3083 | 3083 | 3038 |  821 | R$ 884.006,84  | rotulagem |

Observações:

1. **`itau_cc` e `santander_cartao` fecham em R$ 0,00** após aplicar
   SHA-dedup + dedup nível 1/2 do pipeline. Causa raiz (a) para Itaú e
   (a)+(b) para Santander (o PDF do Santander repete cabeçalhos internos
   que o dedup por identificador sintético colapsa — 15 duplicatas nível 1
   observadas em runtime, ver log de execução).

2. **`c6_cc` e `nubank_cartao` agora mostram N_XLSX > N_extrator-dedup**.
   Ou seja, o XLSX tem MAIS linhas do que o diretório bruto + pipeline
   produziria hoje. Essas linhas extras vêm de outras fontes (histórico
   `controle_antigo.xlsx`, OFX, ingestões anteriores que limparam os
   brutos). **Isso é Família B/E, não Família A.** Sprint 93b já formalizada
   para propagar `arquivo_origem` ao XLSX e permitir auditoria linha-a-linha.

3. **`nubank_cc` é um caso especial**. O extrator já deduplica
   INTERNAMENTE por UUID do Nubank (`_identificador` nas linhas 102-106
   de `src/extractors/nubank_cc.py`), logo passar o diretório inteiro
   com cópias SHA iguais não infla a contagem — o extrator nativamente
   descarta duplicatas internas. O delta residual (3038 vs 821) decorre
   de OUTRA coisa: o extrator retorna `banco_origem="Nubank (PF)"`
   para TODAS as tx de `data/raw/andre/nubank_cc/` (ambiguidade da lógica
   interna), mas no XLSX consolidado o pipeline re-rotula esses registros
   em `Nubank` (André, 1266 tx) e `Nubank (PF)` com `pessoa="Casal"`
   (2310 tx). Isso é diagnóstico de rotulagem inconsistente, não de
   perda de linhas — Sprint 93c já proposta trata desse rótulo. Nenhum
   fix de parser é indicado aqui.

## Classificação final por banco (a/b/c/d/e)

| Banco | Causa | Ação |
|---|:-:|---|
| `itau_cc`          | (a)       | `--deduplicado` resolve. OK. |
| `santander_cartao` | (a) + (b) | `--deduplicado` resolve. OK. |
| `c6_cc`            | (e)       | Não é Família A. Sprint 93b pendente. |
| `nubank_cartao`    | (e)       | Não é Família A. Sprint 93b pendente. |
| `nubank_cc`        | rotulagem | Não é Família A. Sprint 93c pendente. |

Zero casos das hipóteses (c) bug de parser ou (d) perda silenciosa —
então NENHUM extrator foi modificado nesta sprint, conforme escopo
proibido do spec ("Aplicar fix sem antes documentar a causa raiz").

## Fase 2 — Entregas

### Enhancement — flag `--deduplicado` em `scripts/auditar_extratores.py`

Adicionada a flag `--deduplicado` que, quando combinada com
`--modo-abrangente`:

1. **SHA-dedup físico** — lista os arquivos do diretório, computa
   SHA-256 de cada um e preserva apenas a primeira ocorrência de
   cada hash único. Remove as ~86% de cópias físicas redundantes.

2. **Dedup nível 1 (identificador)** — converte cada `Transacao` do
   extrator em dict no formato esperado pelo `deduplicator` do
   pipeline e aplica `deduplicar_por_identificador`. Remove tx com
   UUID/hash canônico duplicado.

3. **Dedup nível 2 (hash fuzzy)** — aplica `deduplicar_por_hash_fuzzy`
   com a mesma chave `data|valor|local` usada em produção.

4. **Não aplica nível 3** — `marcar_transferencias_internas` só muda
   `tipo` de linhas, não remove. Soma absoluta ficaria igual.

Campos novos em `ResultadoAuditoria`: `arquivos_fisicos`,
`arquivos_unicos_sha`, `n_pos_dedup`, `total_pos_dedup`, `modo_dedup`.
A `observacao` ganha sufixo legível quando ativada (ex:
`"duplicatas removidas: 25"`).

Tocou 1 arquivo de produção (`scripts/auditar_extratores.py`) e
1 de testes (`tests/test_auditoria_fidelidade.py`, +6 testes novos).
Nenhum extrator foi modificado.

### Sem fixes de extrator

Nenhuma das 5 famílias caiu em causa (c) ou (d). O spec era explícito:
"Aplicar fix em extrator SEM antes documentar causa raiz no relatório"
é proibido. Respeitado.

## Proof-of-work empírico

### Antes do fix (reprodução Sprint 93)

```
.venv/bin/python scripts/auditar_extratores.py --tudo --modo-abrangente
```

Resultado: 9/9 DIVERGE, soma de deltas > R$ 2,3 milhões.

### Depois do fix

```
.venv/bin/python scripts/auditar_extratores.py \
    --tudo --modo-abrangente --deduplicado
```

Resultado:

| Banco | Delta antes | Delta depois | Veredito final |
|---|---:|---:|:-:|
| `itau_cc`          | R$ 308.455 | **R$ 0,00**   | **OK** |
| `santander_cartao` | R$ 141.668 | **R$ 0,00**   | **OK** |
| `c6_cc`            | R$ 739.192 | R$  63.581    | DIVERGE (Família B/E) |
| `c6_cartao`        | R$  21.152 | R$  30.216    | DIVERGE (Família B) |
| `nubank_cartao`    | R$ 222.250 | R$  64.849    | DIVERGE (Família B/E) |
| `nubank_cc`        | R$ 889.234 | R$ 884.006    | DIVERGE (rotulagem) |
| `nubank_pf_cc`     | R$ 267.211 | R$ 268.891    | DIVERGE (Família B) |
| `nubank_pj_cc`     | R$ 126.170 | R$ 125.989    | DIVERGE (Família C) |
| `nubank_pj_cartao` | R$  46.943 | R$  44.214    | DIVERGE (Família C) |

**2 dos 5 bancos da Família A agora são OK com delta R$ 0,00.** Os outros
3 bancos da Família A confirmam que o padrão `N_extrator >> N_xlsx` NÃO
era Família A: após SHA-dedup, passaram a exibir `N_extrator < N_xlsx`
(Família B/E) ou diagnóstico de rotulagem inconsistente. Sprints 93b
e 93c, já formalizadas, tratam desses.

### Suite de testes

Baseline pré-sprint: 1.366 passed. Pós-sprint: 1.372 passed + 0
regressão. 6 testes novos em `tests/test_auditoria_fidelidade.py`:

- `test_sha256_arquivo_deterministico` — SHA-256 estável.
- `test_unicos_por_sha_remove_copias_identicas` — dedup físico.
- `test_aplicar_dedup_pipeline_respeita_identificador` — nível 1.
- `test_aplicar_dedup_pipeline_fuzzy_hash_colapsa` — nível 2.
- `test_auditar_banco_com_deduplicado_dir_completo` — integração
  com/sem flag.
- `test_cli_flag_deduplicado_aceita` — CLI parseia flag.

### Gauntlet

```
make lint                                         → exit 0
.venv/bin/pytest tests/ -q                         → 1372 passed / 9 skipped / 1 xfailed
make smoke                                         → 23 checagens 0 erros + 8/8 contratos aritméticos
```

## Limitações conhecidas

1. **`nubank_cc` com duplicatas SHA não se beneficia da flag**, pois o
   extrator já deduplica por UUID nativo. O delta residual (R$ 884.006)
   permanece diagnóstico de rotulagem — NÃO é perda de linha. Medido
   isoladamente: total bruto = R$ 1.040.429,53 (3.083 tx); soma do XLSX
   em TODOS os rótulos Nubank para André nos mesmos meses = R$ 1.145.825,06
   (3.576 tx). O XLSX TEM MAIS dados que o bruto, redistribuídos entre
   `banco_origem="Nubank"` (André) e `banco_origem="Nubank (PF)"` (Casal).
   Sprint 93c tratará da consolidação do rótulo.

2. **SHA-dedup não pega duplicatas "quase idênticas"** (ex: mesmo
   PDF baixado com metadados diferentes, timestamp interno distinto).
   Esse caso não foi observado em volume real neste diretório — os 86%
   de duplicatas são bit-a-bit. Caso apareça, cair na dedup nível 2
   (hash fuzzy) já cobre.

3. **A flag muda o número reportado mas não o que o pipeline grava no
   XLSX.** O XLSX consolidado segue sendo produzido pelo `pipeline.py`
   real, que já tinha dedup correto. A mudança é apenas na
   instrumentação (auditoria).

## Recomendações acionáveis

1. **Sprint 93b** (P1): propagar `arquivo_origem` para coluna do XLSX.
   Resolve c6_cc, c6_cartao, nubank_cartao, nubank_pf_cc residuais.

2. **Sprint 93c** (P1): consolidar rotulagem `Nubank (PJ)` e corrigir
   `nubank_cc` (Casal vs André ambiguidade). Afeta ~2.800 tx.

3. **Limpeza de inbox** (não é sprint formal): sugerir ao usuário
   limpar as cópias físicas em `data/raw/andre/<banco>/` — 86% do
   diretório é redundância. Economia de espaço ≈ 150 MB. Mitigação
   pós-esta sprint opcional.

4. **Adicionar `make audit-deduplicado` ao Makefile** para que o
   gauntlet recomendado rode com a flag. Follow-up trivial.

## Achados colaterais

Nenhum. O escopo da Família A foi limpo pela flag `--deduplicado` sem
revelar bugs de parser. Os 3 bancos residuais caem em Famílias B/C já
formalizadas.

---

*"Evidência antes de conclusão. Medida antes de conserto." — princípio
de dedup honesto.*
