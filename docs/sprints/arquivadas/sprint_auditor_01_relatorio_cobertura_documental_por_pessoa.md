# Sprint AUDITOR-01 -- Relatório de cobertura documental por pessoa (Claude lê tudo + fala dos faltantes)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 2
**Esforço estimado**: 5h
**Depende de**: LLM-01, DESIGN-01
**Fecha itens da auditoria**: item N da revisão 2026-04-29 (visão do dono)

## Problema

Visão do dono: 'eu quero que o claude leia cada arquivo atual, fale dos faltantes, gere os outputs, compare com os dele, veja como podemos integrar'. Hoje o Revisor 4-way mostra divergência item a item, mas falta visão agregada por pessoa (André, Vitória) e por domínio (financeiro, identidade, saúde, profissional, acadêmico) do que está presente vs faltante.

## Hipótese

Comparar `data/raw/<pessoa>/` + nodes do grafo com a tabela do BLUEPRINT (DESIGN-01) e gerar relatório por pessoa: lista de tipos esperados × tipos presentes × tipos faltantes. Para cada faltante, sugerir ação (subir foto, baixar do gov.br, pedir do RH, etc.). Output em `data/output/cobertura_<pessoa>.md`.

## Implementação proposta

1. `src/analysis/cobertura_documental.py` — função `gerar_relatorio_pessoa(pessoa: str)`.
2. Lê tabela do BLUEPRINT (YAML estruturado, derivado).
3. Cruza com nodes do grafo + arquivos físicos.
4. Aba 'Cobertura Pessoal' no dashboard com 2 colunas (André × Vitória).
5. Encadear em `--full-cycle` para regenerar a cada rodada.

## Proof-of-work (runtime real)

Para cada pessoa, relatório lista pelo menos 30 tipos esperados com status presente/faltante/parcial.

## Acceptance criteria

- Módulo + função.
- Relatórios MD em runtime real.
- Aba dashboard.
- Encadeado em --full-cycle.

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
