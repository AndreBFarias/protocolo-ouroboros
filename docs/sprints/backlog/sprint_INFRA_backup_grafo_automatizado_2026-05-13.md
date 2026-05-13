---
id: INFRA-BACKUP-GRAFO-AUTOMATIZADO
titulo: Backup automático do grafo.sqlite antes de cada pipeline + retenção 7 dias
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-13
fase: PRODUCAO_READY
depende_de: []
esforco_estimado_horas: 2
origem: auditoria operacional 2026-05-13 (Explore agent). data/output/grafo.sqlite (5.4M, 7639 nós, 25024 arestas) é single-point-of-failure. Pipeline default não faz snapshot pré-execução -- se ./run.sh --tudo crashar no meio, estado fica inconsistente sem rollback fácil.
---

# Sprint INFRA-BACKUP-GRAFO-AUTOMATIZADO

## Contexto

Hoje 2 scripts isolados fazem backup do grafo: `scripts/dedup_nfce_grafo.py` e `scripts/processar_inbox_massa.py`. O pipeline default `./run.sh --tudo` não. Crash mid-pipeline (linker, dedup, ingestor) deixa grafo em estado inconsistente.

Padrão `(m)` do BRIEF: branch reversível. Toda mudança não-trivial deve ser revertível. Backup é o equivalente operacional.

## Objetivo

1. Função `_executar_backup_grafo()` em `src/pipeline.py` chamada antes de `_descobrir_extratores`. Grava em `data/output/backup/grafo_YYYY-MM-DD_HHMMSS.sqlite` (gitignored, mesmo padrão de `data/output/backup/` para XLSX).
2. Retenção 7 dias: deleta backups mais antigos automaticamente (mantém últimos 7 + 1 por semana das últimas 4 semanas).
3. Comando manual `./run.sh --restore-grafo <timestamp>` para reverter ao snapshot dado.
4. Checksum SHA256 do backup em `.sha256` ao lado para detectar corrupção.

## Proof-of-work

```bash
ls data/output/backup/grafo_*.sqlite | wc -l   # antes: 0
./run.sh --tudo
ls data/output/backup/grafo_*.sqlite | wc -l   # depois: 1 + os antigos
sha256sum -c data/output/backup/grafo_*.sqlite.sha256
```

## Acceptance

- Backup criado em `data/output/backup/` antes de cada `--tudo`.
- Retenção 7 dias automática (cron interno do script).
- Comando `--restore-grafo` funcional.
- Pytest > 2964 + testes novos.
- Smoke 10/10. Lint 0.

---

*"Dado sem backup é dado emprestado." -- princípio do arquivista pragmático*
