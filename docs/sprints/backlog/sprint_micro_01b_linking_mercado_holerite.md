---
id: MICRO-01B-LINKING-MERCADO-HOLERITE
titulo: Sprint MICRO-01b -- Linking transação→nfce→item para mercado físico + holerite
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint MICRO-01b -- Linking transação→nfce→item para mercado físico + holerite

**Origem**: ramificação de `sprint_micro_01_linking_micro_runtime.md` por decisão do dono em 2026-04-29 (Fase 0 do plano `glittery-munching-russell`, decisão D1).
**Prioridade**: P2
**Onda**: 4
**Esforço estimado**: 2h
**Depende de**: DOC-02 (mercado_nf_fisica) **E** DOC-19 (holerite contem_item sem código) **E** MICRO-01a (backbone)
**Fecha itens da auditoria**: amplificação do backbone do cruzamento micro

## Problema

MICRO-01a entrega backbone funcional mas com cobertura ínfima (2 NFCe, 33 items). Auditoria mostra que volume real está em:

- 477 transações em mercado/padaria/Vivendas (R$ 26 mil) -- coberto se DOC-02 ingerir as NFs físicas.
- 24 holerites × ~7 verbas cada = ~170 arestas `contem_item` adicionais -- coberto se DOC-19 enriquecer holerites com items granulares mesmo sem `codigo_produto`.

Sem DOC-02 + DOC-19, o backbone do MICRO-01a fica restrito a 2 transações, e a aba MICRO-03 + IRPF-01 exibem demonstração mas não cobertura útil.

## Hipótese

Após DOC-02 ingerir NFs físicas (Vivendas, Panificadora, mercados similares) e DOC-19 enriquecer holerites com itens granulares, rodar o motor de MICRO-01a sobre o grafo expandido produz:

- ~250 transações de mercado/padaria com `documento_de` apontando para NF física → drill-down item-a-item por compra.
- ~170 arestas `contem_item` adicionais cobrindo verbas de holerite (Salário base, INSS, IRRF, VR-VA, FGTS, plano saúde) → drill-down de renda.

## Implementação proposta

1. **Pré-condição**: aguardar DOC-02 e DOC-19 estarem em `docs/sprints/concluidos/` antes de iniciar.
2. Reusar módulo de MICRO-01a (path canônico já decidido lá).
3. Adicionar 2 fixtures sintéticas: 1 NF física Vivendas com 5 itens; 1 holerite G4F com 7 verbas.
4. Adicionar testes específicos (≥6) cobrindo: NF física com itens, holerite com verbas, holerite com edge case de verba sem código.
5. Rodar pipeline e conferir crescimento.

## Proof-of-work (runtime real)

Para 1 transação Vivendas R$ 800: drill-down via grafo retorna ≥5 itens (ex: ARROZ TIO JOÃO 5KG, FEIJÃO CARIOCA 1KG, etc.).
Para 1 holerite G4F: drill-down retorna ≥7 verbas (Salário base, INSS, IRRF, VR, etc.).

Métrica de crescimento esperada:
- Arestas `transacao_documento` (canônico de MICRO-01a): 2 → ≥250 (+248).
- Arestas `contem_item`: 33 → ≥200 (+170 de holerite).
- Cobertura drill-down: 2 → ≥250 transações com items.

## Acceptance criteria

- Pré-requisitos DOC-02 + DOC-19 confirmados em `docs/sprints/concluidos/`.
- Reuso do módulo MICRO-01a (não duplicar).
- ≥6 testes adicionais; fixtures sintéticas para NF física + holerite.
- ≥250 transações de mercado com drill-down em runtime real.
- ≥7 verbas drill-downáveis para 1 holerite.
- Smoke 10/10, lint OK, baseline pytest crescida.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese validada com query SQL pós-DOC-02/DOC-19 antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` quando aplicável (não -- usa motor MICRO-01a).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.

## Notas

- Sprint irmã `sprint_micro_01a_linking_nfce_existente.md` é a primeira a executar (sem dependência) e estabelece o backbone.
- Spec pai histórica: `sprint_micro_01_linking_micro_runtime.md`.
