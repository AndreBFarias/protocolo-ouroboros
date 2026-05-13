---
id: IRPF-02-IRPF-DEDUTIVEL-MEDICO
titulo: Sprint IRPF-02 -- Link automático receita médica + exame + pagamento bancário
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint IRPF-02 -- Link automático receita médica + exame + pagamento bancário

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 4
**Esforço estimado**: 3h
**Depende de**: DOC-09, DOC-10
**Fecha itens da auditoria**: nenhum

## Problema

Despesas médicas dedutíveis precisam cruzamento manual.

## Hipótese

Heurística (CPF do paciente + data ±30d + valor ±10%) cria edge dedutivel_medico.

## Implementação proposta

src/transform/linking_medico.py.

## Proof-of-work (runtime real)

Casal tem 5+ despesas médicas → 5+ edges dedutivel_medico criadas.

## Acceptance criteria

- Heurística testada.
- Edges em runtime real.

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
