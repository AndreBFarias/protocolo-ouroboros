## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 87b
  title: "Propagar identificador canônico de transação do grafo para o XLSX"
  touches:
    - path: src/load/xlsx_writer.py
      reason: "adicionar coluna identificador no schema da aba extrato"
    - path: src/graph/migracao_inicial.py
      reason: "expor _hash_transacao como helper público"
    - path: src/pipeline.py
      reason: "computar identificador canônico ao escrever transações no XLSX"
    - path: src/dashboard/dados.py
      reason: "carregar coluna identificador no df do dashboard"
    - path: tests/test_xlsx_identificador.py
      reason: "round-trip: pipeline grava, dashboard carrega, bate com nome_canonico do grafo"
  forbidden:
    - "Alterar o schema do grafo (nome_canonico do node transacao continua sendo a chave)"
    - "Quebrar compatibilidade de XLSX antigos (coluna nova é opcional na leitura)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Aba extrato do XLSX gerado ganha coluna `identificador` preenchida com hash canônico igual ao nome_canonico do node transacao no grafo"
    - "src/dashboard/dados.py carrega essa coluna quando presente; ausência não quebra dashboard (XLSX antigos continuam abrindo)"
    - "tests/test_xlsx_identificador.py valida round-trip: rodar pipeline em fixture produz XLSX com identificador que bate com _hash_transacao"
    - "Sprint 87.2 (coluna Doc? consulta grafo) passa a funcionar em runtime real — transações com aresta documento_de marcam OK"
    - "Zero regressão: baseline 1079 passed / 15 skipped mantido ou cresce"
```

---

# Sprint 87b — Propagar identificador canônico de transação

**Status:** BACKLOG
**Prioridade:** P2 (desbloqueia Sprint 87.2 em runtime real; hoje plumbing está correto mas dormente)
**Dependências:** Sprint 87.2 (helper e lógica já existem)
**Origem:** achado AC87-2-01 durante execução da Sprint 87.2 em 2026-04-23

## Problema

A Sprint 87.2 implementou a query `transacoes_com_documento` em `src/graph/queries.py` e o helper `_marcar_tracking` em `src/dashboard/paginas/extrato.py` para marcar "OK" quando transação tem aresta `documento_de` no grafo. Os testes unitários passam (8 em `tests/test_gap_consultando_grafo.py`), mas em runtime real o marcador sempre cai no fallback porque a coluna `identificador` **não existe no XLSX gerado pelo pipeline**.

A tabela `COLUNAS_EXTRATO` em `src/load/xlsx_writer.py:15-28` não inclui `identificador`. Assim, o df que chega em `_exibir_tabela` nunca tem como cruzar com `nome_canonico` dos nodes `transacao` no grafo (que é o identificador canônico, gerado por `_hash_transacao` em `src/graph/migracao_inicial.py`).

## Escopo (5 itens)

### 87b.1 — Expor `_hash_transacao` como helper público

Em `src/graph/migracao_inicial.py`, a função `_hash_transacao` (linha ~44) gera o hash canônico que identifica um node `transacao` (SHA256 truncado em 16 chars). Hoje é privada do módulo. Transformar em função pública `hash_transacao_canonico` (ou similar) para que outros módulos possam computar o mesmo hash.

### 87b.2 — Adicionar coluna `identificador` em COLUNAS_EXTRATO

Em `src/load/xlsx_writer.py`, acrescentar `identificador` à lista `COLUNAS_EXTRATO`. Ordem: entre `tipo` e `mes_ref` (ou no final — decisão estética).

### 87b.3 — Computar identificador ao escrever

Em `src/pipeline.py` no passo 11 (gerar XLSX), cada transação precisa ganhar campo `identificador = hash_transacao_canonico(tx)` antes de escrever. Isso pode ser feito em uma passagem nova pós-categorização OU diretamente em `xlsx_writer.gerar_xlsx` se a função tiver acesso ao dict.

### 87b.4 — Carregar coluna no dashboard

Em `src/dashboard/dados.py`, o loader do extrato deve carregar `identificador` quando presente. Quando ausente (XLSX antigo), cair no comportamento atual.

### 87b.5 — Teste de round-trip

`tests/test_xlsx_identificador.py`:
- Fixture com 3 transações sintéticas
- Rodar `gerar_xlsx(transacoes, path, ...)`
- Ler XLSX de volta (openpyxl ou pandas)
- Para cada linha, conferir que `identificador` bate com `hash_transacao_canonico(tx_original)`
- Confirmar que a coluna passa pelo `dados.py` do dashboard

## Armadilhas conhecidas

- XLSX antigos não têm a coluna. O loader precisa usar `.get()` seguro e não quebrar.
- Categoria/classificação mudam o hash? O hash canônico do grafo é sobre (data, valor, local, banco) — invariantes da transação, não da categorização. Verificar em `migracao_inicial.py` antes de assumir.
- O `nome_canonico` do node `transacao` é gerado com 16 chars. Se `_hash_transacao` evoluir no futuro, a coluna gravada descasa com nodes antigos do grafo. Registrar esse acoplamento na docstring.

## Evidência obrigatória

- [ ] `COLUNAS_EXTRATO` lista `identificador`
- [ ] Round-trip pytest passa
- [ ] Rodar uma transação sintética no pipeline + conferir que `nome_canonico` no grafo == `identificador` no XLSX (teste e1e)
- [ ] Gauntlet verde: lint + pytest + smoke
- [ ] Sprint 87.2 passa a marcar "OK" em produção quando o grafo tem arestas `documento_de`

---

*"Um identificador sem propagação é nome que ninguém usa." — princípio pós-Sprint 87.2*
