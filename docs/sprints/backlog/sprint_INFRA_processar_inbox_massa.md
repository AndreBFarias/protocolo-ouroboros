---
id: INFRA-PROCESSAR-INBOX-MASSA
titulo: Rodar inbox_reader.processar_fila em massa em data/raw/{andre,casal,vitoria}/**
status: backlog
prioridade: altissima
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: [INFRA-OCR-OPUS-VISAO, INFRA-INBOX-OFX-READER]
esforco_estimado_horas: 4
origem: docs/auditorias/VALIDACAO_END2630_2026-05-08.md (854 arquivos brutos vs 48 documentos no grafo)
---

# Sprint INFRA-PROCESSAR-INBOX-MASSA — processar a massa real

## Contexto

INFRA-INBOX-OFX-READER (commit `62f71d0`) criou o leitor da inbox mas só foi rodado em 5 fixtures sintéticas. Na prática há **854 arquivos brutos** em `data/raw/{andre,casal,vitoria}/**` (excluindo `_classificar`, `_conferir`, `_envelopes`, `originais` que são pool/triagem). Hoje no grafo: **48 documentos**.

Esta sprint preenche o gap rodando o pipeline em massa.

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
