---
id: DOC-24-EXTRATOR-CRLV-CRV
titulo: Sprint DOC-24 — Extrator de CRLV/CRV digital (gov.br)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint DOC-24 — Extrator de CRLV/CRV digital (gov.br)

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 7 (Mobilidade) + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: ANTI-MIGUE-01

## Problema

Casal tem 0 nodes de veículos no grafo. CRLV/CRV é documento gov.br padrão; sem extrator, contexto de mobilidade fica fora.

## Hipótese

`src/extractors/crlv_pdf.py` parseia layout gov.br: placa, RENAVAM, chassi, marca/modelo, ano, proprietário, validade. Cria node `documento` + node `fornecedor` (DETRAN) + alerta de validade.

## Acceptance criteria

- Extrator + 3 amostras 4-way ([A] e [V]).
- Alerta no dashboard se validade < 90d.

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
