# Sprint ANTI-MIGUE-10 -- Documentar bootstrap em install.sh + docs/BOOTSTRAP.md

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P3
**Onda**: 1
**Esforço estimado**: 1h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 41 da auditoria honesta

## Problema

Hooks git são locais; em fresh clone, dependem de install.sh. Sem documentação clara, novo usuário/sessão pode pular setup e quebrar validações.

## Hipótese

Criar docs/BOOTSTRAP.md com passos numerados: clone → install.sh → verificar hooks → rodar make smoke → rodar pytest. install.sh já deve copiar hooks para .git/hooks/.

## Implementação proposta

1. Auditar install.sh (verificar se já copia hooks).
2. Se não, adicionar bloco de cópia idempotente.
3. Criar docs/BOOTSTRAP.md com checklist.

## Proof-of-work (runtime real)

Em VM/clone limpo: rodar install.sh + git commit malformado → hook bloqueia.

## Acceptance criteria

- install.sh copia hooks idempotentemente.
- docs/BOOTSTRAP.md publicado.
- CLAUDE.md §estrutura aponta para BOOTSTRAP.md.

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
