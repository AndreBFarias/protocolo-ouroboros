# Sprint UX-10 -- Clarificar hierarquia cluster vs aba (mesmos rótulos confundem usuário)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 6
**Esforço estimado**: 2h
**Depende de**: nenhuma
**Fecha itens da auditoria**: achado da auditoria visual 2026-04-29

## Problema

Cluster 'Home' tem aba 'Finanças'; cluster 'Documentos' tem aba 'Catalogação'. A sidebar mostra dropdown 'Área' com clusters; o topo mostra abas. Mas alguns rótulos repetem (cluster 'Análise' tem aba 'Análise' interna). Usuário não sabe se está em cluster ou em aba. Auditoria visual 2026-04-29 detectou ambiguidade.

## Hipótese

Renomear sidebar 'Área' para 'Domínio' (5 domínios) e diferenciar visualmente domínio (sidebar, label maiúsculo) de aba (top, lowercase mono). Eliminar nomes duplicados: cluster 'Análise' vira 'Análise & Categorias'.

## Implementação proposta

1. Renomear label sidebar.
2. Auditar MAPA_ABA_PARA_CLUSTER e renomear duplicatas.
3. Adicionar breadcrumb 'Domínio › Aba' em cada página.
4. Validação visual em 5 clusters.

## Proof-of-work (runtime real)

Screenshot lado-a-lado antes/depois mostrando hierarquia clara.

## Acceptance criteria

- Sidebar com label 'Domínio'.
- Zero duplicação de rótulos.
- Breadcrumb por página.

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
