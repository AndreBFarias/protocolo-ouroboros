---
id: DOC-21-EXTRATOR-CONTRATO-LOCACAO
titulo: Sprint DOC-21 — Extrator de contrato de locação
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint DOC-21 — Extrator de contrato de locação

**Origem**: BLUEPRINT_VIDA_ADULTA.md §1 domínio 6 (Casa) + ramificação ANTI-MIGUE-06.
**Prioridade**: P3
**Onda**: 3 (cobertura documental)
**Esforço estimado**: 4h
**Depende de**: ANTI-MIGUE-01 (gate 4-way obrigatório para extratores novos)

## Problema

Contrato de locação imobiliária é documento legal recorrente do casal mas não tem extrator dedicado — cai em catch-all `recibo_nao_fiscal`.

## Hipótese

`src/extractors/contrato_locacao_pdf.py` extrai: locador, locatário, imóvel, valor mensal, data início/fim, índice de reajuste. Cria nodes `documento` + `fornecedor` (locador) + `periodo` (vigência) + arestas.

## Acceptance criteria

- Extrator funcional em fixture sintética + 1 amostra real.
- Gate 4-way ≥3 amostras antes de mover para concluidos.
- Linkado em mappings/tipos_documento.yaml com prio `especifico`.

## Gate anti-migué

Padrão dos 9 checks de ANTI-MIGUE-01 + frontmatter `concluida_em`.
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
