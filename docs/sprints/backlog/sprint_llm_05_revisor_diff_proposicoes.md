# Sprint LLM-05 -- UI no Revisor 4-way para aceitar/rejeitar proposições LLM

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 2
**Esforço estimado**: 5h
**Depende de**: LLM-02, LLM-03
**Fecha itens da auditoria**: nenhum

## Problema

Proposições em mappings/proposicoes/ ficam sem revisão visual.

## Hipótese

Adicionar aba 'Proposições' no Revisor que lista cada YAML pendente com botão aceitar/rejeitar/modificar. Aceitar move para mappings/ definitivo + commit. Rejeitar move para mappings/proposicoes/_rejeitadas/ com SHA registrado.

## Implementação proposta

src/dashboard/paginas/proposicoes.py + integração com sync_rico para commit automático ao aceitar.

## Proof-of-work (runtime real)

Subir proposição manual → aba mostra → aceitar → mappings/categorias.yaml atualizado + git diff visível.

## Acceptance criteria

- Aba live no Revisor.
- Fluxo aceitar/rejeitar/modificar funcional.
- Commit automático ao aceitar (com confirmação humana).

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
