---
id: DOC-28-PASSAPORTE
titulo: Sprint DOC-28 -- Extrator de passaporte digital
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint DOC-28 -- Extrator de passaporte digital

**Origem**: lacuna 2 da auditoria `docs/auditorias/cobertura_backlog_2026-04-29.md` (item 19 do plan `pure-swinging-mitten`, Onda 3).
**Prioridade**: P2
**Onda**: 3 (apoio à fase OMEGA-94b -- identidade)
**Esforço estimado**: 3h
**Depende de**: DOC-12 (gov.br PDF auto-detect) recomendado se passaporte vier do gov.br
**Fecha itens da auditoria**: lacuna 2 dos 8 tipos cotidianos

## Problema

Passaporte brasileiro digital (PDF do gov.br ou foto do passaporte físico) não é declarado em `mappings/tipos_documento.yaml`. Classifier roteia para `_classificar/`. Sem cobertura, fase OMEGA-94b (identidade) fica incompleta -- RG e CNH têm spec, passaporte ficaria buraco.

Baixa frequência (emissão a cada 10 anos), mas relevante para o domínio identidade.

## Hipótese

Detector via match-mode `all` com 3 padrões:

- `(PASSAPORTE|Passport|REPÚBLICA FEDERATIVA DO BRASIL)`.
- Padrão MRZ (Machine Readable Zone) `P<BRA<` no rodapé.
- Número do passaporte: padrão `^[A-Z]{2}\\d{6}$` (Brasil usa BR + 6 dígitos atualmente).

Extrator parseia: número, validade (data), nome completo (mascarar para hash[:8] em log), CPF se presente.

## Implementação proposta

1. Adicionar entrada `passaporte_digital` em `mappings/tipos_documento.yaml`.
2. Criar `src/extractors/passaporte_digital.py`.
3. Registry + fixture sintética + ≥3 amostras reais.
4. PII: nunca log INFO com nome/número; usar hash[:8].
5. Rodar `make conformance-passaporte_digital`.

## Proof-of-work (runtime real)

3 amostras reais (André + Vitória + 1 expirado para edge case): cada uma gera node `documento` com metadata.numero (mascarado), metadata.validade. Aresta `documento_de` opcional (passaporte raramente tem transação direta correlata; é documento de identidade).

## Acceptance criteria

- Entrada YAML + extrator + registry + fixture + ≥6 testes.
- ≥3 amostras 4-way verdes.
- PII nunca em log INFO.
- Smoke 10/10, lint OK.
- Alerta de validade próxima (≤6 meses) registrado em metadata.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` em amostra real antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-passaporte_digital` exit 0 com ≥3 amostras 4-way.
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
