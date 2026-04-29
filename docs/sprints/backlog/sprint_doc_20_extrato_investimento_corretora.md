# Sprint DOC-20 -- Extrator: extrato de investimento (B3, NuInvest, Rico, XP, BTG)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 3
**Esforço estimado**: 5h
**Depende de**: LLM-01, ANTI-MIGUE-01
**Fecha itens da auditoria**: item G da revisão 2026-04-29 — IRPF-01 sem investimentos

## Problema

Visão do dono: 'gerar IRPF do ano X' deve incluir investimentos. Hoje IRPF-01 cobre NFs, holerites, transações, parcelamentos, DAS — mas não há extrator de extrato de corretora. Ações, FIIs, RF, tesouro direto e cripto ficam invisíveis para tributação e patrimônio.

## Hipótese

Extrator unificado por corretora (PDF + CSV). B3 disponibiliza informe consolidado anual; corretoras geram extratos mensais. Tipo `extrato_investimento` com campos: ativo, quantidade, preco_medio, valor_aplicado, valor_atual, rendimento, data, corretora.

## Implementação proposta

1. Tipo em mappings/tipos_documento.yaml.
2. src/extractors/extrato_investimento.py com sub-extratores.
3. Node novo `investimento` no grafo + edge `posicao_em`.
4. Coluna `tipo=Investimento` no XLSX (separa de Receita/Despesa).
5. Fixture sintética + 3 amostras reais para gate 4-way.
6. IRPF-01 consome via grafo.

## Proof-of-work (runtime real)

make conformance-extrato_investimento exit 0.

## Acceptance criteria

- Tipo + extrator + node novo.
- 8+ testes.
- Gate 4-way verde.
- IRPF-01 consome.

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
