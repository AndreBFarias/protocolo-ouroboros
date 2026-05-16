---
id: INFRA-PIPELINE-TRANSACIONALIDADE
titulo: Transacionalidade SQLite por estágio do pipeline (BEGIN/COMMIT explícito)
status: concluída
concluida_em: 2026-05-15
prioridade: P0
data_criacao: 2026-05-13
fase: PRODUCAO_READY
depende_de:
  - INFRA-BACKUP-GRAFO-AUTOMATIZADO (recomendado antes)
esforco_estimado_horas: 4
origem: auditoria operacional 2026-05-13. src/pipeline.py::executar() não usa transações explícitas. Estágios (extração → dedup → linking → ER → categorizer → skill_d7) commitam parcialmente -- crash em estágio N deixa grafo com estágios 1..N-1 aplicados.
---

# Sprint INFRA-PIPELINE-TRANSACIONALIDADE

## Contexto

`pipeline.py::executar()` orquestra 15 estágios sequenciais. Cada um abre `GrafoDB` próprio, commit autônomo. Se `_executar_linking_documentos` crasha após `_extrair_tudo` ter inserido 200 nós novos, esses 200 nós ficam mas linking parcial → grafo inconsistente.

Padrão `(m)` reversibilidade exige rollback granular.

## Hipótese

SQLite WAL mode + transações explícitas por estágio. Em crash, rollback do estágio corrente; estágios anteriores ficam confirmados.

## Objetivo

1. Cada `_executar_*` recebe contexto `with db.transaction():` que envolve BEGIN/COMMIT.
2. Em exceção, ROLLBACK + log estruturado em `logs/pipeline_falha_<ts>.json` com estágio + traceback + estado pré-falha.
3. Re-run de `./run.sh --tudo` continua de onde parou (idempotência via hash de arquivos já processados).
4. Testes que provocam exceção controlada em cada estágio e verificam rollback.

## Decisão pendente

`GrafoDB` hoje não tem contexto transacional explícito. Adicionar `__enter__/__exit__` que faz BEGIN/COMMIT/ROLLBACK conforme `__exit__(exc_type)`.

## Proof-of-work

```bash
.venv/bin/python -c "
from src.graph.db import GrafoDB, caminho_padrao
db = GrafoDB(caminho_padrao())
n0 = db.con.execute('SELECT COUNT(*) FROM node').fetchone()[0]
try:
    with db.transaction():
        db.con.execute(\"INSERT INTO node(tipo, nome_canonico) VALUES('test', 'rollback_test')\")
        raise RuntimeError('forçar rollback')
except RuntimeError:
    pass
n1 = db.con.execute('SELECT COUNT(*) FROM node').fetchone()[0]
assert n0 == n1, f'rollback falhou: {n0} -> {n1}'
print('OK rollback')
"
```

## Acceptance

- `GrafoDB.transaction()` context manager.
- 15 estágios do pipeline envolvidos em transações próprias.
- Crash em qualquer estágio: log estruturado + rollback do estágio + estágios anteriores preservados.
- ≥6 testes (rollback por estágio).
- Pytest > 2964. Smoke 10/10.

---

*"Comprometer um pedaço por vez é poder voltar atrás sem perder o resto." -- princípio transacional*
