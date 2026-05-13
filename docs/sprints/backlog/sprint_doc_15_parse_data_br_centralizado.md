---
id: DOC-15-PARSE-DATA-BR-CENTRALIZADO
titulo: Sprint DOC-15 -- parse_data_br() em src/utils/parse_br.py + remover regex
  local de 22 extratores
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint DOC-15 -- parse_data_br() em src/utils/parse_br.py + remover regex local de 22 extratores

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 26 da auditoria

## Problema

22 extratores fazem regex próprio para data DD/MM/YYYY. Inconsistente.

## Hipótese

parse_data_br(s: str, formatos: tuple = ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d')) -> date | None com fallback. Substituir em todos os 22.

## Implementação proposta

Adicionar função + grep+sed substitui em cada extrator.

## Proof-of-work (runtime real)

grep para regex de data deve voltar 0 fora de parse_br.py.

## Acceptance criteria

- Função coberta.
- Migração completa.
- Pytest baseline mantido.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
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
