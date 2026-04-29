# Sprint DOC-25 — Extrator de IPVA + apólice de seguro auto

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 7 + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: DOC-24 (precisa node veículo no grafo)

## Problema

IPVA e seguro auto são despesas anuais recorrentes do casal sem extrator dedicado.

## Hipótese

`src/extractors/ipva_pdf.py` + sub-classe de cupom_garantia para apólice auto. Linkam ao node veículo (criado por DOC-24) via `cobre`.

## Acceptance criteria

- 2 extratores (IPVA + apólice) com 3 amostras 4-way cada.
- IPVA tag IRPF `imposto_pago`.
- Apólice cria node `garantia` linkado ao veículo.

## Gate anti-migué

9 checks padrão.
---

## Papel do supervisor (Opus Claude Code)

Conforme ADR-13 e `docs/SUPERVISOR_OPUS.md`, eu (Opus principal nesta sessão interativa) executo este extrator novo seguindo:

1. Leio amostra bruta (`Read` tool sobre PDF/foto) — meu OCR/visão multimodal.
2. Comparo meu output com o do extrator candidato em runtime: `python scripts/reprocessar_documentos.py --dry-run --raiz <pasta-com-amostra>`.
3. Diferenças viram regex/regra ajustada na implementação ou Edit-pronto na hora.
4. Marco >=3 amostras 4-way no Revisor (gate ANTI-MIGUE-01) antes de mover spec para `concluidos/`.
5. Para refactor substancial despacho subagent `executor-sprint` em worktree isolado via Agent tool.
6. Após cada amostra, atualizo `docs/HISTORICO_SESSOES.md` com snapshot — preserva progresso se a sessão cair.

**NÃO há chamada Anthropic API. NÃO há cliente Python `anthropic`. NÃO existe `src/llm/`.** Regra inviolável (ADR-13).
