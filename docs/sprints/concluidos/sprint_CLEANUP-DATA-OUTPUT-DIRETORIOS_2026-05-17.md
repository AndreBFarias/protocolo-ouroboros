---
id: CLEANUP-DATA-OUTPUT-DIRETORIOS
titulo: "Limpeza de diretórios obsoletos em `data/output/` (_lixo, _backup, _arquivado)"
status: concluída
concluida_em: 2026-05-17
prioridade: P3
data_criacao: 2026-05-17
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.5
origem: "auditoria independente 2026-05-17. Cluttering em `data/output/`: (a) `opus_ocr_pendentes_lixo_2026-05-12/` (6 .txt com paths /tmp/pytest), (b) `opus_ocr_cache_sintetico_backup/` (cache antigo pós-migração), (c) `_backup_pre_migracao_quem/` (2026-05-01 — 16 dias atrás). Acumulam, não consumidos."
---

# Sprint CLEANUP-DATA-OUTPUT-DIRETORIOS

## Contexto

Auditoria filesystem revelou diretórios em `data/output/` que viraram cemitérios:

| Diretório | Tamanho | Idade | Origem |
|---|---|---|---|
| `opus_ocr_pendentes_lixo_2026-05-12/` | ? | 5d | Sprint Fase A — caches de teste vazaram |
| `opus_ocr_cache_sintetico_backup/` | ? | 5d | Sprint substituir-cache-sintetico (preservado para rollback) |
| `_backup_pre_migracao_quem/` | 626KB | 16d | Migração tipo_documento (sprint antiga) |

Nenhum desses é consumido por código atual. Backup automático do grafo (`data/output/backup/grafo_*.sqlite`) tem política de retenção (7d + 1/sem); mas esses diretórios manuais não têm.

## Hipótese e validação ANTES

```bash
ls -la data/output/ | grep -E "_lixo|_backup|_sintetico|_arquivado" | head -10

du -sh data/output/opus_ocr_pendentes_lixo_2026-05-12/ \
       data/output/opus_ocr_cache_sintetico_backup/ \
       data/output/_backup_pre_migracao_quem/ 2>/dev/null

# Confirmar que não são consumidos:
grep -rn "opus_ocr_pendentes_lixo\|_backup_pre_migracao_quem\|opus_ocr_cache_sintetico_backup" src/ scripts/ tests/ | head -5
```

## Objetivo

1. **Auditar cada diretório**:
   - `opus_ocr_pendentes_lixo_2026-05-12/`: 6 arquivos de pytest temp — **SAFE deletar**.
   - `opus_ocr_cache_sintetico_backup/`: cache pré-substituição — **mover para `data/_arquivo_historico/2026-05-12/`** (retenção 90d explícita).
   - `_backup_pre_migracao_quem/`: XLSXs pré-migração — **mover para `data/_arquivo_historico/2026-05-01/`**.

2. **Script `scripts/limpar_data_output.py`** (NOVO):
   ```python
   """Limpa diretorios obsoletos em data/output/ com retencao configurada.

   Politica:
   - opus_ocr_pendentes_lixo_*  -> DELETE (resíduos de teste)
   - _backup_pre_*              -> MOVE para data/_arquivo_historico/
   - opus_ocr_cache_sintetico_* -> MOVE
   """
   ```
   Com `--dry-run` e `--apply`.

3. **Atualizar `.gitignore`** se necessário (já cobre `data/`).

4. **Documentar política** em `docs/ARMADILHAS.md` ou novo `docs/RETENCAO_DATA.md`:
   - Backups grafo: 7d + 1/sem 4 sem.
   - Caches OCR sintéticos pós-substituição: 90d em `_arquivo_historico/`.
   - Resíduos pytest: deletados em cada limpeza.

5. **Hook opcional** em `make smoke` ou `./run.sh --check`: avisar se >100MB em data/output/ acumulado.

## Não-objetivos

- Não tocar `data/output/dossies/` (estado canônico).
- Não tocar `data/output/grafo.sqlite` ou `ouroboros_2026.xlsx` (artefatos vivos).
- Não criar cron — script é manual.

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/limpar_data_output.py --dry-run
# Esperado: lista os 3 diretorios + acao

.venv/bin/python scripts/limpar_data_output.py --apply
ls data/output/ | grep -E "_lixo|_backup_pre|_sintetico_backup"
# Esperado: vazio

ls data/_arquivo_historico/ 2>/dev/null
# Esperado: 2026-05-01/, 2026-05-12/ com artefatos preservados
```

## Acceptance

- 3 diretórios obsoletos removidos/movidos.
- `data/_arquivo_historico/` contém backups deslocados.
- Política documentada.
- Script idempotente (rodar 2× não duplica).

## Padrões aplicáveis

- (m) Branch reversível — move (não delete) para histórico antes de apagar.
- (l) Anti-débito — política previne acúmulo futuro.

---

*"Diretório morto é hospede silencioso." — princípio da casa arrumada*
