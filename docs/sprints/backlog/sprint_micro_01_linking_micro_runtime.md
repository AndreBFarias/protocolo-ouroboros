# Sprint MICRO-01 -- Edges transação→nfce→item no grafo em runtime (SPEC PAI HISTÓRICA)

> **Status: ramificada em 01a/01b por bloqueio de DOC-02/DOC-19, decisão do dono em 2026-04-29**
> (Fase 0 do plano `~/.claude/plans/glittery-munching-russell.md`, decisão D1).
>
> Esta spec permanece em `backlog/` como referência histórica. Execução real foi divida em:
>
> - `sprint_micro_01a_linking_nfce_existente.md` (P1, ~3h, **sem dependência** -- usa material já no grafo: 2 NFCe + 33 arestas `contem_item` + 41 items).
> - `sprint_micro_01b_linking_mercado_holerite.md` (P2, ~2h, **depende de DOC-02 + DOC-19 + MICRO-01a** -- amplifica para ~250 transações de mercado físico + ~170 arestas de holerite).
>
> Auditoria que motivou a ramificação: `docs/auditorias/linking_2026-04-29.md`.

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 4
**Esforço estimado**: 5h (3h MICRO-01a + 2h MICRO-01b)
**Depende de**: DOC-02, DOC-19 (apenas para MICRO-01b -- MICRO-01a não tem dependência)
**Fecha itens da auditoria**: nenhum

## Problema

Drill-down 'paguei R$ 800 Vivendas → 3 itens granulares' impossível porque edge transação→item não existe.

## Hipótese

Após linking transação↔documento (Sprint 95), expandir: para cada edge documento_de, criar edges transação→nfce e nfce→item.

## Implementação proposta

src/transform/linking_micro.py + integração no pipeline.

## Proof-of-work (runtime real)

Transação Vivendas tem 1 nfce + 3 itens acessíveis via grafo.

## Acceptance criteria

- Edges criadas em runtime real.
- 8+ testes.

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
