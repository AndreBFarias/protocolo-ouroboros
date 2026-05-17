---
id: GRAFO-AUDIT-ORPHAN-NODES
titulo: "3 nodes fornecedor sem edges no grafo (órfãos): auditar + limpar ou relinkar"
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-17
fase: SANEAMENTO
epico: 3
depende_de: []
esforco_estimado_horas: 1
origem: "auditoria independente 2026-05-17. Query SQL identificou 3 nodes `fornecedor` sem nenhuma edge: ID 7426 (`45.850.636/0001-60`), ID 643 (`BIR COMERCIO`), ID 7463 (`DIRPF|E7536C39308A`). Possíveis duplicatas, fragmentos de migração antiga, ou nodes criados em testes que não foram limpos. Não afetam runtime, mas poluem queries e estatísticas."
---

# Sprint GRAFO-AUDIT-ORPHAN-NODES

## Contexto

Grafo SQLite tem ~7639 nodes / 25024 edges. Auditoria revelou:

```sql
SELECT id, nome_canonico FROM node
WHERE tipo='fornecedor'
AND id NOT IN (SELECT src_id FROM edge UNION SELECT dst_id FROM edge);
```

Retorna 3 nodes:
- `7426` — `fornecedor|45.850.636/0001-60` (CNPJ MEI André)
- `643` — `fornecedor|BIR COMERCIO`
- `7463` — `fornecedor|DIRPF|E7536C39308A`

Hipóteses:
- **Duplicata**: já existe outro node com mesma razão social via diferente CNPJ/alias.
- **Fragmento de migração**: criado em sprint anterior mas não linkado.
- **Teste vazado**: pytest criou e não cleanou.

## Hipótese e validação ANTES

```bash
sqlite3 data/output/grafo.sqlite "
SELECT id, nome_canonico, json_extract(metadata, '\$.aliases') as alias
FROM node WHERE tipo='fornecedor' AND id IN (7426, 643, 7463);
"

# Procurar duplicatas por razao_social:
sqlite3 data/output/grafo.sqlite "
SELECT id, nome_canonico FROM node
WHERE tipo='fornecedor' AND nome_canonico LIKE '%45.850.636%';
"
```

## Objetivo

1. **Script `scripts/auditar_grafo_orfaos.py`** (NOVO):
   - Lista TODOS os nodes sem edges (todos os tipos: fornecedor, documento, item, etc).
   - Para cada órfão, indica:
     - Quando criado (`created_at`)
     - Última modificação (`updated_at`)
     - Metadata (resumo)
     - Razão provável de orfandade (heurística: tem alias? mesma razão social em outro node?)
   - Output em `data/output/grafo_orfaos_<ts>.json`.

2. **Decisão por órfão** (manual ou semi-automática):
   - **Limpar** (DELETE) se for fragmento puro.
   - **Re-linkar** se for duplicata (merge com node primário existente).
   - **Manter** se for legítimo aguardando uso futuro (raro).

3. **Script complementar `scripts/limpar_grafo_orfaos.py`** com `--dry-run` / `--apply`:
   - Lê output do auditor.
   - Aplica decisões (DELETE ou UPDATE merge).
   - Log estruturado.

4. **Backup automático** antes de qualquer deleção (já existe via `_executar_backup_grafo`, mas ativá-lo explicitamente).

5. **Testes regressivos**:
   - `test_listar_orfaos_devolve_estrutura_canonica`
   - `test_limpar_orfaos_dry_run_nao_modifica`
   - `test_limpar_orfaos_apply_remove_e_loga`

## Não-objetivos

- Não rodar limpeza automática (decisão humana por órfão).
- Não tocar nodes com edges (out of scope).
- Não criar política de retenção (sprint-filha se necessário).

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/auditar_grafo_orfaos.py
cat data/output/grafo_orfaos_*.json | head -30
# Esperado: 3+ nodes listados com metadata

.venv/bin/python scripts/limpar_grafo_orfaos.py --dry-run
# Esperado: lista o que seria deletado

# Apos decisao:
.venv/bin/python scripts/limpar_grafo_orfaos.py --apply
sqlite3 data/output/grafo.sqlite "
SELECT COUNT(*) FROM node
WHERE id NOT IN (SELECT src_id FROM edge UNION SELECT dst_id FROM edge);
"
# Esperado: 0 (todos limpos OU re-linkados)
```

## Acceptance

- 2 scripts criados (auditar + limpar).
- 3 testes regressivos verdes.
- Grafo de produção com 0 nodes órfãos (apos decisão humana).
- Log estruturado `grafo_orfaos_<ts>.json` para audit.

## Padrões aplicáveis

- (m) Branch reversível — backup antes de DELETE.
- (l) Anti-débito — auditoria periódica detecta acúmulo.

---

*"Node sem edge é fantasma do grafo." — princípio da consistência relacional*
