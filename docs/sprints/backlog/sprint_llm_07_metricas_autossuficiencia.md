# Sprint LLM-07 -- Métricas de autossuficiência (ADR-09) no dashboard

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 2
**Esforço estimado**: 3h
**Depende de**: LLM-01
**Fecha itens da auditoria**: nenhum

## Problema

ADR-09 declara que LLM é provisório; métrica-chave é % determinístico. Sem dashboard, não há controle de evolução.

## Hipótese

Calcular % de classificações que vieram só de regex/YAML vs % que precisaram de LLM. Mostrar tendência mensal.

## Implementação proposta

Página/aba 'Autossuficiência' com line chart.

## Proof-of-work (runtime real)

Gráfico exibe valor numérico real.

## Acceptance criteria

- Aba live.
- % calculado a partir de dados reais.

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
