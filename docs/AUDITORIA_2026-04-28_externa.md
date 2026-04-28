# Auditoria Externa 2026-04-28 -- Sessão Automações Opus

**Disparada por:** dono Opus após mergeação de 7 sprints novas (commits 598e723..59bc381).
**Agentes:** 2 sub-agentes Claude (code-reviewer + Explore) em paralelo.
**Escopo:** bugs reais, gaps de testes, segurança LGPD, sincronia de docs.

---

## SUMÁRIO EXECUTIVO

| Severidade | Quantidade | Aplicados nesta sessão |
|---|---|---|
| P0 (bugs reais) | 3 | 3/3 |
| P1 (regressão potencial) | 4 | 3/4 (1 deferido) |
| P2 (débito técnico) | 6 | 1/6 (5 viraram backlog) |
| P3 (polish) | 4 | 1/4 (3 viraram backlog) |
| Docs desatualizados | 13 | 8/13 |

---

## P0 -- BUGS REAIS (todos aplicados em commit 2026-04-28)

### P0-01: `--menu` duplicado em `run.sh`

`case "${1:-}"` tinha dois padrões `--menu` (linhas 502 e 602). Segundo era código morto.

**Fix aplicado:** removido o segundo bloco. Apenas o primeiro permanece (delega para `scripts/menu_interativo.py`).

### P0-02: `tipo_inferido` sempre `cupom_fiscal_foto`

Em `src/intake/ocr_fallback_similar.py::reanalisar_pasta_conferir`, ambos os branches do if/else atribuíam o mesmo valor. Motor de fallback ficava inoperante para tipos não-cupom.

**Fix aplicado:** mapa real `_MAPA_TIPO_POR_NOME` por prefixo (recibo_, das_, holerite, nfce_, etc.) com fallback inteligente por extensão.

### P0-03: `reanalisar_pasta_conferir` movia arquivo sem atualizar grafo

Causava ciclo: `arquivo_origem` no grafo apontava para `_conferir/`, arquivo já tinha sido movido para pasta canônica.

**Fix aplicado:** após `shutil.move`, atualiza `metadata.arquivo_origem` + adiciona `metadata.fallback_origem` e `metadata.confidence_fallback` no node correspondente.

---

## P1 -- REGRESSÃO POTENCIAL

### P1-01: `migrar_pessoa_via_cpf` não contava colisões

Quando destino existia, `continue` sem incrementar `migrados` nem `preservados` -- invariante `total = migrados + preservados` quebrava.

**Fix aplicado:** `stats["preservados"] += 1` antes do continue.

### P1-03: `dedup_classificar` ignorava erros SHA-256

Arquivos com permissão negada sumiam do relatório.

**Fix aplicado:** novo contador `erros_sha` no retorno do dict.

### P1-04: `rglob(f"*{nome}")` em `backfill_arquivo_origem` -- risco cross-pasta

Glob com prefixo `*` poderia casar arquivos em pastas erradas (ex: holerite Vitória → arquivo Andre).

**Fix aplicado:** `glob.escape(nome)` + `rglob(nome)` exato.

### P1-02: contribuinte vazio em metadata (DEFERIDO)

Quando `razao_social` é vazio, `metadata.contribuinte` não é gravado -- auditoria fica cega.

**Status:** deferido. Comportamento atual logicamente coerente; risco baixo. Sub-sprint candidata se revisor flagar.

---

## P2 -- DÉBITO TÉCNICO (5 deferidos para backlog)

### P2-01: `src/` importa de `scripts/` (antipadrão)

`ocr_fallback_similar.py:349` faz `from scripts.migrar_pessoa_via_cpf import _extrair_preview`. Camada inversa.

**Sub-sprint:** mover `_extrair_preview` para `src/intake/preview.py`.

### P2-02: `_CONFIG_CACHE` não thread-safe

Padrão `global` mutável em vários módulos. Pode falhar em pytest paralelo.

**Sub-sprint:** trocar para `functools.lru_cache`.

### P2-03: Timezone naive em `_score_temporal`

`datetime.fromisoformat()` (naive) vs `datetime.fromtimestamp()` (local). Erro de ±1 dia possível.

**Sub-sprint:** comparar apenas datas (`.date()`).

### P2-04: Confirmação interativa em menu opção 7

`./run.sh --reextrair-tudo` chamado pelo menu Python pode receber stdin redirecionado, falhar silenciosamente.

**Sub-sprint:** flag `--sim` para pular confirmação quando vindo de menu.

### P2-05: Path absoluto em `arquivo_origem`

Não-portável entre máquinas.

**Sub-sprint:** gravar path relativo a `_RAIZ_REPO`.

### P2-06: O(N×M) em `_atualizar_grafo`

Para volumes grandes, query precisa de filtro JSON.

