## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 95
  title: "Linking runtime: 0% docs vinculados a tx -- investigar e corrigir motor da Sprint 48"
  prioridade: P0
  estimativa: 4-6h
  origem: "auditoria 2026-04-26 -- dashboard Catalogação mostra KPI 'Vinculados a transação: 0%' para 41 documentos"
  touches:
    - path: src/graph/linking.py
      reason: "motor invocado em pipeline.py:498 mas não produz arestas"
    - path: src/pipeline.py
      reason: "ordem de execução do _executar_linking_documentos"
    - path: tests/test_linking_runtime.py
      reason: "regressão para garantir que arestas documento_de são produzidas em volume real"
  forbidden:
    - "Mexer no schema do grafo (ADR-14) sem ADR-14-update separado"
    - "Mockar o motor em vez de rodar em runtime real -- bug é runtime, teste unitário não pega"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_linking_runtime.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Após ./run.sh --tudo, pelo menos 30% dos 41 docs (ou 12 docs) têm aresta documento_de no grafo"
    - "Holerites linkam com tx do dia de pagamento (PAGTO SALARIO no Itaú) -- 24 holerites = pelo menos 18 linkados"
    - "DAS PARCSN linkam com tx de pagamento DAS PARCSN no extrato (descrição contém DARF/DAS/IMPOSTO)"
    - "Boletos SESC linkam com tx PIX SESC no Itaú/Nubank"
    - "Dashboard Catalogação mostra '> 30% Vinculados' após reprocessamento"
    - "Teste regressivo em test_linking_runtime.py com fixture sintética: 1 holerite + 1 tx PAGTO SALARIO -> 1 aresta documento_de"
  proof_of_work_esperado: |
    # Antes
    sqlite3 data/output/grafo.sqlite \
      "SELECT COUNT(*) FROM edge WHERE tipo='documento_de';"
    # = 0
    
    # Investigação root cause
    .venv/bin/python -c "
    from src.graph.db import GrafoDB, caminho_padrao
    from src.graph.linking import linkar_documentos_a_transacoes
    with GrafoDB(caminho_padrao()) as db:
        stats = linkar_documentos_a_transacoes(db)
        print(stats)
    "
    # Suspeitas: (a) extratores documentais não gravam metadata.data_emissao no formato esperado;
    # (b) função casa documento por nome canônico do fornecedor mas tx tem descrição abreviada;
    # (c) tolerância temporal muito apertada (3 dias quando deveria ser 7 ou 14)
    
    # Fix (depois de identificar root cause)
    [editar src/graph/linking.py conforme diagnóstico]
    
    # Depois
    ./run.sh --tudo 2>&1 | tail -5
    sqlite3 data/output/grafo.sqlite \
      "SELECT COUNT(*) FROM edge WHERE tipo='documento_de';"
    # = >= 12
    
    .venv/bin/streamlit run src/dashboard/app.py
    # Cluster Documentos: KPI "Vinculados a transação" mostra >= 30%
```

---

# Sprint 95 -- Linking runtime

**Status:** BACKLOG (P0, criada 2026-04-26)
**Origem:** Auditoria visual do dashboard mostrou KPI "Vinculados a transação: 0%". Sprint 48 (linking) tem plumbing OK mas motor não produz arestas em volume real.

## Motivação

A página `Catalogação` é o coração do produto declarado: "joguei foto de NF + paguei no cartão -> sistema mostra que aquela tx tem comprovante". Hoje:

- 41 documentos catalogados no grafo (24 holerites + 10 DAS + 4 NFC-e + 2 boletos + 1 DIRPF).
- 0 arestas `documento_de` em runtime real.
- Função `linkar_documentos_a_transacoes` em `src/graph/linking.py` é invocada em `pipeline.py:498` na rodada `--tudo`.
- Logs do pipeline registram `Linking documento->transação: {...}` mas as estatísticas mostram 0 matches.

## Investigação dirigida (não pular)

Antes de tocar código, rodar diagnóstico:

```bash
sqlite3 data/output/grafo.sqlite <<EOF
-- Quais tipos de documento existem?
SELECT json_extract(metadata, '\$.tipo_documento') AS tipo, COUNT(*)
FROM node WHERE tipo='documento'
GROUP BY tipo;

-- Quais campos metadata os documentos têm?
SELECT id, tipo, json_extract(metadata, '\$.tipo_documento'), 
       json_extract(metadata, '\$.data_emissao'),
       json_extract(metadata, '\$.valor_total')
FROM node WHERE tipo='documento' LIMIT 5;

-- Tx do mesmo período + valor próximo
SELECT id, json_extract(metadata, '\$.descricao'), 
       json_extract(metadata, '\$.valor'),
       json_extract(metadata, '\$.data')
FROM node WHERE tipo='transacao' 
  AND json_extract(metadata, '\$.data') >= '2026-04-01'
  AND json_extract(metadata, '\$.data') <= '2026-04-30'
LIMIT 10;
EOF
```

Hipóteses prováveis:
1. **Holerite tem `metadata.data_emissao` mas linker procura `data_pagamento`.**
2. **DAS tem `metadata.cnpj_emissor` mas tx só tem descrição em texto livre** -- matching depende de regex `DARF|DAS PARCSN|IMPOSTO RECEITA`.
3. **Tolerância temporal apertada** (3 dias). Holerite emitido em 30/04 mas pagamento cai em 02/05 ou 05/05.
4. **Ordem de execução errada**: linker pode estar rodando ANTES dos extratores documentais terem persistido. Em `pipeline.py`: passo 12 é `_executar_linking_documentos()` (linha 498), mas passo 10 é `processar_holerites` que pode não estar persistindo a tempo.

## Escopo

### Fase 1 -- Diagnóstico (1-2h)

Rodar queries diagnósticas, identificar root cause real (uma das hipóteses ou nova).

### Fase 2 -- Fix dirigido (2h)

Editar `src/graph/linking.py` conforme diagnóstico. Provável: ampliar tolerância temporal para 14 dias, melhorar matching textual, ou refatorar ordem de execução.

### Fase 3 -- Teste regressivo (1h)

Criar `tests/test_linking_runtime.py`:
- Fixture sintética: GrafoDB em memória + 1 holerite com `metadata.data_pagamento='2026-04-30'` + 1 tx Itaú `descricao='PAGTO SALARIO'` `data='2026-05-02'`.
- Rodar `linkar_documentos_a_transacoes(db)`.
- Asserir: 1 aresta `documento_de` criada.
- Asserir idempotência: rodar de novo, conta arestas continua 1.

### Fase 4 -- Validação em volume real (1h)

```bash
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM edge WHERE tipo='documento_de';"
# Deve retornar >= 12
```

Capturar screenshot do dashboard com KPI atualizado.

## Armadilhas

- **Bug pode estar no extrator, não no linker.** Se holerite não persiste `data_pagamento` no metadata, linker não tem como casar. Investigar com `SELECT metadata FROM node` antes de assumir.
- **Idempotência crítica.** Re-rodar `--tudo` não pode duplicar arestas. `INSERT OR IGNORE` em `adicionar_edge` deve cobrir, mas confirmar.
- **Volume real pode demorar.** `./run.sh --tudo` em ~760 arquivos pode levar minutos. Não bloqueio, só planejamento.

## Dependências

- Nenhuma. Pode rodar antes ou depois de Sprint 90a (holerites mal classificados) -- o linking opera sobre nodes já presentes no grafo, não sobre arquivos brutos.

---

*"O motor existe, só falta a ignição." -- princípio do plumbing-runtime gap*
