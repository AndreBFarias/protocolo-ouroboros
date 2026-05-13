---
id: DOC-23-EXTRATOR-CONDOMINIO
titulo: Sprint DOC-23 — Extrator de boleto de condomínio
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint DOC-23 — Extrator de boleto de condomínio

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 6 (Casa) + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: ANTI-MIGUE-01 + Sprint 87.3 (extrator boleto base já existe)

## Problema

Condomínio mensal vem como boleto PDF ou email; quando boleto, é detectado como `boleto_servico` genérico, perdendo metadata específica (rateio, taxa extra, etc.).

## Hipótese

Estender extrator de boleto (Sprint 87.3) com regex específica para condomínio (admin do prédio, rateio, fundo de reserva). Fornecedor canônico = administradora.

## Acceptance criteria

- Sub-classe ou flag em `boleto_pdf.py` para condomínio.
- 3 amostras 4-way.

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