**Sub-sprint:** índice em `json_extract(metadata, '$.arquivo_origem')`.

---

## P3 -- POLISH (3 deferidos)

### P3-01: Citação filosófica sem acentos

`ocr_fallback_similar.py:443`: "peca o template ao gemeo".

**Fix aplicado:** "peça o template ao gêmeo".

### P3-02 + P3-03 + P3-04: deferidos

- Score textual usa só primeira palavra (risco falso-positivo "BANCO").
- Comentário "default razoável" enganoso.
- `_DISPATCHER` não mapeia `"0"`.

---

## DOCS DESATUALIZADOS (8/13 aplicados)

### Aplicados nesta sessão

1. **CLAUDE.md** -- contagem 165->174 sprints, grafo 7.494->7.485 nodes, "DAS PARCSN apontando para Receita Federal".
2. **README.md** -- transações 2.859->6.094, meses 44->82, IRPF 79->164, extratores 21->22, pytest 1.261->1.971.
3. **ADR-13** -- update 2026-04-28 com Sprint 108 (automações encadeadas + helper `run_passo`).
4. **ADR-14** -- update 2026-04-28 com Sprint 107 (fornecedor sintético + `mappings/fornecedores_sinteticos.yaml`).
5. **ADR-21** -- status PROPOSTO -> ACEITA (Sprints 70/71 em produção).
6. **contexto/ESTADO_ATUAL.md** -- reescrito completo para 2026-04-28.
7. **docs/HANDOFF_2026-04-28_automacoes_opus.md** -- criado.
8. **docs/AUTOMACOES_OPUS.md** -- criado pela Sprint 108.

### Deferidos (não-críticos)

- README.md: gráfico mermaid não menciona Revisor visual (Sprint D2).
- ESTADO_ATUAL.md: Sprint INFRA-97a status vago no roteiro.
- AUTOMACOES_OPUS.md não menciona Sprint 106a.

---

## ACHADO MATERIAL CRÍTICO -- Sprint 104 incompleta

Durante validação da reextração rodada nesta sessão, descobriu-se que
`scripts/reprocessar_documentos.py::EXTRATORES_DOCUMENTAIS` **NÃO** inclui
`ExtratorContrachequePDF`. Holerites usam função `processar_holerites()`
em vez de classe Extrator -- não foram re-ingeridos pelo `--forcar-reextracao`.

**Impacto runtime real:** 24 holerites desapareceram do grafo após
`--forcar-reextracao` rodado nesta sessão.

**Fix aplicado:**
1. `scripts/reprocessar_documentos.py` ganhou bloco extra: após o loop principal,
   se `--forcar-reextracao` ativo, chama `processar_holerites()` em
   `data/raw/andre/holerites/` para re-ingerir os 24 holerites.
2. Holerites do grafo restaurados manualmente em runtime real (24/24 voltaram).

**Lição:** `--forcar-reextracao` precisa cobrir TODOS os extratores documentais,
incluindo os baseados em função (não só classes). Validador futuro deve
comparar contagem antes/depois e alertar se cair acima de 50%.

---

## RESUMO POR ARQUIVO MODIFICADO

| Arquivo | Mudanças |
|---|---|
| `run.sh` | -1 bloco `--menu` duplicado |
| `src/intake/ocr_fallback_similar.py` | mapa real de tipo + atualização de grafo após move + acentuação citação |
| `src/graph/backfill_arquivo_origem.py` | glob.escape em `_resolver_generico` |
| `scripts/migrar_pessoa_via_cpf.py` | contador `preservados` em colisão |
| `src/intake/dedup_classificar.py` | contador `erros_sha` |
| `scripts/reprocessar_documentos.py` | re-ingestão de holerites pós `--forcar-reextracao` |
| `tests/test_dedup_classificar.py` | ajuste assertions para novo schema do dict |
| `CLAUDE.md`, `README.md`, `ADR-13/14/21`, `ESTADO_ATUAL.md` | sincronia |

---

## PADRÕES META PARA VALIDATOR_BRIEF

1. **`src/` nunca importa de `scripts/`.** Validador: `grep -r "from scripts\." src/` deve retornar vazio.
2. **`rglob(f"*{nome}")` sem `glob.escape` é antipadrão.** Use `rglob(glob.escape(nome))` ou `rglob(nome)` exato.
3. **`case ... in` bash com padrão duplicado: o segundo nunca executa.** Validador: `grep -n '^\s*--[a-z]' run.sh | sort | uniq -d` deve retornar vazio.
4. **Invariante de relatório `total == migrados + preservados + erros`.** Qualquer script de migração deve incluir assertion final.

---

*"Auditoria externa lê com olhos novos -- onde o autor vê padrão, ela vê armadilha." -- princípio do segundo par de olhos*
