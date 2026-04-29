---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 98a
  title: "Backfill automatico de metadata.arquivo_origem em nodes do grafo apos rename retroativo"
  prioridade: P1
  estimativa: ~2h
  origem: "achado da fase Opus Sprint 103: 4 nodes (7446/7454/7457/7460) tem arquivo_origem apontando para arquivos REMOVIDOS pela Sprint 98 --executar"
  touches:
    - path: src/graph/backfill_arquivo_origem.py
      reason: "estende a logica existente (Sprint 87.5) para detectar paths quebrados e re-resolver via grafo+filesystem"
    - path: scripts/migrar_holerites_retroativo.py
      reason: "ao executar rename, atualiza arquivo_origem dos nodes correspondentes em vez de deixar stale"
    - path: tests/test_sprint_98a_backfill.py
      reason: "regressao: rename de holerite atualiza tambem o metadata no grafo"
  forbidden:
    - "Modificar nome_canonico ou hash do node (so metadata.arquivo_origem)"
    - "Apagar nodes que nao tem mais arquivo correspondente -- so marcar com warning"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_sprint_98a_backfill.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "scripts/migrar_holerites_retroativo.py atualiza arquivo_origem para o novo path canonico apos rename"
    - "backfill_arquivo_origem ganha rotina detectar_paths_quebrados que lista nodes apontando para arquivos inexistentes"
    - "Helper resolve_path_por_metadata busca o novo path via tipo_documento + mes_ref + valor (heuristica)"
    - "Apos rodar, 0 nodes apontam para arquivos removidos pela Sprint 98 (verificavel em runtime real)"
  proof_of_work_esperado: |
    # Antes
    .venv/bin/python -c "
    from src.graph.db import GrafoDB
    from pathlib import Path
    db = GrafoDB('data/output/grafo.sqlite')
    cur = db._conn.execute(
      \"SELECT json_extract(metadata, '$.arquivo_origem') FROM node WHERE tipo='documento'\"
    )
    quebrados = [r[0] for r in cur if r[0] and not Path(r[0]).exists()]
    print(f'Nodes com path quebrado: {len(quebrados)}')
    "
    # Esperado: 4+ nodes
    
    # Depois (apos sprint)
    [mesmo comando]
    # Esperado: 0 nodes
```

---

# Sprint 98a -- Backfill arquivo_origem retroativo

**Status:** BACKLOG (P1, criada 2026-04-28 como achado Opus Sprint 103)

## Motivação

Sprint 98 (commit `a48b843`) renomeou 24 holerites de `holerite_<timestamp>.pdf` para `HOLERITE_<YYYY-MM>_<empresa>_<liquido>.pdf` no filesystem -- mas o `metadata.arquivo_origem` no node `documento` do grafo continuou apontando para o nome ANTIGO. Resultado: 4 nodes (7446, 7454, 7457, 7460) apontam para arquivos que não existem mais.

Isso quebra:
- Preview de PDF no Revisor Visual (Sprint D2).
- Reconciliacao boleto-tx (Sprint 87.7).
- Auditoria via grep no grafo.

## Implementação

### 1. Atualizar `migrar_holerites_retroativo.py`

Quando `--executar` move o arquivo, propagar o novo path para `metadata.arquivo_origem` do node correspondente. Chave de match: `tipo_documento` + `mes_ref` + valor.

### 2. Estender `src/graph/backfill_arquivo_origem.py`

Adicionar:
- `detectar_paths_quebrados(grafo) -> list[dict]`: lista nodes onde `metadata.arquivo_origem` aponta para Path inexistente.
- `resolver_via_metadata(grafo, node_id) -> Path | None`: heuristica busca arquivo atual via tipo_documento + mes_ref + valor.

### 3. Integrar em `run.sh --reextrair-tudo`

Antes da reextracao completa (Sprint 104), rodar `backfill_arquivo_origem.py` para corrigir paths quebrados. Mais barato que reextrair.

## Testes regressivos

1. Sintetico: 1 holerite no grafo + arquivo renomeado no FS -> backfill atualiza metadata.
2. Holerite sem candidato no FS -> log warning, não apaga node.
3. Idempotencia: rodar 2x não corrompe.

## Dependências

- Sprint 98 ja em main.
- Sprint 87.5 (commit `8a98c1e`) ja tem o esqueleto do backfill.
