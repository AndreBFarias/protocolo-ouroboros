# Auditoria Família C -- Nubank PJ (2026-04-24)

**Sprint:** 93c
**Origem:** `docs/auditoria_extratores_2026-04-23.md` §Família C
**Baseline:** 1378 passed → **1380 passed** / 9 skipped / 1 xfailed (+2 testes).

---

## 1. Escopo

Família C da auditoria 2026-04-23: transações das subcontas MEI da Vitória
(conta corrente `nubank_pj_cc` + cartão `nubank_pj_cartao`) saem dos extratores
brutos mas chegam ao XLSX com contagem **zero** sob qualquer rótulo
`banco_origem` reconhecível como PJ. Delta reportado:

| Banco         | N extrator | N XLSX | Delta (R$) |
|---------------|-----------:|-------:|-----------:|
| nubank_pj_cc  | 562        | 0      | 125.989,47 |
| nubank_pj_cartao | 275     | 0      | 43.966,32  |

---

## 2. Investigação empírica

Rastreio do fluxo ``extrator → normalizer → deduplicator → xlsx`` em runtime
real (dados brutos do repositório, não fixture):

1. **`nubank_cc.py`** produz `banco_origem="Nubank (PJ)"` corretamente quando
   path contém `nubank_pj` (método `_detectar_conta` existente).
   - Extração crua: 566 tx, `banco_origem={'Nubank (PJ)'}`.
2. **`normalizer.normalizar_transacao`** preserva o rótulo (atribuição direta
   em `normalizer.py:229`). Confirmado: 566 tx pós-normalizer ainda
   `Nubank (PJ)`, `quem=Vitória`.
3. **`deduplicator.deduplicar` + `marcar_transferencias_internas`**: 4
   duplicatas fuzzy removidas, 562 tx pós-dedup, rótulo íntegro.
4. **`nubank_cartao.py`** -- diferente -- emite `banco_origem="Nubank"` FIXO
   (linha 102). Nenhum método equivalente a `_detectar_conta` existia.
   - Extração crua do cartão PJ: 275 tx, `banco_origem={'Nubank'}` (genérico,
     colidindo com cartão PF do André).

### Causa raiz (2 fatores independentes)

- **C-1 (dados estáticos no XLSX):** as 562 tx PJ CC são geradas corretamente
  pelo pipeline *atual* mas o `data/output/ouroboros_2026.xlsx` em produção
  foi gerado em 2026-04-23 22:47 -- antes que a corrida de auditoria da Sprint
  93 (2026-04-23) registrasse o diagnóstico. Um `./run.sh --tudo` resolve
  sem mudança de código. Isto **não é bug de código**; é estado estático.
- **C-2 (bug real de rotulagem):** `nubank_cartao.py::_parse_linha` nunca
  diferenciava subconta. Toda fatura PJ saía com rótulo genérico `Nubank`,
  e no XLSX se confundia com fatura PF do André. Delta da auditoria confirma:
  o cartão PJ não chegava ao rótulo canônico `Nubank (PJ)` ainda que
  `scripts/smoke_aritmetico.py::BANCOS_VALIDOS` já o aceitasse desde Sprint 56.

---

## 3. Fix aplicado

### `src/extractors/nubank_cartao.py` (+17L)

- Novo método `_rotular_banco_origem(caminho: Path) -> str` espelhando o padrão
  do `ExtratorNubankCC._detectar_conta`: quando `"nubank_pj"` aparece no path
  minúsculo, retorna `"Nubank (PJ)"`; caso contrário, `"Nubank"`.
- `_parse_linha` passa a chamar o novo método em vez de string literal.
- Docstring explicita que a decisão é via path (por simetria com o CC) e
  documenta a armadilha de colisão PF/PJ sob rótulo genérico.

### `tests/test_nubank_cartao.py` (+29L, 2 testes novos)

- `test_cartao_pj_detecta_subtipo_via_path`: fixture sintética sob path
  `vitoria/nubank_pj_cartao/` produz `banco_origem=="Nubank (PJ)"`.
- `test_cartao_sem_pj_no_path_mantem_rotulo_nubank`: fixture sob
  `andre/nubank_cartao/` continua como `"Nubank"` (regressão do caminho
  canônico PF do André).

