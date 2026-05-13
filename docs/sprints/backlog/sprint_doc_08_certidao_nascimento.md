---
id: DOC-08-CERTIDAO-NASCIMENTO
titulo: 'Sprint DOC-08 -- Extrator: certidão de nascimento'
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint DOC-08 -- Extrator: certidão de nascimento

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: LLM-01, ANTI-MIGUE-01
**Fecha itens da auditoria**: itens 19, 22 da auditoria honesta

## Problema

certidão de nascimento é documento cotidiano sem regra YAML nem extrator. Cai silenciosamente em _classificar/ ou roteamento-only.

## Hipótese

Spec do tipo + regra de classificação + extrator dedicado + fixtures sintéticas + 3 amostras reais para gate 4-way.

## Implementação proposta

1. Adicionar tipo em mappings/tipos_documento.yaml.
2. Criar src/extractors/certidao_nascimento.py.
3. Registrar em src/intake/registry.py.
4. Fixture sintética em tests/fixtures/.
5. 3 amostras reais validadas no Revisor 4-way.

## Proof-of-work (runtime real)

`make conformance-certidao_nascimento` retorna exit 0 (≥3 amostras 4-way verdes).

## Acceptance criteria

- Tipo em tipos_documento.yaml.
- Extrator src/extractors/certidao_nascimento.py com 8+ testes.
- Fixture sintética + 3 amostras reais.
- Gate 4-way verde.

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
