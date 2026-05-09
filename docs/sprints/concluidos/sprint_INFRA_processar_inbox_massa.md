---
id: INFRA-PROCESSAR-INBOX-MASSA
titulo: Wrapper sobre reprocessar_documentos.py + log estruturado por categoria
status: concluída
concluida_em: 2026-05-09
prioridade: media
data_criacao: 2026-05-08
revisada_em: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: [INFRA-EXTRATORES-USAR-OPUS]
esforco_estimado_horas: 2
origem: docs/auditorias/VALIDACAO_END2END_2026-05-08.md + revisão do agent executor 2026-05-08
---

# Sprint INFRA-PROCESSAR-INBOX-MASSA — wrapper sobre reprocessar_documentos.py

## Contexto (revisado 2026-05-08 após primeira tentativa de execução)

**Achado do agent executor**: já existe `scripts/reprocessar_documentos.py` (557L, Sprint 57) que faz exatamente o pipeline proposto. Rodar idempotente NÃO incrementa o grafo (48 → 48 documentos) porque os extratores específicos para cupom_foto/garantia/danfe FALHAM com `campos_insuficientes` (OCR fraco — confirmado pela validação fim-a-fim).

**Aritmética corrigida**: dos 854 arquivos brutos, 770 são bancários (viram `transacao`, não `documento`). Universo realista de nodes `documento` ingeríveis: **40-60** (vs meta original 200, inviável).

**Solução real**: depende de INFRA-EXTRATORES-USAR-OPUS (sprint nova) que refatora os 5 extratores que falham para usar `extrair_via_opus()` como fallback quando OCR local retorna `campos_insuficientes`.

## Objetivo (revisado)

Wrapper fino sobre `reprocessar_documentos.py`:
1. `scripts/processar_inbox_massa.py` que invoca `reprocessar_documentos.main(--forcar-reextracao)` após INFRA-EXTRATORES-USAR-OPUS estar integrado.
2. Log estruturado em `logs/inbox_massa_<timestamp>.log` com totais por categoria + falhas + delta vs estado anterior.
3. Backup automático de `grafo.sqlite` antes de rodar.

Critério ajustado: documentos passam de 48 para >=70 (após extratores OCR-Opus funcionarem).

## Objetivo

1. Criar `scripts/processar_inbox_massa.py` que:
   - Varre `data/raw/andre/**`, `data/raw/casal/**`, `data/raw/vitoria/**`.
   - Filtra extensões `{pdf, csv, xlsx, xls, ofx, jpeg, jpg, png}`.
   - Para cada arquivo: roteia ao extrator apropriado (já existem em `src/extractors/`); cataloga em grafo; persiste em `data/output/inbox_fila.json` (gerado por INFRA-INBOX-OFX-READER).
2. Idempotência: pular arquivos já presentes no grafo (lookup por sha256).
3. Logs estruturados em `logs/inbox_massa_<timestamp>.log` com totais por categoria + falhas.
4. Modo `--dry-run` que apenas relata o que faria.

## Validação ANTES

```bash
find data/raw -type f \( -name "*.pdf" -o -name "*.csv" -o -name "*.xlsx" -o -name "*.xls" -o -name "*.ofx" -o -name "*.jpeg" -o -name "*.png" \) 2>/dev/null | grep -v "/_\|/originais/" | wc -l
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento'"
```

## Não-objetivos

- NÃO reprocessar arquivos já catalogados (idempotente por sha256).
- NÃO mover arquivos da `data/raw/` (apenas leitura).
- NÃO chamar API externa massivamente nesta sprint (cupom_foto fica para INFRA-OCR-OPUS-VISAO + INFRA-EXTRATOR-CUPOM-FOTO).

## Proof-of-work

```bash
python scripts/processar_inbox_massa.py --dry-run
python scripts/processar_inbox_massa.py
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento'"
# Esperado: subir de 48 -> >=200 documentos
make lint && make smoke
.venv/bin/pytest tests/ -k "inbox or processar" -q
```

## Critério de aceitação

1. Script roda sem erro em `data/raw/andre/`, `data/raw/casal/`, `data/raw/vitoria/`.
2. Documentos no grafo passa de 48 para pelo menos 200 (mínimo conservador, varias NFCe + boletos + faturas + extratos).
3. Logs estruturados gerados.
4. Lint + smoke + pytest baseline.

## Referência

- Spec dependente: `INFRA-INBOX-OFX-READER` (commit `62f71d0`, leitor base).
- Auditoria: `VALIDACAO_END2END_2026-05-08.md`.

*"Pipeline sem rodar é arquitetura promissora; pipeline rodado é dado real." — princípio INFRA-PROCESSAR-INBOX-MASSA*
