---
id: INFRA-PIPELINE-TX-RESTORE-AUTOMATICO
titulo: Restore automático do backup em crash mid-pipeline (complemento à transacionalidade)
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-15
fase: PRODUCAO_READY
epico: 2
depende_de:
  - INFRA-PIPELINE-TRANSACIONALIDADE (transação por estágio)
  - INFRA-BACKUP-GRAFO-AUTOMATIZADO (concluída em d97df41)
esforco_estimado_horas: 1.5
origem: auditoria 2026-05-15. INFRA-PIPELINE-TRANSACIONALIDADE cobre rollback ATÔMICO por estágio. Mas se SQLite mesmo falhar (disco cheio, corrupção, OOM kill), rollback não basta — precisa restore do backup pré-pipeline. Hoje backup é criado mas nunca consumido automaticamente em crash.
---

# Sprint INFRA-PIPELINE-TX-RESTORE-AUTOMATICO

## Contexto

`_executar_backup_grafo()` (commit `d97df41`) cria snapshot no início de `executar()`. Mas nada consome esse backup automaticamente em caso de falha catastrófica (OOM, signal kill, corrupção SQLite).

Cenário real: pipeline crashou no estágio 12 (linking), grafo ficou em estado intermediário. Hoje exige:
1. Diagnóstico humano que o grafo está corrompido.
2. Encontrar timestamp do backup pré-execução nos logs.
3. Rodar manualmente `./run.sh --restore-grafo <ts>`.

## Hipótese e validação ANTES

H1: nenhuma chamada automática a `_restaurar_grafo_de_backup` em paths de exception:

```bash
grep -n "_restaurar_grafo_de_backup\|restore_grafo" src/pipeline.py
# Esperado: só chamada manual via CLI (linha ~830), nenhum auto
```

H2: backup automatizado já existe e funciona (validado em d97df41):

```bash
ls data/output/backup/grafo_*.sqlite | head -3
ls data/output/backup/grafo_*.sha256 | head -3
# Esperado: pares (.sqlite + .sha256) presentes
```

## Objetivo

1. Envolver `executar()` em `try/except`:
   ```python
   ts_backup = _executar_backup_grafo()
   try:
       # 15 estágios
   except Exception as exc:
       if ts_backup:
           ts_str = ts_backup.stem[len(PREFIXO_BACKUP_GRAFO):]
           logger.error("Pipeline crashou no estágio %s. Restaurando backup %s.", _estagio_atual, ts_str)
           _restaurar_grafo_de_backup(ts_str)
           _registrar_falha_estruturada(_estagio_atual, exc, ts_backup)
       raise
   ```
2. Variável módulo `_estagio_atual` atualizada antes de cada `_executar_*`.
3. `_registrar_falha_estruturada` grava `logs/pipeline_falha_<ts>.json` com estágio + traceback + timestamp + path do backup usado.
4. Restore só dispara se backup existe (graceful em primeira execução).
5. Falha de restore não suprime exception original (re-raise).

## Não-objetivos

- Não tocar `INFRA-PIPELINE-TRANSACIONALIDADE` (transação por estágio é responsabilidade dela).
- Não criar UI para visualizar falhas (futuro: dashboard de saúde do pipeline).
- Não retry automático após restore (decisão humana decide se re-rodar).

## Proof-of-work runtime-real

```bash
# 1. Simular crash mid-pipeline e verificar restore
.venv/bin/python -c "
from src.pipeline import executar, _executar_backup_grafo, _restaurar_grafo_de_backup
from src.graph.db import GrafoDB, caminho_padrao
import shutil, tempfile

# Snapshot baseline
db = GrafoDB(caminho_padrao())
n0 = db.con.execute('SELECT COUNT(*) FROM node').fetchone()[0]

# Forçar exception no meio (monkey-patch um estágio)
import src.pipeline as p
original = p._executar_linking_documentos
p._executar_linking_documentos = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('forçar crash'))

try:
    executar(processar_tudo=False)
except RuntimeError:
    pass
finally:
    p._executar_linking_documentos = original

db = GrafoDB(caminho_padrao())
n1 = db.con.execute('SELECT COUNT(*) FROM node').fetchone()[0]
assert n0 == n1, f'restore falhou: {n0} -> {n1}'
print('OK restore automatico em crash')
"

# 2. Log estruturado
ls logs/pipeline_falha_*.json | tail -1
# Esperado: 1 arquivo com estagio + traceback
```

## Acceptance

- `try/except` em `executar()` com auto-restore.
- 3 testes regressivos: (a) crash dispara restore; (b) crash sem backup re-raise sem corromper; (c) log estruturado gerado.
- `logs/pipeline_falha_<ts>.json` schema documentado em `docs/SCHEMAS_LOGS.md`.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (m) Branch reversível — restore é o "git revert" do grafo.
- (n) Defesa em camadas — TX por estágio (sprint anterior) + restore catastrófico (esta).
- (u) Proof-of-work runtime-real com simulação de crash.

---

*"Toda fortaleza precisa de duas muralhas: a interna repara o golpe, a externa repara a queda." — princípio da defesa em profundidade*
