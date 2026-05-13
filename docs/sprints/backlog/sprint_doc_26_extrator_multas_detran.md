---
id: DOC-26-EXTRATOR-MULTAS-DETRAN
titulo: Sprint DOC-26 — Extrator de multas Detran
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint DOC-26 — Extrator de multas Detran

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 7 + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: DOC-24

## Problema

Multas Detran chegam por email/PDF; sem extrator, perdem contexto (auto da infração, pontos CNH).

## Hipótese

`src/extractors/multa_detran_pdf.py` parseia auto de infração: AIT, placa, data, local, valor, pontos CNH. Linka ao veículo + alerta.

## Acceptance criteria

- 3 amostras 4-way.
- Alerta de pontos CNH acumulando perto do limite (20).

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