### Arquivos intactos por decisão arquitetural

- **`src/extractors/nubank_cc.py`**: rotulagem correta desde origem. Teste
  `test_deteccao_conta_pj_vs_pf_pelo_caminho` já validava `"Nubank (PJ)"` sob
  path PJ (`tests/test_nubank_cc.py:115-123`). Nenhuma mudança necessária.
- **`src/transform/normalizer.py`**: preserva `banco_origem` recebido
  (linha 229). A lista `bancos_vitoria_pj = {"Nubank PJ"}` em `inferir_pessoa`
  (linha 159) usa grafia *sem parênteses* que nunca é atingida -- mas
  `subtipo="pj"` via `_inferir_subtipo(arquivo)` em `pipeline.py:281` captura
  "Vitória" pelo path. Rota redundante mas não bug; fora do escopo 93c.
- **`src/load/xlsx_writer.py`**: escreve `banco_origem` direto (linha 146),
  sem filtro por whitelist. Alterar seria violar `forbidden: Mudar layout
  XLSX (coluna banco_origem é stable)` do spec.
- **`scripts/auditar_extratores.py`**: já aceita `"Nubank (PJ)"` na
  definição de `nubank_pj_cc` (linha 220) e `nubank_pj_cartao` (linha 232)
  desde Sprint 93 original. Nenhuma ampliação necessária.

---

## 4. Proof-of-work

### Runtime real pós-fix (extração direta, dados reais)

```
Extrator crua cartão PJ: 294 tx, banco_origem={'Nubank (PJ)'}   OK
Extrator crua CC PJ:    566 tx, banco_origem={'Nubank (PJ)'}   OK (já funcionava)
```

### Checks canônicos

- `make lint` → exit 0 (ruff + acentuação contextual 0 violações).
- `.venv/bin/pytest tests/ -q` → **1380 passed**, 9 skipped, 1 xfailed
  (baseline 1378 + 2 novos).
- `make smoke` → 23/0 checks + 8/8 contratos aritméticos.

### Auditor

Dry-run pós-fix (XLSX em produção **NÃO sobrescrito**, spec proíbe sem OK):

```
nubank_pj_cartao | 2025-05 | ... | 2728.61 | 0.00 | 2728.61 | 19 | 0 | DIVERGE
nubank_pj_cc    | 2024-11 | cc_pj_vitoria.csv | 125989.47 | 0.00 | 562 | 0 | DIVERGE
```

**Nota explícita:** delta persiste até o André rodar `./run.sh --tudo` para
regenerar o XLSX consolidado com os dois extratores já corretos. Unit-tests
novos provam empiricamente que as tx PJ sobrevivem à cadeia (extrator →
normalizer → dedup → TI) com rótulo íntegro; o próximo `--tudo` fecha o
contador XLSX>0.

---

## 5. Ressalvas

Nenhuma sprint-filha formalizada.

Item fora do escopo mas registrado para o dono Opus decidir:

- **R93c-1 (minúcia, não-bloqueante):** `src/transform/normalizer.py:158-159`
  usa grafia sem parênteses (`"Nubank PF"`, `"Nubank PJ"`) que nunca casa
  no fluxo atual, porque o rótulo canônico tem parênteses. Rota redundante:
  `subtipo` via path já infere "Vitória". Limpeza cosmética, zero impacto
  funcional. Proposta de Edit pronta para qualquer sprint de higiene:
  - `bancos_vitoria_pf = {"Nubank PF", "Nubank (PF)"}`
  - `bancos_vitoria_pj = {"Nubank PJ", "Nubank (PJ)"}`
  Deixo como comentário de backlog, não abro sprint-filha.

---

## 6. Arquivos tocados

| Arquivo                                            | Delta |
|----------------------------------------------------|------:|
| `src/extractors/nubank_cartao.py`                  | +17L  |
| `tests/test_nubank_cartao.py`                      | +29L  |
| `docs/sprints/backlog/sprint_93c_rotulagem_nubank_pj.md` → `concluidos/` | move |
| `docs/auditoria_familia_C_2026-04-24.md` (este)    | novo  |

---

*"Um rótulo perdido no pipeline é um domínio perdido na análise." -- princípio da rotulagem canônica*
