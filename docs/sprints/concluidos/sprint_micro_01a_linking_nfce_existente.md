---
concluida_em: 2026-04-30
escopo_refinado_por: padrão (k) BRIEF -- hipótese empírica refutou parte da spec
entrega_real: src/graph/drill_down.py (resolver de drill-down 2 saltos)
seguimento: sprint_micro_01a_followup_nfce_reais.md (validar com NFCe reais)
---

# Sprint MICRO-01a -- Linking transação→nfce→item para NFCe já no grafo

> **Nota de fechamento (2026-04-30)**: investigação empírica refutou parte
> da hipótese original. `src/graph/linking.py` (Sprint 48) JÁ cobre
> `nfce_modelo_65` em `mappings/linking_config.yaml`. Os 2 NFCe atuais
> são placeholders PoC sem transação correspondente, por isso 0 arestas
> `documento_de` para eles. **O gap real entregue**: `src/graph/drill_down.py`
> com resolver `obter_items_da_transacao` + `obter_documentos_da_transacao`
> + `contar_drill_down`. Quando NFCe reais aparecerem,
> `linking.py` cria as arestas automaticamente; a sprint follow-up
> `MICRO-01a-FOLLOWUP-NFCE-REAIS` valida o ciclo completo.

**Origem**: ramificação de `sprint_micro_01_linking_micro_runtime.md` por decisão do dono em 2026-04-29 (Fase 0 do plano `glittery-munching-russell`, decisão D1).
**Prioridade**: P1
**Onda**: 4
**Esforço estimado**: 3h
**Depende de**: nenhuma (usa material já no grafo)
**Fecha itens da auditoria**: backbone do cruzamento micro

## Problema

Drill-down "paguei R$ X num NFCe → ver os 3 itens granulares" não funciona porque arestas `transacao→nfce` e `nfce→item` não existem no grafo, mesmo quando o NFCe está catalogado e os items extraídos. Auditoria de 2026-04-29 confirma:

- 2 nodes `documento` tipo `nfce_modelo_65` no grafo.
- 33 arestas `contem_item` partindo desses 2 nodes para 41 nodes `item` granulares (Atacadão CNPJ 00.776.574/0160-79: CONTROLE P55 R$ 449,99, BASE CARREGAMENTO R$ 179,99, etc.).
- 0 arestas `transacao→nfce` ou variantes -- o backbone está faltando.
- Adicional: hoje 0/2 NFCe têm aresta `documento_de` apontando para transação, então mesmo o linking transação↔documento padrão não cobre essas NFCe.

## Hipótese

Para os NFCe já no grafo, o linking transação→nfce pode ser estabelecido via duas rotas complementares:

1. **Rota direta**: se aresta `documento_de` existe entre transacao e nfce_modelo_65, propagar para criar `transacao_documento` semântica (nome canônico a confirmar com supervisor) ligando a transação aos items via composição de arestas `contem_item`.
2. **Rota CNPJ-data-valor**: para NFCe órfão (sem `documento_de`), tentar match dedicado via CNPJ do emissor + data do cupom + valor total dentro de janela 1d e diff 1% (mais apertado que linking genérico, pois NFCe tem total fiscal exato).

Após `documento_de` existir (rota 1 ou 2), criar resolver de drill-down: dada transação T, walk até NFCe via `documento_de`, walk até items via `contem_item`.

## Implementação proposta

1. **Path canônico decidido por grep**: rodar `grep -rn "linking" src/graph/linking.py src/transform/ | head` antes de criar módulo. Se `src/graph/linking.py` é canônico (provável), criar `src/graph/linking_micro.py` e abrir sprint paralela `sprint_fix_micro_01_path.md` documentando a escolha. Senão, manter `src/transform/linking_micro.py` literal da spec original. Em qualquer caso, registrar evidência grep no commit body.
2. Implementar função `linkar_transacao_a_nfce(grafo)` que percorre os 2 NFCe e cria aresta nova `transacao_documento` (ou nome canônico) onde possível.
3. Implementar resolver `obter_items_da_transacao(transacao_id)` para drill-down.
4. Adicionar 8 testes (fixtures sintéticos + 1 amostra real).
5. Rodar pipeline em ambiente isolado e conferir crescimento das arestas.

## Proof-of-work (runtime real)

Para a transação Atacadão CNPJ 00.776.574/0160-79 de 2026-04-19, o resolver retorna ≥3 items granulares (CONTROLE P55 R$ 449,99, BASE CARREGAMENTO R$ 179,99, KIT TIGELAS R$ 64,99) acessíveis via grafo.

Métrica de crescimento esperada:
- Arestas `documento_de` para nfce_modelo_65: 0 → 2.
- Aresta nova `transacao_documento` (ou canônico): 0 → 2.
- Cobertura de drill-down: 0 → 2 transações com items granulares.

## Acceptance criteria

- Módulo criado em path canônico (decidido por grep).
- ≥8 testes; fixture sintética + 1 amostra real.
- 2 NFCe vinculados a transação via grafo.
- Resolver `obter_items_da_transacao` funcional.
- Smoke 10/10, lint OK, baseline pytest crescida.
- Commit body cita evidência grep que justificou path.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese validada com query SQL antes de codar (NFCe + arestas existentes).
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` quando aplicável (não -- não é extrator novo).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.

## Notas

- Esta sprint **NÃO** depende de DOC-02 ou DOC-19. Ela usa material já no grafo.
- Sprint irmã `sprint_micro_01b_linking_mercado_holerite.md` cobre amplificação para mercado físico + holerites, depende de DOC-02 + DOC-19 fecharem antes.
- Spec pai histórica: `sprint_micro_01_linking_micro_runtime.md` (mantida em backlog/ como referência).
